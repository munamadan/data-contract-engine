import pytest
from fastapi.testclient import TestClient


def test_validate_single_record_api(client, db_session, sample_contract_data):
    from app.core.contract_manager import ContractManager
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    response = client.post(
        f"/api/v1/validate/{contract.id}",
        json={
            "data": {
                "user_id": "usr_123",
                "email": "test@example.com",
                "age": 25
            }
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "PASS"


def test_validate_batch_api(client, db_session, sample_contract_data):
    from app.core.contract_manager import ContractManager
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    response = client.post(
        f"/api/v1/validate/{contract.id}/batch",
        json={
            "data": [
                {"user_id": "usr_1", "email": "test1@example.com"},
                {"user_id": "usr_2", "email": "test2@example.com"}
            ]
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["total_records"] == 2


def test_get_validation_history_api(client, db_session, sample_contract_data):
    from app.core.contract_manager import ContractManager
    from app.core.validation_engine import ValidationEngine
    import asyncio
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    engine = ValidationEngine(db_session)
    asyncio.run(engine.validate_record(
        contract.id,
        {"user_id": "usr_123", "email": "test@example.com"}
    ))
    
    response = client.get(f"/api/v1/validate/{contract.id}/results")
    
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert result["total"] >= 1


def test_get_error_summary_api(client, db_session, sample_contract_data):
    from app.core.contract_manager import ContractManager
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    response = client.get(
        f"/api/v1/validate/{contract.id}/errors/summary",
        params={"days": 7}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "error_counts" in result
    assert "period" in result


def test_batch_size_limit(client, db_session, sample_contract_data):
    from app.core.contract_manager import ContractManager
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    large_batch = [{"user_id": f"usr_{i}"} for i in range(10001)]
    
    response = client.post(
        f"/api/v1/validate/{contract.id}/batch",
        json={"data": large_batch}
    )
    
    assert response.status_code == 413