"""
Data fetcher for daily OHLCV from Yahoo Finance.
Downloads, caches, and loads daily price data for S&P 500 tickers.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from tqdm import tqdm

from .config import (
    DAILY_DATA_START, DAILY_DATA_END, CACHE_DIR,
    FETCH_SLEEP, FETCH_MAX_RETRIES, FETCH_BACKOFF_BASE,
)

logger = logging.getLogger(__name__)


def get_cached_path(ticker: str, cache_dir: str = CACHE_DIR) -> Path:
    """Get cache file path for a ticker."""
    return Path(cache_dir) / f'{ticker}.csv'


def fetch_daily_prices(
    ticker: str,
    start: str = DAILY_DATA_START,
    end: str = DAILY_DATA_END,
    max_retries: int = FETCH_MAX_RETRIES,
    backoff_base: int = FETCH_BACKOFF_BASE,
) -> Optional[pd.DataFrame]:
    """
    Download daily OHLCV from Yahoo Finance with retry logic.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    start : str
        Start date (YYYY-MM-DD)
    end : str
        End date (YYYY-MM-DD)
    max_retries : int
        Maximum number of retries on failure
    backoff_base : int
        Base for exponential backoff (2s, 4s, 8s, ...)

    Returns
    -------
    pd.DataFrame or None
        DataFrame with columns: date, open, high, low, close, adj_close, volume
        None if download fails after all retries
    """
    for attempt in range(max_retries + 1):
        try:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )

            if df is None or len(df) == 0:
                logger.warning(f"No data returned for {ticker}")
                return None

            # Handle multi-level columns from yfinance: (Price, Ticker)
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten: keep only the price level, drop ticker level
                df.columns = [c[0] for c in df.columns]

            df = df.reset_index()

            # Ensure date column exists
            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date'})
            elif 'date' not in df.columns:
                df = df.reset_index()
                if 'Datetime' in df.columns:
                    df = df.rename(columns={'Datetime': 'date'})

            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            # With auto_adjust=True, Close is already adjusted.
            # Map Close -> adj_close for consistency.
            col_map = {
                'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'adj_close', 'adj_close': 'adj_close',
                'Volume': 'volume', 'volume': 'volume',
            }
            df = df.rename(columns=col_map)

            required_cols = ['date', 'adj_close', 'volume']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                logger.warning(f"Missing columns for {ticker}: {missing}. Available: {df.columns.tolist()}")
                return None

            # Add placeholder columns for high/low/open if missing
            for col in ['open', 'high', 'low']:
                if col not in df.columns:
                    df[col] = df['adj_close']

            return df

        except Exception as e:
            if attempt < max_retries:
                delay = backoff_base ** (attempt + 1)
                logger.warning(
                    f"Failed to download {ticker} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"Failed to download {ticker} after {max_retries + 1} attempts: {e}")
                return None


def fetch_and_cache(
    ticker: str,
    cache_dir: str = CACHE_DIR,
    start: str = DAILY_DATA_START,
    end: str = DAILY_DATA_END,
    force: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Download daily data and cache to CSV.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    cache_dir : str
        Directory to cache CSV files
    start : str
        Start date
    end : str
        End date
    force : bool
        If True, re-download even if cached

    Returns
    -------
    pd.DataFrame or None
        Downloaded data, or None if failed
    """
    cache_path = get_cached_path(ticker, cache_dir)

    if cache_path.exists() and not force:
        try:
            df = pd.read_csv(cache_path, parse_dates=['date'])
            return df
        except Exception as e:
            logger.warning(f"Failed to read cache for {ticker}: {e}. Re-downloading...")

    df = fetch_daily_prices(ticker, start, end)

    if df is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)

    return df


def fetch_all_tickers(
    ticker_list: List[str],
    cache_dir: str = CACHE_DIR,
    start: str = DAILY_DATA_START,
    end: str = DAILY_DATA_END,
    force: bool = False,
    sleep: float = FETCH_SLEEP,
) -> Dict[str, pd.DataFrame]:
    """
    Download daily data for all tickers with rate limiting and caching.

    Parameters
    ----------
    ticker_list : List[str]
        List of ticker symbols
    cache_dir : str
        Directory to cache CSV files
    start : str
        Start date
    end : str
        End date
    force : bool
        If True, re-download even if cached
    sleep : float
        Seconds between requests

    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary of {ticker: DataFrame} for successfully downloaded tickers
    """
    results = {}
    failures = []

    print(f"\nFetching daily data for {len(ticker_list)} tickers...")
    print(f"Date range: {start} to {end}")
    print(f"Cache directory: {cache_dir}")
    print(f"Force re-download: {force}")

    for ticker in tqdm(ticker_list, desc="Downloading"):
        df = fetch_and_cache(ticker, cache_dir, start, end, force)

        if df is not None and len(df) > 100:
            results[ticker] = df
        else:
            failures.append(ticker)

        time.sleep(sleep)

    print(f"\nSuccessfully downloaded: {len(results)}/{len(ticker_list)} tickers")
    if failures:
        print(f"Failed ({len(failures)}): {', '.join(failures[:20])}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")

    return results


def load_cached_tickers(
    ticker_list: List[str],
    cache_dir: str = CACHE_DIR,
) -> Dict[str, pd.DataFrame]:
    """
    Load cached daily data for all available tickers.

    Parameters
    ----------
    ticker_list : List[str]
        List of ticker symbols to load
    cache_dir : str
        Directory with cached CSV files

    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary of {ticker: DataFrame} for available tickers
    """
    results = {}
    missing = []

    for ticker in ticker_list:
        cache_path = get_cached_path(ticker, cache_dir)
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path, parse_dates=['date'])
                if len(df) > 100:
                    results[ticker] = df
                else:
                    missing.append(ticker)
            except Exception as e:
                logger.warning(f"Failed to load cache for {ticker}: {e}")
                missing.append(ticker)
        else:
            missing.append(ticker)

    print(f"\nLoaded cached data: {len(results)}/{len(ticker_list)} tickers")
    if missing:
        print(f"Missing ({len(missing)}): {', '.join(missing[:20])}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")

    return results
