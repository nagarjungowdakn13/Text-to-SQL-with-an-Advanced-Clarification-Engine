from typing import List, Tuple
from app.services.llm.base import LLMProvider
from app.services.schema.extractor import DatabaseSchemaMetadata
from app.services.sql.validator import SQLValidator
from app.schemas.sql import SQLPlan
from app.core.config import settings
from app.core.logging import logger

class SQLRepairEngine:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.validator = SQLValidator()

    def repair_plan(
        self,
        question: str,
        invalid_plan: SQLPlan,
        errors: List[str],
        schema: DatabaseSchemaMetadata,
        semantic_terms_text: str = ""
    ) -> SQLPlan:
        """
        Attempts to repair an invalid SQLPlan by sending the error feedback back to the LLM.
        Loops up to settings.MAX_REPAIR_ATTEMPTS.
        """
        attempts = 0
        current_plan = invalid_plan
        current_errors = errors

        # Format schema metadata for prompt
        schema_lines = []
        for table_name, table in schema.tables.items():
            col_lines = []
            for col in table.columns:
                col_lines.append(f"  - {col.name} ({col.data_type})")
            schema_lines.append(f"Table '{table_name}':")
            schema_lines.extend(col_lines)
            if table.primary_keys:
                schema_lines.append(f"  - Primary Keys: {table.primary_keys}")
            for fk in table.foreign_keys:
                schema_lines.append(f"  - Foreign Key: {fk.constrained_columns} -> {fk.referred_table}({fk.referred_columns})")
        schema_text = "\n".join(schema_lines)

        while attempts < settings.MAX_REPAIR_ATTEMPTS:
            attempts += 1
            logger.info(f"SQL repair attempt {attempts}/{settings.MAX_REPAIR_ATTEMPTS} for question: '{question}'")

            prompt = f"""
You are the SQL Repair Engine for QueryPilot.
A previously generated SQL query failed validation or execution.
Your task is to fix the SQL query and provide a valid, safe SQLPlan.

Original User Query:
"{question}"

Database Schema:
{schema_text}

Business Semantic Mappings:
{semantic_terms_text or "No terms defined."}

Previously Generated SQL (FAILED):
```sql
{current_plan.sql}
```

Validation / Execution Errors Encountered:
{chr(10).join([f"- {err}" for err in current_errors])}

Strict Repair Instructions:
1. Correct all listed errors. Ensure column names, join tables, and functions are correct.
2. The generated query MUST be a SELECT query.
3. Validate that you are only using table and column names specified in the schema.
4. Ensure no Cartesian products or cross joins occur.
5. Limit the results returned to at most {settings.MAX_EXECUTION_ROWS} records.
"""

            system_instruction = (
                "You are an expert SQL debugger. Your job is to analyze database execution errors, "
                "syntactic anomalies, and schema violations, and rewrite clean, optimized, and compliant PostgreSQL queries."
            )

            try:
                # Generate repaired plan
                repaired_plan = self.llm_provider.generate_structured(
                    prompt=prompt,
                    response_model=SQLPlan,
                    system_instruction=system_instruction,
                    temperature=0.1
                )
                
                # Enforce server-side max limits on rows
                if repaired_plan.limit is None or repaired_plan.limit > settings.MAX_EXECUTION_ROWS:
                    repaired_plan.limit = settings.MAX_EXECUTION_ROWS

                # Validate repaired plan
                is_valid, validation_errors = self.validator.validate(repaired_plan.sql, schema)
                
                if is_valid:
                    logger.info(f"SQL repaired successfully on attempt {attempts}!")
                    return repaired_plan
                
                # If still invalid, update loop variables and try again
                current_plan = repaired_plan
                current_errors = validation_errors
                
            except Exception as e:
                logger.warning(f"Error during repair attempt {attempts}: {e}")
                current_errors = [f"Repair loop exception: {str(e)}"]

        logger.error(f"SQL repair failed after {settings.MAX_REPAIR_ATTEMPTS} attempts.")
        # Return the last plan generated, which will eventually fail execution with errors.
        return current_plan
