"""
Backtest Module - Real Backtest Calculation

Calculates real historical performance of a portfolio vs S&P 500 benchmark.
Uses actual historical data, no hardcoded values.
Includes dynamically fetched bond prices.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
import streamlit as st
import warnings

warnings.filterwarnings('ignore')

BOND_ETFS = [
    'SHY', 'IEF', 'AGG', 'LQD', 'HYG', 'JNK', 'EMB', 'TLT',
    'BOND', 'VCIT', 'IGIB', 'VCSH', 'IGSB', 'SCHO', 'VGSH',
    'MBB', 'TIP', 'SCHP', 'VTIP', 'STIP', 'GOVT', 'BND',
    'PFF', 'PFFD', 'JEPI', 'HYLB', 'USHY', 'ANGL', 'HYDB',
    'FALN', 'SJNK', 'BWX', 'FLRN', 'FLOT', 'IGOV', 'VGIT',
    'SCHR', 'VMBS', 'NEAR', 'SUB', 'IUSB', 'SPIB', 'GBF',
    'USIG', 'QLTA', 'BNDX', 'IAGG', 'MUB', 'SPSB', 'VTEB',
    'LTPZ', 'SPTL', 'EDV', 'ZROZ', 'VGLT'
]


@st.cache_data(ttl=3600)
def fetch_bond_prices(_bond_tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch bond ETF prices using yfinance.
    
    Parameters
    ----------
    _bond_tickers : List[str]
        List of bond ETF tickers (passed as argument to use in cache key)
    start_date : str
        Start date for price data
    end_date : str
        End date for price data
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns [date, ticker, adj_close]
    """
    try:
        import yfinance as yf
        
        valid_tickers = [t for t in BOND_ETFS if t in _bond_tickers]
        
        if not valid_tickers:
            return pd.DataFrame()
        
        # Download one at a time to handle failures gracefully
        result_rows = []
        
        for ticker in valid_tickers:
            try:
                # Use yfinance Ticker object
                ticker_obj = yf.Ticker(ticker)
                data = ticker_obj.history(start=start_date, end=end_date)
                
                if data.empty or 'Close' not in data.columns:
                    continue
                
                for idx, row in data.iterrows():
                    if pd.notna(row['Close']):
                        # Normalize the date to remove timezone info
                        norm_date = pd.Timestamp(idx).tz_localize(None).normalize()
                        result_rows.append({
                            'date': norm_date,
                            'ticker': ticker,
                            'adj_close': float(row['Close'])
                        })
            except Exception:
                continue
        
        return pd.DataFrame(result_rows)
    
    except Exception as e:
        return pd.DataFrame()


