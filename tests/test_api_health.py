
import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add current directory to path
sys.path.append(os.getcwd())

from api_server import app
import server_auth

client = TestClient(app)

def test_health_check_unauthenticated():
    # Health check should ideally be public or have specific behavior.
    # Currently app has global dependency on server_auth.get_current_user
    # So we expect 401 if we don't provide auth, OR if we want it public we need to override.
    # Let's check current behavior.
    response = client.get("/health")
    assert response.status_code == 401

def test_health_check_authenticated(monkeypatch):
    # Mock auth
    async def mock_get_current_user():
        return "testuser"
    
    app.dependency_overrides[server_auth.get_current_user] = mock_get_current_user
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
    
    # Clean up
    app.dependency_overrides = {}
