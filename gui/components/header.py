"""
Header Component - App Header
"""

import streamlit as st


def render_header():
    """
    Render the app header with branding.

    Displays:
    - App title: "Predictive Asset Allocation System"
    - Tagline: "Real-Time AI-Powered Portfolio Optimization"
    """
    st.markdown("""
        <div style="margin-bottom: 2rem;">
            <h1 style="font-weight: 800; font-size: 2.2rem; margin-bottom: 0; letter-spacing: -0.5px; color: #E2E8F0;">
                PREDICTIVE <span style="color: #3B82F6;">ASSET ALLOCATION</span> SYSTEM
            </h1>
            <p style="color: #94A3B8; letter-spacing: 1.5px; font-weight: 500; margin-top: 0.4rem; font-size: 0.78rem; text-transform: uppercase;">
                REAL-TIME AI-POWERED PORTFOLIO OPTIMIZATION
            </p>
        </div>
    """, unsafe_allow_html=True)
