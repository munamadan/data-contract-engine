import pytest
from app.core.schema_validator import SchemaValidator
from app.models.schemas import ContractSchema, FieldDefinition


@pytest.fixture
def simple_schema():
    return ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user_id": FieldDefinition(
                type="string",
                required=True,
                pattern=r"^usr_\d+$"
            ),
            "email": FieldDefinition(
                type="string",
                required=True,
                format="email"
            ),
            "age": FieldDefinition(
                type="integer",
                required=False,
                min=0,
                max=120
            )
        }
    )


def test_validate_valid_record(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "usr_123",
        "email": "test@example.com",
        "age": 25
    }
    
    errors = validator.validate(data)
    assert len(errors) == 0


def test_validate_missing_required_field(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "usr_123"
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "REQUIRED_FIELD_MISSING"
    assert errors[0].field == "email"


def test_validate_type_mismatch(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "usr_123",
        "email": "test@example.com",
        "age": "twenty-five"
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "TYPE_MISMATCH"
    assert errors[0].field == "age"


def test_validate_pattern_mismatch(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "user_123",
        "email": "test@example.com"
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "PATTERN_MISMATCH"
    assert errors[0].field == "user_id"


def test_validate_format_email(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "usr_123",
        "email": "invalid-email"
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "FORMAT_MISMATCH"
    assert errors[0].field == "email"


def test_validate_range_constraint(simple_schema):
    validator = SchemaValidator(simple_schema)
    
    data = {
        "user_id": "usr_123",
        "email": "test@example.com",
        "age": 150
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert errors[0].error_type == "VALUE_TOO_LARGE"
    assert errors[0].field == "age"


def test_validate_nested_object():
    schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "user": FieldDefinition(
                type="object",
                required=True,
                properties={
                    "name": FieldDefinition(type="string", required=True),
                    "email": FieldDefinition(type="string", format="email", required=True)
                }
            )
        }
    )
    
    validator = SchemaValidator(schema)
    
    data = {
        "user": {
            "name": "John",
            "email": "invalid"
        }
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert "user.email" in errors[0].field


def test_validate_array():
    schema = ContractSchema(
        contract_version="1.0",
        domain="test",
        schema={
            "items": FieldDefinition(
                type="array",
                required=True,
                items=FieldDefinition(
                    type="object",
                    properties={
                        "id": FieldDefinition(type="string", required=True)
                    }
                )
            )
        }
    )
    
    validator = SchemaValidator(schema)
    
    data = {
        "items": [
            {"id": "123"},
            {}
        ]
    }
    
    errors = validator.validate(data)
    assert len(errors) == 1
    assert "items[1]" in errors[0].field