from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid
import time

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.api.auth import get_current_user
from app.models.user import User
from app.models.history import QueryHistory, ClarificationSession
from app.models.audit import AuditLog

# Import services
from app.services.llm.factory import get_llm_provider
from app.services.schema.cache import SchemaCache
from app.services.schema.graph import SchemaGraph
from app.services.semantic.engine import SemanticLayerEngine
from app.services.clarification.manager import ClarificationManager
from app.services.sql.generator import SQLGenerator
from app.services.sql.validator import SQLValidator
from app.services.sql.repair import SQLRepairEngine
from app.services.executor.postgres import DatabaseExecutor
from app.services.analyzer.summarizer import ResultSummarizer

router = APIRouter(prefix="/query", tags=["query"])

# Singletons / Service Instances
schema_cache = SchemaCache(settings.EXECUTION_DB_READONLY_URL)
db_executor = DatabaseExecutor(settings.EXECUTION_DB_READONLY_URL)

class AnalyzeRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class RespondRequest(BaseModel):
    session_id: str
    answer: str
    provider: Optional[str] = None
    model: Optional[str] = None

def _log_audit_step(db: Session, request_id: str, session_id: str, step: str, details: Dict[str, Any]):
    """Helper to log internal steps to AuditLog table."""
    audit = AuditLog(
        request_id=request_id,
        session_id=session_id,
        step=step,
        details=details
    )
    db.add(audit)
    db.commit()

