"""
Data preprocessing module.
Handles cleaning, forward-fill, outlier clipping, feature engineering,
rolling volatility, and sector normalization.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from .config import (
    ANNUAL_FFILL_COLS, CLIP_BOUNDS, SECTOR_NORMALIZE_COLS,
    GICS_SECTOR_MAPPING, TEMPORAL_LAGS
)


def map_to_gics_sector(sub_industry: str) -> str:
    """Map sub-industry to GICS sector."""
    return GICS_SECTOR_MAPPING.get(sub_industry, 'Unknown')


def forward_fill_annual_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Forward-fill annual-only fields per ticker.
    Cash flow columns are ~88% available for Q1 but only ~3% for Q2/Q3.
    """
    df = df.copy()

    # Sort by ticker and quarter_end
    df = df.sort_values(['ticker', 'quarter_end']).reset_index(drop=True)

    # Forward fill per ticker
    for col in ANNUAL_FFILL_COLS:
        if col in df.columns:
            df[col] = df.groupby('ticker')[col].ffill()

    return df


def clip_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clip extreme values to reasonable bounds.
    """
    df = df.copy()

    for col, (lower, upper) in CLIP_BOUNDS.items():
        if col in df.columns:
            df[col] = df[col].clip(lower=lower, upper=upper)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create new engineered features from existing columns.
    """
    df = df.copy()

    # Asset turnover
    if 'revenue' in df.columns and 'total_assets' in df.columns:
        df['asset_turnover'] = df['revenue'] / df['total_assets'].replace(0, np.nan)

    # Interest coverage
    if 'ebit' in df.columns and 'interest_expense' in df.columns:
        df['interest_coverage'] = df['ebit'] / df['interest_expense'].replace(0, np.nan)
        df['interest_coverage'] = df['interest_coverage'].clip(upper=50)  # Cap extreme values

    # Cash to debt
    if 'cash_and_equivalents' in df.columns and 'total_debt' in df.columns:
        df['cash_to_debt'] = df['cash_and_equivalents'] / df['total_debt'].replace(0, np.nan)
        df['cash_to_debt'] = df['cash_to_debt'].clip(upper=5)  # Cap extreme values

    # Earnings quality (OCF / Net Income)
    if 'operating_cash_flow' in df.columns and 'net_income' in df.columns:
        df['earnings_quality'] = df['operating_cash_flow'] / df['net_income'].replace(0, np.nan)
        df['earnings_quality'] = df['earnings_quality'].clip(-10, 10)

    # Log market cap
    if 'market_cap' in df.columns:
        df['log_market_cap'] = np.log1p(df['market_cap'])

    # Net debt
    if 'total_debt' in df.columns and 'cash_and_equivalents' in df.columns:
        df['net_debt'] = df['total_debt'] - df['cash_and_equivalents']

    # Leverage ratio
    if 'total_debt' in df.columns and 'total_assets' in df.columns:
        df['leverage_ratio'] = df['total_debt'] / df['total_assets'].replace(0, np.nan)
        df['leverage_ratio'] = df['leverage_ratio'].clip(upper=5)

    # Capex to revenue
    if 'capital_expenditures' in df.columns and 'revenue' in df.columns:
        # Handle negative capex (common)
        capex = df['capital_expenditures'].abs()
        df['capex_to_revenue'] = capex / df['revenue'].replace(0, np.nan)
        df['capex_to_revenue'] = df['capex_to_revenue'].clip(upper=1)

    # Working capital ratio
    if 'current_assets' in df.columns and 'current_liabilities' in df.columns and 'total_assets' in df.columns:
        df['working_capital_ratio'] = (
            (df['current_assets'] - df['current_liabilities']) /
            df['total_assets'].replace(0, np.nan)
        )

    # FCF yield (using market cap)
    if 'free_cash_flow' in df.columns and 'market_cap' in df.columns:
        df['fcf_yield'] = df['free_cash_flow'] / df['market_cap'].replace(0, np.nan)
        df['fcf_yield'] = df['fcf_yield'].clip(-0.5, 0.5)

    return df


def compute_rolling_volatility(df: pd.DataFrame, window: int = 8) -> pd.DataFrame:
    """
    Compute rolling volatility features per ticker.
    Uses backward-looking data only to avoid target leakage.

    IMPORTANT: We compute volatility from stock_price percent changes,
    NOT from forward returns, to avoid target leakage.
    """
    df = df.copy()

    # Sort by ticker and quarter_end
    df = df.sort_values(['ticker', 'quarter_end']).reset_index(drop=True)

    # Stock price return volatility (backward-looking)
    if 'stock_price' in df.columns:
        df['price_return'] = df.groupby('ticker')['stock_price'].pct_change()
        df['return_volatility'] = df.groupby('ticker')['price_return'].transform(
            lambda x: x.rolling(window, min_periods=4).std()
        )
        df = df.drop(columns=['price_return'])

    # Revenue growth volatility
    if 'revenue_qoq_growth' in df.columns:
        df['revenue_growth_vol'] = df.groupby('ticker')['revenue_qoq_growth'].transform(
            lambda x: x.rolling(window, min_periods=4).std()
        )

    # Net income volatility (using yoy growth for stability)
    if 'net_income_yoy_growth' in df.columns:
        df['net_income_vol'] = df.groupby('ticker')['net_income_yoy_growth'].transform(
            lambda x: x.rolling(window, min_periods=4).std()
        )

    # Operating margin volatility
    if 'operating_margin' in df.columns:
        df['operating_margin_vol'] = df.groupby('ticker')['operating_margin'].transform(
            lambda x: x.rolling(window, min_periods=4).std()
        )

    return df


