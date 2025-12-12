from typing import Dict, Any, List, Optional, Callable
from uuid import UUID
import uuid
import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.file_handlers import FileHandlerFactory
from app.core.validation_engine import ValidationEngine
from app.models.schemas import BatchProcessingResult
from app.utils.exceptions import InvalidFileFormatError


class BatchProcessor:
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
        self.progress_callback: Optional[Callable[[float], None]] = None
    
    async def process_file(
        self,
        contract_id: UUID,
        file_path: str,
        file_type: str,
        chunk_size: int = 1000
    ) -> BatchProcessingResult:
        batch_id = uuid.uuid4()
        start_time = time.time()
        
        handler = FileHandlerFactory.get_handler(file_type)
        validation_engine = ValidationEngine(self.db)
        
        if not handler.validate_format(file_path):
            raise InvalidFileFormatError(f"Invalid {file_type} format")
        
        total_records = 0
        passed_records = 0
        failed_records = 0
        all_errors = []
        
        for chunk_num, chunk in enumerate(handler.read_chunks(file_path, chunk_size)):
            self.logger.info(f"Processing chunk {chunk_num}, {len(chunk)} records")
            
            chunk_result = await validation_engine.validate_batch(
                contract_id=contract_id,
                data=chunk,
                batch_id=batch_id
            )
            
            total_records += chunk_result.total_records
            passed_records += chunk_result.passed
            failed_records += chunk_result.failed
            all_errors.extend(chunk_result.sample_errors)
            
            if self.progress_callback and total_records > 0:
                progress = (chunk_num + 1) * chunk_size / total_records * 100
                self.progress_callback(min(progress, 100))
        
        execution_time = (time.time() - start_time) * 1000
        pass_rate = (passed_records / total_records * 100) if total_records > 0 else 0
        error_counts = self._count_errors_by_type(all_errors)
        
        result = BatchProcessingResult(
            batch_id=batch_id,
            contract_id=contract_id,
            total_records=total_records,
            passed=passed_records,
            failed=failed_records,
            pass_rate=pass_rate,
            execution_time_ms=execution_time,
            errors_summary=error_counts,
            sample_errors=all_errors[:50],
            processed_at=datetime.utcnow()
        )
        
        self._store_batch_summary(result)
        
        return result
    
    def set_progress_callback(self, callback: Callable[[float], None]):
        self.progress_callback = callback
    
    def _count_errors_by_type(self, errors: List) -> Dict[str, int]:
        from collections import Counter
        error_types = [err.error_type for err in errors]
        return dict(Counter(error_types))
    
    def _store_batch_summary(self, result: BatchProcessingResult):
        from app.models.database import BatchSummary
        
        batch_summary = BatchSummary(
            batch_id=result.batch_id,
            contract_id=result.contract_id,
            total_records=result.total_records,
            passed=result.passed,
            failed=result.failed,
            pass_rate=result.pass_rate,
            execution_time_ms=result.execution_time_ms,
            errors_summary=result.errors_summary,
            processed_at=result.processed_at
        )
        
        self.db.add(batch_summary)
        self.db.commit()