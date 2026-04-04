"""
Portfolio Builder Module - Builds Portfolio Using Enhanced System

Orchestrates the portfolio building process:
1. Load model predictions (fundamental + technical)
2. Compute composite scores
3. Compute stock risk scores
4. Build portfolio using portfolio_enhanced
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import streamlit as st

from .data_loader import (
    load_fundamental_model,
    load_technical_model,
    load_daily_prices,
    load_stock_risk_scores,
    predict_stock_scores,
)
from .mappings import build_model_features


def load_model_predictions() -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Load and generate model predictions for all stocks.
    
    Returns
    -------
    Tuple[fund_scores, tech_scores]
        - fund_scores: {ticker: fundamental_score}
        - tech_scores: {ticker: technical_score}
    """
    fund_model, fund_features, fund_df = load_fundamental_model()
    tech_model, tech_features, tech_df = load_technical_model()
    
    fund_scores = {}
    tech_scores = {}
    
    # Fundamental predictions
    if fund_model and fund_features and not fund_df.empty:
        fund_scores = predict_stock_scores(fund_df, fund_model, fund_features)
    
    # Technical predictions
    if tech_model and tech_features and not tech_df.empty:
        tech_scores = predict_stock_scores(tech_df, tech_model, tech_features)
    
    return fund_scores, tech_scores


def load_bond_scores() -> pd.Series:
    """Load bond scores from the bond scores CSV file."""
    import os
    base_path = get_base_path()
    bond_scores_path = base_path / 'output_bond_ml' / 'bond_scores.csv'
    
    if not os.path.exists(bond_scores_path):
        return pd.Series(dtype=float)
    
    try:
        bond_df = pd.read_csv(bond_scores_path)
        if 'ticker' in bond_df.columns and 'bond_score' in bond_df.columns:
            return bond_df.set_index('ticker')['bond_score']
        return pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)


def get_bond_buckets(risk_score: float) -> list:
    """Get allowed bond ETFs based on investor risk score."""
    if risk_score <= 20:
        return ['SHY', 'VGSH', 'SCHO', 'VCSH', 'IGSB']
    elif risk_score <= 35:
        return ['SHY', 'IEF', 'VCIT', 'IGIB', 'AGG']
    elif risk_score <= 50:
        return ['IEF', 'AGG', 'LQD', 'VCIT', 'BOND']
    elif risk_score <= 70:
        return ['AGG', 'LQD', 'HYG', 'JNK', 'BOND']
    elif risk_score <= 85:
        return ['LQD', 'HYG', 'JNK', 'EMB', 'TLT']
    else:
        return ['HYG', 'JNK', 'EMB', 'TLT', 'LTPZ']


def get_investor_allocation(risk_score: float) -> tuple:
    """Get equity/bond/cash allocation percentages based on risk score."""
    if risk_score <= 20:
        return (0.98, 0.00, 0.02)
    elif risk_score <= 35:
        return (0.82, 0.15, 0.03)
    elif risk_score <= 50:
        return (0.84, 0.13, 0.03)
    elif risk_score <= 70:
        return (0.93, 0.05, 0.02)
    elif risk_score <= 85:
        return (0.98, 0.00, 0.02)
    else:
        return (1.00, 0.00, 0.00)


def get_category_name(risk_score: float) -> str:
    """Get risk category name from score."""
    if risk_score <= 20:
        return 'Ultra Conservative'
    elif risk_score <= 35:
        return 'Conservative'
    elif risk_score <= 50:
        return 'Moderate'
    elif risk_score <= 70:
        return 'Growth'
    elif risk_score <= 85:
        return 'Aggressive'
    else:
        return 'Ultra Aggressive'