def compute_sector_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute z-scores within sector x quarter for specified columns.
    Maps sub_industry to GICS sector first for stable normalization.
    """
    df = df.copy()

    # Map sub_industry to GICS sector
    df['gics_sector'] = df['sub_industry'].apply(map_to_gics_sector)

    # Compute z-scores within sector x quarter
    for col in SECTOR_NORMALIZE_COLS:
        if col in df.columns:
            zscore_col = f'{col}_sector_zscore'

            # Group by sector and year (not quarter for more stable estimates)
            df[zscore_col] = df.groupby(['gics_sector', 'year'])[col].transform(
                lambda x: (x - x.mean()) / (x.std() + 1e-8)
            )

            # Clip extreme z-scores
            df[zscore_col] = df[zscore_col].clip(-5, 5)

    return df


def add_temporal_lags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal lag features (t-1, t-2, t-4) for specified columns.
    This captures temporal patterns without needing LSTM.

    Also adds momentum features (ratio of current to lagged value).
    """
    df = df.copy()

    # Sort by ticker and quarter_end
    df = df.sort_values(['ticker', 'quarter_end']).reset_index(drop=True)

    lags = TEMPORAL_LAGS['feature_lags']
    lag_features = TEMPORAL_LAGS['lag_features']

    for col in lag_features:
        if col not in df.columns:
            continue

        for lag in lags:
            lag_col = f'{col}_lag_{lag}'
            df[lag_col] = df.groupby('ticker')[col].shift(lag)

    # Momentum features (current / lag-1)
    for col in TEMPORAL_LAGS['momentum_features']:
        if col not in df.columns:
            continue

        lag1_col = f'{col}_lag_1'
        if lag1_col in df.columns:
            momentum_col = f'{col}_momentum'
            df[momentum_col] = df[col] / df[lag1_col].replace(0, np.nan)
            df[momentum_col] = df[momentum_col].clip(0.1, 10)  # Cap extreme ratios

    return df


def normalize_target_within_quarter(df: pd.DataFrame, target_cols: List[str]) -> pd.DataFrame:
    """
    Rank-normalize target within each quarter to remove regime effects.
    This is the standard approach in quant finance to handle regime shifts.

    Parameters
    ----------
    df : pd.DataFrame
        Input data with target columns
    target_cols : List[str]
        List of target columns to normalize (e.g., ['excess_return_1y', 'excess_return_3y'])

    Returns
    -------
    pd.DataFrame
        Data with rank-normalized targets added
    """
    df = df.copy()

    for target_col in target_cols:
        if target_col not in df.columns:
            continue

        rank_col = f'{target_col}_rank'
        df[rank_col] = df.groupby('quarter_end')[target_col].rank(pct=True)

    return df


def preprocess_data(df: pd.DataFrame, add_lags: bool = True) -> pd.DataFrame:
    """
    Full preprocessing pipeline.

    Steps:
    1. Forward-fill annual-only fields
    2. Clip outliers
    3. Engineer features
    4. Compute rolling volatility
    5. Compute sector z-scores
    6. Add temporal lag features

    Parameters
    ----------
    df : pd.DataFrame
        Raw input data
    add_lags : bool
        Whether to add temporal lag features (default True)

    Returns
    -------
    pd.DataFrame
        Preprocessed data
    """
    print("Starting preprocessing pipeline...")

    # Step 1: Forward-fill annual-only fields
    print("  - Forward-filling annual fields...")
    df = forward_fill_annual_fields(df)

    # Step 2: Clip outliers
    print("  - Clipping outliers...")
    df = clip_outliers(df)

    # Step 3: Engineer features
    print("  - Engineering features...")
    df = engineer_features(df)

    # Step 4: Compute rolling volatility
    print("  - Computing rolling volatility...")
    df = compute_rolling_volatility(df)

    # Step 5: Compute sector z-scores
    print("  - Computing sector z-scores...")
    df = compute_sector_zscores(df)

    # Step 6: Add temporal lag features
    if add_lags:
        print("  - Adding temporal lag features...")
        df = add_temporal_lags(df)

    print(f"Preprocessing complete. Shape: {df.shape}")

    return df