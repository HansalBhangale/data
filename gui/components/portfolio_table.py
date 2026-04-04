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

    # Professional color palette
    colors = [
        '#3B82F6', '#6366F1', '#10B981', '#EF4444', '#F59E0B',
        '#06B6D4', '#EC4899', '#14B8A6', '#F97316', '#8B5CF6',
        '#64748B'
    ]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker_colors=colors[:len(labels)],
        textinfo='label+percent',
        textposition='outside',
        textfont={'family': 'Outfit', 'size': 11, 'color': '#94A3B8'},
    )])

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font={'family': 'Outfit', 'size': 11, 'color': '#94A3B8'}
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

    # Check if this is a unified portfolio (with type field) or just stocks
    has_type = 'type' in df.columns

    if has_type:
        # Unified portfolio with stocks and bonds
        df['Type'] = df['type']
        
        # Different columns for equity vs bond
        equity_mask = df['Type'] == 'Equity'
        bond_mask = df['Type'] == 'Bond'
        
        display_data = []
        for _, row in df.iterrows():
            if row['Type'] == 'Equity':
                display_data.append({
                    'Type': 'Equity',
                    'Ticker': row['ticker'],
                    'Score': f"{row.get('final_score', row.get('composite_score', 0)):.3f}",
                    'Risk': row.get('risk_bucket', '-'),
                    'Weight': f"{row['weight_pct']:.1f}%",
                    'Capital': f"${row['capital_allocated']:,.0f}",
                })
            else:
                display_data.append({
                    'Type': 'Bond',
                    'Ticker': row['ticker'],
                    'Score': f"{row.get('score', row.get('composite_score', 0)):.2f}",
                    'Risk': '-',
                    'Weight': f"{row['weight_pct']:.1f}%",
                    'Capital': f"${row['capital_allocated']:,.0f}",
                })
        
        display_df = pd.DataFrame(display_data)
        
        # Display with styling
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Type': st.column_config.TextColumn('Type', width='small'),
                'Ticker': st.column_config.TextColumn('Ticker', width='small'),
                'Score': st.column_config.TextColumn('Score'),
                'Risk': st.column_config.TextColumn('Bucket'),
                'Weight': st.column_config.TextColumn('Weight %'),
                'Capital': st.column_config.TextColumn('Capital'),
            }
        )
    else:
        # Original stock-only format
        display_df = pd.DataFrame({
            'Ticker': df['ticker'],
            'Final Score': df['final_score'].round(3),
            'Momentum': df['momentum_score'].round(3),
            'Quality': df['quality_score'].round(3),
            'Risk Bucket': df['risk_bucket'],
            'Weight': df['weight_pct'].apply(lambda x: f"{x:.1f}%"),
            'Capital': df['capital_allocated'].apply(lambda x: f"${x:,.0f}"),
        })

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

    # Check if this is a unified portfolio (has bonds)
    has_bonds = 'bond_weight' in portfolio and portfolio.get('bond_weight', 0) > 0
    
    if has_bonds:
        # Unified portfolio with stocks and bonds
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                label="Holdings",
                value=portfolio.get('n_holdings', 0)
            )

        with col2:
            st.metric(
                label="Stocks",
                value=portfolio.get('n_stocks', 0)
            )

        with col3:
            st.metric(
                label="Bonds",
                value=portfolio.get('n_bonds', 0)
            )

        with col4:
            st.metric(
                label="Equity",
                value=f"{portfolio.get('equity_weight', 0):.0f}%"
            )

        with col5:
            st.metric(
                label="Bonds",
                value=f"{portfolio.get('bond_weight', 0):.0f}%"
            )
    else:
        # Original stock-only format
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
