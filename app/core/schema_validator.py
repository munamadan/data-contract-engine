import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from functools import lru_cache

from app.models.schemas import ContractSchema, FieldDefinition, ValidationError


class SchemaValidator:
    def __init__(self, contract_schema: ContractSchema):
        self.schema = contract_schema.schema
        self.logger = logging.getLogger(__name__)
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        for field_name, field_def in self.schema.items():
            if field_def.pattern:
                try:
                    self.compiled_patterns[field_name] = re.compile(field_def.pattern)
                except re.error as e:
                    self.logger.error(f"Invalid regex pattern for {field_name}: {e}")
    
    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        for field_name, field_def in self.schema.items():
            if field_def.required and field_name not in data:
                errors.append(ValidationError(
                    field=field_name,
                    error_type="REQUIRED_FIELD_MISSING",
                    message=f"Required field '{field_name}' is missing",
                    value=None,
                    expected="required field"
                ))
                continue
            
            if field_name not in data:
                continue
            
            value = data[field_name]
            
            if value is None and not field_def.required:
                continue
            
            type_error = self._validate_type(field_name, value, field_def.type)
            if type_error:
                errors.append(type_error)
                continue
            
            if field_def.type == 'string':
                errors.extend(self._validate_string(field_name, value, field_def))
            elif field_def.type in ['integer', 'float']:
                errors.extend(self._validate_number(field_name, value, field_def))
            elif field_def.type == 'timestamp':
                errors.extend(self._validate_timestamp(field_name, value, field_def))
            elif field_def.type == 'array':
                errors.extend(self._validate_array(field_name, value, field_def))
            elif field_def.type == 'object':
                errors.extend(self._validate_object(field_name, value, field_def))
            
            if len(errors) >= 10:
                break
        
        return errors
    
    def _validate_type(
        self,
        field_name: str,
        value: Any,
        expected_type: str
    ) -> Optional[ValidationError]:
        type_checks = {
            'string': lambda v: isinstance(v, str),
            'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
            'float': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            'boolean': lambda v: isinstance(v, bool),
            'timestamp': lambda v: isinstance(v, (str, int, float, datetime)),
            'date': lambda v: isinstance(v, str),
            'array': lambda v: isinstance(v, list),
            'object': lambda v: isinstance(v, dict)
        }
        
        check = type_checks.get(expected_type)
        if not check or not check(value):
            return ValidationError(
                field=field_name,
                error_type="TYPE_MISMATCH",
                message=f"Expected {expected_type}, got {type(value).__name__}",
                value=str(value)[:100],
                expected=expected_type
            )
        return None
    
    def _validate_string(
        self,
        field_name: str,
        value: str,
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        if field_def.pattern and field_name in self.compiled_patterns:
            if not self.compiled_patterns[field_name].match(value):
                errors.append(ValidationError(
                    field=field_name,
                    error_type="PATTERN_MISMATCH",
                    message=f"Value does not match pattern: {field_def.pattern}",
                    value=value[:100],
                    expected=field_def.pattern
                ))
        
        if field_def.format:
            if not self._validate_format(value, field_def.format):
                errors.append(ValidationError(
                    field=field_name,
                    error_type="FORMAT_MISMATCH",
                    message=f"Value does not match format: {field_def.format}",
                    value=value[:100],
                    expected=field_def.format
                ))
        
        if field_def.min_length is not None and len(value) < field_def.min_length:
            errors.append(ValidationError(
                field=field_name,
                error_type="LENGTH_TOO_SHORT",
                message=f"Length {len(value)} is less than minimum {field_def.min_length}",
                value=value[:100],
                expected=f"min_length: {field_def.min_length}"
            ))
        
        if field_def.max_length is not None and len(value) > field_def.max_length:
            errors.append(ValidationError(
                field=field_name,
                error_type="LENGTH_TOO_LONG",
                message=f"Length {len(value)} exceeds maximum {field_def.max_length}",
                value=value[:100],
                expected=f"max_length: {field_def.max_length}"
            ))
        
        if field_def.enum and value not in field_def.enum:
            errors.append(ValidationError(
                field=field_name,
                error_type="ENUM_MISMATCH",
                message=f"Value not in allowed list: {field_def.enum}",
                value=value[:100],
                expected=str(field_def.enum)
            ))
        
        return errors
    
    def _validate_number(
        self,
        field_name: str,
        value: Union[int, float],
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        if field_def.min is not None and value < field_def.min:
            errors.append(ValidationError(
                field=field_name,
                error_type="VALUE_TOO_SMALL",
                message=f"Value {value} is less than minimum {field_def.min}",
                value=str(value),
                expected=f"min: {field_def.min}"
            ))
        
        if field_def.max is not None and value > field_def.max:
            errors.append(ValidationError(
                field=field_name,
                error_type="VALUE_TOO_LARGE",
                message=f"Value {value} exceeds maximum {field_def.max}",
                value=str(value),
                expected=f"max: {field_def.max}"
            ))
        
        if field_def.enum and value not in field_def.enum:
            errors.append(ValidationError(
                field=field_name,
                error_type="ENUM_MISMATCH",
                message=f"Value not in allowed list: {field_def.enum}",
                value=str(value),
                expected=str(field_def.enum)
            ))
        
        return errors
    
    def _validate_timestamp(
        self,
        field_name: str,
        value: Any,
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value)
            elif isinstance(value, datetime):
                dt = value
            else:
                errors.append(ValidationError(
                    field=field_name,
                    error_type="INVALID_TIMESTAMP",
                    message="Cannot parse timestamp",
                    value=str(value)[:100],
                    expected="ISO 8601 or Unix timestamp"
                ))
                return errors
            
            if field_def.min:
                min_dt = datetime.fromisoformat(str(field_def.min).replace('Z', '+00:00'))
                if dt < min_dt:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="TIMESTAMP_TOO_OLD",
                        message=f"Timestamp before minimum: {field_def.min}",
                        value=str(value)[:100],
                        expected=f"min: {field_def.min}"
                    ))
            
            if field_def.max:
                max_dt = datetime.fromisoformat(str(field_def.max).replace('Z', '+00:00'))
                if dt > max_dt:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="TIMESTAMP_TOO_RECENT",
                        message=f"Timestamp after maximum: {field_def.max}",
                        value=str(value)[:100],
                        expected=f"max: {field_def.max}"
                    ))
        
        except Exception as e:
            errors.append(ValidationError(
                field=field_name,
                error_type="INVALID_TIMESTAMP",
                message=f"Cannot parse timestamp: {str(e)}",
                value=str(value)[:100],
                expected="Valid timestamp"
            ))
        
        return errors
    
    def _validate_array(
        self,
        field_name: str,
        value: List,
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        if field_def.min is not None and len(value) < field_def.min:
            errors.append(ValidationError(
                field=field_name,
                error_type="ARRAY_TOO_SHORT",
                message=f"Array length {len(value)} less than minimum {field_def.min}",
                value=f"[{len(value)} items]",
                expected=f"min: {field_def.min}"
            ))
        
        if field_def.max is not None and len(value) > field_def.max:
            errors.append(ValidationError(
                field=field_name,
                error_type="ARRAY_TOO_LONG",
                message=f"Array length {len(value)} exceeds maximum {field_def.max}",
                value=f"[{len(value)} items]",
                expected=f"max: {field_def.max}"
            ))
        
        if field_def.items:
            for idx, item in enumerate(value[:10]):
                item_errors = self._validate_nested_field(
                    f"{field_name}[{idx}]",
                    item,
                    field_def.items
                )
                errors.extend(item_errors)
                if len(errors) >= 10:
                    break
        
        return errors
    
    def _validate_object(
        self,
        field_name: str,
        value: Dict,
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        if field_def.properties:
            for prop_name, prop_def in field_def.properties.items():
                prop_path = f"{field_name}.{prop_name}"
                
                if prop_def.required and prop_name not in value:
                    errors.append(ValidationError(
                        field=prop_path,
                        error_type="REQUIRED_FIELD_MISSING",
                        message=f"Required property '{prop_name}' is missing",
                        value=None,
                        expected="required property"
                    ))
                    continue
                
                if prop_name in value:
                    prop_errors = self._validate_nested_field(
                        prop_path,
                        value[prop_name],
                        prop_def
                    )
                    errors.extend(prop_errors)
                
                if len(errors) >= 10:
                    break
        
        return errors
    
    def _validate_nested_field(
        self,
        field_path: str,
        value: Any,
        field_def: FieldDefinition
    ) -> List[ValidationError]:
        errors = []
        
        type_error = self._validate_type(field_path, value, field_def.type)
        if type_error:
            errors.append(type_error)
            return errors
        
        if field_def.type == 'string':
            errors.extend(self._validate_string(field_path, value, field_def))
        elif field_def.type in ['integer', 'float']:
            errors.extend(self._validate_number(field_path, value, field_def))
        elif field_def.type == 'object' and field_def.properties:
            errors.extend(self._validate_object(field_path, value, field_def))
        
        return errors
    
    @lru_cache(maxsize=100)
    def _validate_format(self, value: str, format_type: str) -> bool:
        format_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'url': r'^https?://[^\s/$.?#].[^\s]*$',
            'uuid': r'^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$',
            'ipv4': r'^(\d{1,3}\.){3}\d{1,3}$'
        }
        
        pattern = format_patterns.get(format_type)
        if not pattern:
            return True
        
        return bool(re.match(pattern, value, re.IGNORECASE))