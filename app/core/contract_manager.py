import logging
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Contract, ContractVersion
from app.models.schemas import ContractCreate, ContractUpdate, ContractSchema
from app.core.yaml_parser import YAMLParser, YAMLParserError
from app.utils.exceptions import (
    DuplicateContractError,
    ContractNotFoundError,
    InvalidYAMLError,
    InvalidContractSchemaError,
    DatabaseError
)


logger = logging.getLogger(__name__)


class ContractManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.yaml_parser = YAMLParser()
        self.logger = logging.getLogger(__name__)
    
    def create_contract(self, contract_data: ContractCreate) -> Contract:
        self.logger.info(f"Creating contract: {contract_data.name}")
        
        existing = self.db.query(Contract).filter(
            Contract.name == contract_data.name
        ).first()
        
        if existing:
            raise DuplicateContractError(
                contract_name=contract_data.name,
                details={"existing_id": str(existing.id)}
            )
        
        try:
            contract_schema = self.yaml_parser.parse_yaml(contract_data.yaml_content)
        except YAMLParserError as e:
            raise InvalidYAMLError(
                error_message=str(e),
                details={"yaml_content_preview": contract_data.yaml_content[:200]}
            )
        
        try:
            contract = Contract(
                name=contract_data.name,
                version="1.0.0",
                domain=contract_data.domain,
                yaml_content=contract_data.yaml_content,
                description=contract_data.description,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(contract)
            self.db.flush()
            
            version = ContractVersion(
                contract_id=contract.id,
                version="1.0.0",
                yaml_content=contract_data.yaml_content,
                change_type="INITIAL",
                change_summary={
                    "breaking_changes": [],
                    "non_breaking_changes": [],
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "total_changes": 0,
                    "message": "Initial contract creation"
                },
                created_at=datetime.now(timezone.utc),
                created_by="system"
            )
            
            self.db.add(version)
            self.db.commit()
            
            self.logger.info(f"Contract created successfully: {contract.id}")
            return contract
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create contract: {str(e)}")
            raise DatabaseError(
                operation="create",
                error_message=str(e),
                details={"contract_name": contract_data.name}
            )
    
    def get_contract_by_id(self, contract_id: UUID) -> Optional[Contract]:
        contract = self.db.query(Contract).filter(
            Contract.id == str(contract_id)
        ).first()
        
        return contract
    
    def get_contract_by_name(self, name: str) -> Optional[Contract]:
        contract = self.db.query(Contract).filter(
            Contract.name.ilike(name)
        ).first()
        
        return contract
    
    def list_contracts(
        self,
        domain: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Contract], int]:
        query = self.db.query(Contract)
        
        filters = [Contract.is_active == is_active]
        
        if domain:
            filters.append(Contract.domain == domain)
        
        query = query.filter(and_(*filters))
        
        total = query.count()
        
        contracts = query.order_by(
            Contract.updated_at.desc()
        ).offset(skip).limit(limit).all()
        
        self.logger.info(
            f"Listed {len(contracts)} contracts (total: {total}, "
            f"domain: {domain}, active: {is_active})"
        )
        
        return contracts, total
    
    def update_contract(
        self,
        contract_id: UUID,
        update_data: ContractUpdate
    ) -> Contract:
        self.logger.info(f"Updating contract: {contract_id}")
        
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(
                contract_id=str(contract_id)
            )
        
        try:
            new_schema = self.yaml_parser.parse_yaml(update_data.yaml_content)
        except YAMLParserError as e:
            raise InvalidYAMLError(
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
        
        current_version = contract.version
        version_parts = current_version.split('.')
        major, minor, patch = int(version_parts[0]), int(version_parts[1]), int(version_parts[2])
        
        patch += 1
        new_version = f"{major}.{minor}.{patch}"
        
        try:
            contract.yaml_content = update_data.yaml_content
            contract.version = new_version
            contract.updated_at = datetime.now(timezone.utc)
            
            if update_data.description is not None:
                contract.description = update_data.description
            
            version = ContractVersion(
                contract_id=contract.id,
                version=new_version,
                yaml_content=update_data.yaml_content,
                change_type="PATCH",
                change_summary={
                    "breaking_changes": [],
                    "non_breaking_changes": [],
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "total_changes": 0,
                    "message": "Contract updated (change detection in Phase 4)"
                },
                created_at=datetime.now(timezone.utc),
                created_by="system"
            )
            
            self.db.add(version)
            self.db.commit()
            
            self.logger.info(
                f"Contract updated: {contract_id}, "
                f"version {current_version} → {new_version}"
            )
            
            return contract
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update contract: {str(e)}")
            raise DatabaseError(
                operation="update",
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
    
    def delete_contract(
        self,
        contract_id: UUID,
        hard_delete: bool = False
    ) -> bool:
        self.logger.info(
            f"Deleting contract: {contract_id} "
            f"(hard_delete={hard_delete})"
        )
        
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        
        try:
            if hard_delete:
                self.db.delete(contract)
                self.logger.warning(
                    f"Hard deleted contract {contract_id} and all related data"
                )
            else:
                contract.is_active = False
                contract.updated_at = datetime.now(timezone.utc)
                self.logger.info(f"Soft deleted contract {contract_id}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete contract: {str(e)}")
            raise DatabaseError(
                operation="delete",
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
    
    def activate_contract(self, contract_id: UUID) -> Contract:
        self.logger.info(f"Activating contract: {contract_id}")
        
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        
        try:
            contract.is_active = True
            contract.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            
            self.logger.info(f"Contract activated: {contract_id}")
            return contract
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to activate contract: {str(e)}")
            raise DatabaseError(
                operation="activate",
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
    
    def get_contract_schema(self, contract_id: UUID) -> ContractSchema:
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        
        try:
            schema = self.yaml_parser.parse_yaml(contract.yaml_content)
            return schema
        except YAMLParserError as e:
            raise InvalidYAMLError(
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
    
    def get_domains(self) -> List[str]:
        domains = self.db.query(Contract.domain).distinct().all()
        return [d[0] for d in domains if d[0]]