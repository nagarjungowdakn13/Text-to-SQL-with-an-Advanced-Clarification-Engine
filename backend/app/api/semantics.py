from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.semantic.engine import SemanticLayerEngine
from app.api.auth import get_current_user, get_current_admin
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/semantics", tags=["semantics"])

class SemanticMappingCreate(BaseModel):
    term: str
    category: str  # 'metric', 'dimension', 'business_rule'
    sql_fragment: str
    definition: str = ""

@router.get("")
def list_semantic_terms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all defined business semantic mappings."""
    return SemanticLayerEngine.get_all_mappings(db)

@router.post("")
def create_or_update_term(
    request: SemanticMappingCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new business semantic mapping or update an existing one (Admin only)."""
    if request.category not in ["metric", "dimension", "business_rule"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category must be one of: 'metric', 'dimension', 'business_rule'."
        )
    mapping = SemanticLayerEngine.add_or_update_mapping(
        db=db,
        term=request.term.strip().lower(),
        category=request.category,
        sql_fragment=request.sql_fragment.strip(),
        definition=request.definition.strip()
    )
    return {
        "status": "success",
        "message": f"Semantic mapping for '{mapping.term}' saved.",
        "data": mapping
    }

@router.delete("/{term_id}")
def delete_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a business semantic mapping by ID (Admin only)."""
    success = SemanticLayerEngine.delete_mapping(db, term_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semantic mapping not found."
        )
    return {
        "status": "success",
        "message": f"Semantic mapping with ID {term_id} deleted."
    }
