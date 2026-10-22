from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.llm.base import LLMProvider
from app.services.schema.extractor import DatabaseSchemaMetadata
from app.core.config import settings
from app.core.logging import logger

class AmbiguityAnalysis(BaseModel):
    is_ambiguous: bool = Field(
        ..., 
        description="True if the question is subjective, missing essential filters, or could map to multiple schema paths."
    )
    ambiguity_score: float = Field(
        ..., 
        description="Confidence score of ambiguity from 0.0 (entirely clear) to 1.0 (highly ambiguous)."
    )
    ambiguity_type: str = Field(
        ..., 
        description="Type of ambiguity. Allowed values: 'metric', 'temporal', 'ranking', 'noun', 'filter', 'join', 'none'."
    )
    clarification_question: str = Field(
        ..., 
        description="Concise, contextual multiple-choice question to ask the user. Empty if is_ambiguous is False."
    )
    options: List[str] = Field(
        default_factory=list, 
        description="Numbered or concise options representing different interpretations (e.g. ['Total Revenue', 'Order Count'])."
    )
    suggested_safest_assumption: str = Field(
        ..., 
        description="Safest assumption to make if we proceed without clarification (e.g. 'assuming sales means gross revenue')."
    )
    reasoning: str = Field(
        ..., 
        description="Internal chain-of-thought explaining the ambiguity or why the query is clear."
    )

class AmbiguityDetector:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def analyze_question(
        self, 
        question: str, 
        schema: DatabaseSchemaMetadata,
        semantic_terms_text: str = ""
    ) -> AmbiguityAnalysis:
        """Analyze user question against schema and semantic layer to detect ambiguity."""
        
        # Format schema metadata for the LLM
        schema_lines = []
        for table_name, table in schema.tables.items():
            col_lines = []
            for col in table.columns:
                col_type = col.data_type
                col_desc = f" - {col.comment}" if col.comment else ""
                col_lines.append(f"  - {col.name} ({col_type}){col_desc}")
            
            table_desc = f" ({table.comment})" if table.comment else ""
            schema_lines.append(f"Table '{table_name}'{table_desc}:")
            schema_lines.extend(col_lines)
            
            # Primary & Foreign keys
            if table.primary_keys:
                schema_lines.append(f"  - Primary Keys: {table.primary_keys}")
            for fk in table.foreign_keys:
                schema_lines.append(f"  - Foreign Key: {fk.constrained_columns} -> {fk.referred_table}({fk.referred_columns})")
        
        schema_text = "\n".join(schema_lines)

        prompt = f"""
You are the Ambiguity Detection Engine for QueryPilot.
Evaluate the user's natural language question against the database schema and business semantic terms below.

Your goal is to detect if the question is underspecified, subjective, or ambiguous.
Common ambiguity categories:
1. 'metric' (e.g., 'best customer' - by revenue, profit, or order count? 'sales performance' - revenue or volume?)
2. 'temporal' (e.g., 'active users' - active in the last 7 days? 30 days? 1 year? 'sales' - this year or all time?)
3. 'ranking' (e.g., 'top products' - by sales, price, or ratings?)
4. 'noun' (e.g., 'region' - state, country, or sales territory?)
5. 'filter' (e.g., 'users' - all users or only active ones?)
6. 'join' (e.g., multiple join paths exist between tables)

Database Schema:
{schema_text}

Business Semantic Terms & Mappings:
{semantic_terms_text or "No terms defined."}

User Question:
"{question}"

Task:
Determine if the query needs clarification. If the ambiguity_score is higher than {settings.AMBIGUITY_THRESHOLD}, mark is_ambiguous = true.
Provide a concise, helpful clarification question, offering 2-4 concrete choices.
Identify a safe, standard default assumption (e.g., 'highest revenue' for 'best customer') to proceed with if max rounds are reached.
"""

        system_instruction = (
            "You are an expert databases systems analyst specializing in disambiguating user queries. "
            "You analyze schemas, data columns, and key relations to identify subjective business terms."
        )

        try:
            analysis = self.llm_provider.generate_structured(
                prompt=prompt,
                response_model=AmbiguityAnalysis,
                system_instruction=system_instruction,
                temperature=0.1
            )
            logger.info(f"Ambiguity analysis complete: is_ambiguous={analysis.is_ambiguous}, score={analysis.ambiguity_score}")
            return analysis
        except Exception as e:
            logger.error(f"Error executing ambiguity analysis: {e}")
            # Fallback safe analysis
            return AmbiguityAnalysis(
                is_ambiguous=False,
                ambiguity_score=0.0,
                ambiguity_type="none",
                clarification_question="",
                options=[],
                suggested_safest_assumption="Execute direct match",
                reasoning=f"Error in LLM analysis, default to clear path: {e}"
            )
