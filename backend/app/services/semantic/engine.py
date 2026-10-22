from typing import List
from sqlalchemy.orm import Session
from app.models.semantic import SemanticMapping
from app.core.logging import logger

class SemanticLayerEngine:
    @staticmethod
    def get_all_mappings(db: Session) -> List[SemanticMapping]:
        """Fetch all registered semantic mappings from the database."""
        return db.query(SemanticMapping).all()

    @staticmethod
    def format_mappings_for_llm(db: Session) -> str:
        """Format semantic mappings into a clear text description for LLM prompts."""
        mappings = SemanticLayerEngine.get_all_mappings(db)
        if not mappings:
            return "No custom business semantic terms are defined."

        formatted_lines = []
        for mapping in mappings:
            formatted_lines.append(
                f"- Term: '{mapping.term}'\n"
                f"  Category: {mapping.category}\n"
                f"  Description: {mapping.definition or 'No description'}\n"
                f"  SQL Formula: {mapping.sql_fragment}"
            )
        
        return "\n".join(formatted_lines)

    @staticmethod
    def add_or_update_mapping(
        db: Session,
        term: str,
        category: str,
        sql_fragment: str,
        definition: str = ""
    ) -> SemanticMapping:
        """Add a new term or update an existing semantic term in the registry."""
        existing = db.query(SemanticMapping).filter(SemanticMapping.term == term).first()
        if existing:
            existing.category = category
            existing.sql_fragment = sql_fragment
            existing.definition = definition
            logger.info(f"Updated semantic mapping for: '{term}'")
        else:
            existing = SemanticMapping(
                term=term,
                category=category,
                sql_fragment=sql_fragment,
                definition=definition
            )
            db.add(existing)
            logger.info(f"Created new semantic mapping for: '{term}'")

        db.commit()
        db.refresh(existing)
        return existing

    @staticmethod
    def delete_mapping(db: Session, term_id: int) -> bool:
        """Delete a mapping by ID."""
        mapping = db.query(SemanticMapping).filter(SemanticMapping.id == term_id).first()
        if mapping:
            db.delete(mapping)
            db.commit()
            logger.info(f"Deleted semantic mapping ID: {term_id}")
            return True
        return False
