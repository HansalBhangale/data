"""
Backtest Module - Real Backtest Calculation

Calculates real historical performance of a portfolio vs S&P 500 benchmark.
Uses actual historical data, no hardcoded values.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
import streamlit as st


def calculate_real_backtest(
    portfolio: Dict,
    daily_prices: pd.DataFrame,
    spy_daily: pd.DataFrame,
    start_date: str = '2024-01-01',
) -> Dict:
    """
    Calculate real backtest using historical price data.
    
    Uses available data only - skips quarters with missing data.
    
    Parameters
    ----------
    portfolio : Dict
        Portfolio dictionary with 'allocations' key containing holdings
    daily_prices : pd.DataFrame
        Historical daily prices for all stocks
    spy_daily : pd.DataFrame
        Historical SPY prices
    start_date : str
        Start date for backtest (default: '2024-01-01')
    
    Returns
    -------
    Dict
        {
            'annual_return': float,
            'annual_volatility': float,
            'sharpe_ratio': float,
            'alpha': float,
            'beta': float,
            'max_drawdown': float,
            'spy_annual_return': float,
            'spy_sharpe': float,
            'cumulative_portfolio': pd.Series,
            'cumulative_spy': pd.Series,
            'beat_spy': bool,
            'outperformance': float,
            'start_date': str,
            'end_date': str,
            'n_periods': int,
        }
    """
    if not portfolio or 'allocations' not in portfolio or not portfolio['allocations']:
        return _empty_backtest_result(start_date)
    
    # Get portfolio tickers and weights
    tickers = [a['ticker'] for a in portfolio['allocations']]
    weights = np.array([a['weight_pct'] / 100 for a in portfolio['allocations']])
    
    # Normalize weights
    weights = weights / weights.sum()
    
    # Filter to start date
    daily_prices = daily_prices[daily_prices['date'] >= start_date].copy()
    spy_daily = spy_daily[spy_daily['date'] >= start_date].copy()
    
    if daily_prices.empty or spy_daily.empty:
        return _empty_backtest_result(start_date)
    
    # Create price pivot table
    prices = daily_prices.pivot_table(
        index='date', 
        columns='ticker', 
        values='adj_close'
    ).sort_index()
    
    # Get available tickers (skip missing)
    available_tickers = [t for t in tickers if t in prices.columns]
    
    if len(available_tickers) < 2:
        return _empty_backtest_result(start_date)
    
    # Get weights for available tickers only
    available_weights = np.array([
        weights[tickers.index(t)] for t in available_tickers
    ])
    available_weights = available_weights / available_weights.sum()
    
    # Calculate portfolio daily returns
    port_returns = prices[available_tickers].pct_change().dropna()
    port_daily_return = (port_returns * available_weights).sum(axis=1)
    
    # Calculate SPY returns
    spy_prices = spy_daily.set_index('date')['adj_close'].sort_index()
    spy_returns = spy_prices.pct_change().dropna()
    
    # Align dates (use available data only)
    common_dates = port_daily_return.index.intersection(spy_returns.index)
    
    if len(common_dates) < 30:  # Need at least 30 days
        return _empty_backtest_result(start_date)
    
    port_daily_return = port_daily_return.loc[common_dates]
    spy_returns = spy_returns.loc[common_dates]
    
    # Calculate metrics
    trading_days = 252
    risk_free_rate = 0.04
    
    # Portfolio metrics
    annual_return = port_daily_return.mean() * trading_days
    annual_vol = port_daily_return.std() * np.sqrt(trading_days)
    sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
    
    # SPY metrics
    spy_annual_return = spy_returns.mean() * trading_days
    spy_annual_vol = spy_returns.std() * np.sqrt(trading_days)
    spy_sharpe = (spy_annual_return - risk_free_rate) / spy_annual_vol if spy_annual_vol > 0 else 0
    
    # Beta calculation
    covariance = np.cov(port_daily_return, spy_returns)[0, 1]
    spy_variance = np.var(spy_returns)
    beta = covariance / spy_variance if spy_variance > 0 else 1.0
    
    # Alpha calculation
    alpha = annual_return - (risk_free_rate + beta * (spy_annual_return - risk_free_rate))
    
    # Max Drawdown
    cumulative = (1 + port_daily_return).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # SPY cumulative for charting
    spy_cumulative = (1 + spy_returns.loc[common_dates]).cumprod()
    
    # Beat S&P
    beat_spy = annual_return > spy_annual_return
    outperformance = annual_return - spy_annual_return
    
    return {
        'annual_return': float(annual_return),
        'annual_volatility': float(annual_vol),
        'sharpe_ratio': float(sharpe),
        'alpha': float(alpha),
        'beta': float(beta),
        'max_drawdown': float(max_drawdown),
        'spy_annual_return': float(spy_annual_return),
        'spy_sharpe': float(spy_sharpe),
        'cumulative_portfolio': cumulative,
        'cumulative_spy': spy_cumulative,
        'beat_spy': beat_spy,
        'outperformance': float(outperformance),
        'start_date': start_date,
        'end_date': str(common_dates.max().date()),
        'n_periods': len(common_dates),
    }


def _empty_backtest_result(start_date: str) -> Dict:
    """Return an empty backtest result when data is unavailable."""
    return {
        'annual_return': 0.0,
        'annual_volatility': 0.0,
        'sharpe_ratio': 0.0,
        'alpha': 0.0,
        'beta': 1.0,
        'max_drawdown': 0.0,
        'spy_annual_return': 0.0,
        'spy_sharpe': 0.0,
        'cumulative_portfolio': pd.Series(),
        'cumulative_spy': pd.Series(),
        'beat_spy': False,
        'outperformance': 0.0,
        'start_date': start_date,
        'end_date': 'N/A',
        'n_periods': 0,
    }


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal as percentage string."""
    sign = '+' if value >= 0 else ''
    return f"{sign}{value * 100:.{decimals}f}%"


def format_ratio(value: float, decimals: int = 2) -> str:
    """Format a ratio with specified decimals."""
    return f"{value:.{decimals}f}"
