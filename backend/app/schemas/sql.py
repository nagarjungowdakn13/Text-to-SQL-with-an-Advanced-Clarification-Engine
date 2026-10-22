from typing import List, Optional
from pydantic import BaseModel, Field

class SQLPlan(BaseModel):
    intent: str = Field(
        ..., 
        description="Detailed description of what the query aims to retrieve."
    )
    tables: List[str] = Field(
        default_factory=list, 
        description="The exact list of table names queried."
    )
    columns: List[str] = Field(
        default_factory=list, 
        description="The columns and computed metrics selected in the projection."
    )
    filters: List[str] = Field(
        default_factory=list, 
        description="Any filter conditions applied in the WHERE clause."
    )
    joins: List[str] = Field(
        default_factory=list, 
        description="Explicit JOIN conditions used (e.g. 'orders.customer_id = customers.customer_id')."
    )
    aggregations: List[str] = Field(
        default_factory=list, 
        description="Group by aggregations performed (e.g., 'SUM(orders.total_amount)')."
    )
    order_by: List[str] = Field(
        default_factory=list, 
        description="Columns and directions specified for sorting (e.g., 'revenue DESC')."
    )
    limit: Optional[int] = Field(
        default=500, 
        description="Row restriction limit applied. Must be less than or equal to settings.MAX_EXECUTION_ROWS."
    )
    sql: str = Field(
        ..., 
        description="The executable, syntactically correct PostgreSQL SELECT query."
    )
    assumptions: List[str] = Field(
        default_factory=list, 
        description="Explicit list of any assumptions made about definitions, filters, or missing data ranges."
    )
    confidence: float = Field(
        ..., 
        description="Value from 0.0 to 1.0 indicating model confidence in the generated SQL plan."
    )
