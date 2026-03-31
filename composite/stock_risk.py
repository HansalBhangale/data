"""
Stock Risk Scorer — computes per-stock risk scores (0-100) using weighted average.

Components (with weights):
  1. Volatility (252d realized)          → 0.20
  2. Beta (252d vs SPY)                  → 0.20
  3. Max Drawdown (252d)                 → 0.15
  4. Downside Deviation (252d)           → 0.15
  5. Leverage (debt-to-equity)           → 0.10
  6. Earnings Volatility (8-quarter rev growth std) → 0.10
  7. Valuation Risk (P/E vs sector)      → 0.10

Each component is normalized to 0-100 via cross-sectional percentile ranking,
then combined into a weighted average.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


# Component weights
COMPONENT_WEIGHTS = {
    'volatility': 0.20,
    'beta': 0.20,
    'max_drawdown': 0.15,
    'downside_deviation': 0.15,
    'leverage': 0.10,
    'earnings_volatility': 0.10,
    'valuation_risk': 0.10,
}


def _percentile_rank(series: pd.Series) -> pd.Series:
    """Convert series to 0-100 percentile rank."""
    return series.rank(pct=True) * 100


def compute_stock_risk_scores(
    daily_prices: pd.DataFrame,
    spy_daily: pd.DataFrame,
    fundamental_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Compute per-stock risk scores.

    Parameters
    ----------
    daily_prices : pd.DataFrame
        Columns: ticker, date, adj_close, volume, high, low, open
    spy_daily : pd.DataFrame
        SPY daily data with columns: date, adj_close
    fundamental_df : pd.DataFrame, optional
        Fundamental data for leverage, earnings vol, valuation risk.
        Columns: ticker, quarter_end, total_debt, stockholders_equity,
                 revenue, pe_ratio, sector

    Returns
    -------
    pd.DataFrame
        Columns: ticker, stock_risk_score, and each component score
    """
    daily_prices = daily_prices.copy()
    daily_prices['date'] = pd.to_datetime(daily_prices['date'])
    daily_prices = daily_prices.sort_values(['ticker', 'date'])

    spy_daily = spy_daily.copy()
    spy_daily['date'] = pd.to_datetime(spy_daily['date'])
    spy_daily = spy_daily.sort_values('date')
    spy_returns = spy_daily.set_index('date')['adj_close'].pct_change()

    records = []

    for ticker, grp in daily_prices.groupby('ticker'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 252:
            continue

        close = grp['adj_close'].values
        dates = grp['date'].values
        returns = np.diff(close) / (close[:-1] + 1e-10)
        returns = np.insert(returns, 0, 0)

        # 1. Volatility (252d annualized)
        if len(returns) >= 252:
            vol = np.std(returns[-252:]) * np.sqrt(252)
        else:
            vol = np.std(returns) * np.sqrt(252)

        # 2. Beta (252d vs SPY)
        stock_dates = pd.DatetimeIndex(dates)
        aligned = pd.DataFrame({
            'stock_ret': returns,
            'spy_ret': spy_returns.reindex(stock_dates, method='ffill').values
        }).dropna()
        if len(aligned) >= 60:
            cov = np.cov(aligned['stock_ret'].iloc[-252:], aligned['spy_ret'].iloc[-252:])[0, 1]
            var = np.var(aligned['spy_ret'].iloc[-252:])
            beta = cov / (var + 1e-10)
        else:
            beta = 1.0

        # 3. Max Drawdown (252d)
        if len(close) >= 252:
            window = close[-252:]
        else:
            window = close
        running_max = np.maximum.accumulate(window)
        drawdowns = (window - running_max) / (running_max + 1e-10)
        max_dd = np.min(drawdowns)

        # 4. Downside Deviation (252d)
        if len(returns) >= 252:
            neg_returns = returns[-252:][returns[-252:] < 0]
        else:
            neg_returns = returns[returns < 0]
        downside_dev = np.std(neg_returns) * np.sqrt(252) if len(neg_returns) > 0 else 0.0

        records.append({
            'ticker': ticker,
            'volatility': vol,
            'beta': beta,
            'max_drawdown': max_dd,
            'downside_deviation': downside_dev,
        })

    if not records:
        raise ValueError("No stocks with sufficient daily data")

    df = pd.DataFrame(records)

    # Normalize each component to 0-100 via percentile ranking
    # For volatility, beta, max_drawdown, downside_deviation: higher = riskier
    df['volatility_score'] = _percentile_rank(df['volatility'])
    df['beta_score'] = _percentile_rank(df['beta'].clip(-2, 5))
    df['max_drawdown_score'] = _percentile_rank(-df['max_drawdown'])  # more negative = riskier
    df['downside_dev_score'] = _percentile_rank(df['downside_deviation'])

    # Add fundamental-based components if available
    if fundamental_df is not None:
        # Get latest fundamental data per ticker
        fund_latest = fundamental_df.sort_values('quarter_end').groupby('ticker').last().reset_index()

        # 5. Leverage (debt-to-equity)
        if 'total_debt' in fund_latest.columns and 'stockholders_equity' in fund_latest.columns:
            fund_latest = fund_latest.copy()
            fund_latest['debt_to_equity'] = (
                fund_latest['total_debt'] / (fund_latest['stockholders_equity'].abs() + 1e-10)
            )
            dte_map = dict(zip(fund_latest['ticker'], fund_latest['debt_to_equity']))
            df['leverage'] = df['ticker'].map(dte_map)
            df['leverage'] = df['leverage'].fillna(df['leverage'].median())
            df['leverage_score'] = _percentile_rank(df['leverage'].clip(0, 10))
        else:
            df['leverage_score'] = 50.0

        # 6. Earnings Volatility (revenue growth std over time)
        if 'revenue' in fundamental_df.columns and 'ticker' in fundamental_df.columns:
            rev_growth = fundamental_df.sort_values(['ticker', 'quarter_end']).copy()
            rev_growth['rev_yoy'] = rev_growth.groupby('ticker')['revenue'].pct_change(4)
            rev_vol = rev_growth.groupby('ticker')['rev_yoy'].std()
            rev_vol_map = rev_vol.to_dict()
            df['earnings_vol'] = df['ticker'].map(rev_vol_map)
            df['earnings_vol'] = df['earnings_vol'].fillna(df['earnings_vol'].median())
            df['earnings_vol_score'] = _percentile_rank(df['earnings_vol'].clip(0, 5))
        else:
            df['earnings_vol_score'] = 50.0

        # 7. Valuation Risk (P/E vs sector median)
        if 'pe_ratio' in fund_latest.columns and 'sector' in fund_latest.columns:
            fund_latest = fund_latest.copy()
            fund_latest = fund_latest[fund_latest['pe_ratio'] > 0]
            sector_median_pe = fund_latest.groupby('sector')['pe_ratio'].median()
            fund_latest['pe_deviation'] = (
                (fund_latest['pe_ratio'] - fund_latest['sector'].map(sector_median_pe)).abs()
                / (fund_latest['sector'].map(sector_median_pe) + 1e-10)
            )
            pe_dev_map = dict(zip(fund_latest['ticker'], fund_latest['pe_deviation']))
            df['pe_deviation'] = df['ticker'].map(pe_dev_map)
            df['pe_deviation'] = df['pe_deviation'].fillna(df['pe_deviation'].median())
            df['valuation_risk_score'] = _percentile_rank(df['pe_deviation'].clip(0, 5))
        else:
            df['valuation_risk_score'] = 50.0
    else:
        df['leverage_score'] = 50.0
        df['earnings_vol_score'] = 50.0
        df['valuation_risk_score'] = 50.0

    # Ensure all score columns exist
    for col in ['leverage_score', 'earnings_vol_score', 'valuation_risk_score']:
        if col not in df.columns:
            df[col] = 50.0

    # Compute weighted average
    df['stock_risk_score'] = (
        df['volatility_score'] * COMPONENT_WEIGHTS['volatility'] +
        df['beta_score'] * COMPONENT_WEIGHTS['beta'] +
        df['max_drawdown_score'] * COMPONENT_WEIGHTS['max_drawdown'] +
        df['downside_dev_score'] * COMPONENT_WEIGHTS['downside_deviation'] +
        df['leverage_score'] * COMPONENT_WEIGHTS['leverage'] +
        df['earnings_vol_score'] * COMPONENT_WEIGHTS['earnings_volatility'] +
        df['valuation_risk_score'] * COMPONENT_WEIGHTS['valuation_risk']
    )

    # Clip to 0-100
    df['stock_risk_score'] = df['stock_risk_score'].clip(0, 100).round(2)

    # Assign risk bucket
    df['risk_bucket'] = pd.cut(
        df['stock_risk_score'],
        bins=[0, 20, 40, 60, 80, 100],
        labels=[1, 2, 3, 4, 5],
        include_lowest=True,
    ).astype(int)

    # Sort by risk score
    df = df.sort_values('stock_risk_score').reset_index(drop=True)

    print(f"\nStock Risk Scores:")
    print(f"  Total stocks: {len(df)}")
    for b in range(1, 6):
        count = (df['risk_bucket'] == b).sum()
        print(f"  Bucket {b}: {count} stocks")
    print(f"  Score range: {df['stock_risk_score'].min():.1f} - {df['stock_risk_score'].max():.1f}")
    print(f"  Mean: {df['stock_risk_score'].mean():.1f}")

    return df[['ticker', 'stock_risk_score', 'risk_bucket',
               'volatility_score', 'beta_score', 'max_drawdown_score',
               'downside_dev_score', 'leverage_score', 'earnings_vol_score',
               'valuation_risk_score']]
