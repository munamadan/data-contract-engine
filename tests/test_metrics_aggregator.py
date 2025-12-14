import pytest
from datetime import date, timedelta
from app.core.metrics_aggregator import MetricsAggregator


class TestMetricsAggregator:
    
    def test_calculate_daily_metrics(self, db_session, sample_contract, sample_validations):
        aggregator = MetricsAggregator(db_session)
        
        metrics = aggregator.calculate_daily_metrics(
            contract_id=sample_contract.id,
            target_date=date.today()
        )
        
        assert metrics.total_validations > 0
        assert 0 <= metrics.pass_rate <= 100
        assert metrics.quality_score >= 0
    
    def test_quality_score_calculation(self, db_session, sample_contract):
        aggregator = MetricsAggregator(db_session)
        
        score = aggregator._calculate_quality_score(
            pass_rate=95.0,
            total_validations=1000,
            error_variety=3,
            contract_id=sample_contract.id
        )
        
        assert 0 <= score <= 100
        assert score > 90
    
    def test_get_trend_data(self, db_session, sample_contract, sample_metrics):
        aggregator = MetricsAggregator(db_session)
        
        trend = aggregator.get_trend_data(sample_contract.id, days=7)
        
        assert trend.days == 7
        assert trend.pass_rate_trend in ['INCREASING', 'DECREASING', 'STABLE']