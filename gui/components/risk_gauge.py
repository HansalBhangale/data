"""
Risk Gauge Component - Risk Score Visualization
"""

import streamlit as st
import plotly.graph_objects as go


def render_risk_gauge(risk_score: float, category: str):
    """
    Render a gauge chart showing the risk score (0-100).
    
    Parameters
    ----------
    risk_score : float
        Investor risk score (0-100)
    category : str
        Risk category (e.g., "Moderate", "Aggressive")
    """
    # Determine color based on category
    if 'Conservative' in category or 'Ultra Conservative' in category:
        gauge_color = '#00f2ff'  # Cyan
    elif 'Moderate' in category or 'Growth' in category:
        gauge_color = '#7000ff'  # Purple
    else:
        gauge_color = '#ff0055'  # Red/Pink for aggressive
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        title={
            'text': f"Risk Score: {category}",
            'font': {'size': 20, 'color': '#e0e6ed', 'family': 'Outfit'}
        },
        number={
            'font': {'size': 36, 'color': gauge_color, 'family': 'JetBrains Mono'},
            'suffix': '/100'
        },
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': '#30363d',
                'dtick': 20,
            },
            'bar': {'color': gauge_color},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 2,
            'bordercolor': '#30363d',
            'steps': [
                {'range': [0, 20], 'color': 'rgba(0, 242, 255, 0.1)'},
                {'range': [20, 35], 'color': 'rgba(0, 242, 255, 0.15)'},
                {'range': [35, 50], 'color': 'rgba(0, 242, 255, 0.2)'},
                {'range': [50, 70], 'color': 'rgba(112, 0, 255, 0.2)'},
                {'range': [70, 85], 'color': 'rgba(112, 0, 255, 0.3)'},
                {'range': [85, 100], 'color': 'rgba(255, 0, 85, 0.3)'}
            ],
            'threshold': {
                'line': {'color': gauge_color, 'width': 4},
                'thickness': 0.75,
                'value': risk_score
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#e0e6ed', 'family': 'Outfit'},
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_risk_metrics_row(risk_score: float, category: str, equity_pct: float, buckets: list):
    """
    Render a compact row of risk metrics.
    
    Parameters
    ----------
    risk_score : float
        Investor risk score
    category : str
        Risk category
    equity_pct : float
        Equity allocation percentage
    buckets : list
        Assigned risk buckets
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-label">Risk Score</div>
                <div class="stat-val glow-text-primary">{risk_score:.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-label">Profile</div>
                <div class="stat-val" style="font-size: 1.4rem;">{category.split()[0]}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-label">Equity Allocation</div>
                <div class="stat-val glow-text-success">{equity_pct:.0f}%</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        bucket_str = str(buckets) if buckets else "N/A"
        st.markdown(f"""
            <div class="metric-card">
                <div class="stat-label">Risk Buckets</div>
                <div class="stat-val glow-text-secondary" style="font-size: 1.4rem;">{bucket_str}</div>
            </div>
        """, unsafe_allow_html=True)
