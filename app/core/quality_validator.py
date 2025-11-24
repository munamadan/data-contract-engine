import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from collections import Counter


class QualityError:
    def __init__(
        self,
        rule_type: str,
        message: str,
        severity: str = "ERROR",
        details: Optional[Dict] = None
    ):
        self.rule_type = rule_type
        self.message = message
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "rule_type": self.rule_type,
            "message": self.message,
            "severity": self.severity,
            "details": self.details
        }


class QualityValidationResult:
    def __init__(
        self,
        passed: bool,
        errors: List[QualityError],
        quality_score: float
    ):
        self.passed = passed
        self.errors = errors
        self.quality_score = quality_score
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def errors_by_severity(self) -> Dict[str, List[QualityError]]:
        result = {"ERROR": [], "WARNING": []}
        for error in self.errors:
            result[error.severity].append(error)
        return result
    
    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "errors": [e.to_dict() for e in self.errors],
            "quality_score": self.quality_score
        }


class QualityValidator:
    def __init__(self, quality_rules: Dict[str, Any]):
        self.rules = quality_rules
        self.logger = logging.getLogger(__name__)
    
    def validate(self, data: Union[Dict, List[Dict]]) -> QualityValidationResult:
        if isinstance(data, dict):
            data = [data]
        
        errors = []
        
        if 'freshness' in self.rules:
            freshness_error = self._check_freshness(data)
            if freshness_error:
                errors.append(freshness_error)
        
        if 'completeness' in self.rules:
            errors.extend(self._check_completeness(data))
        
        if 'uniqueness' in self.rules:
            errors.extend(self._check_uniqueness(data))
        
        if 'statistics' in self.rules:
            errors.extend(self._check_statistics(data))
        
        quality_score = self._calculate_quality_score(errors)
        passed = len([e for e in errors if e.severity == "ERROR"]) == 0
        
        return QualityValidationResult(
            passed=passed,
            errors=errors,
            quality_score=quality_score
        )
    
    def _check_freshness(self, data: List[Dict]) -> Optional[QualityError]:
        max_latency_hours = self.rules['freshness'].get('max_latency_hours')
        if not max_latency_hours:
            return None
        
        timestamp_fields = ['timestamp', 'created_at', 'updated_at', 'date']
        
        for record in data:
            for field in timestamp_fields:
                if field in record:
                    try:
                        if isinstance(record[field], str):
                            ts = datetime.fromisoformat(record[field].replace('Z', '+00:00'))
                        elif isinstance(record[field], (int, float)):
                            ts = datetime.fromtimestamp(record[field])
                        else:
                            continue
                        
                        age_hours = (datetime.now(ts.tzinfo) - ts).total_seconds() / 3600
                        
                        if age_hours > max_latency_hours:
                            return QualityError(
                                rule_type="FRESHNESS",
                                message=f"Data is {age_hours:.1f} hours old, exceeds limit of {max_latency_hours} hours",
                                severity="ERROR",
                                details={"age_hours": age_hours, "max_latency_hours": max_latency_hours}
                            )
                    except Exception as e:
                        self.logger.warning(f"Cannot parse timestamp from {field}: {e}")
                    break
        
        return None
    
    def _check_completeness(self, data: List[Dict]) -> List[QualityError]:
        errors = []
        rules = self.rules['completeness']
        
        min_row_count = rules.get('min_row_count')
        if min_row_count and len(data) < min_row_count:
            errors.append(QualityError(
                rule_type="COMPLETENESS",
                message=f"Insufficient records: got {len(data)}, expected {min_row_count}",
                severity="ERROR",
                details={"actual_count": len(data), "min_count": min_row_count}
            ))
        
        max_null_percentage = rules.get('max_null_percentage')
        if max_null_percentage and data:
            for field in data[0].keys():
                null_count = sum(1 for record in data if record.get(field) is None)
                null_pct = (null_count / len(data)) * 100
                
                if null_pct > max_null_percentage:
                    errors.append(QualityError(
                        rule_type="COMPLETENESS",
                        message=f"Field '{field}' has {null_pct:.1f}% nulls, exceeds {max_null_percentage}% limit",
                        severity="ERROR",
                        details={"field": field, "null_percentage": null_pct}
                    ))
        
        return errors
    
    def _check_uniqueness(self, data: List[Dict]) -> List[QualityError]:
        errors = []
        fields = self.rules['uniqueness'].get('fields', [])
        
        for field in fields:
            values = [record.get(field) for record in data if field in record]
            if not values:
                continue
            
            counter = Counter(values)
            duplicates = {val: count for val, count in counter.items() if count > 1}
            
            if duplicates:
                dup_list = [f"'{val}' ({count}x)" for val, count in list(duplicates.items())[:5]]
                errors.append(QualityError(
                    rule_type="UNIQUENESS",
                    message=f"Duplicate values in '{field}': {', '.join(dup_list)}",
                    severity="ERROR",
                    details={"field": field, "duplicate_count": len(duplicates)}
                ))
        
        return errors
    
    def _check_statistics(self, data: List[Dict]) -> List[QualityError]:
        errors = []
        stats_rules = self.rules['statistics']
        
        for field, constraints in stats_rules.items():
            values = [record.get(field) for record in data if field in record and isinstance(record.get(field), (int, float))]
            
            if not values:
                continue
            
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            
            if 'mean' in constraints:
                mean_constraints = constraints['mean']
                if 'min' in mean_constraints and mean < mean_constraints['min']:
                    errors.append(QualityError(
                        rule_type="STATISTICS",
                        message=f"Field '{field}' mean {mean:.2f} below minimum {mean_constraints['min']}",
                        severity="WARNING",
                        details={"field": field, "mean": mean}
                    ))
                if 'max' in mean_constraints and mean > mean_constraints['max']:
                    errors.append(QualityError(
                        rule_type="STATISTICS",
                        message=f"Field '{field}' mean {mean:.2f} exceeds maximum {mean_constraints['max']}",
                        severity="WARNING",
                        details={"field": field, "mean": mean}
                    ))
            
            if 'std_dev' in constraints:
                std_constraints = constraints['std_dev']
                if 'max' in std_constraints and std_dev > std_constraints['max']:
                    errors.append(QualityError(
                        rule_type="STATISTICS",
                        message=f"Field '{field}' std dev {std_dev:.2f} exceeds maximum {std_constraints['max']}",
                        severity="WARNING",
                        details={"field": field, "std_dev": std_dev}
                    ))
        
        return errors
    
    def _calculate_quality_score(self, errors: List[QualityError]) -> float:
        base_score = 100.0
        
        for error in errors:
            if error.severity == "ERROR":
                base_score -= 10
            elif error.severity == "WARNING":
                base_score -= 3
        
        return max(0.0, base_score)