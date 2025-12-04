import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.version_controller import VersionController
from app.models.schemas import (
    ContractVersionResponse,
    VersionHistoryResponse,
    RollbackRequest,
    RollbackResponse,
    ContractResponse
)
from app.utils.exceptions import ContractNotFoundError


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["versions"])


@router.get("/{contract_id}/versions", response_model=VersionHistoryResponse)
def get_version_history(
    contract_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    if limit > 100:
        limit = 100
    
    try:
        version_controller = VersionController(db)
        versions = version_controller.get_version_history(contract_id, limit)
        
        version_responses = [
            ContractVersionResponse(
                id=str(v.id),
                contract_id=str(v.contract_id),
                version=v.version,
                yaml_content=v.yaml_content,
                change_type=v.change_type,
                change_summary=v.change_summary,
                created_at=v.created_at,
                created_by=v.created_by
            )
            for v in versions
        ]
        
        return VersionHistoryResponse(
            versions=version_responses,
            total=len(version_responses)
        )
    
    except Exception as e:
        logger.error(f"Error getting version history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve version history: {str(e)}"
        )


@router.get("/{contract_id}/versions/{version}", response_model=ContractVersionResponse)
def get_version(
    contract_id: str,
    version: str,
    db: Session = Depends(get_db)
):
    try:
        version_controller = VersionController(db)
        version_record = version_controller.get_version_by_number(
            contract_id,
            version
        )
        
        if not version_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for contract {contract_id}"
            )
        
        return ContractVersionResponse(
            id=str(version_record.id),
            contract_id=str(version_record.contract_id),
            version=version_record.version,
            yaml_content=version_record.yaml_content,
            change_type=version_record.change_type,
            change_summary=version_record.change_summary,
            created_at=version_record.created_at,
            created_by=version_record.created_by
        )
    
    except HTTPException:
        raise
    except ContractNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve version: {str(e)}"
        )


@router.get("/{contract_id}/diff/{version1}/{version2}")
def compare_versions(
    contract_id: str,
    version1: str,
    version2: str,
    db: Session = Depends(get_db)
):
    try:
        version_controller = VersionController(db)
        change_report = version_controller.compare_versions(
            contract_id,
            version1,
            version2
        )
        
        return change_report.to_dict()
    
    except ContractNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error comparing versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare versions: {str(e)}"
        )


@router.get("/{contract_id}/versions/latest", response_model=ContractVersionResponse)
def get_latest_version(
    contract_id: str,
    db: Session = Depends(get_db)
):
    try:
        version_controller = VersionController(db)
        versions = version_controller.get_version_history(contract_id, limit=1)
        
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No versions found for contract {contract_id}"
            )
        
        latest = versions[0]
        
        return ContractVersionResponse(
            id=str(latest.id),
            contract_id=str(latest.contract_id),
            version=latest.version,
            yaml_content=latest.yaml_content,
            change_type=latest.change_type,
            change_summary=latest.change_summary,
            created_at=latest.created_at,
            created_by=latest.created_by
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest version: {str(e)}"
        )


@router.post("/{contract_id}/rollback", response_model=RollbackResponse)
def rollback_contract(
    contract_id: str,
    request: RollbackRequest,
    db: Session = Depends(get_db)
):
    try:
        version_controller = VersionController(db)
        
        contract = version_controller.rollback_to_version(
            contract_id=contract_id,
            target_version=request.target_version,
            created_by=request.created_by,
            reason=request.reason
        )
        
        return RollbackResponse(
            contract=ContractResponse.from_db_model(contract),
            new_version=contract.version,
            rolled_back_to=request.target_version,
            message=f"Successfully rolled back to version {request.target_version}"
        )
    
    except ContractNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rolling back contract: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback contract: {str(e)}"
        )