import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.contract_manager import ContractManager
from app.models.schemas import ContractCreate


@pytest.fixture
def client(db_session):
    from app.database import get_db
    
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
def sample_contract(db_session):
    contract_manager = ContractManager(db_session)
    
    yaml_content = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
    pattern: "^usr_\\\\d+$"
  email:
    type: string
    required: true
    format: email
"""
    
    contract_data = ContractCreate(
        name="test-version-contract",
        domain="test",
        yaml_content=yaml_content
    )
    
    return contract_manager.create_contract(contract_data)


def test_get_version_history_api(client, sample_contract):
    response = client.get(f"/api/v1/contracts/{sample_contract.id}/versions")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "versions" in data
    assert "total" in data
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == "1.0.0"


def test_get_specific_version_api(client, sample_contract):
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/versions/1.0.0"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["version"] == "1.0.0"
    assert data["contract_id"] == sample_contract.id
    assert "yaml_content" in data


def test_get_latest_version_api(client, sample_contract):
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/versions/latest"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["version"] == "1.0.0"
    assert data["contract_id"] == sample_contract.id


def test_compare_versions_api(client, sample_contract):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
    pattern: "^usr_\\\\d+$"
"""
    
    update_response = client.put(
        f"/api/v1/contracts/{sample_contract.id}",
        json={"yaml_content": new_yaml}
    )
    
    assert update_response.status_code == 200
    
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/diff/1.0.0/2.0.0"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "breaking_changes" in data
    assert "non_breaking_changes" in data
    assert "risk_score" in data
    assert "risk_level" in data


def test_rollback_to_version_api(client, sample_contract):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
"""
    
    client.put(
        f"/api/v1/contracts/{sample_contract.id}",
        json={"yaml_content": new_yaml}
    )
    
    rollback_request = {
        "target_version": "1.0.0",
        "reason": "Bug in v2.0.0",
        "created_by": "test_user"
    }
    
    response = client.post(
        f"/api/v1/contracts/{sample_contract.id}/rollback",
        json=rollback_request
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["new_version"] == "3.0.0"
    assert data["rolled_back_to"] == "1.0.0"
    assert "message" in data


def test_invalid_version_format(client, sample_contract):
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/versions/invalid-version"
    )
    
    assert response.status_code == 404


def test_version_not_found(client, sample_contract):
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/versions/99.99.99"
    )
    
    assert response.status_code == 404


def test_contract_not_found_versions(client):
    response = client.get("/api/v1/contracts/non-existent-id/versions")
    
    # API returns empty list for non-existent contract (graceful handling)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["versions"]) == 0


def test_version_history_with_limit(client, sample_contract):
    for i in range(5):
        new_yaml = f"""
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
  field_{i}:
    type: string
    required: false
"""
        client.put(
            f"/api/v1/contracts/{sample_contract.id}",
            json={"yaml_content": new_yaml}
        )
    
    response = client.get(
        f"/api/v1/contracts/{sample_contract.id}/versions?limit=3"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["versions"]) <= 3


def test_rollback_invalid_target_version(client, sample_contract):
    rollback_request = {
        "target_version": "99.99.99",
        "reason": "Test",
        "created_by": "test_user"
    }
    
    response = client.post(
        f"/api/v1/contracts/{sample_contract.id}/rollback",
        json=rollback_request
    )
    
    assert response.status_code == 404