def _execute_and_summarize_plan(
    db: Session,
    request_id: str,
    session: ClarificationSession,
    llm_provider: Any,
    schema_subset: Any,
    semantics_text: str,
    user_id: Optional[int]
) -> Dict[str, Any]:
    """
    Handles SQL Generation, Validation, Repair Loop, Safe Execution,
    and Result Summarization. Separated to share code between endpoints.
    """
    sql_generator = SQLGenerator(llm_provider)
    sql_validator = SQLValidator()
    sql_repair = SQLRepairEngine(llm_provider)
    result_summarizer = ResultSummarizer(llm_provider)

    # 1. SQL Generation
    start_gen = time.perf_counter()
    plan = sql_generator.generate_plan(
        question=session.current_question,
        schema=schema_subset,
        semantic_terms_text=semantics_text
    )
    gen_time_ms = (time.perf_counter() - start_gen) * 1000
    
    _log_audit_step(
        db=db,
        request_id=request_id,
        session_id=session.session_id,
        step="sql_generation",
        details={
            "resolved_question": session.current_question,
            "generated_sql": plan.sql,
            "latency_ms": gen_time_ms,
            "confidence": plan.confidence,
            "assumptions": plan.assumptions
        }
    )

    # 2. SQL Validation
    is_valid, validation_errors = sql_validator.validate(plan.sql, schema_subset)
    
    # 3. SQL Repair Loop (if validation fails)
    if not is_valid:
        logger.warning(f"Initial SQL validation failed with errors: {validation_errors}. Triggering repair loop.")
        _log_audit_step(
            db=db,
            request_id=request_id,
            session_id=session.session_id,
            step="sql_validation_failure",
            details={"errors": validation_errors, "invalid_sql": plan.sql}
        )
        
        plan = sql_repair.repair_plan(
            question=session.current_question,
            invalid_plan=plan,
            errors=validation_errors,
            schema=schema_subset,
            semantic_terms_text=semantics_text
        )
        # Revalidate repaired SQL
        is_valid, validation_errors = sql_validator.validate(plan.sql, schema_subset)
        _log_audit_step(
            db=db,
            request_id=request_id,
            session_id=session.session_id,
            step="sql_repair_attempted",
            details={"errors": validation_errors, "repaired_sql": plan.sql, "is_valid": is_valid}
        )

    # If still invalid after repair, halt execution and raise error
    if not is_valid:
        error_msg = f"SQL Safety Validation failed after repair: {', '.join(validation_errors)}"
        _save_failed_query(db, session, plan.sql, error_msg, user_id)
        return {
            "status": "failed",
            "session_id": session.session_id,
            "sql": plan.sql,
            "error": error_msg,
            "assumptions": plan.assumptions,
            "confidence": plan.confidence
        }

    # 4. SQL Execution
    columns, rows, exec_time_ms, exec_error = db_executor.execute_query(plan.sql)
    
    # 5. Execution Error Repair Loop (if database throws exception at runtime)
    if exec_error:
        logger.warning(f"Database execution failed: {exec_error}. Triggering repair loop.")
        _log_audit_step(
            db=db,
            request_id=request_id,
            session_id=session.session_id,
            step="sql_execution_failure",
            details={"error": exec_error, "failed_sql": plan.sql}
        )
        
        plan = sql_repair.repair_plan(
            question=session.current_question,
            invalid_plan=plan,
            errors=[f"Database Execution Exception: {exec_error}"],
            schema=schema_subset,
            semantic_terms_text=semantics_text
        )
        # Re-validate
        is_valid, validation_errors = sql_validator.validate(plan.sql, schema_subset)
        if not is_valid:
            error_msg = f"Repaired SQL failed security validations: {', '.join(validation_errors)}"
            _save_failed_query(db, session, plan.sql, error_msg, user_id)
            return {"status": "failed", "session_id": session.session_id, "sql": plan.sql, "error": error_msg}
            
        # Re-execute
        columns, rows, exec_time_ms, exec_error = db_executor.execute_query(plan.sql)
        _log_audit_step(
            db=db,
            request_id=request_id,
            session_id=session.session_id,
            step="sql_execution_repair_attempted",
            details={"repaired_sql": plan.sql, "exec_error": exec_error}
        )

    if exec_error:
        _save_failed_query(db, session, plan.sql, exec_error, user_id)
        return {
            "status": "failed",
            "session_id": session.session_id,
            "sql": plan.sql,
            "error": f"Database execution error: {exec_error}",
            "assumptions": plan.assumptions,
            "confidence": plan.confidence
        }

    # 6. SQL Explain Diagnostics
    explain_plan, explain_error = db_executor.explain_query(plan.sql)

    # 7. Summarize Results (LLM text explanation)
    start_sum = time.perf_counter()
    summary = result_summarizer.summarize_results(
        question=session.current_question,
        sql=plan.sql,
        columns=columns,
        rows=rows
    )
    sum_time_ms = (time.perf_counter() - start_sum) * 1000
    
    _log_audit_step(
        db=db,
        request_id=request_id,
        session_id=session.session_id,
        step="result_analysis",
        details={
            "summary": summary.summary,
            "insights": summary.insights,
            "anomalies": summary.anomalies,
            "latency_ms": sum_time_ms
        }
    )

    # 8. Save successful QueryHistory
    query_history = QueryHistory(
        user_id=user_id,
        session_id=session.session_id,
        user_question=session.original_question,
        resolved_question=session.current_question,
        generated_sql=plan.sql,
        execution_status="success",
        row_count=len(rows),
        execution_time_ms=exec_time_ms,
        explanation=summary.summary,
        assumptions=plan.assumptions,
        confidence=plan.confidence,
        audit_logs={
            "generation_time_ms": gen_time_ms,
            "explain_plan": explain_plan,
            "insights": summary.insights,
            "anomalies": summary.anomalies
        }
    )
    db.add(query_history)
    db.commit()

    return {
        "status": "success",
        "session_id": session.session_id,
        "question": session.original_question,
        "resolved_question": session.current_question,
        "sql": plan.sql,
        "columns": columns,
        "rows": rows,
        "execution_time_ms": exec_time_ms,
        "explanation": summary.summary,
        "insights": summary.insights,
        "anomalies": summary.anomalies,
        "assumptions": plan.assumptions,
        "confidence": plan.confidence
    }

def _save_failed_query(db: Session, session: ClarificationSession, sql: str, error: str, user_id: Optional[int]):
    """Helper to record query execution failure details in history."""
    qh = QueryHistory(
        user_id=user_id,
        session_id=session.session_id,
        user_question=session.original_question,
        resolved_question=session.current_question,
        generated_sql=sql,
        execution_status="failed",
        execution_error=error,
        row_count=0,
        execution_time_ms=0.0,
        explanation="Execution failed due to safety, syntax, or runtime errors.",
        assumptions=[],
        confidence=0.0
    )
    db.add(qh)
    db.commit()

