import pytest
import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add project directories to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import settings

# Force using SQLite file database paths for testing
settings.DATABASE_URL = "sqlite:///./test_querypilot_app.db"
settings.EXECUTION_DB_ADMIN_URL = "sqlite:///./test_querypilot_execution.db"
settings.EXECUTION_DB_READONLY_URL = "sqlite:///./test_querypilot_execution.db"
settings.DEFAULT_LLM_PROVIDER = "mock"
settings.AMBIGUITY_THRESHOLD = 0.7
settings.MAX_CLARIFICATION_ROUNDS = 2
settings.MAX_REPAIR_ATTEMPTS = 3

from app.main import app
from app.core.database import Base, get_db
from app.setup_sample_db import setup_app_database, setup_execution_database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB engines
app_engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initializes SQLite databases once for the entire test session."""
    # Ensure any residual files are cleared
    for file in ["test_querypilot_app.db", "test_querypilot_execution.db"]:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception:
                pass

    # Build application tables and seed default users
    Base.metadata.create_all(bind=app_engine)
    setup_app_database()
    
    # Build execution target tables and seed e-commerce rows
    setup_execution_database()
    
    yield
    
    # Teardown: drop tables and delete database files
    Base.metadata.drop_all(bind=app_engine)
    app_engine.dispose()
    
    for file in ["test_querypilot_app.db", "test_querypilot_execution.db"]:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"Cleaned up test database file: {file}")
            except Exception as e:
                print(f"Failed to remove test database file {file}: {e}")

@pytest.fixture(scope="function", autouse=True)
def reset_settings():
    """Reset configuration settings before and after each test to prevent test pollution."""
    saved_settings = {
        "DEFAULT_LLM_PROVIDER": settings.DEFAULT_LLM_PROVIDER,
        "DEFAULT_LLM_MODEL": settings.DEFAULT_LLM_MODEL,
        "AMBIGUITY_THRESHOLD": settings.AMBIGUITY_THRESHOLD,
        "MAX_CLARIFICATION_ROUNDS": settings.MAX_CLARIFICATION_ROUNDS,
        "MAX_REPAIR_ATTEMPTS": settings.MAX_REPAIR_ATTEMPTS,
        "QUERY_TIMEOUT_SECONDS": settings.QUERY_TIMEOUT_SECONDS,
        "MAX_EXECUTION_ROWS": settings.MAX_EXECUTION_ROWS,
    }
    yield
    for key, val in saved_settings.items():
        setattr(settings, key, val)

@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional database session for tests, rolling back changes after."""
    connection = app_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Provides a FastAPI test client with database session overrides."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    """Logs in and returns bearer authorization headers for tests."""
    response = client.post("/api/auth/login", json={
        "email": "admin@querypilot.com",
        "password": "adminpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
