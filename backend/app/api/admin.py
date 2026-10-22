from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.api.auth import get_current_admin, get_current_user
from app.models.user import User
from app.core.config import settings
from pydantic import BaseModel, Field
from app.core.logging import logger
from pathlib import Path
import json

router = APIRouter(prefix="/admin", tags=["admin"])

class SettingsUpdate(BaseModel):
    default_llm_provider: str = Field(..., description="Default LLM Provider (openai, gemini, anthropic, mock)")
    default_llm_model: str = Field(..., description="Default model name")
    ambiguity_threshold: float = Field(..., ge=0.0, le=1.0, description="Ambiguity detection threshold")
    max_clarification_rounds: int = Field(..., ge=0, le=5, description="Max conversation clarification rounds")
    max_repair_attempts: int = Field(..., ge=0, le=5, description="Max SQL self-repair attempts")
    query_timeout_seconds: int = Field(..., ge=1, le=60, description="SQL Statement Timeout in seconds")
    max_execution_rows: int = Field(..., ge=1, le=1000, description="Max query rows return limit")

@router.get("/settings")
def get_settings(current_user: User = Depends(get_current_user)):
    """Retrieve current system configuration settings."""
    return {
        "default_llm_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_llm_model": settings.DEFAULT_LLM_MODEL,
        "ambiguity_threshold": settings.AMBIGUITY_THRESHOLD,
        "max_clarification_rounds": settings.MAX_CLARIFICATION_ROUNDS,
        "max_repair_attempts": settings.MAX_REPAIR_ATTEMPTS,
        "query_timeout_seconds": settings.QUERY_TIMEOUT_SECONDS,
        "max_execution_rows": settings.MAX_EXECUTION_ROWS
    }

@router.post("/settings")
def update_settings(
    request: SettingsUpdate,
    current_admin: User = Depends(get_current_admin)
):
    """Dynamically update system configuration settings at runtime (Admin only)."""
    provider = request.default_llm_provider.lower()
    if provider not in ["openai", "gemini", "anthropic", "mock"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be one of: 'openai', 'gemini', 'anthropic', 'mock'."
        )

    settings.DEFAULT_LLM_PROVIDER = provider
    settings.DEFAULT_LLM_MODEL = request.default_llm_model
    settings.AMBIGUITY_THRESHOLD = request.ambiguity_threshold
    settings.MAX_CLARIFICATION_ROUNDS = request.max_clarification_rounds
    settings.MAX_REPAIR_ATTEMPTS = request.max_repair_attempts
    settings.QUERY_TIMEOUT_SECONDS = request.query_timeout_seconds
    settings.MAX_EXECUTION_ROWS = request.max_execution_rows

    logger.info(f"System settings updated dynamically by admin {current_admin.email}")
    
    return {
        "status": "success",
        "message": "Configuration settings updated successfully.",
        "settings": {
            "default_llm_provider": settings.DEFAULT_LLM_PROVIDER,
            "default_llm_model": settings.DEFAULT_LLM_MODEL,
            "ambiguity_threshold": settings.AMBIGUITY_THRESHOLD,
            "max_clarification_rounds": settings.MAX_CLARIFICATION_ROUNDS,
            "max_repair_attempts": settings.MAX_REPAIR_ATTEMPTS,
            "query_timeout_seconds": settings.QUERY_TIMEOUT_SECONDS,
            "max_execution_rows": settings.MAX_EXECUTION_ROWS
        }
    }

# ==========================================
# EVALUATION TRIGGER ENDPOINTS
# ==========================================

def run_eval_bg():
    """Background task to run evaluate.py and write outputs."""
    try:
        logger.info("Background evaluation runner started.")
        from evaluate import EvaluationRunner
        
        # Execute benchmark
        runner = EvaluationRunner(settings.DEFAULT_LLM_PROVIDER, settings.DEFAULT_LLM_MODEL)
        results = runner.run_evaluations()
        
        # Save output paths
        reports_dir = Path(__file__).resolve().parents[3] / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        json_path = reports_dir / "evaluation_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        html_path = reports_dir / "evaluation_report.html"
        runner.generate_html_report(results, str(html_path))
        logger.info("Background evaluation runner complete. Reports saved.")
    except Exception as e:
        logger.error(f"Error in background evaluation execution: {e}")

@router.get("/evaluate")
def get_evaluation_report(current_user: User = Depends(get_current_user)):
    """Fetch the latest evaluation results from cached json files."""
    json_path = Path(__file__).resolve().parents[3] / "reports" / "evaluation_report.json"
    if not json_path.exists():
        # Fallback empty report
        return {
            "status": "no_report",
            "message": "No evaluation run report has been generated yet."
        }
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to read evaluation report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read evaluation report: {str(e)}"
        )

@router.post("/evaluate")
def run_evaluation_suite(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin)
):
    """Triggers the evaluation CLI script in the background (Admin only)."""
    background_tasks.add_task(run_eval_bg)
    return {
        "status": "success",
        "message": "Evaluation runner started in the background. Check logs or refresh report dashboard shortly."
    }
