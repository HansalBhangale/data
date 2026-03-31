"""
Market Data Fetcher
====================
Retrieves stock price and market data from Yahoo Finance via yfinance.
Computes valuation metrics (P/E, P/B, P/S, EV/EBITDA) by merging
market prices with fundamental data.
"""

import logging
import time
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from . import config

logger = logging.getLogger(__name__)


def _fetch_ticker_history(
    ticker: str,
    start: str = config.DATA_START_DATE,
    end: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch daily price history for a single ticker.
    
    Args:
        ticker: Stock ticker symbol
        start: Start date string (YYYY-MM-DD)
        end: End date string (YYYY-MM-DD), defaults to today
        
    Returns:
        DataFrame with columns: Date, Close, Volume, or None on failure
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end, auto_adjust=True)
        
        if hist.empty:
            logger.warning(f"{ticker}: No price history returned")
            return None
        
        hist = hist[["Close", "Volume"]].copy()
        hist.index = pd.to_datetime(hist.index.date)
        hist.index.name = "date"
        hist["ticker"] = ticker
        
        return hist.reset_index()
    
    except Exception as e:
        logger.warning(f"{ticker}: Failed to fetch price history: {e}")
        return None


def _resample_to_quarterly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily price data to quarter-end closing prices.
    
    Takes the last available closing price in each calendar quarter
    and aligns it to the quarter-end date.
    """
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    
    # Get quarter-end price (last trading day of each quarter)
    quarterly = df.groupby("ticker").resample("QE").agg({
        "Close": "last",
        "Volume": "mean",  # Average daily volume in the quarter
    }).reset_index()
    
    quarterly = quarterly.rename(columns={
        "date": "quarter_end",
        "Close": "stock_price",
        "Volume": "avg_daily_volume",
    })
    
    return quarterly


def fetch_market_data(
    tickers: list,
    start: str = config.DATA_START_DATE,
    batch_size: int = 20,
    delay_between_batches: float = 2.0,
) -> pd.DataFrame:
    """
    Fetch quarterly market data for a list of tickers.
    
    Processes tickers in batches to avoid Yahoo Finance rate limits.
    Returns quarterly closing prices and average volume.
    
    Args:
        tickers: List of ticker symbols
        start: Start date for price history
        batch_size: Number of tickers to process in parallel
        delay_between_batches: Seconds to wait between batches
        
    Returns:
        DataFrame with columns: ticker, quarter_end, stock_price, avg_daily_volume
    """
    logger.info(f"Fetching market data for {len(tickers)} tickers...")
    
    all_quarterly = []
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logger.info(f"  Batch {i//batch_size + 1}: {batch[:5]}...")
        
        for ticker in batch:
            daily = _fetch_ticker_history(ticker, start=start)
            if daily is not None and not daily.empty:
                quarterly = _resample_to_quarterly(daily)
                all_quarterly.append(quarterly)
        
        # Delay between batches to be respectful to Yahoo
        if i + batch_size < len(tickers):
            time.sleep(delay_between_batches)
    
    if not all_quarterly:
        logger.error("No market data retrieved for any ticker")
        return pd.DataFrame()
    
    result = pd.concat(all_quarterly, ignore_index=True)
    logger.info(f"Market data: {len(result)} quarterly observations for {result['ticker'].nunique()} tickers")
    
    return result


def fetch_spy_data(start: str = config.DATA_START_DATE) -> pd.DataFrame:
    """
    Fetch quarterly S&P 500 (SPY) benchmark data for computing excess returns.
    
    Returns:
        DataFrame with columns: quarter_end, spy_price
    """
    logger.info("Fetching SPY benchmark data...")
    daily = _fetch_ticker_history("SPY", start=start)
    
    if daily is None or daily.empty:
        logger.error("Failed to fetch SPY data")
        return pd.DataFrame()
    
    quarterly = _resample_to_quarterly(daily)
    quarterly = quarterly.rename(columns={"stock_price": "spy_price"})
    quarterly = quarterly[["quarter_end", "spy_price"]]
    
    return quarterly


def compute_valuation_metrics(
    financials_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute valuation metrics by merging financial data with market prices.
    
    Metrics computed:
      - Market Cap (estimated from price × shares)
      - P/E Ratio (trailing 4Q net income)
      - P/B Ratio (price / book value per share)
      - Price-to-Sales (trailing 4Q revenue)
      - EV/EBITDA (trailing 4Q EBITDA with enterprise value)
    
    Args:
        financials_df: DataFrame with quarterly financials (must have 'ticker', 'quarter_end')
        market_df: DataFrame with quarterly market data (must have 'ticker', 'quarter_end', 'stock_price')
        
    Returns:
        Input financials_df with valuation columns appended
    """
    logger.info("Computing valuation metrics...")
    
    df = financials_df.copy()
    df["quarter_end"] = pd.to_datetime(df["quarter_end"]).dt.normalize()
    
    market_df = market_df.copy()
    market_df["quarter_end"] = pd.to_datetime(market_df["quarter_end"]).dt.normalize()
    
    # Ensure matching datetime resolution for merge_asof (pandas 3.0 strict)
    common_unit = "ns"
    df["quarter_end"] = df["quarter_end"].astype(f"datetime64[{common_unit}]")
    market_df["quarter_end"] = market_df["quarter_end"].astype(f"datetime64[{common_unit}]")
    
    # Merge market data onto financials per-ticker using merge_asof
    # (avoids sorting issues with by= parameter in pandas 3.0)
    merged_parts = []
    for ticker in df["ticker"].unique():
        df_t = df[df["ticker"] == ticker].sort_values("quarter_end").copy()
        mkt_t = market_df[market_df["ticker"] == ticker].sort_values("quarter_end").copy()
        
        if mkt_t.empty:
            merged_parts.append(df_t)
            continue
        
        m = pd.merge_asof(
            df_t,
            mkt_t[["quarter_end", "stock_price", "avg_daily_volume"]],
            on="quarter_end",
            direction="nearest",
            tolerance=pd.Timedelta("45 days"),
        )
        merged_parts.append(m)
    
    merged = pd.concat(merged_parts, ignore_index=True)
    
    # ── Market Cap ──
    if "shares_outstanding" in merged.columns:
        merged["market_cap"] = merged["stock_price"] * merged["shares_outstanding"]
    else:
        merged["market_cap"] = np.nan
    
    
    # -- Trailing 4-Quarter Sums (TTM) --
    # Compute trailing twelve months for flow metrics.
    # Use min_periods=1 and count available quarters to handle sparse data.
    merged = merged.sort_values(["ticker", "quarter_end"])
    
    for col in ["net_income", "revenue", "ebitda"]:
        if col in merged.columns:
            # Rolling sum with at least 2 quarters of data
            rolling_sum = merged.groupby("ticker")[col].transform(
                lambda x: x.rolling(window=4, min_periods=2).sum()
            )
            # Count how many non-NaN values in the window
            rolling_count = merged.groupby("ticker")[col].transform(
                lambda x: x.rolling(window=4, min_periods=2).count()
            )
            # Annualize: scale up if we have fewer than 4 quarters
            merged[f"{col}_ttm"] = np.where(
                rolling_count >= 2,
                rolling_sum * (4.0 / rolling_count),
                np.nan,
            )
    
    # ── P/E Ratio ──
    if "net_income_ttm" in merged.columns:
        merged["pe_ratio"] = np.where(
            (merged["net_income_ttm"] > 0) & merged["market_cap"].notna(),
            merged["market_cap"] / merged["net_income_ttm"],
            np.nan,
        )
    
    # ── P/B Ratio ──
    if "stockholders_equity" in merged.columns:
        merged["pb_ratio"] = np.where(
            (merged["stockholders_equity"] > 0) & merged["market_cap"].notna(),
            merged["market_cap"] / merged["stockholders_equity"],
            np.nan,
        )
    
    # ── Price-to-Sales ──
    if "revenue_ttm" in merged.columns:
        merged["ps_ratio"] = np.where(
            (merged["revenue_ttm"] > 0) & merged["market_cap"].notna(),
            merged["market_cap"] / merged["revenue_ttm"],
            np.nan,
        )
    
    # ── EV/EBITDA ──
    if "ebitda_ttm" in merged.columns:
        total_debt = merged.get("total_debt", pd.Series(0, index=merged.index)).fillna(0)
        cash = merged.get("cash_and_equivalents", pd.Series(0, index=merged.index)).fillna(0)
        merged["enterprise_value"] = merged["market_cap"].fillna(0) + total_debt - cash
        
        merged["ev_ebitda"] = np.where(
            (merged["ebitda_ttm"] > 0) & (merged["enterprise_value"] > 0),
            merged["enterprise_value"] / merged["ebitda_ttm"],
            np.nan,
        )
    
    logger.info("Valuation metrics computed")
    return merged
