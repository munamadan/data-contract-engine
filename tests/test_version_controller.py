import pytest
from app.core.version_controller import VersionController
from app.core.contract_manager import ContractManager
from app.models.schemas import ContractCreate
from app.utils.exceptions import ContractNotFoundError


@pytest.fixture
def version_controller(db_session):
    return VersionController(db_session)


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
  age:
    type: integer
    required: true
    min: 0
    max: 120
"""
    
    contract_data = ContractCreate(
        name="test-contract",
        domain="test",
        yaml_content=yaml_content
    )
    
    return contract_manager.create_contract(contract_data)


def test_create_initial_version(sample_contract, db_session):
    from app.models.database import ContractVersion
    
    versions = db_session.query(ContractVersion).filter(
        ContractVersion.contract_id == sample_contract.id
    ).all()
    
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"
    assert versions[0].change_type == "INITIAL"


def test_create_version_with_breaking_change(version_controller, sample_contract):
    new_yaml = """
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
    
    version = version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    assert version.version == "2.0.0"
    assert version.change_type == "BREAKING"
    # One field removed = 15 points = LOW risk
    assert version.change_summary["risk_level"] == "LOW"
    assert version.change_summary["risk_score"] == 15


def test_create_version_with_non_breaking_change(version_controller, sample_contract):
    new_yaml = """
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
  age:
    type: integer
    required: true
    min: 0
    max: 120
  nickname:
    type: string
    required: false
"""
    
    version = version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    assert version.version == "1.1.0"
    assert version.change_type == "NON_BREAKING"


def test_version_number_calculation(version_controller):
    from app.core.change_detector import ChangeReport, Change
    
    report_breaking = ChangeReport(
        breaking_changes=[Change("TEST", "field", "desc", None, None, "impact")],
        non_breaking_changes=[],
        risk_score=15,
        risk_level="LOW",
        total_changes=1,
        summary="test"
    )
    
    new_version = version_controller.calculate_next_version("1.2.3", report_breaking)
    assert new_version == "2.0.0"
    
    report_non_breaking = ChangeReport(
        breaking_changes=[],
        non_breaking_changes=[Change("TEST", "field", "desc", None, None, "impact")],
        risk_score=3,
        risk_level="LOW",
        total_changes=1,
        summary="test"
    )
    
    new_version = version_controller.calculate_next_version("1.2.3", report_non_breaking)
    assert new_version == "1.3.0"
    
    report_patch = ChangeReport(
        breaking_changes=[],
        non_breaking_changes=[],
        risk_score=0,
        risk_level="LOW",
        total_changes=0,
        summary="test"
    )
    
    new_version = version_controller.calculate_next_version("1.2.3", report_patch)
    assert new_version == "1.2.4"


def test_get_version_history(version_controller, sample_contract):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
"""
    
    version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    history = version_controller.get_version_history(sample_contract.id)
    
    assert len(history) == 2
    assert history[0].version == "2.0.0"
    assert history[1].version == "1.0.0"


def test_get_version_by_number(version_controller, sample_contract):
    version = version_controller.get_version_by_number(
        sample_contract.id,
        "1.0.0"
    )
    
    assert version is not None
    assert version.version == "1.0.0"


def test_compare_versions(version_controller, sample_contract):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
"""
    
    version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    report = version_controller.compare_versions(
        sample_contract.id,
        "1.0.0",
        "2.0.0"
    )
    
    assert report.has_breaking_changes
    assert report.total_changes > 0


def test_rollback_to_version(version_controller, sample_contract, db_session):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
"""
    
    version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    contract = version_controller.rollback_to_version(
        contract_id=sample_contract.id,
        target_version="1.0.0",
        created_by="test_user",
        reason="Bug in v2.0.0"
    )
    
    assert contract.version == "3.0.0"
    
    db_session.refresh(contract)
    assert "user_id" in contract.yaml_content
    assert "email" in contract.yaml_content
    assert "age" in contract.yaml_content


def test_rollback_creates_new_version(version_controller, sample_contract):
    new_yaml = """
contract_version: "1.0"
domain: "test"
schema:
  user_id:
    type: string
    required: true
"""
    
    version_controller.create_version(
        contract_id=sample_contract.id,
        new_yaml=new_yaml,
        created_by="test_user"
    )
    
    version_controller.rollback_to_version(
        contract_id=sample_contract.id,
        target_version="1.0.0",
        created_by="test_user",
        reason="Rollback test"
    )
    
    history = version_controller.get_version_history(sample_contract.id)
    
    assert len(history) == 3
    assert history[0].version == "3.0.0"
    assert history[0].change_type == "ROLLBACK"


def test_version_not_found(version_controller, sample_contract):
    version = version_controller.get_version_by_number(
        sample_contract.id,
        "99.99.99"
    )
    assert version is None


def test_contract_not_found(version_controller):
    with pytest.raises(ContractNotFoundError):
        version_controller.create_version(
            contract_id="non-existent-id",
            new_yaml="test",
            created_by="test"
        )