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
        <div style="text-align: left; margin-bottom: 2rem;">
            <h1 style="font-weight: 800; font-size: 2.5rem; margin-bottom: 0;">
                PREDICTIVE <span style="color: #00f2ff; text-shadow: 0 0 20px rgba(0, 242, 255, 0.5);">ASSET ALLOCATION</span> SYSTEM
            </h1>
            <p style="color: #8a99ad; letter-spacing: 2px; font-weight: 500; margin-top: 0.5rem;">
                REAL-TIME AI-POWERED PORTFOLIO OPTIMIZATION
            </p>
        </div>
    """, unsafe_allow_html=True)
