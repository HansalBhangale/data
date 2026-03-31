"""
Central configuration for SP500 Technical model.
"""

# =============================================================================
# Data Fetching Configuration
# =============================================================================

DAILY_DATA_START = '2006-01-01'
DAILY_DATA_END = '2025-12-31'
CACHE_DIR = 'cache/daily_prices'
RISK_FREE_RATE = 0.02  # 2% annual
FETCH_SLEEP = 0.5  # seconds between yfinance requests
FETCH_MAX_RETRIES = 3
FETCH_BACKOFF_BASE = 2  # exponential backoff: 2s, 4s, 8s

# =============================================================================
# Technical Feature Definitions
# =============================================================================

MOMENTUM_COLS = [
    'momentum_12m_1m',
    'momentum_6m_1m',
    'momentum_1m',
    'high_52w_ratio',
]

TREND_COLS = [
    'price_sma_50_ratio',
    'price_sma_100_ratio',
    'price_sma_200_ratio',
    'sma_50_200_ratio',
    'dist_from_52w_low',
]

VOLATILITY_COLS = [
    'vol_20d',
    'vol_60d',
    'vol_252d',
    'vol_ratio_20_252',
    'atr_norm',
]

VOLUME_COLS = [
    'rel_volume_20_252',
    'price_volume_corr',
    'volume_momentum',
]

MEAN_REVERSION_COLS = [
    'rsi_14',
    'bb_distance',
    'price_zscore_252d',
]

RISK_COLS = [
    'max_drawdown_252d',
    'sharpe_252d',
    'beta_252d',
    'downside_dev_252d',
]

ALL_TECH_FEATURES = (
    MOMENTUM_COLS + TREND_COLS + VOLATILITY_COLS +
    VOLUME_COLS + MEAN_REVERSION_COLS + RISK_COLS
)

# =============================================================================
# Minimum Lookback Requirements (trading days)
# =============================================================================

FEATURE_MIN_LOOKBACK = {
    'momentum_12m_1m': 252,
    'momentum_6m_1m': 126,
    'momentum_1m': 21,
    'high_52w_ratio': 252,
    'price_sma_50_ratio': 50,
    'price_sma_100_ratio': 100,
    'price_sma_200_ratio': 200,
    'sma_50_200_ratio': 200,
    'dist_from_52w_low': 252,
    'vol_20d': 20,
    'vol_60d': 60,
    'vol_252d': 252,
    'vol_ratio_20_252': 252,
    'atr_norm': 20,
    'rel_volume_20_252': 252,
    'price_volume_corr': 60,
    'volume_momentum': 60,
    'rsi_14': 14,
    'bb_distance': 20,
    'price_zscore_252d': 252,
    'max_drawdown_252d': 252,
    'sharpe_252d': 252,
    'beta_252d': 252,
    'downside_dev_252d': 252,
}

# =============================================================================
# Outlier Clipping Bounds
# =============================================================================

TECH_CLIP_BOUNDS = {
    'rsi_14': (0, 100),
    'momentum_12m_1m': (-2, 5),
    'momentum_6m_1m': (-2, 5),
    'momentum_1m': (-1, 2),
    'high_52w_ratio': (0.1, 1.5),
    'price_sma_50_ratio': (0.5, 2.0),
    'price_sma_100_ratio': (0.5, 2.0),
    'price_sma_200_ratio': (0.5, 2.0),
    'sma_50_200_ratio': (0.5, 2.0),
    'dist_from_52w_low': (-0.5, 5),
    'vol_20d': (0, 2),
    'vol_60d': (0, 2),
    'vol_252d': (0, 2),
    'vol_ratio_20_252': (0.1, 10),
    'atr_norm': (0, 0.1),
    'rel_volume_20_252': (0.1, 10),
    'price_volume_corr': (-1, 1),
    'volume_momentum': (0.1, 10),
    'bb_distance': (-5, 5),
    'price_zscore_252d': (-5, 5),
    'max_drawdown_252d': (-1, 0),
    'sharpe_252d': (-5, 5),
    'beta_252d': (-3, 5),
    'downside_dev_252d': (0, 2),
}

# =============================================================================
# Columns for Sector Normalization (z-score within sector x year)
# =============================================================================

TECH_SECTOR_NORM_COLS = [
    'momentum_12m_1m',
    'momentum_6m_1m',
    'momentum_1m',
    'vol_20d',
    'vol_60d',
    'vol_252d',
    'beta_252d',
    'max_drawdown_252d',
    'rsi_14',
]

# =============================================================================
# Columns to Exclude from Features (identifiers, dates, targets)
# =============================================================================

TECH_EXCLUDE_COLS = [
    'ticker', 'sector', 'quarter_end', 'quarter_label',
    'year', 'quarter',
    'excess_return_1y', 'excess_return_3y',
    'excess_return_1y_rank', 'excess_return_3y_rank',
    'fwd_return_1y', 'fwd_return_3y',
    'spy_fwd_return_1y', 'spy_fwd_return_3y',
]

# =============================================================================
# Time Split Configuration (same as fundamental model)
# =============================================================================

TIME_SPLIT = {
    'train_end_year': 2019,
    'val_start_year': 2020,
    'val_end_year': 2021,
    'test_start_year': 2022,
}
