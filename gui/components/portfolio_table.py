"""
Portfolio Table Component - Holdings Display
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_holdings_pie(portfolio: dict):
    """
    Render a pie chart of top holdings.
    
    Parameters
    ----------
    portfolio : dict
        Portfolio dictionary with 'allocations' key
    """
    if not portfolio or 'allocations' not in portfolio:
        st.warning("No portfolio data available")
        return
    
    allocations = portfolio['allocations']
    
    # Prepare data (top 10 + cash)
    top_holdings = allocations[:10]
    labels = [a['ticker'] for a in top_holdings]
    values = [a['weight_pct'] for a in top_holdings]
    
    # Add cash if present
    if portfolio.get('cash_weight', 0) > 0:
        labels.append('Cash')
        values.append(portfolio['cash_weight'])
    
    # Color palette
    colors = [
        '#00f2ff', '#7000ff', '#00ff9d', '#ff0055', '#ffaa00',
        '#0066ff', '#ff66aa', '#66ffcc', '#ff9933', '#6699ff',
        '#cccccc'
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker_colors=colors[:len(labels)],
        textinfo='label+percent',
        textposition='outside',
        textfont={'family': 'Outfit', 'size': 11},
    )])
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font={'family': 'Outfit', 'size': 11}
        ),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=10),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_holdings_table(portfolio: dict):
    """
    Render the full holdings table.
    
    Parameters
    ----------
    portfolio : dict
        Portfolio dictionary with 'allocations' key
    """
    if not portfolio or 'allocations' not in portfolio:
        st.warning("No holdings to display")
        return
    
    allocations = portfolio['allocations']
    
    # Create DataFrame
    df = pd.DataFrame(allocations)
    
    # Format columns for display
    display_df = pd.DataFrame({
        'Ticker': df['ticker'],
        'Final Score': df['final_score'].round(3),
        'Momentum': df['momentum_score'].round(3),
        'Quality': df['quality_score'].round(3),
        'Risk Bucket': df['risk_bucket'],
        'Weight': df['weight_pct'].apply(lambda x: f"{x:.1f}%"),
        'Capital': df['capital_allocated'].apply(lambda x: f"${x:,.0f}"),
    })
    
    # Display with styling
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Ticker': st.column_config.TextColumn('Ticker', width='small'),
            'Final Score': st.column_config.NumberColumn('Score', format='%.3f'),
            'Momentum': st.column_config.NumberColumn('Momentum', format='%.3f'),
            'Quality': st.column_config.NumberColumn('Quality', format='%.3f'),
            'Risk Bucket': st.column_config.TextColumn('Bucket'),
            'Weight': st.column_config.TextColumn('Weight %'),
            'Capital': st.column_config.TextColumn('Capital'),
        }
    )


def render_portfolio_summary(portfolio: dict):
    """
    Render portfolio summary metrics.
    
    Parameters
    ----------
    portfolio : dict
        Portfolio dictionary
    """
    if not portfolio:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Holdings",
            value=portfolio.get('n_holdings', 0)
        )
    
    with col2:
        st.metric(
            label="Equity",
            value=f"{portfolio.get('equity_weight', 0):.0f}%"
        )
    
    with col3:
        st.metric(
            label="Cash",
            value=f"{portfolio.get('cash_weight', 0):.0f}%"
        )
    
    with col4:
        bucket_str = str(portfolio.get('buckets', []))
        st.metric(
            label="Buckets",
            value=bucket_str
        )


def render_section_header(title: str):
    """Render a section header."""
    st.markdown(f"""
        <h2 class="section-header">{title}</h2>
    """, unsafe_allow_html=True)
