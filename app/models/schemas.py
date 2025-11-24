from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re
import yaml


class FieldDefinition(BaseModel):
    type: str
    required: bool = True
    pattern: Optional[str] = None
    format: Optional[str] = None
    min: Optional[Union[int, float, str]] = None
    max: Optional[Union[int, float, str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    items: Optional['FieldDefinition'] = None
    properties: Optional[Dict[str, 'FieldDefinition']] = None
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        allowed_types = [
            'string', 'integer', 'float', 'boolean', 
            'timestamp', 'date', 'array', 'object'
        ]
        if v not in allowed_types:
            raise ValueError(f"Type must be one of: {', '.join(allowed_types)}")
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v is None:
            return v
        allowed_formats = ['email', 'url', 'uuid', 'ipv4']
        if v not in allowed_formats:
            raise ValueError(f"Format must be one of: {', '.join(allowed_formats)}")
        return v
    
    @field_validator('pattern')
    @classmethod
    def validate_pattern(cls, v):
        if v is None:
            return v
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {str(e)}")
        return v
    
    def validate_constraints(self):
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError(f"min ({self.min}) must be less than max ({self.max})")
        
        if self.min_length is not None and self.max_length is not None:
            if self.min_length > self.max_length:
                raise ValueError(f"min_length must be less than max_length")
    
    class Config:
        arbitrary_types_allowed = True


FieldDefinition.model_rebuild()


class ContractSchema(BaseModel):
    contract_version: str
    domain: str
    description: Optional[str] = None
    schema: Dict[str, FieldDefinition]
    quality_rules: Optional[Dict[str, Any]] = None
    
    @field_validator('contract_version')
    @classmethod
    def validate_version(cls, v):
        if not re.match(r'^\d+\.\d+$', v):
            raise ValueError("contract_version must be in format 'X.Y' (e.g., '1.0')")
        return v
    
    @field_validator('schema')
    @classmethod
    def validate_schema_not_empty(cls, v):
        if not v:
            raise ValueError("Schema must contain at least one field")
        return v


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    domain: str = Field(..., min_length=2, max_length=100)
    yaml_content: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v):
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-_]*$', v):
            raise ValueError(
                "Name must start with alphanumeric and contain only "
                "alphanumeric characters, dashes, and underscores"
            )
        return v
    
    @field_validator('domain')
    @classmethod
    def validate_domain_format(cls, v):
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', v):
            raise ValueError(
                "Domain must be lowercase, start with alphanumeric, "
                "and contain only lowercase alphanumeric and dashes"
            )
        return v
    
    @field_validator('yaml_content')
    @classmethod
    def validate_yaml_syntax(cls, v):
        try:
            yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {str(e)}")
        return v
    
    def validate_contract_structure(self) -> ContractSchema:
        data = yaml.safe_load(self.yaml_content)
        
        required_keys = ['contract_version', 'schema']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: '{key}'")
        
        try:
            return ContractSchema(**data)
        except Exception as e:
            raise ValueError(f"Invalid contract structure: {str(e)}")


class ContractUpdate(BaseModel):
    yaml_content: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('yaml_content')
    @classmethod
    def validate_yaml_syntax(cls, v):
        try:
            yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {str(e)}")
        return v
    
    def validate_contract_structure(self) -> ContractSchema:
        data = yaml.safe_load(self.yaml_content)
        
        required_keys = ['contract_version', 'schema']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: '{key}'")
        
        try:
            return ContractSchema(**data)
        except Exception as e:
            raise ValueError(f"Invalid contract structure: {str(e)}")


class ContractResponse(BaseModel):
    id: str
    name: str
    version: str
    domain: str
    yaml_content: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
    
    @classmethod
    def from_db_model(cls, db_model):
        return cls(
            id=str(db_model.id),
            name=db_model.name,
            version=db_model.version,
            domain=db_model.domain,
            yaml_content=db_model.yaml_content,
            description=db_model.description,
            is_active=db_model.is_active,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )


class ContractList(BaseModel):
    contracts: List[ContractResponse]
    total: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    
    @classmethod
    def paginate(cls, contracts: List[ContractResponse], total: int, skip: int, limit: int):
        page = (skip // limit) + 1
        has_next = (skip + limit) < total
        
        return cls(
            contracts=contracts,
            total=total,
            page=page,
            page_size=limit,
            has_next=has_next
        )


class ContractSummary(BaseModel):
    id: str
    name: str
    version: str
    domain: str
    is_active: bool
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ContractTemplate(BaseModel):
    name: str
    description: str
    domain: str
    yaml_content: str


class ContractTemplateList(BaseModel):
    templates: List[ContractTemplate]
    total: int


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    error_type: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    path: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    version: str = "0.1.0"

class ValidationError(BaseModel):
    field: str
    error_type: str
    message: str
    value: Optional[Any] = None
    expected: Optional[Any] = None
    
    def __str__(self) -> str:
        return f"{self.field}: {self.message}"
    
    class Config:
        arbitrary_types_allowed = True


class ValidationResult(BaseModel):
    status: str
    errors: List[ValidationError] = []
    execution_time_ms: float
    validated_at: datetime
    contract_version: str
    
    def is_pass(self) -> bool:
        return self.status == "PASS"
    
    def error_count(self) -> int:
        return len(self.errors)
    
    def errors_by_type(self) -> Dict[str, List[ValidationError]]:
        result = {}
        for error in self.errors:
            if error.error_type not in result:
                result[error.error_type] = []
            result[error.error_type].append(error)
        return result


class ValidationRequest(BaseModel):
    data: Dict[str, Any]


class BatchValidationResult(BaseModel):
    total_records: int
    passed: int
    failed: int
    pass_rate: float
    execution_time_ms: float
    errors_summary: Dict[str, int]
    sample_errors: List[ValidationError]
    batch_id: str
    
    def get_top_errors(self, n: int = 10) -> List[tuple]:
        sorted_errors = sorted(
            self.errors_summary.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_errors[:n]


class ValidationHistoryResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    filters_applied: Dict[str, Any]