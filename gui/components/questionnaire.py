"""
Questionnaire Component - Main Content Area

Investor questionnaire rendered in the main content area (not sidebar).
Fixed layout - cannot be collapsed or hidden.

NOTE: All questions, options, field names, and return values are UNCHANGED.
Only visual styling has been updated.
"""

import streamlit as st
from typing import Dict


def render_questionnaire() -> Dict:
    """
    Render the investor profiling questionnaire in the main content area.
    Fixed layout - everything always visible.
    """
    # Title
    st.markdown("""
        <div style="margin-bottom: 1.2rem;">
            <h2 style="color: #E2E8F0; font-weight: 700; font-size: 1.4rem; margin-bottom: 0.3rem;">
                📋 Investor Profiling Questionnaire
            </h2>
            <p style="color: #94A3B8; font-size: 0.88rem; margin: 0;">
                Fill in your details below to generate your personalized portfolio.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)

    # Create columns for layout
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            <p style="color: #60A5FA; font-size: 0.75rem; font-weight: 600;
                      letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.8rem;">
                👤 Personal Information
            </p>
        """, unsafe_allow_html=True)

        age = st.slider("Age", 18, 85, 35, help="Your current age")

        education = st.selectbox(
            "Education Level",
            [
                "Less than High School",
                "High School/GED",
                "Some College",
                "Bachelor's",
                "Master's",
                "Doctoral"
            ],
            index=3,
        )

        occupation = st.selectbox(
            "Occupation Status",
            [
                "Employee/Salaried",
                "Self-Employed",
                "Retired",
                "Not Working/Student"
            ],
        )

    with col2:
        st.markdown("""
            <p style="color: #60A5FA; font-size: 0.75rem; font-weight: 600;
                      letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.8rem;">
                💰 Financial Details
            </p>
        """, unsafe_allow_html=True)

        income = st.selectbox(
            "Annual Income",
            [
                "Under $30K",
                "$30K-$55K",
                "$55K-$90K",
                "$90K-$150K",
                "$150K-$250K",
                "Over $250K"
            ],
            index=3,
        )

        networth = st.selectbox(
            "Net Worth",
            [
                "Under $30K",
                "$30K-$200K",
                "$200K-$700K",
                "$700K-$2M",
                "Over $2M"
            ],
            index=2,
        )

        assets = st.selectbox(
            "Total Assets",
            [
                "Under $30K",
                "$30K-$200K",
                "$200K-$500K",
                "$500K-$1M",
                "$1M-$2M",
                "Over $2M"
            ],
            index=2,
        )

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)

    # Second row
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            <p style="color: #60A5FA; font-size: 0.75rem; font-weight: 600;
                      letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.8rem;">
                📈 Investment Experience
            </p>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            has_emergency = st.checkbox("Emergency Fund", value=True)
            has_mutual = st.checkbox("Mutual Funds", value=True)
        with col_b:
            has_savings = st.checkbox("Savings Account", value=True)
            has_retirement = st.checkbox("Retirement Account", value=True)

    with col2:
        st.markdown("""
            <p style="color: #60A5FA; font-size: 0.75rem; font-weight: 600;
                      letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.8rem;">
                💵 Investment Capital
            </p>
        """, unsafe_allow_html=True)

        capital = st.number_input(
            "Capital to Invest ($)",
            min_value=1000,
            max_value=100000000,
            value=100000,
            step=10000,
            help="Amount you want to invest",
        )

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)

    # Generate Button - Full width
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate = st.button(
            "🚀 GENERATE PORTFOLIO",
            type="primary",
            use_container_width=True,
        )

    # Handle button click
    if generate:
        st.session_state.run_portfolio = True
        if 'portfolio_result' in st.session_state:
            del st.session_state['portfolio_result']
        if 'backtest_result' in st.session_state:
            del st.session_state['backtest_result']
        st.rerun()

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)

    return {
        'age': age,
        'education': education,
        'occupation': occupation,
        'income': income,
        'networth': networth,
        'assets': assets,
        'has_emergency': has_emergency,
        'has_savings': has_savings,
        'has_mutual': has_mutual,
        'has_retirement': has_retirement,
        'capital': capital,
    }