def load_sentiment_scores(tickers: list = None) -> dict:
    """
    Load sentiment scores for stocks.
    
    Uses Marketaux API + FinBERT for real-time sentiment analysis.
    
    Parameters
    ----------
    tickers : list, optional
        Specific tickers to get sentiment for. If None, returns empty dict.
    
    Returns
    -------
    dict
        {ticker: sentiment_score_0_to_100}
    """
    import os
    from pathlib import Path
    
    # Try to load .env file from multiple locations
    for env_path in [Path(__file__).parent.parent / 'sentiment' / '.env', Path('.') / 'sentiment' / '.env']:
        try:
            from dotenv import load_dotenv
            if env_path.exists():
                load_dotenv(env_path)
                break
        except ImportError:
            pass
    
    api_key = os.environ.get("MARKETAUX_API_KEY", "")
    
    if not api_key or not tickers:
        return {}
    
    try:
        from sentiment.run_sentiment import get_stock_sentiment
        return get_stock_sentiment(tickers, use_cache=True, max_per_stock=5)
    except Exception as e:
        return {}


def build_investor_portfolio(
    risk_score: float,
    capital: float = 100000,
    use_enhanced: bool = True,
    max_stocks: int = 10,
    use_sentiment: bool = True,
) -> Dict:
    """
    Build a complete portfolio for an investor.
    
    Parameters
    ----------
    risk_score : float
        Investor risk score (0-100)
    capital : float
        Investment capital
    use_enhanced : bool
        Use enhanced portfolio builder (default: True)
    max_stocks : int
        Maximum number of stocks in portfolio (default: 10)
    use_sentiment : bool
        Include sentiment analysis (default: True)
    
    Returns
    -------
    Dict
        Portfolio dictionary with allocations and metadata
    """
    from composite.scorer import compute_composite_scores
    from composite.portfolio_enhanced import build_portfolio_enhanced
    from composite.stock_risk import compute_stock_risk_scores
    
    # Step 1: Load model predictions
    with st.spinner("Loading model predictions..."):
        fund_scores, tech_scores = load_model_predictions()
    
    if not fund_scores and not tech_scores:
        return {'error': 'No model predictions available'}
    
    # Step 1.5: Load sentiment scores (if enabled)
    sentiment_scores = {}
    if use_sentiment:
        with st.spinner("Analyzing market sentiment..."):
            # Get top tickers to analyze sentiment for
            top_tickers = list(fund_scores.keys())[:50]  # Analyze top 50
            sentiment_scores = load_sentiment_scores(top_tickers)
            if sentiment_scores:
                print(f"Loaded sentiment for {len(sentiment_scores)} stocks")
    
    # Step 2: Compute composite scores
    with st.spinner("Computing composite scores..."):
        composite_df = compute_composite_scores(
            fund_scores, 
            tech_scores, 
            sentiment_scores=sentiment_scores if sentiment_scores else None
        )
    
    if composite_df is None or composite_df.empty:
        return {'error': 'Failed to compute composite scores'}
    
    # Step 3: Load daily prices and SPY
    with st.spinner("Loading price data..."):
        daily_prices, spy_daily = load_daily_prices()
    
    if daily_prices.empty:
        return {'error': 'No price data available'}
    
    # Step 4: Compute stock risk scores
    with st.spinner("Computing stock risk scores..."):
        stock_risk_df = load_stock_risk_scores()
        
        if stock_risk_df.empty:
            fundamental_df = pd.read_csv(
                next((get_base_path() / 'output' / 'preprocessed_data.csv').glob('*.csv'))
            )
            stock_risk_df = compute_stock_risk_scores(
                daily_prices, spy_daily, fundamental_df
            )
    
    # Step 5: Load fundamental data for quality scores
    fundamental_df = pd.DataFrame()
    try:
        from .data_loader import get_fundamental_data_path
        fundamental_df = pd.read_csv(get_fundamental_data_path())
    except:
        pass
    
    # Step 6: Build stock portfolio
    with st.spinner("Building stock portfolio..."):
        if use_enhanced:
            stock_portfolio = build_portfolio_enhanced(
                composite_df=composite_df,
                stock_risk_df=stock_risk_df,
                investor_risk_score=risk_score,
                capital=capital,
                fundamental_df=fundamental_df,
                daily_prices=daily_prices,
                spy_daily=spy_daily,
                max_stocks=max_stocks,
            )
        else:
            from composite.portfolio import build_portfolio
            stock_portfolio = build_portfolio(
                composite_df=composite_df,
                stock_risk_df=stock_risk_df,
                investor_risk_score=risk_score,
                capital=capital,
            )
    
    if 'error' in stock_portfolio:
        return stock_portfolio
    
    # Step 7: Load and allocate bonds
    with st.spinner("Allocating bonds..."):
        bond_scores = load_bond_scores()
        allowed_bond_etfs = get_bond_buckets(risk_score)
        equity_pct, bond_pct, cash_pct = get_investor_allocation(risk_score)
        
        eligible_bonds = bond_scores[bond_scores.index.isin(allowed_bond_etfs)] if not bond_scores.empty else pd.Series(dtype=float)
        
        if eligible_bonds.empty and not bond_scores.empty:
            eligible_bonds = bond_scores.sort_values(ascending=False).head(5)
        
        bond_allocations = []
        if not eligible_bonds.empty:
            bond_total_pct = bond_pct
            bond_pct_value = bond_pct * 100
            
            if bond_pct_value >= 30:
                n_bonds = 5
            elif bond_pct_value >= 15:
                n_bonds = 4
            elif bond_pct_value >= 5:
                n_bonds = 3
            else:
                n_bonds = 2 if bond_pct_value > 2 else 1
            
            eligible_bonds = eligible_bonds.head(n_bonds)
            
            if len(eligible_bonds) > 0:
                bond_weights = np.power(eligible_bonds.values, 1.5)
                bond_weights = bond_weights / bond_weights.sum()
                
                for i, (ticker, score) in enumerate(eligible_bonds.items()):
                    weight_pct = bond_weights[i] * bond_total_pct * 100
                    bond_allocations.append({
                        'ticker': ticker,
                        'type': 'Bond',
                        'score': round(float(score), 2),
                        'weight_pct': round(weight_pct, 2),
                        'capital_allocated': round(weight_pct / 100 * capital, 2),
                    })
    
    # Step 8: Merge stock and bond allocations
    stock_allocations = stock_portfolio.get('allocations', [])
    
    for alloc in stock_allocations:
        alloc['type'] = 'Equity'
        original_weight = alloc['weight_pct']
        alloc['weight_pct'] = round(original_weight * equity_pct, 2)
        alloc['capital_allocated'] = round(alloc['weight_pct'] / 100 * capital, 2)
    
    all_allocations = stock_allocations + bond_allocations
    all_allocations.sort(key=lambda x: x['weight_pct'], reverse=True)
    
    # Step 9: Add sentiment scores to allocations (for portfolio holdings only)
    stock_tickers = [a['ticker'] for a in all_allocations if a.get('type') == 'Equity']
    bond_tickers = [a['ticker'] for a in all_allocations if a.get('type') == 'Bond']
    sentiments = fetch_portfolio_sentiments(stock_tickers, bond_tickers)
    
    for alloc in all_allocations:
        alloc['sentiment_score'] = sentiments.get(alloc['ticker'], 50.0)
    
    # Recalculate amounts based on actual allocations
    total_equity = sum(a['capital_allocated'] for a in stock_allocations)
    total_bond = sum(a['capital_allocated'] for a in bond_allocations)
    total_cash = capital - total_equity - total_bond
    
    return {
        'investor_risk_score': risk_score,
        'category': get_category_name(risk_score),
        'equity_weight': round(equity_pct * 100, 2),
        'equity_amount': round(total_equity, 2),
        'bond_weight': round(bond_pct * 100, 2),
        'bond_amount': round(total_bond, 2),
        'cash_weight': round(cash_pct * 100, 2),
        'cash_amount': round(total_cash, 2),
        'n_holdings': len(all_allocations),
        'n_stocks': len(stock_allocations),
        'n_bonds': len(bond_allocations),
        'allocations': all_allocations,
    }