@router.post("/analyze")
def analyze_query(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts natural-language queries, retrieves schema and semantics,
    and runs the ambiguity resolution pipeline.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received query analysis request: '{request.question}' (session: {request.session_id})")

    # 1. Initialize services
    llm_provider = get_llm_provider(request.provider, request.model)
    full_schema = schema_cache.get_schema()
    
    # 2. Get relevant schema subset using Graph Breadth-First-Search (BFS)
    schema_graph = SchemaGraph(full_schema)
    schema_subset = schema_graph.get_relevant_schema_subset(request.question)
    
    # 3. Retrieve business semantic glossaries
    semantics_text = SemanticLayerEngine.format_mappings_for_llm(db)

    # 4. Clarification Session Manager
    clarification_manager = ClarificationManager(llm_provider)
    session = clarification_manager.get_or_create_session(
        db=db,
        session_id=request.session_id,
        question=request.question,
        user_id=current_user.id
    )

    _log_audit_step(
        db=db,
        request_id=request_id,
        session_id=session.session_id,
        step="intent_analysis",
        details={
            "question": request.question,
            "seed_tables": list(schema_subset.tables.keys()),
            "semantics_loaded": len(SemanticLayerEngine.get_all_mappings(db))
        }
    )

    # 5. Process turn for ambiguity analysis
    session, analysis = clarification_manager.process_turn(
        db=db,
        session_id=session.session_id,
        user_answer=None,
        schema=schema_subset,
        semantic_terms_text=semantics_text
    )

    _log_audit_step(
        db=db,
        request_id=request_id,
        session_id=session.session_id,
        step="ambiguity_detection",
        details={
            "is_ambiguous": analysis.is_ambiguous,
            "score": analysis.ambiguity_score,
            "type": analysis.ambiguity_type,
            "safest_assumption": analysis.suggested_safest_assumption,
            "clarification_question": analysis.clarification_question,
            "options": analysis.options
        }
    )

    # 6. Check if clarification is required
    if analysis.is_ambiguous and session.status == "active":
        return {
            "status": "clarifying",
            "session_id": session.session_id,
            "question": session.original_question,
            "clarification_question": analysis.clarification_question,
            "options": analysis.options,
            "ambiguity_score": analysis.ambiguity_score,
            "reasoning": analysis.reasoning
        }

    # 7. No ambiguity (or max rounds exceeded), generate SQL!
    return _execute_and_summarize_plan(
        db=db,
        request_id=request_id,
        session=session,
        llm_provider=llm_provider,
        schema_subset=schema_subset,
        semantics_text=semantics_text,
        user_id=current_user.id
    )

@router.post("/respond")
def respond_clarification(
    request: RespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a user response to a clarification question,
    resolving the ambiguity or executing the query.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received clarification answer for session {request.session_id}: '{request.answer}'")

    # 1. Initialize services
    llm_provider = get_llm_provider(request.provider, request.model)
    full_schema = schema_cache.get_schema()
    
    # Find session to get original question
    session = db.query(ClarificationSession).filter(
        ClarificationSession.session_id == request.session_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clarification session not found."
        )

    # 2. Get relevant schema subset using Graph BFS
    schema_graph = SchemaGraph(full_schema)
    schema_subset = schema_graph.get_relevant_schema_subset(session.original_question)
    
    # 3. Retrieve business semantic glossaries
    semantics_text = SemanticLayerEngine.format_mappings_for_llm(db)

    # 4. Clarification Session Manager
    clarification_manager = ClarificationManager(llm_provider)
    
    # 5. Process turn with user answer
    session, analysis = clarification_manager.process_turn(
        db=db,
        session_id=session.session_id,
        user_answer=request.answer,
        schema=schema_subset,
        semantic_terms_text=semantics_text
    )

    _log_audit_step(
        db=db,
        request_id=request_id,
        session_id=session.session_id,
        step="clarification_answer_processed",
        details={
            "user_answer": request.answer,
            "is_ambiguous": analysis.is_ambiguous,
            "score": analysis.ambiguity_score,
            "safest_assumption": analysis.suggested_safest_assumption,
            "clarification_question": analysis.clarification_question,
            "options": analysis.options
        }
    )

    # 6. Check if clarification is STILL required (or a new ambiguity arose)
    if analysis.is_ambiguous and session.status == "active":
        return {
            "status": "clarifying",
            "session_id": session.session_id,
            "question": session.original_question,
            "clarification_question": analysis.clarification_question,
            "options": analysis.options,
            "ambiguity_score": analysis.ambiguity_score,
            "reasoning": analysis.reasoning
        }

    # 7. Disambiguation resolved (or max rounds exceeded), generate SQL!
    return _execute_and_summarize_plan(
        db=db,
        request_id=request_id,
        session=session,
        llm_provider=llm_provider,
        schema_subset=schema_subset,
        semantics_text=semantics_text,
        user_id=current_user.id
    )
