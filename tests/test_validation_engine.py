import pytest
from uuid import uuid4
from app.core.validation_engine import ValidationEngine
from app.core.contract_manager import ContractManager
from app.models.schemas import ContractCreate


@pytest.mark.asyncio
async def test_validate_record_pass(db_session, sample_contract_data):
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    engine = ValidationEngine(db_session)
    
    data = {
        "user_id": "usr_123",
        "email": "test@example.com",
        "age": 25
    }
    
    result = await engine.validate_record(contract.id, data)
    
    assert result.status == "PASS"
    assert len(result.errors) == 0
    assert result.execution_time_ms > 0


@pytest.mark.asyncio
async def test_validate_record_fail(db_session, sample_contract_data):
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    engine = ValidationEngine(db_session)
    
    data = {
        "user_id": "invalid_format",
        "email": "test@example.com"
    }
    
    result = await engine.validate_record(contract.id, data)
    
    assert result.status == "FAIL"
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_validate_batch(db_session, sample_contract_data):
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    engine = ValidationEngine(db_session)
    
    data = [
        {"user_id": "usr_1", "email": "test1@example.com", "age": 25},
        {"user_id": "usr_2", "email": "test2@example.com", "age": 30},
        {"user_id": "invalid", "email": "test3@example.com", "age": 35}
    ]
    
    result = await engine.validate_batch(contract.id, data)
    
    assert result.total_records == 3
    assert result.passed == 2
    assert result.failed == 1
    assert result.pass_rate == pytest.approx(66.67, rel=0.01)


@pytest.mark.asyncio
async def test_validation_result_storage(db_session, sample_contract_data):
    from app.models.database import ValidationResult as DBValidationResult
    
    manager = ContractManager(db_session)
    contract = manager.create_contract(sample_contract_data)
    
    engine = ValidationEngine(db_session)
    
    data = {"user_id": "usr_123", "email": "test@example.com"}
    
    await engine.validate_record(contract.id, data)
    
    stored_results = db_session.query(DBValidationResult).filter(
        DBValidationResult.contract_id == str(contract.id)
    ).all()
    
    assert len(stored_results) == 1
    assert stored_results[0].status == "PASS"


@pytest.mark.asyncio
async def test_contract_not_found(db_session):
    engine = ValidationEngine(db_session)
    
    with pytest.raises(ValueError, match="not found"):
        await engine.validate_record(uuid4(), {})