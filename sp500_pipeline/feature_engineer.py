"""
Feature Engineering
====================
Computes derived financial features from raw quarterly data:
  - Growth metrics (QoQ, YoY)
  - Profitability ratios
  - Financial health indicators
  - Cash flow quality metrics
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide two series, returning NaN where denominator is zero or NaN."""
    return np.where(
        (denominator == 0) | denominator.isna() | numerator.isna(),
        np.nan,
        numerator / denominator,
    )


def _pct_change_periods(series: pd.Series, periods: int) -> pd.Series:
    """
    Compute percentage change over N periods.
    Uses absolute value of base to handle negative base values correctly.
    """
    shifted = series.shift(periods)
    return np.where(
        (shifted == 0) | shifted.isna() | series.isna(),
        np.nan,
        (series - shifted) / shifted.abs(),
    )


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all derived financial features from raw quarterly data.
    
    The input DataFrame must have columns:
      ticker, quarter_end, revenue, cost_of_revenue, gross_profit,
      operating_income, net_income, total_assets, total_liabilities,
      stockholders_equity, cash_and_equivalents, current_assets,
      current_liabilities, operating_cash_flow, capital_expenditures,
      free_cash_flow, total_debt, ebitda
    
    Missing columns are handled gracefully — corresponding features become NaN.
    
    Args:
        df: Raw quarterly financials DataFrame
        
    Returns:
        DataFrame with additional feature columns appended
    """
    logger.info(f"Computing features for {df['ticker'].nunique()} companies...")
    
    result = df.copy()
    
    # Sort by ticker and date for correct time-series calculations
    result = result.sort_values(["ticker", "quarter_end"]).reset_index(drop=True)
    
    # ═══════════════════════════════════════════════════════════
    # Growth Metrics (computed per-company)
    # ═══════════════════════════════════════════════════════════
    
    # Compute growth metrics per company using explicit loop
    # (avoids pandas 3.0 groupby().apply() dropping the groupby column)
    growth_parts = []
    for ticker, group in result.groupby("ticker"):
        g = group.copy()
        
        # Revenue growth
        if "revenue" in g.columns:
            g["revenue_qoq_growth"] = _pct_change_periods(g["revenue"], 1)
            g["revenue_yoy_growth"] = _pct_change_periods(g["revenue"], 4)
        
        # Net Income growth
        if "net_income" in g.columns:
            g["net_income_yoy_growth"] = _pct_change_periods(g["net_income"], 4)
        
        # Operating Income growth
        if "operating_income" in g.columns:
            g["operating_income_yoy_growth"] = _pct_change_periods(g["operating_income"], 4)
        
        # Total Assets growth
        if "total_assets" in g.columns:
            g["total_assets_yoy_growth"] = _pct_change_periods(g["total_assets"], 4)
        
        growth_parts.append(g)
    
    result = pd.concat(growth_parts, ignore_index=True)
    
    # ═══════════════════════════════════════════════════════════
    # Profitability Ratios
    # ═══════════════════════════════════════════════════════════
    
    rev = result.get("revenue", pd.Series(dtype=float, index=result.index))
    
    # Gross Margin = Gross Profit / Revenue
    if "gross_profit" in result.columns:
        result["gross_margin"] = _safe_divide(result["gross_profit"], rev)
    
    # Operating Margin = Operating Income / Revenue
    if "operating_income" in result.columns:
        result["operating_margin"] = _safe_divide(result["operating_income"], rev)
    
    # Net Margin = Net Income / Revenue
    if "net_income" in result.columns:
        result["net_margin"] = _safe_divide(result["net_income"], rev)
    
    # ROA = Net Income / Total Assets
    if "net_income" in result.columns and "total_assets" in result.columns:
        result["roa"] = _safe_divide(result["net_income"], result["total_assets"])
    
    # ROE = Net Income / Stockholders' Equity
    if "net_income" in result.columns and "stockholders_equity" in result.columns:
        result["roe"] = _safe_divide(result["net_income"], result["stockholders_equity"])
    
    # ═══════════════════════════════════════════════════════════
    # Financial Health Indicators
    # ═══════════════════════════════════════════════════════════
    
    # Debt-to-Equity = Total Liabilities / Stockholders' Equity
    if "total_liabilities" in result.columns and "stockholders_equity" in result.columns:
        result["debt_to_equity"] = _safe_divide(
            result["total_liabilities"], result["stockholders_equity"]
        )
    
    # Current Ratio = Current Assets / Current Liabilities
    if "current_assets" in result.columns and "current_liabilities" in result.columns:
        result["current_ratio"] = _safe_divide(
            result["current_assets"], result["current_liabilities"]
        )
    
    # Cash Ratio = Cash / Current Liabilities
    if "cash_and_equivalents" in result.columns and "current_liabilities" in result.columns:
        result["cash_ratio"] = _safe_divide(
            result["cash_and_equivalents"], result["current_liabilities"]
        )
    
    # ═══════════════════════════════════════════════════════════
    # Cash Flow Quality
    # ═══════════════════════════════════════════════════════════
    
    # FCF Margin = Free Cash Flow / Revenue
    if "free_cash_flow" in result.columns:
        result["fcf_margin"] = _safe_divide(result["free_cash_flow"], rev)
    
    # Cash Flow Quality = Operating CF / Net Income
    if "operating_cash_flow" in result.columns and "net_income" in result.columns:
        result["cf_quality"] = _safe_divide(
            result["operating_cash_flow"], result["net_income"]
        )
    
    logger.info(
        f"Feature engineering complete. "
        f"Added {len(result.columns) - len(df.columns)} new columns. "
        f"Total columns: {len(result.columns)}"
    )
    
    return result
