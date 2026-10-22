from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class SemanticMapping(Base):
    __tablename__ = "semantic_mappings"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), unique=True, index=True, nullable=False)  # e.g., 'revenue', 'active customer'
    category = Column(String(50), nullable=False)  # 'metric', 'dimension', 'business_rule'
    definition = Column(Text, nullable=True)  # Business description
    sql_fragment = Column(Text, nullable=False)  # e.g., 'SUM(quantity * price)' or 'last_login > NOW() - INTERVAL \'30 days\''
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