def fetch_portfolio_sentiments(
    stock_tickers: List[str],
    bond_tickers: List[str]
) -> Dict[str, float]:
    """
    Fetch sentiment scores for portfolio holdings.
    
    Priority:
    1. Try Yahoo Finance + FinBERT (free, unlimited)
    2. If Yahoo fails, try Marketaux API (may have limits)
    3. If API fails, load from CSV files
    4. If CSV doesn't exist, use neutral (50)
    
    Parameters
    ----------
    stock_tickers : List[str]
        Stock tickers in portfolio
    bond_tickers : List[str]
        Bond tickers in portfolio
    
    Returns
    -------
    Dict[str, float]
        {ticker: sentiment_score_0_to_100}
    """
    from pathlib import Path
    import os
    
    results = {}
    
    # Step 1: Try Yahoo Finance + FinBERT (PRIMARY - free, unlimited)
    try:
        from sentiment.yahoo_sentiment import get_stock_sentiment_yahoo, get_bond_sentiment_yahoo
        
        # Get stock sentiments
        if stock_tickers:
            stock_sentiments = get_stock_sentiment_yahoo(stock_tickers, max_per_stock=5)
            results.update(stock_sentiments)
        
        # Get bond sentiments  
        if bond_tickers:
            bond_sentiments = get_bond_sentiment_yahoo(bond_tickers)
            results.update(bond_sentiments)
        
        if results:
            print(f"Using Yahoo Finance sentiment for {len(results)} tickers")
            return results
            
    except Exception as e:
        print(f"Yahoo Finance sentiment failed: {e}")
        pass
    
    # Step 2: Try Marketaux API (fallback)
    api_key = ""
    for env_path in [Path(__file__).parent.parent / 'sentiment' / '.env', Path('.') / 'sentiment' / '.env']:
        try:
            from dotenv import load_dotenv
            if env_path.exists():
                load_dotenv(env_path)
                break
        except ImportError:
            pass
    
    api_key = os.environ.get("MARKETAUX_API_KEY", "")
    
    if api_key:
        try:
            from sentiment.run_sentiment import get_stock_sentiment, get_bond_sentiment_scores
            
            # Get stock sentiments
            if stock_tickers:
                stock_sentiments = get_stock_sentiment(stock_tickers, use_cache=True, max_per_stock=3)
                results.update(stock_sentiments)
            
            # Get bond sentiments
            if bond_tickers:
                bond_sentiments = get_bond_sentiment_scores(bond_tickers, use_cache=True)
                results.update(bond_sentiments)
            
            # If we got results from API, return them
            if results:
                print(f"Using Marketaux API sentiment for {len(results)} tickers")
                return results
                
        except Exception as e:
            print(f"Marketaux API sentiment failed: {e}")
            pass
    
    # Step 3: Try loading from CSV files
    base_path = get_base_path()
    stock_csv = base_path / 'output' / 'stock_sentiment.csv'
    bond_csv = base_path / 'output' / 'bond_sentiment.csv'
    
    # Load stock sentiment from CSV
    if stock_csv.exists():
        try:
            import pandas as pd
            stock_df = pd.read_csv(stock_csv)
            if 'ticker' in stock_df.columns and 'sentiment_score' in stock_df.columns:
                csv_results = dict(zip(stock_df['ticker'], stock_df['sentiment_score']))
                # Filter to only requested tickers
                for ticker in stock_tickers:
                    if ticker in csv_results:
                        results[ticker] = csv_results[ticker]
                print(f"Using CSV stock sentiment for {len(stock_tickers)} stocks")
        except Exception as e:
            print(f"Failed to load stock sentiment CSV: {e}")
    
    # Load bond sentiment from CSV
    if bond_csv.exists():
        try:
            import pandas as pd
            bond_df = pd.read_csv(bond_csv)
            if 'ticker' in bond_df.columns and 'sentiment_score' in bond_df.columns:
                csv_results = dict(zip(bond_df['ticker'], bond_df['sentiment_score']))
                # Filter to only requested tickers
                for ticker in bond_tickers:
                    if ticker in csv_results:
                        results[ticker] = csv_results[ticker]
                print(f"Using CSV bond sentiment for {len(bond_tickers)} bonds")
        except Exception as e:
            print(f"Failed to load bond sentiment CSV: {e}")
    
    # Step 3: Default to neutral (50) for any missing
    for t in stock_tickers + bond_tickers:
        if t not in results:
            results[t] = 50.0
    
    return results


def get_base_path():
    """Get the base project path."""
    from pathlib import Path
    return Path(__file__).parent.parent.parent
