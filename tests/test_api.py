import pytest
from fastapi.testclient import TestClient

def test_auth_login(client):
    """Verify login with correct credentials yields access token."""
    response = client.post("/api/auth/login", json={
        "email": "admin@querypilot.com",
        "password": "adminpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"

    # Bad login
    response_bad = client.post("/api/auth/login", json={
        "email": "admin@querypilot.com",
        "password": "wrongpassword"
    })
    assert response_bad.status_code == 401

def test_schema_explorer(client, auth_headers):
    """Verify that schema explorer API returns full database schema metadata."""
    response = client.get("/api/schema/explorer", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert "customers" in data["tables"]

def test_query_analyze_clarifying(client, auth_headers):
    """Verify that ambiguous queries trigger clarifying status and options."""
    response = client.post("/api/query/analyze", json={
        "question": "Who is our best customer?"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarifying"
    assert "session_id" in data
    assert "clarification_question" in data
    assert len(data["options"]) >= 2

def test_query_analyze_and_respond_success(client, auth_headers):
    """Verify complete query cycle: analyze, receive ambiguity, respond, and get results."""
    # 1. Start session
    response = client.post("/api/query/analyze", json={
        "question": "Who is our best customer?"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # 2. Respond to the clarification question
    response_resp = client.post("/api/query/respond", json={
        "session_id": session_id,
        "answer": "Highest total revenue"
    }, headers=auth_headers)
    
    assert response_resp.status_code == 200
    res_data = response_resp.json()
    # Mock LLM provider will resolve this to success on respond
    assert res_data["status"] == "success"
    assert "sql" in res_data
    assert "rows" in res_data
    assert len(res_data["rows"]) > 0
    assert "explanation" in res_data

def test_semantic_mappings_crud(client, auth_headers):
    """Verify CRUD endpoints for semantics mapping management."""
    # List mappings
    response = client.get("/api/semantics", headers=auth_headers)
    assert response.status_code == 200
    initial_count = len(response.json())
    assert initial_count > 0

    # Add a mapping
    response_add = client.post("/api/semantics", json={
        "term": "test metric",
        "category": "metric",
        "sql_fragment": "COUNT(*)",
        "definition": "Simple row count metric"
    }, headers=auth_headers)
    assert response_add.status_code == 200
    term_id = response_add.json()["data"]["id"]

    # Verify added
    response_check = client.get("/api/semantics", headers=auth_headers)
    assert len(response_check.json()) == initial_count + 1

    # Delete mapping
    response_del = client.delete(f"/api/semantics/{term_id}", headers=auth_headers)
    assert response_del.status_code == 200

    # Verify deleted
    response_check_del = client.get("/api/semantics", headers=auth_headers)
    assert len(response_check_del.json()) == initial_count

def test_admin_settings(client, auth_headers):
    """Verify setting retrieves and updates dynamic server parameters."""
    response = client.get("/api/admin/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "ambiguity_threshold" in data

    # Update settings
    response_update = client.post("/api/admin/settings", json={
        "default_llm_provider": "mock",
        "default_llm_model": "mock-model-v2",
        "ambiguity_threshold": 0.85,
        "max_clarification_rounds": 3,
        "max_repair_attempts": 4,
        "query_timeout_seconds": 10,
        "max_execution_rows": 200
    }, headers=auth_headers)
    
    assert response_update.status_code == 200
    updated_data = response_update.json()["settings"]
    assert updated_data["ambiguity_threshold"] == 0.85
    assert updated_data["max_clarification_rounds"] == 3
    assert updated_data["default_llm_model"] == "mock-model-v2"