def calculate_real_backtest(
    portfolio: Dict,
    daily_prices: pd.DataFrame,
    spy_daily: pd.DataFrame,
    start_date: str = '2024-01-01',
) -> Dict:
    """
    Calculate real backtest using historical price data.
    
    Uses available data only - skips quarters with missing data.
    Dynamically fetches bond prices for backtest.
    
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
            'n_stocks': int,
            'n_bonds': int,
            'bonds_included': bool,
        }
    """
    if not portfolio or 'allocations' not in portfolio or not portfolio['allocations']:
        return _empty_backtest_result(start_date)
    
    # Separate stocks and bonds from allocations
    stock_allocations = [a for a in portfolio['allocations'] if a.get('type') == 'Equity']
    bond_allocations = [a for a in portfolio['allocations'] if a.get('type') == 'Bond']
    
    # Get tickers and weights for stocks
    stock_tickers = [a['ticker'] for a in stock_allocations]
    stock_weights = np.array([a['weight_pct'] / 100 for a in stock_allocations])
    
    # Get tickers and weights for bonds
    bond_tickers = [a['ticker'] for a in bond_allocations]
    bond_weights = np.array([a['weight_pct'] / 100 for a in bond_allocations])
    
    # Combine all tickers and weights
    all_tickers = stock_tickers + bond_tickers
    all_weights = np.concatenate([stock_weights, bond_weights])
    
    # Normalize weights to sum to 1
    if all_weights.sum() > 0:
        all_weights = all_weights / all_weights.sum()
    
    # Filter to start date for stocks
    daily_prices = daily_prices[daily_prices['date'] >= start_date].copy()
    spy_daily = spy_daily[spy_daily['date'] >= start_date].copy()
    
    if daily_prices.empty or spy_daily.empty:
        return _empty_backtest_result(start_date)
    
    # Create stock price pivot table
    stock_prices = daily_prices.pivot_table(
        index='date', 
        columns='ticker', 
        values='adj_close'
    ).sort_index()
    
    # Fetch bond prices dynamically
    bonds_included = False
    bond_prices = pd.DataFrame()
    
    if bond_tickers:
        end_date = (pd.Timestamp(start_date).normalize() + pd.Timedelta(days=400)).strftime('%Y-%m-%d')
        bond_prices = fetch_bond_prices(bond_tickers, start_date, end_date)
        
        if not bond_prices.empty:
            # Normalize dates - handle timezone aware timestamps
            bond_prices['date'] = bond_prices['date'].apply(lambda x: pd.Timestamp(x).tz_localize(None).normalize() if pd.notna(x) else x)
            start_ts = pd.Timestamp(start_date).normalize()
            bond_prices = bond_prices[bond_prices['date'] >= start_ts]
            bond_prices = bond_prices.pivot_table(
                index='date',
                columns='ticker',
                values='adj_close'
            ).sort_index()
            if not bond_prices.empty:
                bonds_included = True
    
    # Get available stock tickers
    available_stock_tickers = [t for t in stock_tickers if t in stock_prices.columns]
    available_stock_weights = np.array([
        all_weights[all_tickers.index(t)] for t in available_stock_tickers
    ])
    
    # Get available bond tickers
    available_bond_tickers = []
    available_bond_weights = []
    
    if bonds_included and not bond_prices.empty:
        available_bond_tickers = [t for t in bond_tickers if t in bond_prices.columns]
        available_bond_weights = np.array([
            all_weights[all_tickers.index(t)] for t in available_bond_tickers
        ])
    
    # Combine available tickers
    available_tickers = available_stock_tickers + available_bond_tickers
    available_weights = np.concatenate([available_stock_weights, available_bond_weights])
    
    if len(available_tickers) < 2:
        return _empty_backtest_result(start_date)
    
    # Normalize available weights
    if available_weights.sum() > 0:
        available_weights = available_weights / available_weights.sum()
    
    # Calculate portfolio daily returns
    port_daily_return = pd.Series(index=pd.DatetimeIndex([]), dtype=float)
    
    # Stock returns
    if available_stock_tickers:
        stock_returns = stock_prices[available_stock_tickers].pct_change().dropna()
        stock_port_return = (stock_returns * available_stock_weights[:len(available_stock_tickers)]).sum(axis=1)
        stock_port_return = stock_port_return / stock_port_return.abs().sum() * available_stock_weights[:len(available_stock_tickers)].sum()
        
        if len(stock_tickers) > 0:
            stock_port_return = (stock_returns * (available_stock_weights / available_stock_weights.sum())).sum(axis=1)
        
        port_daily_return = stock_port_return
    
    # Bond returns - merge with stocks
    if bonds_included and available_bond_tickers and not bond_prices.empty:
        bond_returns = bond_prices[available_bond_tickers].pct_change().dropna()
        
        # Normalize bond weights
        if len(available_bond_tickers) > 0 and available_stock_weights.sum() > 0:
            total_bond_weight = available_bond_weights.sum()
            total_stock_weight = available_stock_weights[:len(available_stock_tickers)].sum()
            
            if total_bond_weight > 0:
                normalized_bond_weights = available_bond_weights / (total_stock_weight + total_bond_weight)
                stock_weights_norm = available_stock_weights[:len(available_stock_tickers)] / (total_stock_weight + total_bond_weight)
            else:
                normalized_bond_weights = available_bond_weights
                stock_weights_norm = available_stock_weights[:len(available_stock_tickers)] / available_stock_weights[:len(available_stock_tickers)].sum()
        else:
            normalized_bond_weights = available_bond_weights
            stock_weights_norm = available_stock_weights[:len(available_stock_tickers)] / available_stock_weights[:len(available_stock_tickers)].sum()
        
        if len(stock_returns.index) > 0:
            # Align dates
            common_dates_stock = stock_returns.index
            common_dates_bond = bond_returns.index
            common_dates = common_dates_stock.intersection(common_dates_bond)
            
            if len(common_dates) > 0:
                stock_returns_aligned = stock_returns.loc[common_dates]
                bond_returns_aligned = bond_returns.loc[common_dates]
                
                # Combined return
                stock_contrib = (stock_returns_aligned * stock_weights_norm).sum(axis=1)
                bond_contrib = (bond_returns_aligned * normalized_bond_weights).sum(axis=1)
                port_daily_return = stock_contrib + bond_contrib
            else:
                port_daily_return = (stock_returns * stock_weights_norm).sum(axis=1)
        else:
            port_daily_return = (bond_returns * normalized_bond_weights).sum(axis=1)
    
    # If only stocks available (no bonds fetched)
    elif available_stock_tickers and not bonds_included:
        if available_weights[:len(available_stock_tickers)].sum() > 0:
            norm_weights = available_weights[:len(available_stock_tickers)] / available_weights[:len(available_stock_tickers)].sum()
            port_daily_return = (stock_prices[available_stock_tickers].pct_change().dropna() * norm_weights).sum(axis=1)
    
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
        'n_stocks': len(available_stock_tickers),
        'n_bonds': len(available_bond_tickers),
        'bonds_included': bonds_included,
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
        'n_stocks': 0,
        'n_bonds': 0,
        'bonds_included': False,
    }


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal as percentage string."""
    sign = '+' if value >= 0 else ''
    return f"{sign}{value * 100:.{decimals}f}%"


def format_ratio(value: float, decimals: int = 2) -> str:
    """Format a ratio with specified decimals."""
    return f"{value:.{decimals}f}"
