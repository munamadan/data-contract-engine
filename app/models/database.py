import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, String, Integer, Float, DateTime,
    ForeignKey, Text, Index, Date
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    domain = Column(String(100), nullable=False, index=True)
    yaml_content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = relationship("ContractVersion", back_populates="contract", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="contract", cascade="all, delete-orphan")
    quality_metrics = relationship("QualityMetric", back_populates="contract", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, name='{self.name}', version='{self.version}')>"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "domain": self.domain,
            "yaml_content": self.yaml_content,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=False, index=True)

    version = Column(String(20), nullable=False)
    yaml_content = Column(Text, nullable=False)
    change_type = Column(String(20), nullable=True)
    change_summary = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    contract = relationship("Contract", back_populates="versions")

    __table_args__ = (
        Index('ix_contract_versions_contract_version', 'contract_id', 'version', unique=True),
        Index('ix_contract_versions_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<ContractVersion(id={self.id}, version='{self.version}', type='{self.change_type}')>"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id),
            "version": self.version,
            "yaml_content": self.yaml_content,
            "change_type": self.change_type,
            "change_summary": self.change_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=False, index=True)

    status = Column(String(20), nullable=False, index=True)
    data_snapshot = Column(JSONB, nullable=True)
    errors = Column(JSONB, nullable=True)
    execution_time_ms = Column(Float, nullable=False)

    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    contract = relationship("Contract", back_populates="validation_results")

    __table_args__ = (
        Index('ix_validation_results_contract_date', 'contract_id', 'validated_at'),
    )
    
    def __repr__(self) -> str:
        return f"<ValidationResult(id={self.id}, status='{self.status}')>"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id),
            "status": self.status,
            "data_snapshot": self.data_snapshot,
            "errors": self.errors,
            "execution_time_ms": self.execution_time_ms,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "batch_id": str(self.batch_id) if self.batch_id else None,
        }
    
    def is_pass(self) -> bool:
        return self.status == "PASS"
    
    def error_count(self) -> int:
        return len(self.errors) if self.errors else 0


class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    contract_id = Column(UUID(as_uuid=True), ForeignKey('contracts.id'), nullable=False, index=True)

    metric_date = Column(Date, nullable=False)
    total_validations = Column(Integer, default=0, nullable=False)
    passed = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    pass_rate = Column(Float, nullable=True)
    avg_execution_time_ms = Column(Float, nullable=True)
    top_errors = Column(JSONB, nullable=True)
    quality_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    contract = relationship("Contract", back_populates="quality_metrics")

    __table_args__ = (
        Index('ix_quality_metrics_contract_date', 'contract_id', 'metric_date', unique=True),
        Index('ix_quality_metrics_date', 'metric_date'),
    )
    
    def __repr__(self) -> str:
        return f"<QualityMetric(id={self.id}, date={self.metric_date}, pass_rate={self.pass_rate})>"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id),
            "metric_date": self.metric_date.isoformat() if self.metric_date else None,
            "total_validations": self.total_validations,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "top_errors": self.top_errors,
            "quality_score": self.quality_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def calculate_pass_rate(self) -> float:
        if self.total_validations == 0:
            return 0.0
        return (self.passed / self.total_validations) * 100