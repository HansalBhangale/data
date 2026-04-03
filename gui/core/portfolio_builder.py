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
from typing import Dict, Tuple
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


def build_investor_portfolio(
    risk_score: float,
    capital: float = 100000,
    use_enhanced: bool = True,
    max_stocks: int = 10,
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
    
    # Step 2: Compute composite scores
    with st.spinner("Computing composite scores..."):
        composite_df = compute_composite_scores(fund_scores, tech_scores)
    
    if composite_df is None or composite_df.empty:
        return {'error': 'Failed to compute composite scores'}
    
    # Step 3: Load daily prices and SPY
    with st.spinner("Loading price data..."):
        daily_prices, spy_daily = load_daily_prices()
    
    if daily_prices.empty:
        return {'error': 'No price data available'}
    
    # Step 4: Compute stock risk scores
    with st.spinner("Computing stock risk scores..."):
        # Try to load precomputed risk scores first
        stock_risk_df = load_stock_risk_scores()
        
        if stock_risk_df.empty:
            # Compute if not available
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
    
    # Step 6: Build portfolio
    with st.spinner("Building optimized portfolio..."):
        if use_enhanced:
            portfolio = build_portfolio_enhanced(
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
            # Fallback to original
            from composite.portfolio import build_portfolio
            portfolio = build_portfolio(
                composite_df=composite_df,
                stock_risk_df=stock_risk_df,
                investor_risk_score=risk_score,
                capital=capital,
            )
    
    return portfolio


def get_base_path():
    """Get the base project path."""
    from pathlib import Path
    return Path(__file__).parent.parent.parent
