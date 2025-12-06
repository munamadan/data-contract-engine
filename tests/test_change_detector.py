import pytest
from app.core.change_detector import ChangeDetector, Change, ChangeReport
from app.models.schemas import ContractSchema, FieldDefinition


@pytest.fixture
def change_detector():
    return ChangeDetector()


@pytest.fixture
def base_schema():
    return ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120),
            "status": FieldDefinition(type="string", required=False)
        }
    )


def test_detect_field_removed(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    assert len(report.breaking_changes) == 1
    assert report.breaking_changes[0].type == "FIELD_REMOVED"
    assert report.breaking_changes[0].field == "status"


def test_detect_required_field_added(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            **base_schema.schema,
            "phone": FieldDefinition(type="string", required=True)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    assert len(report.breaking_changes) == 1
    assert report.breaking_changes[0].type == "REQUIRED_FIELD_ADDED"
    assert report.breaking_changes[0].field == "phone"


def test_detect_optional_field_added(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            **base_schema.schema,
            "nickname": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert not report.has_breaking_changes
    assert len(report.non_breaking_changes) == 1
    assert report.non_breaking_changes[0].type == "OPTIONAL_FIELD_ADDED"
    assert report.non_breaking_changes[0].field == "nickname"


def test_detect_field_made_required(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120),
            "status": FieldDefinition(type="string", required=True)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    assert len(report.breaking_changes) == 1
    assert report.breaking_changes[0].type == "FIELD_MADE_REQUIRED"
    assert report.breaking_changes[0].field == "status"


def test_detect_field_made_optional(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=False, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert not report.has_breaking_changes
    assert len(report.non_breaking_changes) == 1
    assert report.non_breaking_changes[0].type == "FIELD_MADE_OPTIONAL"
    assert report.non_breaking_changes[0].field == "email"


def test_detect_type_changed(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="string", required=True),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    breaking_types = [c.type for c in report.breaking_changes]
    assert "TYPE_CHANGED" in breaking_types


def test_detect_pattern_stricter(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d{5,10}$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    breaking_types = [c.type for c in report.breaking_changes]
    assert "PATTERN_STRICTER" in breaking_types


def test_detect_pattern_relaxed(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=120),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert not report.has_breaking_changes
    non_breaking_types = [c.type for c in report.non_breaking_changes]
    assert "PATTERN_RELAXED" in non_breaking_types


def test_detect_range_narrower(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=18, max=65),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    breaking_types = [c.type for c in report.breaking_changes]
    assert "CONSTRAINT_TIGHTENED" in breaking_types


def test_detect_range_wider(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "age": FieldDefinition(type="integer", required=True, min=0, max=150),
            "status": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert not report.has_breaking_changes
    non_breaking_types = [c.type for c in report.non_breaking_changes]
    assert "CONSTRAINT_RELAXED" in non_breaking_types


def test_risk_score_no_changes(change_detector, base_schema):
    report = change_detector.detect_changes(base_schema, base_schema)
    
    assert report.risk_score == 0
    assert report.risk_level == "LOW"
    assert report.total_changes == 0


def test_risk_score_minor_changes(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            **base_schema.schema,
            "nickname": FieldDefinition(type="string", required=False),
            "bio": FieldDefinition(type="string", required=False)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.risk_score == 6
    assert report.risk_level == "LOW"


def test_risk_score_major_changes(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email")
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.risk_score == 30
    assert report.risk_level == "MEDIUM"


def test_multiple_breaking_changes(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "phone": FieldDefinition(type="string", required=True)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    assert len(report.breaking_changes) == 3  # Changed from 2 to 3
    # age removed, status removed, phone added (required)


def test_mixed_breaking_and_non_breaking(change_detector, base_schema):
    new_schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(type="string", required=True, pattern="^usr_\\d+$"),
            "email": FieldDefinition(type="string", required=True, format="email"),
            "nickname": FieldDefinition(type="string", required=False),
            "phone": FieldDefinition(type="string", required=True)
        }
    )
    
    report = change_detector.detect_changes(base_schema, new_schema)
    
    assert report.has_breaking_changes
    assert len(report.breaking_changes) == 3  # Changed from 2 to 3
    # age removed, status removed, phone added (required)
    assert len(report.non_breaking_changes) == 1
    # nickname added (optional)