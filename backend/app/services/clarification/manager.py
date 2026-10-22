from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.history import ClarificationSession
from app.services.clarification.detector import AmbiguityDetector, AmbiguityAnalysis
from app.services.schema.extractor import DatabaseSchemaMetadata
from app.services.llm.base import LLMProvider
from app.core.config import settings
from app.core.logging import logger
import uuid

class ClarificationManager:
    def __init__(self, llm_provider: LLMProvider):
        self.detector = AmbiguityDetector(llm_provider)

    def get_or_create_session(
        self,
        db: Session,
        session_id: Optional[str],
        question: str,
        user_id: Optional[int] = None
    ) -> ClarificationSession:
        """Fetch an existing active clarification session or create a new one."""
        if session_id:
            session = db.query(ClarificationSession).filter(
                ClarificationSession.session_id == session_id,
                ClarificationSession.status == "active"
            ).first()
            if session:
                return session

        # Generate a new session ID if not provided or session expired
        new_id = session_id or str(uuid.uuid4())
        session = ClarificationSession(
            session_id=new_id,
            user_id=user_id,
            original_question=question,
            current_question=question,
            ambiguity_score=0.0,
            rounds=0,
            clarification_history=[],
            options=[],
            safest_assumption="",
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created new ClarificationSession: {new_id}")
        return session

    def process_turn(
        self,
        db: Session,
        session_id: str,
        user_answer: Optional[str],
        schema: DatabaseSchemaMetadata,
        semantic_terms_text: str = ""
    ) -> Tuple[ClarificationSession, AmbiguityAnalysis]:
        """
        Process a single clarification turn.
        - Appends answer to history.
        - Formulates the resolved question.
        - Analyzes the resolved question for any remaining ambiguity.
        - Prevents infinite loops using configured limits.
        """
        session = db.query(ClarificationSession).filter(
            ClarificationSession.session_id == session_id
        ).first()

        if not session:
            raise ValueError(f"Clarification session {session_id} not found.")

        if user_answer:
            # Append user answer to history
            history = list(session.clarification_history or [])
            history.append({
                "round": session.rounds + 1,
                "question": session.current_question,
                "options": session.options,
                "answer": user_answer
            })
            session.clarification_history = history
            session.rounds += 1
            
            # Formulate the updated resolved question combining user inputs
            resolved = session.original_question
            clarification_summaries = []
            for h in history:
                clarification_summaries.append(f"{h['question']} Answer: {h['answer']}")
            
            # Build current working question for disambiguation
            session.current_question = f"{session.original_question} (Clarified: {', '.join([h['answer'] for h in history])})"
            db.commit()

        # Run ambiguity detection on the new resolved question
        analysis = self.detector.analyze_question(
            question=session.current_question,
            schema=schema,
            semantic_terms_text=semantic_terms_text
        )

        # Update session with new analysis details
        session.ambiguity_score = analysis.ambiguity_score
        session.options = analysis.options
        session.safest_assumption = analysis.suggested_safest_assumption

        # Check for loop prevention / max rounds limit
        if analysis.is_ambiguous and session.rounds >= settings.MAX_CLARIFICATION_ROUNDS:
            logger.warning(f"Clarification max rounds reached ({session.rounds}/{settings.MAX_CLARIFICATION_ROUNDS}) for session {session_id}. Forcing resolution.")
            session.status = "max_rounds_reached"
            # Modify analysis to proceed with assumption
            analysis.is_ambiguous = False
            session.current_question = f"{session.current_question} (Assuming: {analysis.suggested_safest_assumption})"
        elif not analysis.is_ambiguous:
            session.status = "resolved"
        else:
            session.status = "active"

        db.commit()
        db.refresh(session)
        
        return session, analysis
