"""
Components package - UI components for the app
"""

from .header import render_header
from .sidebar import render_sidebar
from .questionnaire import render_questionnaire
from .risk_gauge import render_risk_gauge, render_risk_metrics_row
from .portfolio_table import (
    render_holdings_pie,
    render_holdings_table,
    render_portfolio_summary,
    render_section_header,
    render_sector_allocation,
)
from .backtest_chart import render_backtest_chart, render_performance_metrics
from .metrics_table import (
    render_beat_spy_badge,
    render_metrics_comparison,
    render_max_drawdown,
)

__all__ = [
    'render_header',
    'render_sidebar',
    'render_questionnaire',
    'render_risk_gauge',
    'render_risk_metrics_row',
    'render_holdings_pie',
    'render_holdings_table',
    'render_portfolio_summary',
    'render_section_header',
    'render_sector_allocation',
    'render_backtest_chart',
    'render_performance_metrics',
    'render_beat_spy_badge',
    'render_metrics_comparison',
    'render_max_drawdown',
]
