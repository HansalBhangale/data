"""
Predictive Asset Allocation System - Main App

Entry point for the Streamlit application.
Modular architecture with separate components for:
- Core business logic (mappings, portfolio building, backtesting)
- UI components (header, sidebar, charts, tables)
- Styling (custom theme)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# STUB CLASSES - Required for unpickling risk tolerance model
# Must be defined before importing core modules
# =============================================================================

class PCABasedRiskScorer:
    """Stub for PCA-based risk scorer."""
    def __init__(self, df=None):
        self.df = df


class EmpiricalCorrelationScorer:
    """Stub for empirical correlation scorer."""
    def __init__(self, df=None):
        self.df = df


# =============================================================================
# IMPORTS
# =============================================================================

import streamlit as st
import pandas as pd

# Import custom components
from gui.components import (
    render_header,
    render_sidebar,
    render_questionnaire,
    render_risk_gauge,
    render_risk_metrics_row,
    render_holdings_pie,
    render_holdings_table,
    render_portfolio_summary,
    render_section_header,
    render_backtest_chart,
    render_performance_metrics,
    render_beat_spy_badge,
    render_metrics_comparison,
)

from gui.styles import get_custom_css
from gui.core import (
    build_model_features,
    load_risk_model,
    predict_risk_score,
    get_enhanced_investor_params,
    get_bucket_config,
    build_investor_portfolio,
    calculate_real_backtest,
    load_daily_prices,
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Predictive Asset Allocation System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# CUSTOM STYLES
# =============================================================================

st.markdown(get_custom_css(), unsafe_allow_html=True)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """
    Main application flow.
    """
    # Render header
    render_header()
    
    # Render sidebar (navigation only - no form elements)
    render_sidebar()
    
    # Initialize session state for results
    if 'risk_score' not in st.session_state:
        st.session_state.risk_score = None
    if 'portfolio_result' not in st.session_state:
        st.session_state.portfolio_result = None
    if 'backtest_result' not in st.session_state:
        st.session_state.backtest_result = None
    
    # Render questionnaire in MAIN CONTENT AREA (not sidebar)
    user_inputs = render_questionnaire()
    
    # Check if portfolio should be generated (button was clicked)
    if st.session_state.get('run_portfolio', False):
        st.session_state.run_portfolio = False  # Reset flag
        
        # Step 1: Map user inputs to features
        features = build_model_features(
            age=user_inputs['age'],
            education=user_inputs['education'],
            occupation=user_inputs['occupation'],
            income_range=user_inputs['income'],
            networth_range=user_inputs['networth'],
            assets_range=user_inputs['assets'],
            has_emergency=user_inputs['has_emergency'],
            has_savings=user_inputs['has_savings'],
            has_mutual=user_inputs['has_mutual'],
            has_retirement=user_inputs['has_retirement'],
        )
        
        # Step 2: Load risk model and predict
        risk_model, feature_names = load_risk_model()
        risk_score = predict_risk_score(features, risk_model, feature_names)
        st.session_state.risk_score = risk_score
        
        # Step 3: Get investor parameters
        params = get_enhanced_investor_params(risk_score)
        bucket_config = get_bucket_config(risk_score)
        
        # Step 4: Build portfolio
        portfolio = build_investor_portfolio(
            risk_score=risk_score,
            capital=user_inputs['capital'],
            use_enhanced=True,
        )
        
        if 'error' in portfolio:
            st.error(f"Portfolio Error: {portfolio['error']}")
            st.session_state.portfolio_result = None
        else:
            st.session_state.portfolio_result = portfolio
            
            # Step 5: Calculate backtest
            daily_prices, spy_daily = load_daily_prices()
            
            if not daily_prices.empty and not spy_daily.empty:
                backtest = calculate_real_backtest(
                    portfolio=portfolio,
                    daily_prices=daily_prices,
                    spy_daily=spy_daily,
                    start_date='2024-01-01',
                )
                st.session_state.backtest_result = backtest
            else:
                st.session_state.backtest_result = None
        
        # Reset the button state to prevent re-running
        st.session_state.generate_portfolio = False
    
    # =================================================================
    # RENDER RESULTS (if available)
    # =================================================================
    
    portfolio = st.session_state.get('portfolio_result')
    backtest = st.session_state.get('backtest_result')
    risk_score = st.session_state.get('risk_score')
    
    if portfolio and 'allocations' in portfolio:
        # Get params for display
        if risk_score:
            params = get_enhanced_investor_params(risk_score)
            bucket_config = get_bucket_config(risk_score)
            category = params.get('category', 'Unknown')
            equity_pct = params.get('base_equity', 0) * 100
            buckets = bucket_config.get('buckets', [])
        
        # =================================================================
        # SECTION 1: RISK ASSESSMENT (First)
        # =================================================================
        
        render_section_header("RISK ASSESSMENT")
        
        if risk_score:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                render_risk_gauge(risk_score, category)
            
            with col2:
                render_risk_metrics_row(risk_score, category, equity_pct, buckets)
        
        st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)
        
        # =================================================================
        # SECTION 2: PORTFOLIO ALLOCATION (Second)
        # =================================================================
        
        render_section_header("PORTFOLIO ALLOCATION")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            render_holdings_pie(portfolio)
        
        with col2:
            render_holdings_table(portfolio)
        
        st.markdown("<br>", unsafe_allow_html=True)
        render_portfolio_summary(portfolio)
        
        st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)
        
        # =================================================================
        # SECTION 3: PERFORMANCE vs S&P 500 (Third)
        # =================================================================
        
        render_section_header("PERFORMANCE vs S&P 500")
        
        if backtest and backtest.get('n_periods', 0) > 0:
            render_beat_spy_badge(backtest)
            render_backtest_chart(backtest)
            render_performance_metrics(backtest)
            st.markdown("<br>", unsafe_allow_html=True)
            render_metrics_comparison(backtest)
        else:
            st.warning("Backtest data not available. Please ensure price data is loaded.")
        
    elif risk_score is not None and portfolio is None:
        # Portfolio generation was attempted but failed
        st.error("Failed to generate portfolio. Please check data availability.")
    
    else:
        # No portfolio generated yet - show instructions
        st.info("👈 Please fill out the investor questionnaire in the sidebar and click 'RUN PORTFOLIO OPTIMIZATION' to get your personalized portfolio.")


if __name__ == '__main__':
    main()
