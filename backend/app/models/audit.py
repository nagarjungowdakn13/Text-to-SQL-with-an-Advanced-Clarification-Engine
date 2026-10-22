from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), index=True, nullable=False)
    session_id = Column(String(100), index=True, nullable=True)
    step = Column(String(100), nullable=False)  # 'intent_analysis', 'ambiguity_detection', 'sql_generation', etc.
    details = Column(JSON, nullable=False)  # Raw logs and execution metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
