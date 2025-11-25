import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def db_session(test_db) -> Generator[Session, None, None]:
    yield test_db


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_contract_data():
    from app.models.schemas import ContractCreate
    
    return ContractCreate(
        name="test-contract",
        domain="test",
        yaml_content="""contract_version: "1.0"
domain: "test"
description: "Test contract"
schema:
  user_id:
    type: string
    required: true
    pattern: "^usr_\\\\d+$"
  email:
    type: string
    format: email
    required: true
  age:
    type: integer
    required: false
    min: 0
    max: 120
quality_rules:
  freshness:
    max_latency_hours: 24
  completeness:
    min_row_count: 1
    max_null_percentage: 5
""",
        description="Test contract for validation"
    )