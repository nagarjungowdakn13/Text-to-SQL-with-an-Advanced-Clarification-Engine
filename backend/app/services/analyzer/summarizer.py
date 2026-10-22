from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.services.llm.base import LLMProvider
from app.core.logging import logger
import json

class ExecutionExplanation(BaseModel):
    summary: str = Field(
        ..., 
        description="A concise human-readable explanation of what the query returned, referencing exact values. Keep it to 1-3 sentences."
    )
    insights: List[str] = Field(
        default_factory=list, 
        description="Key trends, calculations (e.g. percentages, totals), or findings derived directly from the data."
    )
    anomalies: List[str] = Field(
        default_factory=list, 
        description="Any oddities, missing values, outliers, or unexpected values in the data. Empty list if none."
    )
    confidence_score: float = Field(
        ..., 
        description="Rating from 0.0 to 1.0 indicating how complete/informative the explanation is."
    )

class ResultSummarizer:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def summarize_results(
        self,
        question: str,
        sql: str,
        columns: List[str],
        rows: List[Dict[str, Any]]
    ) -> ExecutionExplanation:
        """
        Analyze database results to write a structured explanation.
        Guarantees exact value representation.
        """
        if not rows:
            return ExecutionExplanation(
                summary="The query executed successfully but returned zero results matching your criteria.",
                insights=[],
                anomalies=[],
                confidence_score=1.0
            )

        # Truncate row listings to avoid hitting token length limits (limit context to first 50 rows)
        sample_rows = rows[:50]
        rows_text = json.dumps(sample_rows, indent=2)

        prompt = f"""
You are the Result Analysis Engine for QueryPilot.
Your task is to analyze the retrieved database records and write a clear, accurate, and concise summary explanation for the user.

User's Original Question:
"{question}"

SQL Query Executed:
```sql
{sql}
```

Retrieved Columns: {columns}
Retrieved Rows (showing first {len(sample_rows)} rows out of {len(rows)} total):
{rows_text}

Strict Hallucination Protection Rules:
1. ONLY refer to values that are explicitly present in the retrieved rows.
2. Never make up numbers, names, regions, dates, or trends that are not directly in the JSON data.
3. If the results do not contain enough information to answer the user's question, state that clearly in the summary.
4. Calculate basic aggregated metrics (e.g., sums, percentages, counts) only if they are simple and mathematically correct based on the dataset.
"""

        system_instruction = (
            "You are a Senior Data Analyst. You write concise, high-integrity executive summaries of database query results. "
            "You never extrapolate or hallucinate, and you present data accurately with exact names, values, and dates."
        )

        try:
            explanation = self.llm_provider.generate_structured(
                prompt=prompt,
                response_model=ExecutionExplanation,
                system_instruction=system_instruction,
                temperature=0.1
            )
            logger.info("Generated result summary successfully.")
            return explanation
        except Exception as e:
            logger.error(f"Error summarizing results: {e}")
            # Fallback explanation
            return ExecutionExplanation(
                summary=f"Query returned {len(rows)} records. Summarization failed due to an internal error.",
                insights=[f"Columns retrieved: {', '.join(columns)}"],
                anomalies=[f"Error: {str(e)}"],
                confidence_score=0.1
            )
