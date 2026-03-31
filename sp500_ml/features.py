"""
Feature set definition and selection.
"""

import pandas as pd
from typing import List, Set
from .config import (
    BALANCE_SHEET_COLS, INCOME_STATEMENT_COLS, CASH_FLOW_COLS,
    PROFITABILITY_COLS, LIQUIDITY_COLS, GROWTH_COLS, VALUATION_COLS,
    TTM_COLS, MARKET_COLS, TARGET_COLS, EXCLUDE_COLS, SECTOR_NORMALIZE_COLS
)


def get_exclude_columns() -> List[str]:
    """Get list of columns to exclude from features."""
    return EXCLUDE_COLS.copy()


def get_target_columns() -> List[str]:
    """Get list of target columns."""
    return TARGET_COLS.copy()


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """
    Get list of feature columns for the model.

    Includes:
    - Balance sheet items
    - Income statement items (TTM preferred)
    - Cash flow items
    - Profitability ratios
    - Liquidity metrics
    - Growth metrics
    - Valuation metrics
    - Engineered features
    - Rolling volatility features
    - Sector z-scores
    - Temporal lags
    - Year and quarter

    Excludes:
    - Identifiers (ticker, cik, entity_name)
    - Dates (quarter_end, etc.)
    - Text columns (sector, sub_industry)
    - Target columns
    - Market data that could leak (stock_price, avg_daily_volume)
    """
    exclude_set = set(EXCLUDE_COLS)

    # Add sector z-score suffix
    sector_zscore_cols = [f'{col}_sector_zscore' for col in SECTOR_NORMALIZE_COLS]

    # Temporal lag suffixes
    lag_suffixes = ['_lag_1', '_lag_2', '_lag_4']

    feature_cols = []

    for col in df.columns:
        # Skip excluded columns
        if col in exclude_set:
            continue

        # Skip derived identifier columns
        if col in ['gics_sector', 'quarter_label', 'quarter_end_std']:
            continue

        # Skip price return (temporary for volatility calc)
        if col == 'price_return':
            continue

        # Include all other columns
        feature_cols.append(col)

    # Ensure year and quarter are included
    if 'year' not in feature_cols and 'year' in df.columns:
        feature_cols.append('year')
    if 'quarter' not in feature_cols and 'quarter' in df.columns:
        feature_cols.append('quarter')

    return feature_cols


def get_feature_stats(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """
    Get statistics for feature columns (missing %, dtype, unique count).
    """
    stats = []
    for col in feature_cols:
        if col in df.columns:
            stats.append({
                'column': col,
                'missing_pct': df[col].isna().mean() * 100,
                'dtype': str(df[col].dtype),
                'unique_count': df[col].nunique(),
                'min': df[col].min() if df[col].dtype in ['float64', 'int64'] else None,
                'max': df[col].max() if df[col].dtype in ['float64', 'int64'] else None,
            })

    return pd.DataFrame(stats)


def print_feature_summary(df: pd.DataFrame, feature_cols: List[str]) -> None:
    """Print summary of feature columns."""
    print(f"\nFeature Summary:")
    print(f"  Total features: {len(feature_cols)}")

    # Count by category
    categories = {
        'Balance Sheet': BALANCE_SHEET_COLS,
        'Income Statement': INCOME_STATEMENT_COLS,
        'Cash Flow': CASH_FLOW_COLS,
        'Profitability': PROFITABILITY_COLS,
        'Liquidity': LIQUIDITY_COLS,
        'Growth': GROWTH_COLS,
        'Valuation': VALUATION_COLS,
        'TTM': TTM_COLS,
    }

    for cat_name, cat_cols in categories.items():
        count = sum(1 for c in cat_cols if c in feature_cols)
        print(f"  {cat_name}: {count} features")

    # Count engineered features
    engineered = ['asset_turnover', 'interest_coverage', 'cash_to_debt',
                  'earnings_quality', 'log_market_cap', 'net_debt',
                  'leverage_ratio', 'capex_to_revenue', 'working_capital_ratio',
                  'fcf_yield']
    engineered_count = sum(1 for c in engineered if c in feature_cols)
    print(f"  Engineered: {engineered_count} features")

    # Count volatility features
    vol_features = [c for c in feature_cols if 'volatility' in c or c.endswith('_vol')]
    print(f"  Volatility: {len(vol_features)} features")

    # Count sector z-score features
    zscore_features = [c for c in feature_cols if c.endswith('_sector_zscore')]
    print(f"  Sector Z-scores: {len(zscore_features)} features")

    # Count lag features
    lag_features = [c for c in feature_cols if '_lag_' in c]
    print(f"  Temporal Lags: {len(lag_features)} features")

    # Count momentum features
    momentum_features = [c for c in feature_cols if '_momentum' in c]
    print(f"  Momentum: {len(momentum_features)} features")