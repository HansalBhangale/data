"""
Metrics Table Component - Comparison Metrics Display
"""

import streamlit as st
import pandas as pd


def render_beat_spy_badge(backtest_result: dict):
    """
    Render a badge showing whether portfolio beats S&P 500.
    """
    if not backtest_result:
        return

    beat_spy = backtest_result.get('beat_spy', False)
    outperformance = backtest_result.get('outperformance', 0)

    if beat_spy:
        st.markdown(f"""
            <div class="beat-spy-badge success" style="margin-bottom: 1rem;">
                <span style="font-size: 1.3rem;">✓</span>
                <span>BEATS S&P 500 by {outperformance * 100:+.1f}%</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="beat-spy-badge failure" style="margin-bottom: 1rem;">
                <span style="font-size: 1.3rem;">✗</span>
                <span>BELOW S&P 500 by {abs(outperformance) * 100:.1f}%</span>
            </div>
        """, unsafe_allow_html=True)


def render_metrics_comparison(backtest_result: dict):
    """
    Render a comparison table of portfolio vs S&P 500 metrics.
    """
    if not backtest_result:
        return

    # Build data for table
    metrics_data = []

    # Annual Return
    port_ret = backtest_result.get('annual_return', 0)
    spy_ret = backtest_result.get('spy_annual_return', 0)
    metrics_data.append({
        'Metric': 'Annual Return',
        'Portfolio': f"{port_ret * 100:+.1f}%",
        'S&P 500': f"{spy_ret * 100:+.1f}%",
        'Diff': f"{(port_ret - spy_ret) * 100:+.1f}%",
        'Direction': 'positive' if port_ret > spy_ret else 'negative'
    })

    # Volatility
    port_vol = backtest_result.get('annual_volatility', 0)
    spy_vol = backtest_result.get('annual_volatility', 0.25)
    metrics_data.append({
        'Metric': 'Volatility',
        'Portfolio': f"{port_vol * 100:.1f}%",
        'S&P 500': f"{spy_vol * 100:.1f}%",
        'Diff': f"{(port_vol - spy_vol) * 100:+.1f}%",
        'Direction': 'positive' if port_vol < spy_vol else 'negative'
    })

    # Sharpe Ratio
    port_sharpe = backtest_result.get('sharpe_ratio', 0)
    spy_sharpe = backtest_result.get('spy_sharpe', 0)
    metrics_data.append({
        'Metric': 'Sharpe Ratio',
        'Portfolio': f"{port_sharpe:.2f}",
        'S&P 500': f"{spy_sharpe:.2f}",
        'Diff': f"{port_sharpe - spy_sharpe:+.2f}",
        'Direction': 'positive' if port_sharpe > spy_sharpe else 'negative'
    })

    # Alpha
    alpha = backtest_result.get('alpha', 0)
    metrics_data.append({
        'Metric': 'Alpha',
        'Portfolio': f"{alpha * 100:+.2f}%",
        'S&P 500': "0.00%",
        'Diff': f"{alpha * 100:+.2f}%",
        'Direction': 'positive' if alpha > 0 else 'negative'
    })

    # Beta
    beta = backtest_result.get('beta', 1)
    metrics_data.append({
        'Metric': 'Beta',
        'Portfolio': f"{beta:.2f}",
        'S&P 500': "1.00",
        'Diff': f"{beta - 1:+.2f}",
        'Direction': 'positive' if beta <= 1 else 'negative'
    })

    # Max Drawdown
    max_dd = backtest_result.get('max_drawdown', 0)
    spy_dd = -0.25
    metrics_data.append({
        'Metric': 'Max Drawdown',
        'Portfolio': f"{max_dd * 100:.1f}%",
        'S&P 500': f"{spy_dd * 100:.1f}%",
        'Diff': f"{(max_dd - spy_dd) * 100:+.1f}%",
        'Direction': 'positive' if max_dd > spy_dd else 'negative'
    })

    # Create DataFrame
    df = pd.DataFrame(metrics_data)

    # Display as dataframe
    st.dataframe(
        df[['Metric', 'Portfolio', 'S&P 500', 'Diff']],
        use_container_width=True,
        hide_index=True,
        column_config={
            'Metric': st.column_config.TextColumn('Metric', width='medium'),
            'Portfolio': st.column_config.TextColumn('Portfolio', width='small'),
            'S&P 500': st.column_config.TextColumn('S&P 500', width='small'),
            'Diff': st.column_config.TextColumn('Diff', width='small'),
        }
    )


def render_max_drawdown(backtest_result: dict):
    """
    Render max drawdown metric.
    """
    if not backtest_result:
        return

    max_dd = backtest_result.get('max_drawdown', 0)
    st.metric(
        label="Maximum Drawdown",
        value=f"{max_dd * 100:.1f}%",
    )