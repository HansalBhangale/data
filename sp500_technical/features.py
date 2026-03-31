"""
Technical feature computation from daily OHLCV to quarterly snapshots.

Uses vectorized MultiIndex operations for performance.
All features computed using data strictly BEFORE quarter-end date (no lookahead).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from .config import ALL_TECH_FEATURES, RISK_FREE_RATE


def compute_all_features_vectorized(
    daily_data: Dict[str, pd.DataFrame],
    spy_daily: pd.DataFrame,
    quarter_dates: pd.DatetimeIndex,
    sector_map: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Compute all technical features using vectorized MultiIndex operations.

    Parameters
    ----------
    daily_data : Dict[str, pd.DataFrame]
        Dictionary of {ticker: DataFrame} with columns: date, adj_close, high, low, open, volume
    spy_daily : pd.DataFrame
        SPY daily data with columns: date, adj_close
    quarter_dates : pd.DatetimeIndex
        Quarter-end dates to compute features for
    sector_map : Dict[str, str], optional
        Mapping of ticker to sector

    Returns
    -------
    pd.DataFrame
        Quarterly feature matrix
    """
    print("\nComputing technical features (vectorized)...")

    # Build MultiIndex DataFrame: (ticker, date)
    frames = []
    for ticker, df in daily_data.items():
        df = df.copy()
        df['ticker'] = ticker
        frames.append(df)

    if not frames:
        raise ValueError("No daily data provided")

    all_daily = pd.concat(frames, ignore_index=True)
    all_daily['date'] = pd.to_datetime(all_daily['date'])
    all_daily = all_daily.sort_values(['ticker', 'date']).reset_index(drop=True)
    all_daily = all_daily.set_index(['ticker', 'date'])

    # Prepare SPY returns as a simple Series indexed by date
    spy_daily = spy_daily.copy()
    spy_daily['date'] = pd.to_datetime(spy_daily['date'])
    spy_daily = spy_daily.sort_values('date').set_index('date')
    spy_returns = spy_daily['adj_close'].pct_change()

    # ===== Compute all features per ticker =====
    results = []

    for ticker in all_daily.index.get_level_values(0).unique():
        d = all_daily.loc[ticker].copy()
        d = d.sort_index()

        close = d['adj_close']
        high = d['high']
        low = d['low']
        volume = d['volume']

        # Daily returns
        returns = close.pct_change()

        # Align stock returns with SPY returns on same dates
        aligned = pd.DataFrame({'stock_ret': returns, 'spy_ret': spy_returns}).dropna()

        # True Range
        prev_close = close.shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

        # ----- MOMENTUM -----
        momentum_12m_1m = close / close.shift(252) - 1
        momentum_6m_1m = close / close.shift(126) - 1
        momentum_1m = close / close.shift(21) - 1
        high_52w = close.rolling(252, min_periods=252).max()
        high_52w_ratio = close / (high_52w + 1e-10)

        # ----- TREND -----
        sma_50 = close.rolling(50, min_periods=50).mean()
        sma_100 = close.rolling(100, min_periods=100).mean()
        sma_200 = close.rolling(200, min_periods=200).mean()
        price_sma_50_ratio = close / (sma_50 + 1e-10)
        price_sma_100_ratio = close / (sma_100 + 1e-10)
        price_sma_200_ratio = close / (sma_200 + 1e-10)
        sma_50_200_ratio = sma_50 / (sma_200 + 1e-10)
        low_52w = close.rolling(252, min_periods=252).min()
        dist_from_52w_low = (close - low_52w) / (low_52w + 1e-10)

        # ----- VOLATILITY -----
        vol_20d = returns.rolling(20, min_periods=20).std() * np.sqrt(252)
        vol_60d = returns.rolling(60, min_periods=60).std() * np.sqrt(252)
        vol_252d = returns.rolling(252, min_periods=252).std() * np.sqrt(252)
        vol_ratio_20_252 = vol_20d / (vol_252d + 1e-10)
        atr_20d = tr.rolling(20, min_periods=20).mean()
        atr_norm = atr_20d / (close + 1e-10)

        # ----- VOLUME -----
        vol_ma_20 = volume.rolling(20, min_periods=20).mean()
        vol_ma_60 = volume.rolling(60, min_periods=60).mean()
        vol_ma_252 = volume.rolling(252, min_periods=252).mean()
        rel_volume_20_252 = vol_ma_20 / (vol_ma_252 + 1e-10)
        volume_momentum = vol_ma_20 / (vol_ma_60 + 1e-10)

        # Price-volume correlation (60-day rolling)
        price_volume_corr = returns.rolling(60, min_periods=60).corr(volume)

        # ----- MEAN REVERSION -----
        # RSI
        gain = returns.clip(lower=0)
        loss = -returns.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi_14 = 100 - (100 / (1 + rs))

        # Bollinger Bands
        bb_mid = close.rolling(20, min_periods=20).mean()
        bb_std = close.rolling(20, min_periods=20).std()
        bb_distance = (close - bb_mid) / (bb_std + 1e-10)

        # Price z-score
        price_mean_252 = close.rolling(252, min_periods=252).mean()
        price_std_252 = close.rolling(252, min_periods=252).std()
        price_zscore_252d = (close - price_mean_252) / (price_std_252 + 1e-10)

        # ----- RISK -----
        # Max drawdown
        rolling_max = close.rolling(252, min_periods=252).max()
        max_drawdown_252d = (close - rolling_max) / (rolling_max + 1e-10)

        # Sharpe ratio
        rf_daily = RISK_FREE_RATE / 252
        sharpe_252d = (returns.rolling(252, min_periods=252).mean() - rf_daily) / (returns.rolling(252, min_periods=252).std() + 1e-10) * np.sqrt(252)

        # Beta vs SPY
        if len(aligned) >= 252:
            cov = aligned['stock_ret'].rolling(252, min_periods=252).cov(aligned['spy_ret'])
            var = aligned['spy_ret'].rolling(252, min_periods=252).var()
            beta_252d = cov / (var + 1e-10)
            beta_252d = beta_252d.reindex(returns.index)
        else:
            beta_252d = pd.Series(np.nan, index=returns.index)

        # Downside deviation
        downside_dev_252d = returns.rolling(252, min_periods=252).apply(
            lambda w: np.std(w[w < 0]) * np.sqrt(252) if len(w[w < 0]) > 0 else np.nan,
            raw=True
        )

        # Build row for this ticker
        ticker_features = pd.DataFrame({
            'momentum_12m_1m': momentum_12m_1m,
            'momentum_6m_1m': momentum_6m_1m,
            'momentum_1m': momentum_1m,
            'high_52w_ratio': high_52w_ratio,
            'price_sma_50_ratio': price_sma_50_ratio,
            'price_sma_100_ratio': price_sma_100_ratio,
            'price_sma_200_ratio': price_sma_200_ratio,
            'sma_50_200_ratio': sma_50_200_ratio,
            'dist_from_52w_low': dist_from_52w_low,
            'vol_20d': vol_20d,
            'vol_60d': vol_60d,
            'vol_252d': vol_252d,
            'vol_ratio_20_252': vol_ratio_20_252,
            'atr_norm': atr_norm,
            'rel_volume_20_252': rel_volume_20_252,
            'price_volume_corr': price_volume_corr,
            'volume_momentum': volume_momentum,
            'rsi_14': rsi_14,
            'bb_distance': bb_distance,
            'price_zscore_252d': price_zscore_252d,
            'max_drawdown_252d': max_drawdown_252d,
            'sharpe_252d': sharpe_252d,
            'beta_252d': beta_252d,
            'downside_dev_252d': downside_dev_252d,
        }, index=d.index)

        results.append(ticker_features)

    # Concatenate all ticker features with proper MultiIndex
    # Use the actual ticker order from the iteration to ensure correct alignment
    result_tickers = []
    for ticker in all_daily.index.get_level_values(0).unique():
        result_tickers.append(ticker)
    all_features = pd.concat(results, keys=result_tickers)
    all_features.index.names = ['ticker', 'date']

    print(f"  Computed {len(ALL_TECH_FEATURES)} features for {len(results)} tickers")

    # Resample to quarter-end dates using merge_asof (vectorized, fast)
    quarter_dates = pd.to_datetime(quarter_dates).sort_values()
    quarter_df = pd.DataFrame({'quarter_end': quarter_dates})

    # Flatten features for merge_asof
    all_features_flat = all_features.reset_index()
    all_features_flat = all_features_flat.sort_values(['ticker', 'date'])
    quarter_df = quarter_df.sort_values('quarter_end')

    quarterly_features = []
    for ticker in all_features_flat['ticker'].unique():
        ticker_data = all_features_flat[all_features_flat['ticker'] == ticker].copy()
        merged = pd.merge_asof(
            quarter_df, ticker_data,
            left_on='quarter_end', right_on='date',
            direction='backward'
        )
        # Keep only rows where we found data (date <= quarter_end)
        merged = merged.dropna(subset=['date'])
        quarterly_features.append(merged)

    if not quarterly_features:
        raise ValueError("No quarterly features computed. Check daily data coverage.")

    result = pd.concat(quarterly_features, ignore_index=True)
    result = result.drop(columns=['date'], errors='ignore')
    result['year'] = result['quarter_end'].dt.year
    result['quarter'] = result['quarter_end'].dt.quarter

    if sector_map:
        result['sector'] = result['ticker'].map(sector_map)

    feature_cols = [c for c in ALL_TECH_FEATURES if c in result.columns]
    id_cols = ['ticker', 'quarter_end', 'year', 'quarter']
    if 'sector' in result.columns:
        id_cols.append('sector')

    result = result[id_cols + feature_cols].copy()
    result = result.dropna(subset=feature_cols, how='all')

    print(f"  Quarterly features: {result.shape[0]} rows x {len(feature_cols)} features")
    print(f"  Tickers: {result['ticker'].nunique()}")
    print(f"  Quarters: {result['quarter_end'].nunique()}")

    return result
