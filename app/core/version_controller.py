import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.database import Contract, ContractVersion
from app.core.change_detector import ChangeDetector, ChangeReport
from app.core.yaml_parser import YAMLParser
from app.utils.exceptions import ContractNotFoundError, InvalidYAMLError


logger = logging.getLogger(__name__)


class VersionController:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.change_detector = ChangeDetector()
        self.yaml_parser = YAMLParser()
        self.logger = logging.getLogger(__name__)
    
    def create_version(
        self,
        contract_id: str,
        new_yaml: str,
        created_by: str
    ) -> ContractVersion:
        self.logger.info(f"Creating new version for contract {contract_id}")
        
        contract = self.db.query(Contract).filter(
            Contract.id == str(contract_id)
        ).first()
        
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        
        try:
            old_schema = self.yaml_parser.parse_yaml(contract.yaml_content)
            new_schema = self.yaml_parser.parse_yaml(new_yaml)
        except Exception as e:
            raise InvalidYAMLError(
                error_message=str(e),
                details={"contract_id": str(contract_id)}
            )
        
        change_report = self.change_detector.detect_changes(old_schema, new_schema)
        
        current_version = contract.version
        new_version = self.calculate_next_version(current_version, change_report)
        
        change_type = self._determine_change_type(change_report)
        
        version = ContractVersion(
            contract_id=str(contract_id),
            version=new_version,
            yaml_content=new_yaml,
            change_type=change_type,
            change_summary=change_report.to_dict(),
            created_at=datetime.now(timezone.utc),
            created_by=created_by
        )
        
        contract.yaml_content = new_yaml
        contract.version = new_version
        contract.updated_at = datetime.now(timezone.utc)
        
        self.db.add(version)
        self.db.commit()
        
        self.logger.info(
            f"Version created: {contract_id} v{current_version} → v{new_version} "
            f"({change_type})"
        )
        
        return version
    
    def calculate_next_version(
        self,
        current_version: str,
        change_report: ChangeReport
    ) -> str:
        parts = current_version.split('.')
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
        
        if change_report.has_breaking_changes:
            major += 1
            minor = 0
            patch = 0
        elif len(change_report.non_breaking_changes) > 0:
            minor += 1
            patch = 0
        else:
            patch += 1
        
        return f"{major}.{minor}.{patch}"
    
    def get_version_history(
        self,
        contract_id: str,
        limit: int = 50
    ) -> List[ContractVersion]:
        versions = self.db.query(ContractVersion).filter(
            ContractVersion.contract_id == str(contract_id)
        ).order_by(
            ContractVersion.created_at.desc()
        ).limit(limit).all()
        
        return versions
    
    def get_version_by_number(
        self,
        contract_id: str,
        version: str
    ) -> Optional[ContractVersion]:
        version_record = self.db.query(ContractVersion).filter(
            ContractVersion.contract_id == str(contract_id),
            ContractVersion.version == version
        ).first()
        
        return version_record
    
    def compare_versions(
        self,
        contract_id: str,
        version1: str,
        version2: str
    ) -> ChangeReport:
        self.logger.info(
            f"Comparing versions {version1} and {version2} "
            f"for contract {contract_id}"
        )
        
        v1 = self.get_version_by_number(contract_id, version1)
        v2 = self.get_version_by_number(contract_id, version2)
        
        if not v1:
            raise ContractNotFoundError(
                contract_id=str(contract_id),
                details={"message": f"Version {version1} not found"}
            )
        
        if not v2:
            raise ContractNotFoundError(
                contract_id=str(contract_id),
                details={"message": f"Version {version2} not found"}
            )
        
        schema1 = self.yaml_parser.parse_yaml(v1.yaml_content)
        schema2 = self.yaml_parser.parse_yaml(v2.yaml_content)
        
        change_report = self.change_detector.detect_changes(schema1, schema2)
        
        return change_report
    
    def rollback_to_version(
        self,
        contract_id: str,
        target_version: str,
        created_by: str,
        reason: str = ""
    ) -> Contract:
        self.logger.info(
            f"Rolling back contract {contract_id} to version {target_version}"
        )
        
        contract = self.db.query(Contract).filter(
            Contract.id == str(contract_id)
        ).first()
        
        if not contract:
            raise ContractNotFoundError(contract_id=str(contract_id))
        
        target = self.get_version_by_number(contract_id, target_version)
        
        if not target:
            raise ContractNotFoundError(
                contract_id=str(contract_id),
                details={"message": f"Target version {target_version} not found"}
            )
        
        current_version = contract.version
        parts = current_version.split('.')
        major = int(parts[0])
        new_version = f"{major + 1}.0.0"
        
        rollback_version = ContractVersion(
            contract_id=str(contract_id),
            version=new_version,
            yaml_content=target.yaml_content,
            change_type="ROLLBACK",
            change_summary={
                "breaking_changes": [],
                "non_breaking_changes": [],
                "risk_score": 0,
                "risk_level": "LOW",
                "total_changes": 0,
                "summary": f"Rolled back from v{current_version} to v{target_version}",
                "rollback_info": {
                    "from_version": current_version,
                    "to_version": target_version,
                    "reason": reason
                }
            },
            created_at=datetime.now(timezone.utc),
            created_by=created_by
        )
        
        contract.yaml_content = target.yaml_content
        contract.version = new_version
        contract.updated_at = datetime.now(timezone.utc)
        
        self.db.add(rollback_version)
        self.db.commit()
        
        self.logger.info(
            f"Rollback complete: {contract_id} "
            f"v{current_version} → v{new_version} (content from v{target_version})"
        )
        
        return contract
    
    def _determine_change_type(self, change_report: ChangeReport) -> str:
        if change_report.has_breaking_changes:
            return "BREAKING"
        elif len(change_report.non_breaking_changes) > 0:
            return "NON_BREAKING"
        else:
            return "PATCH"