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
        textfont={'family': 'Outfit', 'size': 10, 'color': '#94A3B8'},
        outsidetextfont={'family': 'Outfit', 'size': 10, 'color': '#94A3B8'},
    )])

    fig.update_layout(
        showlegend=False,
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[
            dict(
                text='<b>Holdings</b>',
                x=0.5, y=0.5,
                font=dict(family='Outfit', size=12, color='#94A3B8'),
                showarrow=False
            )
        ]
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
        display_data = []
        for _, row in df.iterrows():
            sentiment = row.get('sentiment_score', 50)
            
            # Determine sentiment label and emoji
            if sentiment > 55:
                sentiment_emoji = "🟢"
                sentiment_label = "Positive"
            elif sentiment < 45:
                sentiment_emoji = "🔴"
                sentiment_label = "Negative"
            else:
                sentiment_emoji = "⚪"
                sentiment_label = "Neutral"
            
            if row['Type'] == 'Equity':
                display_data.append({
                    'Type': 'Equity',
                    'Ticker': row['ticker'],
                    'Score': f"{row.get('final_score', row.get('composite_score', 0)):.3f}",
                    'Sentiment': f"{sentiment_emoji} {int(sentiment)}",
                    'Sentiment Value': sentiment,
                    'Risk': row.get('risk_bucket', '-'),
                    'Weight': f"{row['weight_pct']:.1f}%",
                    'Capital': f"${row['capital_allocated']:,.0f}",
                })
            else:
                display_data.append({
                    'Type': 'Bond',
                    'Ticker': row['ticker'],
                    'Score': f"{row.get('score', row.get('composite_score', 0)):.2f}",
                    'Sentiment': f"{sentiment_emoji} {int(sentiment)}",
                    'Sentiment Value': sentiment,
                    'Risk': '-',
                    'Weight': f"{row['weight_pct']:.1f}%",
                    'Capital': f"${row['capital_allocated']:,.0f}",
                })
        
        display_df = pd.DataFrame(display_data)
        
        # Calculate average sentiment
        avg_sentiment = display_df['Sentiment Value'].mean()
        
        # Display sentiment summary
        col1, col2, col3 = st.columns(3)
        positive_count = (display_df['Sentiment Value'] > 55).sum()
        negative_count = (display_df['Sentiment Value'] < 45).sum()
        neutral_count = len(display_df) - positive_count - negative_count
        
        with col1:
            st.metric("Avg Sentiment", f"{avg_sentiment:.0f}/100")
        with col2:
            st.metric("Positive", f"🟢 {positive_count}")
        with col3:
            st.metric("Negative", f"🔴 {negative_count}")
        
        st.divider()
        
        # Display with styling (hide Sentiment Value column)
        st.dataframe(
            display_df.drop(columns=['Sentiment Value']),
            use_container_width=True,
            hide_index=True,
            column_config={
                'Type': st.column_config.TextColumn('Type', width='small'),
                'Ticker': st.column_config.TextColumn('Ticker', width='small'),
                'Score': st.column_config.TextColumn('Score'),
                'Sentiment': st.column_config.TextColumn('Sentiment'),
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

    has_bonds = 'bond_weight' in portfolio and portfolio.get('bond_weight', 0) > 0
    
    if has_bonds:
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


def render_sector_allocation(portfolio: dict):
    """
    Render sector allocation pie chart for diversified portfolio.
    
    Parameters
    ----------
    portfolio : dict
        Portfolio dictionary with 'sector_allocation' and 'n_sectors' keys
    """
    if not portfolio:
        return
    
    sector_alloc = portfolio.get('sector_allocation', {})
    n_sectors = portfolio.get('n_sectors', 0)
    
    if not sector_alloc:
        st.info("No sector data available")
        return
    
    st.markdown("#### Sector Diversification")
    
    col_pie, col_metrics = st.columns([2, 1])
    
    with col_pie:
        labels = list(sector_alloc.keys())
        values = list(sector_alloc.values())
        
        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#6366F1',
            '#06B6D4', '#EC4899', '#14B8A6', '#F97316', '#8B5CF6',
            '#64748B', '#84CC16', '#22D3EE', '#A855F7', '#EAB308'
        ]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker_colors=colors[:len(labels)],
            textinfo='label+percent',
            textposition='outside',
            textfont={'family': 'Outfit', 'size': 10, 'color': '#94A3B8'},
            outsidetextfont={'family': 'Outfit', 'size': 10, 'color': '#94A3B8'},
            hovertemplate='%{label}<br>%{percent}<extra></extra>',
        )])
        
        fig.update_layout(
            showlegend=False,
            height=250,
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=60, r=20, t=20, b=20),
            annotations=[
                dict(
                    text='<b>Sectors</b>',
                    x=0.5, y=0.5,
                    font=dict(family='Outfit', size=12, color='#94A3B8'),
                    showarrow=False
                )
            ]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_metrics:
        st.metric("Total Sectors", f"{n_sectors}")
        max_sector = portfolio.get('max_sector_weight', 25)
        st.metric("Max Sector Weight", f"{max_sector:.0f}%")
        st.metric("Stocks", f"{portfolio.get('n_stocks', portfolio.get('n_holdings', 0))}")


def render_section_header(title: str):
    """Render a section header."""
    st.markdown(f"""
        <h2 class="section-header">{title}</h2>
    """, unsafe_allow_html=True)
