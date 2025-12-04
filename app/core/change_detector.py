import logging
from typing import List, Tuple, Dict, Set, Optional
from app.models.schemas import ContractSchema, FieldDefinition


logger = logging.getLogger(__name__)


class Change:
    def __init__(
        self,
        type: str,
        field: str,
        description: str,
        old_value: any,
        new_value: any,
        impact: str
    ):
        self.type = type
        self.field = field
        self.description = description
        self.old_value = old_value
        self.new_value = new_value
        self.impact = impact
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "field": self.field,
            "description": self.description,
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
            "impact": self.impact
        }


class ChangeReport:
    def __init__(
        self,
        breaking_changes: List[Change],
        non_breaking_changes: List[Change],
        risk_score: int,
        risk_level: str,
        total_changes: int,
        summary: str
    ):
        self.breaking_changes = breaking_changes
        self.non_breaking_changes = non_breaking_changes
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.total_changes = total_changes
        self.summary = summary
    
    @property
    def has_breaking_changes(self) -> bool:
        return len(self.breaking_changes) > 0
    
    def to_dict(self) -> dict:
        return {
            "breaking_changes": [c.to_dict() for c in self.breaking_changes],
            "non_breaking_changes": [c.to_dict() for c in self.non_breaking_changes],
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "total_changes": self.total_changes,
            "summary": self.summary
        }


