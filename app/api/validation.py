from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
from uuid import UUID
import uuid
import tempfile
import os

from app.database import get_db
from app.core.validation_engine import ValidationEngine
from app.models.schemas import (
    ValidationRequest,
    ValidationResult,
    BatchValidationResult,
    ValidationHistoryResponse
)
from app.models.database import ValidationResult as DBValidationResult, BatchSummary

router = APIRouter(prefix="/validate", tags=["validation"])


@router.post("/{contract_id}", response_model=ValidationResult)
async def validate_record(
    contract_id: UUID,
    request: ValidationRequest,
    db: Session = Depends(get_db)
):
    try:
        engine = ValidationEngine(db)
        result = await engine.validate_record(contract_id, request.data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/{contract_id}/batch", response_model=BatchValidationResult)
async def validate_batch(
    contract_id: UUID,
    request: dict,
    db: Session = Depends(get_db)
):
    try:
        if 'data' not in request or not isinstance(request['data'], list):
            raise HTTPException(status_code=422, detail="Request must contain 'data' as a list")
        
        data = request['data']
        
        if len(data) > 10000:
            raise HTTPException(status_code=413, detail="Batch size exceeds maximum of 10,000 records")
        
        engine = ValidationEngine(db)
        result = await engine.validate_batch(contract_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch validation error: {str(e)}")


@router.get("/{contract_id}/results", response_model=ValidationHistoryResponse)
def get_validation_history(
    contract_id: UUID,
    status: Optional[str] = Query(None, regex="^(PASS|FAIL)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(DBValidationResult).filter(
            DBValidationResult.contract_id == str(contract_id)
        )
        
        if status:
            query = query.filter(DBValidationResult.status == status)
        
        if start_date:
            query = query.filter(DBValidationResult.validated_at >= start_date)
        
        if end_date:
            query = query.filter(DBValidationResult.validated_at <= end_date)
        
        total = query.count()
        
        results = query.order_by(
            DBValidationResult.validated_at.desc()
        ).offset(offset).limit(limit).all()
        
        return ValidationHistoryResponse(
            results=[r.to_dict() for r in results],
            total=total,
            filters_applied={
                "status": status,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@router.get("/results/{result_id}")
def get_validation_by_id(
    result_id: UUID,
    db: Session = Depends(get_db)
):
    try:
        result = db.query(DBValidationResult).filter(
            DBValidationResult.id == str(result_id)
        ).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Validation result not found")
        
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@router.get("/{contract_id}/errors/summary")
def get_error_summary(
    contract_id: UUID,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    try:
        from datetime import timedelta
        from collections import Counter
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        results = db.query(DBValidationResult).filter(
            DBValidationResult.contract_id == str(contract_id),
            DBValidationResult.validated_at >= start_date,
            DBValidationResult.status == "FAIL"
        ).all()
        
        all_errors = []
        for result in results:
            if result.errors:
                all_errors.extend([e.get('error_type') for e in result.errors])
        
        error_counts = Counter(all_errors)
        top_errors = [
            {"error_type": err_type, "count": count}
            for err_type, count in error_counts.most_common(10)
        ]
        
        return {
            "error_counts": dict(error_counts),
            "top_errors": top_errors,
            "total_errors": len(all_errors),
            "period": f"{days} days"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")


# ============ NEW ENDPOINTS ADDED BELOW ============


@router.post("/{contract_id}/upload")
async def upload_file_for_validation(
    contract_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a file (CSV, JSON, or Parquet) for batch validation.
    
    Args:
        contract_id: UUID of the contract to validate against
        file: Uploaded file containing data to validate
        file_type: Type of file (csv, json, parquet)
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Batch ID and status URL for tracking
    """
    # Check file size (max 100MB)
    if file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")
    
    # Validate file type
    if file_type not in ['csv', 'json', 'parquet']:
        raise HTTPException(
            status_code=422, 
            detail="Unsupported file type. Must be csv, json, or parquet"
        )
    
    # Generate batch ID
    batch_id = uuid.uuid4()
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    # Add background task for processing
    background_tasks.add_task(
        process_file_background,
        contract_id,
        tmp_path,
        file_type,
        batch_id,
        db
    )
    
    return {
        "batch_id": str(batch_id),
        "message": "File processing started",
        "status_url": f"/api/v1/validate/batch/{batch_id}/status",
        "contract_id": str(contract_id),
        "file_name": file.filename,
        "file_size": file.size
    }


@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: UUID, 
    db: Session = Depends(get_db)
):
    """
    Get the status of a batch validation job.
    
    Args:
        batch_id: UUID of the batch job
    
    Returns:
        Current status, progress, and results (if completed)
    """
    # Try to find completed batch in BatchSummary table
    batch = db.query(BatchSummary).filter(BatchSummary.batch_id == str(batch_id)).first()
    
    if not batch:
        # Check if there are validation results with this batch_id
        # This indicates the batch is still processing
        validation_results = db.query(DBValidationResult).filter(
            DBValidationResult.batch_id == str(batch_id)
        ).count()
        
        if validation_results > 0:
            # Batch is processing, return progress
            return {
                "batch_id": str(batch_id),
                "status": "PROCESSING",
                "progress": 50.0,  # Could be more sophisticated with actual progress tracking
                "total_records": validation_results * 2,  # Estimate
                "processed_records": validation_results
            }
        else:
            # Batch not found or not started
            return {
                "batch_id": str(batch_id),
                "status": "PROCESSING",
                "progress": 0.0,
                "total_records": 0,
                "processed_records": 0
            }
    
    # Batch completed, return results
    return {
        "batch_id": str(batch_id),
        "status": "COMPLETED",
        "progress": 100.0,
        "total_records": batch.total_records,
        "processed_records": batch.total_records,
        "result": {
            "contract_id": batch.contract_id,
            "passed": batch.passed,
            "failed": batch.failed,
            "pass_rate": batch.pass_rate,
            "execution_time_ms": batch.execution_time_ms,
            "errors_summary": batch.errors_summary,
            "processed_at": batch.processed_at.isoformat() if batch.processed_at else None
        }
    }


async def process_file_background(
    contract_id: UUID,
    file_path: str,
    file_type: str,
    batch_id: UUID,
    db: Session
):
    """
    Background task to process uploaded file for validation.
    
    Args:
        contract_id: UUID of the contract
        file_path: Path to the temporary file
        file_type: Type of file (csv, json, parquet)
        batch_id: UUID for this batch job
        db: Database session
    """
    from app.core.batch_processor import BatchProcessor  # Import here to avoid circular imports
    
    try:
        processor = BatchProcessor(db)
        
        # Process the file
        result = await processor.process_file(
            contract_id=contract_id,
            file_path=file_path,
            file_type=file_type,
            batch_id=batch_id
        )
        
        # Save batch summary to database
        batch_summary = BatchSummary(
            id=str(uuid.uuid4()),
            batch_id=str(batch_id),
            contract_id=str(contract_id),
            total_records=result.total_records,
            passed=result.passed,
            failed=result.failed,
            pass_rate=result.pass_rate,
            execution_time_ms=result.execution_time_ms,
            errors_summary=result.errors_summary,
            processed_at=datetime.utcnow()
        )
        
        db.add(batch_summary)
        db.commit()
        
        # Log completion
        print(f"Batch {batch_id} completed: {result.passed}/{result.total_records} passed "
              f"({result.pass_rate:.2f}%)")
              
    except Exception as e:
        # Log error but don't crash - file will be cleaned up
        print(f"Error processing batch {batch_id}: {str(e)}")
        
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing temporary file {file_path}: {str(e)}")