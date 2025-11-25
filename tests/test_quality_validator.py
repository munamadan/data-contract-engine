import pytest
from datetime import datetime, timedelta
from app.core.quality_validator import QualityValidator


def test_freshness_check_pass():
    rules = {
        "freshness": {
            "max_latency_hours": 24
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [{
        "user_id": "usr_123",
        "timestamp": datetime.utcnow().isoformat()
    }]
    
    result = validator.validate(data)
    assert result.passed
    assert len(result.errors) == 0


def test_freshness_check_fail():
    rules = {
        "freshness": {
            "max_latency_hours": 1
        }
    }
    
    validator = QualityValidator(rules)
    
    old_time = datetime.utcnow() - timedelta(hours=3)
    data = [{
        "user_id": "usr_123",
        "timestamp": old_time.isoformat()
    }]
    
    result = validator.validate(data)
    assert not result.passed
    assert len(result.errors) == 1
    assert result.errors[0].rule_type == "FRESHNESS"


def test_completeness_row_count():
    rules = {
        "completeness": {
            "min_row_count": 100
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [{"user_id": f"usr_{i}"} for i in range(50)]
    
    result = validator.validate(data)
    assert not result.passed
    assert any(e.rule_type == "COMPLETENESS" for e in result.errors)


def test_completeness_null_percentage():
    rules = {
        "completeness": {
            "max_null_percentage": 5
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [
        {"user_id": "usr_1", "email": "test@example.com"},
        {"user_id": "usr_2", "email": None},
        {"user_id": "usr_3", "email": None}
    ]
    
    result = validator.validate(data)
    assert not result.passed


def test_uniqueness_check_pass():
    rules = {
        "uniqueness": {
            "fields": ["user_id"]
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [
        {"user_id": "usr_1"},
        {"user_id": "usr_2"},
        {"user_id": "usr_3"}
    ]
    
    result = validator.validate(data)
    assert result.passed


def test_uniqueness_check_fail():
    rules = {
        "uniqueness": {
            "fields": ["user_id"]
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [
        {"user_id": "usr_1"},
        {"user_id": "usr_1"},
        {"user_id": "usr_2"}
    ]
    
    result = validator.validate(data)
    assert not result.passed
    assert any(e.rule_type == "UNIQUENESS" for e in result.errors)


def test_statistics_mean():
    rules = {
        "statistics": {
            "age": {
                "mean": {"min": 18, "max": 50}
            }
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [
        {"age": 20},
        {"age": 25},
        {"age": 30}
    ]
    
    result = validator.validate(data)
    assert result.passed


def test_quality_score_calculation():
    rules = {
        "completeness": {
            "min_row_count": 100
        }
    }
    
    validator = QualityValidator(rules)
    
    data = [{"user_id": f"usr_{i}"} for i in range(50)]
    
    result = validator.validate(data)
    assert result.quality_score < 100
    assert result.quality_score >= 0