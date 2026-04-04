"""
Sidebar Component - Navigation Only

This sidebar contains only navigation and branding - no form elements.
The investor questionnaire is in the main content area.
"""

import streamlit as st
from typing import Dict


def render_sidebar() -> None:
    """
    Render only navigation elements in sidebar.
    """
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 1rem;">
                <h2 style="color: #3B82F6; margin: 0; font-size: 1.2rem; font-weight: 800;">PREDICTIVE</h2>
                <h3 style="color: #6366F1; margin: 0; font-size: 1rem; font-weight: 700;">ASSET ALLOCATION</h3>
                <p style="color: #94A3B8; font-size: 0.75rem; margin-top: 0.4rem; letter-spacing: 1px; text-transform: uppercase;">
                    AI-POWERED PORTFOLIO OPTIMIZATION
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 📊 Navigation")

        # Navigation options
        st.info("👆 Fill out the questionnaire in the main area to generate your portfolio.")

        st.markdown("---")

        st.markdown("### ℹ️ About")
        st.markdown("""
        This system uses:
        - Risk tolerance prediction model
        - Fundamental analysis model  
        - Technical analysis model
        - Enhanced portfolio optimization
        - Real backtesting vs S&P 500
        """)
