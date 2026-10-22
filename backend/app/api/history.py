from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.history import QueryHistory
from app.models.audit import AuditLog
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/history", tags=["history"])

@router.get("")
def get_query_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve list of all previous natural-language query conversions and executions."""
    queries = db.query(QueryHistory).order_by(QueryHistory.created_at.desc()).all()
    return queries

@router.get("/{query_id}")
def get_query_details(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of a specific query history item."""
    query = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query history item not found."
        )
    return query

@router.get("/{session_id}/audit")
def get_query_audit_logs(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed step-by-step reasoning audit logs for a specific query session."""
    logs = db.query(AuditLog).filter(
        AuditLog.session_id == session_id
    ).order_by(AuditLog.created_at.ascii if hasattr(AuditLog.created_at, "ascii") else AuditLog.created_at.asc()).all()
    return logs
