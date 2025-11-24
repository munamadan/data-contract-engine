from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
from uuid import UUID

from app.database import get_db
from app.core.validation_engine import ValidationEngine
from app.models.schemas import (
    ValidationRequest,
    ValidationResult,
    BatchValidationResult,
    ValidationHistoryResponse
)
from app.models.database import ValidationResult as DBValidationResult

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