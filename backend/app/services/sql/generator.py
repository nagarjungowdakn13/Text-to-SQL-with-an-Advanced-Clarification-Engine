from typing import Optional
from app.services.llm.base import LLMProvider
from app.services.schema.extractor import DatabaseSchemaMetadata
from app.schemas.sql import SQLPlan
from app.core.config import settings
from app.core.logging import logger

class SQLGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def generate_plan(
        self,
        question: str,
        schema: DatabaseSchemaMetadata,
        semantic_terms_text: str = ""
    ) -> SQLPlan:
        """Generate structured SQLPlan for the resolved query."""
        
        # Format schema metadata for prompt
        schema_lines = []
        for table_name, table in schema.tables.items():
            col_lines = []
            for col in table.columns:
                col_type = col.data_type
                col_desc = f" - {col.comment}" if col.comment else ""
                # Add sample values to help the generator map terms correctly
                samples = f" (Samples: {col.sample_values})" if col.sample_values else ""
                col_lines.append(f"  - {col.name} ({col_type}){col_desc}{samples}")
            
            table_desc = f" ({table.comment})" if table.comment else ""
            schema_lines.append(f"Table '{table_name}'{table_desc}:")
            schema_lines.extend(col_lines)
            
            if table.primary_keys:
                schema_lines.append(f"  - Primary Keys: {table.primary_keys}")
            for fk in table.foreign_keys:
                schema_lines.append(f"  - Foreign Key: {fk.constrained_columns} -> {fk.referred_table}({fk.referred_columns})")
        
        schema_text = "\n".join(schema_lines)

        prompt = f"""
You are the SQL Generation Engine for QueryPilot.
Translate the user's clarified natural language query into a structured, executable SQL query for PostgreSQL.

You MUST only query the tables and columns listed in the schema below.
DO NOT invent columns or tables.

Database Schema:
{schema_text}

Business Semantic Terms & Formulas:
{semantic_terms_text or "No terms defined."}

Clarified User Query:
"{question}"

Strict Rules:
1. Generate SELECT statements ONLY. Never generate INSERT, UPDATE, DELETE, or DDL queries.
2. Verify join keys. You must join tables using correct foreign keys (e.g. JOIN orders ON customers.customer_id = orders.customer_id).
3. If user queries require aggregating business terms, substitute them with the defined formulas from the Business Semantic Terms list.
4. Ensure the query returns at most {settings.MAX_EXECUTION_ROWS} records. Append LIMIT if required.
5. In your structured output, explicitly list any business assumptions you had to make.
"""

        system_instruction = (
            "You are a Senior PostgreSQL Database Administrator. Your goal is to write clean, "
            "efficient, and extremely safe SELECT statements based on user requirements. "
            "You always double-check joins, schemas, column names, and respect data types."
        )

        try:
            plan = self.llm_provider.generate_structured(
                prompt=prompt,
                response_model=SQLPlan,
                system_instruction=system_instruction,
                temperature=0.1
            )
            # Enforce server-side max limits on rows
            if plan.limit is None or plan.limit > settings.MAX_EXECUTION_ROWS:
                plan.limit = settings.MAX_EXECUTION_ROWS
                
            logger.info(f"Structured SQL generated successfully. SQL: {plan.sql[:100]}...")
            return plan
        except Exception as e:
            logger.error(f"Error generating SQL plan: {e}")
            raise e
