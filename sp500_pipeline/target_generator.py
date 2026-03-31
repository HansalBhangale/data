"""
Target Variable Generator
===========================
Generates forward-looking labels for ML model training:
  - Forward 1-year return
  - Forward 3-year return
  - Excess return vs S&P 500 benchmark (SPY)
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_targets(
    df: pd.DataFrame,
    spy_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate forward-looking target variables for model training.
    
    For each company-quarter, computes:
      - fwd_return_1y: (Price_{t+4Q} / Price_t) - 1
      - fwd_return_3y: (Price_{t+12Q} / Price_t) - 1
      - excess_return_1y: fwd_return_1y - SPY_fwd_return_1y
      - excess_return_3y: fwd_return_3y - SPY_fwd_return_3y
    
    Args:
        df: DataFrame with columns: ticker, quarter_end, stock_price
        spy_df: DataFrame with columns: quarter_end, spy_price
        
    Returns:
        Input DataFrame with target columns appended
    """
    logger.info("Computing forward return targets...")
    
    result = df.copy()
    result = result.sort_values(["ticker", "quarter_end"]).reset_index(drop=True)
    
    if "stock_price" in result.columns:
        # Compute per-company using explicit loop
        # (avoids pandas 3.0 groupby().apply() dropping the groupby column)
        parts = []
        for ticker, group in result.groupby("ticker"):
            g = group.copy()
            price = g["stock_price"]
            
            future_price_1y = price.shift(-4)
            g["fwd_return_1y"] = np.where(
                price.notna() & future_price_1y.notna() & (price > 0),
                (future_price_1y / price) - 1,
                np.nan,
            )
            
            future_price_3y = price.shift(-12)
            g["fwd_return_3y"] = np.where(
                price.notna() & future_price_3y.notna() & (price > 0),
                (future_price_3y / price) - 1,
                np.nan,
            )
            parts.append(g)
        
        result = pd.concat(parts, ignore_index=True)
    else:
        logger.warning("No 'stock_price' column — forward returns cannot be computed")
        result["fwd_return_1y"] = np.nan
        result["fwd_return_3y"] = np.nan
    
    # ── SPY Benchmark Returns ──
    if not spy_df.empty and "spy_price" in spy_df.columns:
        spy = spy_df.copy()
        spy = spy.sort_values("quarter_end").reset_index(drop=True)
        spy["quarter_end"] = pd.to_datetime(spy["quarter_end"])
        
        # SPY forward returns
        spy["spy_fwd_return_1y"] = np.where(
            spy["spy_price"].notna() & spy["spy_price"].shift(-4).notna() & (spy["spy_price"] > 0),
            (spy["spy_price"].shift(-4) / spy["spy_price"]) - 1,
            np.nan,
        )
        spy["spy_fwd_return_3y"] = np.where(
            spy["spy_price"].notna() & spy["spy_price"].shift(-12).notna() & (spy["spy_price"] > 0),
            (spy["spy_price"].shift(-12) / spy["spy_price"]) - 1,
            np.nan,
        )
        
        # Merge SPY returns onto main DataFrame
        result["quarter_end"] = pd.to_datetime(result["quarter_end"]).dt.normalize()
        spy["quarter_end"] = spy["quarter_end"].dt.normalize()
        
        # Ensure matching datetime resolution for merge_asof (pandas 3.0 strict)
        result["quarter_end"] = result["quarter_end"].astype("datetime64[ns]")
        spy["quarter_end"] = spy["quarter_end"].astype("datetime64[ns]")
        
        result = pd.merge_asof(
            result.sort_values("quarter_end"),
            spy[["quarter_end", "spy_fwd_return_1y", "spy_fwd_return_3y"]].sort_values("quarter_end"),
            on="quarter_end",
            direction="nearest",
            tolerance=pd.Timedelta("45 days"),
        )
        
        # Excess returns
        result["excess_return_1y"] = result["fwd_return_1y"] - result["spy_fwd_return_1y"]
        result["excess_return_3y"] = result["fwd_return_3y"] - result["spy_fwd_return_3y"]
    else:
        logger.warning("No SPY data — excess returns set to NaN")
        result["spy_fwd_return_1y"] = np.nan
        result["spy_fwd_return_3y"] = np.nan
        result["excess_return_1y"] = np.nan
        result["excess_return_3y"] = np.nan
    
    # Re-sort by ticker and date
    result = result.sort_values(["ticker", "quarter_end"]).reset_index(drop=True)
    
    n_with_1y = result["fwd_return_1y"].notna().sum()
    n_with_3y = result["fwd_return_3y"].notna().sum()
    logger.info(
        f"Target variables computed. "
        f"Rows with 1Y target: {n_with_1y}, "
        f"Rows with 3Y target: {n_with_3y}"
    )
    
    return result
