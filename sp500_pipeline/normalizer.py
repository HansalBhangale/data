"""
Data Normalizer & Cleaner
===========================
Handles final data quality steps:
  - Quarterly date alignment across companies
  - Duplicate removal
  - Outlier winsorization
  - Missing value reporting
"""

import logging

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def normalize_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply final normalization and cleaning to the dataset.
    
    Steps:
      1. Standardize quarter-end dates to calendar quarter-ends
      2. Remove duplicate (ticker, quarter) rows
      3. Winsorize extreme outlier ratios at 1st/99th percentiles
      4. Report coverage statistics
    
    Args:
        df: Full dataset DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    logger.info(f"Normalizing dataset: {len(df)} rows, {len(df.columns)} columns")
    
    result = df.copy()
    initial_rows = len(result)
    
    # ═══════════════════════════════════════════════════════════
    # 1. Standardize Quarter-End Dates
    # ═══════════════════════════════════════════════════════════
    result["quarter_end"] = pd.to_datetime(result["quarter_end"])
    
    # Map each date to the nearest standard calendar quarter-end
    # (March 31, June 30, September 30, December 31)
    result["quarter_end_std"] = result["quarter_end"].dt.to_period("Q").dt.to_timestamp("Q")
    
    # Add human-readable quarter label: "2023Q1", "2023Q2", etc.
    result["quarter_label"] = result["quarter_end"].dt.to_period("Q").astype(str)
    result["year"] = result["quarter_end"].dt.year
    result["quarter"] = result["quarter_end"].dt.quarter
    
    # ═══════════════════════════════════════════════════════════
    # 2. Remove Duplicates
    # ═══════════════════════════════════════════════════════════
    # Keep the most data-rich row if there are duplicates
    before_dedup = len(result)
    
    # Count non-null values per row for tie-breaking
    numeric_cols = result.select_dtypes(include=[np.number]).columns
    result["_completeness"] = result[numeric_cols].notna().sum(axis=1)
    
    result = result.sort_values(
        ["ticker", "quarter_end_std", "_completeness"],
        ascending=[True, True, False],
    )
    result = result.drop_duplicates(subset=["ticker", "quarter_end_std"], keep="first")
    result = result.drop(columns=["_completeness"])
    
    dedup_removed = before_dedup - len(result)
    if dedup_removed > 0:
        logger.info(f"Removed {dedup_removed} duplicate rows")
    
    # ═══════════════════════════════════════════════════════════
    # 3. Winsorize Extreme Outliers
    # ═══════════════════════════════════════════════════════════
    winsorized_cols = []
    for col in config.WINSORIZE_COLUMNS:
        if col in result.columns and result[col].notna().sum() > 10:
            lower = result[col].quantile(config.WINSORIZE_LOWER)
            upper = result[col].quantile(config.WINSORIZE_UPPER)
            
            n_clipped = ((result[col] < lower) | (result[col] > upper)).sum()
            if n_clipped > 0:
                result[col] = result[col].clip(lower=lower, upper=upper)
                winsorized_cols.append(col)
    
    if winsorized_cols:
        logger.info(f"Winsorized {len(winsorized_cols)} columns at {config.WINSORIZE_LOWER:.0%}/{config.WINSORIZE_UPPER:.0%}")
    
    # ═══════════════════════════════════════════════════════════
    # 4. Coverage Statistics
    # ═══════════════════════════════════════════════════════════
    total_tickers = result["ticker"].nunique()
    total_quarters = result["quarter_label"].nunique()
    
    # Per-column coverage
    coverage = {}
    for col in result.columns:
        if result[col].dtype in [np.float64, np.int64, float, int]:
            pct = result[col].notna().mean() * 100
            coverage[col] = f"{pct:.1f}%"
    
    logger.info(f"Dataset: {len(result)} rows, {total_tickers} companies, {total_quarters} quarters")
    logger.info(f"Column coverage (non-null %):")
    for col, pct in sorted(coverage.items(), key=lambda x: x[1], reverse=True)[:15]:
        logger.info(f"  {col:40s} {pct}")
    
    # Sort final output
    result = result.sort_values(["ticker", "quarter_end"]).reset_index(drop=True)
    
    return result
