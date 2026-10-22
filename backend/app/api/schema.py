from fastapi import APIRouter, Depends
from app.services.schema.cache import SchemaCache
from app.core.config import settings
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/schema", tags=["schema"])

# Initialize cache with the target read-only database URL
schema_cache = SchemaCache(settings.EXECUTION_DB_READONLY_URL)

@router.get("/explorer")
def get_schema_explorer(current_user: User = Depends(get_current_user)):
    """Retrieve the cached database schema metadata."""
    schema = schema_cache.get_schema()
    return schema

@router.post("/refresh")
def refresh_schema(current_user: User = Depends(get_current_user)):
    """Force re-extract the schema from the database, clearing the caches."""
    schema = schema_cache.refresh_schema()
    return {
        "status": "success",
        "message": "Database schema cached metadata refreshed successfully.",
        "schema": schema
    }
