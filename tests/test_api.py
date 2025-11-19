import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "version" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_api_v1_root():
    response = client.get("/api/v1/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data

def test_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_accessible():
    response = client.get("/redoc")
    assert response.status_code == 200