class ChangeDetector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_changes(
        self,
        old_schema: ContractSchema,
        new_schema: ContractSchema
    ) -> ChangeReport:
        self.logger.info("Detecting changes between schemas")
        
        breaking_changes, non_breaking_changes = self._analyze_fields(
            old_schema.schema,
            new_schema.schema
        )
        
        total_changes = len(breaking_changes) + len(non_breaking_changes)
        
        risk_score = self._calculate_risk_score(
            breaking_changes,
            non_breaking_changes
        )
        
        risk_level = self._get_risk_level(risk_score)
        
        summary = self._generate_summary(
            breaking_changes,
            non_breaking_changes,
            risk_level
        )
        
        report = ChangeReport(
            breaking_changes=breaking_changes,
            non_breaking_changes=non_breaking_changes,
            risk_score=risk_score,
            risk_level=risk_level,
            total_changes=total_changes,
            summary=summary
        )
        
        self.logger.info(
            f"Change detection complete: {len(breaking_changes)} breaking, "
            f"{len(non_breaking_changes)} non-breaking, risk: {risk_level}"
        )
        
        return report
    
    def _analyze_fields(
        self,
        old_fields: Dict[str, FieldDefinition],
        new_fields: Dict[str, FieldDefinition]
    ) -> Tuple[List[Change], List[Change]]:
        breaking = []
        non_breaking = []
        
        old_field_names = set(old_fields.keys())
        new_field_names = set(new_fields.keys())
        
        removed = old_field_names - new_field_names
        for field in removed:
            breaking.append(Change(
                type="FIELD_REMOVED",
                field=field,
                description=f"Field '{field}' was removed",
                old_value=old_fields[field].type,
                new_value=None,
                impact="Consumers reading this field will fail"
            ))
        
        added = new_field_names - old_field_names
        for field in added:
            if new_fields[field].required:
                breaking.append(Change(
                    type="REQUIRED_FIELD_ADDED",
                    field=field,
                    description=f"Required field '{field}' was added",
                    old_value=None,
                    new_value=new_fields[field].type,
                    impact="Existing data missing this field will fail validation"
                ))
            else:
                non_breaking.append(Change(
                    type="OPTIONAL_FIELD_ADDED",
                    field=field,
                    description=f"Optional field '{field}' was added",
                    old_value=None,
                    new_value=new_fields[field].type,
                    impact="No impact on existing consumers"
                ))
        
        common = old_field_names & new_field_names
        for field in common:
            field_breaking, field_non_breaking = self._analyze_field_spec(
                field,
                old_fields[field],
                new_fields[field]
            )
            breaking.extend(field_breaking)
            non_breaking.extend(field_non_breaking)
        
        return breaking, non_breaking
    
    def _analyze_field_spec(
        self,
        field_name: str,
        old_spec: FieldDefinition,
        new_spec: FieldDefinition
    ) -> Tuple[List[Change], List[Change]]:
        breaking = []
        non_breaking = []
        
        if old_spec.type != new_spec.type:
            breaking.append(Change(
                type="TYPE_CHANGED",
                field=field_name,
                description=f"Type changed from {old_spec.type} to {new_spec.type}",
                old_value=old_spec.type,
                new_value=new_spec.type,
                impact="Existing data may fail type validation"
            ))
        
        if not old_spec.required and new_spec.required:
            breaking.append(Change(
                type="FIELD_MADE_REQUIRED",
                field=field_name,
                description=f"Field '{field_name}' made required",
                old_value=False,
                new_value=True,
                impact="Data missing this field will fail validation"
            ))
        elif old_spec.required and not new_spec.required:
            non_breaking.append(Change(
                type="FIELD_MADE_OPTIONAL",
                field=field_name,
                description=f"Field '{field_name}' made optional",
                old_value=True,
                new_value=False,
                impact="No impact - more permissive"
            ))
        
        if old_spec.pattern != new_spec.pattern:
            if self._is_pattern_stricter(old_spec.pattern, new_spec.pattern):
                breaking.append(Change(
                    type="PATTERN_STRICTER",
                    field=field_name,
                    description=f"Pattern made stricter",
                    old_value=old_spec.pattern,
                    new_value=new_spec.pattern,
                    impact="Some previously valid values may fail"
                ))
            else:
                non_breaking.append(Change(
                    type="PATTERN_RELAXED",
                    field=field_name,
                    description=f"Pattern made more permissive",
                    old_value=old_spec.pattern,
                    new_value=new_spec.pattern,
                    impact="More values will pass validation"
                ))
        
        if self._is_range_narrower(old_spec, new_spec):
            breaking.append(Change(
                type="CONSTRAINT_TIGHTENED",
                field=field_name,
                description=f"Numeric constraints tightened",
                old_value={"min": old_spec.min, "max": old_spec.max},
                new_value={"min": new_spec.min, "max": new_spec.max},
                impact="Values outside new range will fail"
            ))
        elif self._is_range_wider(old_spec, new_spec):
            non_breaking.append(Change(
                type="CONSTRAINT_RELAXED",
                field=field_name,
                description=f"Numeric constraints relaxed",
                old_value={"min": old_spec.min, "max": old_spec.max},
                new_value={"min": new_spec.min, "max": new_spec.max},
                impact="More values will pass validation"
            ))
        
        if old_spec.format != new_spec.format:
            breaking.append(Change(
                type="FORMAT_CHANGED",
                field=field_name,
                description=f"Format changed from {old_spec.format} to {new_spec.format}",
                old_value=old_spec.format,
                new_value=new_spec.format,
                impact="Values valid in old format may fail"
            ))
        
        if old_spec.enum != new_spec.enum:
            if new_spec.enum is not None:
                old_set = set(old_spec.enum) if old_spec.enum else set()
                new_set = set(new_spec.enum)
                
                if new_set < old_set:
                    breaking.append(Change(
                        type="ENUM_VALUES_REMOVED",
                        field=field_name,
                        description=f"Enum values restricted",
                        old_value=old_spec.enum,
                        new_value=new_spec.enum,
                        impact="Some previously valid values no longer allowed"
                    ))
                elif new_set > old_set:
                    non_breaking.append(Change(
                        type="ENUM_VALUES_ADDED",
                        field=field_name,
                        description=f"Enum values expanded",
                        old_value=old_spec.enum,
                        new_value=new_spec.enum,
                        impact="More values now allowed"
                    ))
        
        return breaking, non_breaking
    
    def _is_pattern_stricter(
        self,
        old_pattern: Optional[str],
        new_pattern: Optional[str]
    ) -> bool:
        if old_pattern is None and new_pattern is not None:
            return True
        
        if old_pattern is not None and new_pattern is None:
            return False
        
        if old_pattern == new_pattern:
            return False
        
        if new_pattern and old_pattern:
            return len(new_pattern) > len(old_pattern)
        
        return False
    
    def _is_range_narrower(
        self,
        old_spec: FieldDefinition,
        new_spec: FieldDefinition
    ) -> bool:
        min_tighter = (
            new_spec.min is not None and
            (old_spec.min is None or new_spec.min > old_spec.min)
        )
        
        max_tighter = (
            new_spec.max is not None and
            (old_spec.max is None or new_spec.max < old_spec.max)
        )
        
        return min_tighter or max_tighter
    
    def _is_range_wider(
        self,
        old_spec: FieldDefinition,
        new_spec: FieldDefinition
    ) -> bool:
        min_relaxed = (
            old_spec.min is not None and
            (new_spec.min is None or new_spec.min < old_spec.min)
        )
        
        max_relaxed = (
            old_spec.max is not None and
            (new_spec.max is None or new_spec.max > old_spec.max)
        )
        
        return min_relaxed or max_relaxed
    
    def _calculate_risk_score(
        self,
        breaking_changes: List[Change],
        non_breaking_changes: List[Change]
    ) -> int:
        score = (len(breaking_changes) * 15) + (len(non_breaking_changes) * 3)
        return min(score, 100)
    
    def _get_risk_level(self, score: int) -> str:
        if score <= 20:
            return "LOW"
        elif score <= 50:
            return "MEDIUM"
        elif score <= 80:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _generate_summary(
        self,
        breaking_changes: List[Change],
        non_breaking_changes: List[Change],
        risk_level: str
    ) -> str:
        total = len(breaking_changes) + len(non_breaking_changes)
        
        if total == 0:
            return "No changes detected"
        
        parts = []
        
        if breaking_changes:
            parts.append(f"{len(breaking_changes)} breaking change(s)")
        
        if non_breaking_changes:
            parts.append(f"{len(non_breaking_changes)} non-breaking change(s)")
        
        summary = f"Detected {', '.join(parts)}. Risk level: {risk_level}."
        
        if breaking_changes:
            summary += " This update requires a major version bump."
        elif non_breaking_changes:
            summary += " This update requires a minor version bump."
        
        return summary