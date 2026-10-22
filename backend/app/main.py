from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api import auth, query, schema, semantics, history, admin
from app.setup_sample_db import setup_app_database, setup_execution_database
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DBs are created and seeded
    logger.info("Initializing databases on startup...")
    try:
        setup_app_database()
        setup_execution_database()
        logger.info("Database initialization successful.")
    except Exception as e:
        logger.critical(f"Failed to initialize databases on startup: {e}")
    yield
    # Shutdown: Add any cleanup tasks here if needed
    logger.info("Shutting down QueryPilot API server.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QueryPilot — Intelligent Text-to-SQL Platform with Ambiguity Resolution",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(schema.router, prefix="/api")
app.include_router(semantics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

@app.get("/health")
def health_check():
    """Health check endpoint for Docker orchestration."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENV
    }
