import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
import uuid

from sqlalchemy.orm import Session

from app.core.contract_manager import ContractManager
from app.core.schema_validator import SchemaValidator
from app.core.quality_validator import QualityValidator, QualityValidationResult
from app.models.schemas import ValidationResult, ValidationError, BatchValidationResult
from app.models.database import ValidationResult as DBValidationResult


class ValidationEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.contract_manager = ContractManager(db_session)
        self.logger = logging.getLogger(__name__)
    
    async def validate_record(
        self,
        contract_id: UUID,
        data: Dict[str, Any]
    ) -> ValidationResult:
        start_time = time.time()
        
        contract = self.contract_manager.get_contract_by_id(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        
        contract_schema = self.contract_manager.get_contract_schema(contract_id)
        
        schema_validator = SchemaValidator(contract_schema)
        schema_errors = schema_validator.validate(data)
        
        status = "PASS" if len(schema_errors) == 0 else "FAIL"
        
        quality_errors = []
        if status == "PASS" and contract_schema.quality_rules:
            quality_validator = QualityValidator(contract_schema.quality_rules)
            quality_result = quality_validator.validate(data)
            
            if not quality_result.passed:
                status = "FAIL"
                quality_errors = [
                    ValidationError(
                        field="quality",
                        error_type=e.rule_type,
                        message=e.message,
                        value=None,
                        expected=str(e.details)
                    )
                    for e in quality_result.errors
                ]
        
        all_errors = schema_errors + quality_errors
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        result = ValidationResult(
            status=status,
            errors=all_errors,
            execution_time_ms=execution_time_ms,
            validated_at=datetime.utcnow(),
            contract_version=contract.version
        )
        
        self._store_validation_result(contract_id, result)
        
        return result
    
    async def validate_batch(
        self,
        contract_id: UUID,
        data: List[Dict[str, Any]],
        batch_id: Optional[UUID] = None
    ) -> BatchValidationResult:
        if batch_id is None:
            batch_id = uuid.uuid4()
        
        start_time = time.time()
        
        contract = self.contract_manager.get_contract_by_id(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        
        contract_schema = self.contract_manager.get_contract_schema(contract_id)
        schema_validator = SchemaValidator(contract_schema)
        
        total_records = len(data)
        passed = 0
        failed = 0
        all_errors = []
        
        for record in data:
            errors = schema_validator.validate(record)
            
            if len(errors) == 0:
                passed += 1
            else:
                failed += 1
                all_errors.extend(errors[:5])
        
        if passed > 0 and contract_schema.quality_rules:
            quality_validator = QualityValidator(contract_schema.quality_rules)
            quality_result = quality_validator.validate(data)
            
            if not quality_result.passed:
                for qe in quality_result.errors:
                    all_errors.append(ValidationError(
                        field="batch_quality",
                        error_type=qe.rule_type,
                        message=qe.message,
                        value=None,
                        expected=str(qe.details)
                    ))
        
        execution_time_ms = (time.time() - start_time) * 1000
        pass_rate = (passed / total_records * 100) if total_records > 0 else 0
        
        error_counts = {}
        for error in all_errors:
            error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        
        result = BatchValidationResult(
            batch_id=str(batch_id),
            total_records=total_records,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            execution_time_ms=execution_time_ms,
            errors_summary=error_counts,
            sample_errors=all_errors[:50]
        )
        
        return result
    
    def _store_validation_result(
        self,
        contract_id: UUID,
        validation_result: ValidationResult,
        batch_id: Optional[UUID] = None
    ) -> None:
        db_result = DBValidationResult(
            contract_id=str(contract_id),
            status=validation_result.status,
            errors=[e.dict() for e in validation_result.errors] if validation_result.errors else None,
            execution_time_ms=validation_result.execution_time_ms,
            validated_at=validation_result.validated_at,
            batch_id=str(batch_id) if batch_id else None
        )
        
        self.db.add(db_result)
        self.db.commit()