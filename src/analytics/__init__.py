"""Analytics layer: aggregation queries, engine facade and insights."""

from src.analytics.engine import AnalyticsEngine, build_analytics_bundle, run_analysis_report
from src.analytics.insights import compute_insights

__all__ = [
    "AnalyticsEngine",
    "build_analytics_bundle",
    "compute_insights",
    "run_analysis_report",
]