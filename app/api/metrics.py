from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date, datetime, timedelta
from typing import Optional

from app.database import get_db
from app.core.metrics_aggregator import MetricsAggregator
from app.models.schemas import DailyMetrics, TrendData, PlatformSummary
from app.models.database import Contract, QualityMetric
from app.utils.exceptions import ContractNotFoundError


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/{contract_id}/daily")
async def get_daily_metrics(
    contract_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    metrics = db.query(QualityMetric).filter(
        QualityMetric.contract_id == str(contract_id),
        QualityMetric.metric_date >= start_date,
        QualityMetric.metric_date <= end_date
    ).order_by(QualityMetric.metric_date).all()
    
    if not metrics:
        return {"metrics": [], "period_summary": {}}
    
    avg_pass_rate = sum(m.pass_rate for m in metrics) / len(metrics)
    total_validations = sum(m.total_validations for m in metrics)
    
    aggregator = MetricsAggregator(db)
    pass_rates = [m.pass_rate for m in metrics]
    trend = aggregator._calculate_trend(pass_rates)
    
    return {
        "metrics": [DailyMetrics.from_orm(m) for m in metrics],
        "period_summary": {
            "avg_pass_rate": round(avg_pass_rate, 2),
            "total_validations": total_validations,
            "trend": trend
        }
    }


@router.get("/{contract_id}/trend")
async def get_trend_data(
    contract_id: UUID,
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db)
):
    aggregator = MetricsAggregator(db)
    trend_data = aggregator.get_trend_data(str(contract_id), days)
    return trend_data


@router.get("/{contract_id}/errors/top")
async def get_top_errors(
    contract_id: UUID,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    metrics = db.query(QualityMetric).filter(
        QualityMetric.contract_id == str(contract_id),
        QualityMetric.metric_date >= start_date
    ).all()
    
    all_errors = {}
    for m in metrics:
        if m.top_errors:
            for error_type, count in m.top_errors.items():
                all_errors[error_type] = all_errors.get(error_type, 0) + count
    
    total_errors = sum(all_errors.values())
    
    top_errors = sorted(all_errors.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    errors_list = [
        {
            "error_type": error_type,
            "count": count,
            "percentage": round(count / total_errors * 100, 2) if total_errors > 0 else 0
        }
        for error_type, count in top_errors
    ]
    
    return {
        "errors": errors_list,
        "total_errors": total_errors,
        "period": f"{days} days"
    }


@router.get("/summary")
async def get_platform_summary(db: Session = Depends(get_db)):
    total_contracts = db.query(Contract).count()
    active_contracts = db.query(Contract).filter(Contract.is_active == True).count()
    
    today = date.today()
    today_metrics = db.query(QualityMetric).filter(
        QualityMetric.metric_date == today
    ).all()
    
    total_validations_today = sum(m.total_validations for m in today_metrics)
    
    if today_metrics:
        avg_pass_rate = sum(m.pass_rate for m in today_metrics) / len(today_metrics)
    else:
        avg_pass_rate = 0.0
    
    seven_days_ago = today - timedelta(days=7)
    recent_metrics = db.query(QualityMetric).filter(
        QualityMetric.metric_date >= seven_days_ago
    ).all()
    
    contract_scores = {}
    for m in recent_metrics:
        if m.contract_id not in contract_scores:
            contract_scores[m.contract_id] = []
        contract_scores[m.contract_id].append(m.quality_score)
    
    contract_avg_scores = {
        cid: sum(scores) / len(scores)
        for cid, scores in contract_scores.items()
    }
    
    top_performers = sorted(contract_avg_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    needs_attention = sorted(contract_avg_scores.items(), key=lambda x: x[1])[:5]
    
    def get_contract_info(contract_id, score):
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        return {
            "contract_id": str(contract_id),
            "name": contract.name if contract else "Unknown",
            "quality_score": round(score, 2)
        }
    
    return {
        "total_contracts": total_contracts,
        "active_contracts": active_contracts,
        "total_validations_today": total_validations_today,
        "avg_pass_rate": round(avg_pass_rate, 2),
        "top_performing_contracts": [get_contract_info(cid, score) for cid, score in top_performers],
        "contracts_needing_attention": [get_contract_info(cid, score) for cid, score in needs_attention]
    }


@router.get("/{contract_id}/quality-score")
async def get_quality_score(
    contract_id: UUID,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    metrics = db.query(QualityMetric).filter(
        QualityMetric.contract_id == str(contract_id),
        QualityMetric.metric_date >= start_date
    ).order_by(QualityMetric.metric_date.desc()).all()
    
    if not metrics:
        raise ContractNotFoundError(f"No metrics found for contract {contract_id}")
    
    latest = metrics[0]
    quality_scores = [m.quality_score for m in metrics]
    
    aggregator = MetricsAggregator(db)
    trend = aggregator._calculate_trend(quality_scores)
    
    pass_rate_component = latest.pass_rate * 0.7
    consistency_score = aggregator._calculate_consistency_score(str(contract_id))
    consistency_component = consistency_score * 0.2
    freshness_component = min(latest.total_validations / 1000, 1.0) * 10
    
    return {
        "quality_score": latest.quality_score,
        "components": {
            "pass_rate_score": round(pass_rate_component, 2),
            "consistency_score": round(consistency_component, 2),
            "freshness_score": round(freshness_component, 2)
        },
        "trend": trend,
        "last_updated": latest.created_at
    }