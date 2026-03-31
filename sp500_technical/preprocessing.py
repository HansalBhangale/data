"""
Preprocessing for technical features.
Clips outliers, computes sector z-scores, merges with target variables.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .config import (
    TECH_CLIP_BOUNDS, TECH_SECTOR_NORM_COLS, TECH_EXCLUDE_COLS,
    ALL_TECH_FEATURES,
)


def clip_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clip extreme values for technical features.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with technical feature columns

    Returns
    -------
    pd.DataFrame
        DataFrame with clipped values
    """
    df = df.copy()

    for col, (lower, upper) in TECH_CLIP_BOUNDS.items():
        if col in df.columns:
            df[col] = df[col].clip(lower=lower, upper=upper)

    return df


def compute_sector_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute z-scores within sector x year for technical features.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'sector', 'year', and technical feature columns

    Returns
    -------
    pd.DataFrame
        DataFrame with sector z-score columns added
    """
    df = df.copy()

    if 'sector' not in df.columns or 'year' not in df.columns:
        print("  WARNING: Missing 'sector' or 'year' columns. Skipping sector normalization.")
        return df

    for col in TECH_SECTOR_NORM_COLS:
        if col not in df.columns:
            continue

        zscore_col = f'{col}_sector_zscore'

        df[zscore_col] = df.groupby(['sector', 'year'])[col].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )

        # Clip extreme z-scores
        df[zscore_col] = df[zscore_col].clip(-5, 5)

    return df


def merge_with_targets(
    tech_df: pd.DataFrame,
    fundamental_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge technical features with target variables from fundamental dataset.

    Parameters
    ----------
    tech_df : pd.DataFrame
        Technical features DataFrame with columns: ticker, quarter_end, year, quarter, [features]
    fundamental_df : pd.DataFrame
        Fundamental dataset with target columns: excess_return_1y, excess_return_1y_rank

    Returns
    -------
    pd.DataFrame
        Merged DataFrame with technical features and targets
    """
    # Select target columns from fundamental data
    target_cols = ['ticker', 'quarter_end', 'excess_return_1y', 'excess_return_1y_rank']
    available_targets = [c for c in target_cols if c in fundamental_df.columns]

    if 'excess_return_1y_rank' not in fundamental_df.columns:
        raise ValueError("fundamental_df must contain 'excess_return_1y_rank' column")

    targets = fundamental_df[available_targets].copy()

    # Ensure quarter_end is datetime in both DataFrames
    targets['quarter_end'] = pd.to_datetime(targets['quarter_end'])
    tech_df = tech_df.copy()
    tech_df['quarter_end'] = pd.to_datetime(tech_df['quarter_end'])

    # Merge on ticker + quarter_end
    merged = tech_df.merge(targets, on=['ticker', 'quarter_end'], how='inner')

    # Drop rows where target is NaN
    merged = merged.dropna(subset=['excess_return_1y_rank'])

    print(f"\nMerged technical features with targets:")
    print(f"  Technical rows: {len(tech_df)}")
    print(f"  Merged rows: {len(merged)}")
    print(f"  Tickers: {merged['ticker'].nunique()}")
    print(f"  Quarters: {merged['quarter_end'].nunique()}")

    return merged


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """
    Get list of feature columns for the technical model.

    Includes all technical features + sector z-score variants.
    Excludes identifiers, dates, and target columns.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed technical DataFrame

    Returns
    -------
    List[str]
        Feature column names
    """
    exclude_set = set(TECH_EXCLUDE_COLS)

    feature_cols = []
    for col in df.columns:
        if col in exclude_set:
            continue
        if col in ['sector', 'quarter_label']:
            continue
        feature_cols.append(col)

    return feature_cols


def preprocess_technical_data(
    tech_df: pd.DataFrame,
    fundamental_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Full preprocessing pipeline for technical data.

    Steps:
    1. Clip outliers
    2. Compute sector z-scores
    3. Merge with target variables

    Parameters
    ----------
    tech_df : pd.DataFrame
        Raw technical features DataFrame
    fundamental_df : pd.DataFrame
        Fundamental dataset with targets

    Returns
    -------
    pd.DataFrame
        Preprocessed DataFrame ready for training
    """
    print("\nPreprocessing technical data...")

    # Step 1: Clip outliers
    print("  - Clipping outliers...")
    df = clip_outliers(tech_df)

    # Step 2: Sector z-scores
    print("  - Computing sector z-scores...")
    df = compute_sector_zscores(df)

    # Step 3: Merge with targets
    print("  - Merging with targets...")
    df = merge_with_targets(df, fundamental_df)

    print(f"\nPreprocessing complete. Shape: {df.shape}")

    return df
