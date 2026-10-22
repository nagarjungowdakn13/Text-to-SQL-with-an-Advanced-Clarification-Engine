from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), index=True, nullable=False)
    user_question = Column(Text, nullable=False)
    resolved_question = Column(Text, nullable=True)
    generated_sql = Column(Text, nullable=True)
    execution_status = Column(String(50), nullable=False)  # 'success', 'failed', 'clarifying'
    execution_error = Column(Text, nullable=True)
    row_count = Column(Integer, default=0)
    execution_time_ms = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    assumptions = Column(JSON, nullable=True)  # List of assumptions made
    confidence = Column(Float, default=1.0)
    audit_logs = Column(JSON, nullable=True)  # Detailed internal logs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="queries")

class ClarificationSession(Base):
    __tablename__ = "clarification_sessions"

    session_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    original_question = Column(Text, nullable=False)
    current_question = Column(Text, nullable=False)
    ambiguity_score = Column(Float, nullable=False)
    rounds = Column(Integer, default=0)
    clarification_history = Column(JSON, nullable=True)  # List of {question, answer}
    options = Column(JSON, nullable=True)  # List of choice strings
    safest_assumption = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # 'active', 'resolved', 'max_rounds_reached', 'expired'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", backref="clarification_sessions")
