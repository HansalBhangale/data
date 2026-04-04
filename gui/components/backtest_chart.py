"""
Backtest Chart Component - Portfolio vs S&P 500 Performance
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def render_backtest_chart(backtest_result: dict):
    """
    Render a line chart comparing portfolio vs S&P 500 performance.

    Parameters
    ----------
    backtest_result : dict
        Backtest result dictionary from calculate_real_backtest()
    """
    if not backtest_result or backtest_result.get('n_periods', 0) < 30:
        st.warning("Insufficient data for backtest visualization")
        return

    # Get cumulative series
    cumulative_port = backtest_result.get('cumulative_portfolio')
    cumulative_spy = backtest_result.get('cumulative_spy')

    if cumulative_port is None or cumulative_port.empty:
        st.warning("No cumulative data available")
        return

    # Convert to DataFrame for plotting
    dates = cumulative_port.index

    # Create figure
    fig = go.Figure()

    # Portfolio line (solid blue)
    fig.add_trace(go.Scatter(
        x=dates,
        y=cumulative_port.values,
        mode='lines',
        name='Portfolio',
        line=dict(color='#3B82F6', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.06)',
    ))

    # SPY line (dashed indigo)
    if cumulative_spy is not None and not cumulative_spy.empty:
        # Align dates
        common_idx = cumulative_port.index.intersection(cumulative_spy.index)
        if len(common_idx) > 0:
            fig.add_trace(go.Scatter(
                x=common_idx,
                y=cumulative_spy.loc[common_idx].values,
                mode='lines',
                name='S&P 500',
                line=dict(color='#6366F1', width=2, dash='dash'),
            ))

    # Layout
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family='Outfit', size=12, color='#94A3B8')
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.03)',
            title="",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.03)',
            title="Cumulative Return",
            tickformat='.0%',
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show date range
    start = backtest_result.get('start_date', 'N/A')
    end = backtest_result.get('end_date', 'N/A')
    periods = backtest_result.get('n_periods', 0)
    st.caption(f"Period: {start} to {end} ({periods} trading days)")


def render_performance_metrics(backtest_result: dict):
    """
    Render key performance metrics.

    Parameters
    ----------
    backtest_result : dict
        Backtest result dictionary
    """
    if not backtest_result:
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        ann_ret = backtest_result.get('annual_return', 0)
        st.metric(
            label="Annual Return",
            value=f"{ann_ret * 100:.1f}%",
        )

    with col2:
        vol = backtest_result.get('annual_volatility', 0)
        st.metric(
            label="Volatility",
            value=f"{vol * 100:.1f}%",
        )

    with col3:
        sharpe = backtest_result.get('sharpe_ratio', 0)
        st.metric(
            label="Sharpe Ratio",
            value=f"{sharpe:.2f}",
        )

    with col4:
        alpha = backtest_result.get('alpha', 0)
        st.metric(
            label="Alpha",
            value=f"{alpha * 100:.1f}%",
        )

    with col5:
        beta = backtest_result.get('beta', 1)
        st.metric(
            label="Beta",
            value=f"{beta:.2f}",
        )
