"""
Monte Carlo Chart Component - Future Projections Visualization

Shows:
1. Three-tier projections (Optimistic/Base/Conservative)
2. Toggle between scenarios (Actual/Blend/Stress)
3. Comparison metrics at each time horizon
4. Value at Risk (VaR) metrics
5. Bayesian shrinkage explanation
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def render_monte_carlo_chart(
    mc_result: Dict,
    backtest_data: Optional[Dict] = None,
    show_backtest: bool = True
):
    """
    Render Monte Carlo simulation results with three-tier scenarios.

    Parameters
    ----------
    mc_result : Dict
        Monte Carlo result from run_monte_carlo()
    backtest_data : Dict, optional
        Backtest data with cumulative returns
    show_backtest : bool
        Whether to show backtest historical data
    """
    if not mc_result:
        st.warning("No projection data available")
        return

    initial_capital = mc_result.get('initial_capital', 10000)
    tier_info = mc_result.get('tiers', {})
    n_months = mc_result.get('params', {}).get('n_months', 12)

    st.markdown("### 📈 Future Projections (Monte Carlo)")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Starting Capital", f"${initial_capital:,.0f}")
    with col2:
        p1 = mc_result['actual']['percentiles'].get(1, {})
        st.metric("1-Year Median", f"${p1.get('p50', 0):,.0f}")
    with col3:
        p5 = mc_result['actual']['percentiles'].get(5, {})
        st.metric("5-Year Median", f"${p5.get('p50', 0):,.0f}")
    with col4:
        p10 = mc_result['actual']['percentiles'].get(10, {})
        st.metric("10-Year Median", f"${p10.get('p50', 0):,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Tier selector with Conservative as default
    tier = st.radio(
        "Return Assumption Tier",
        ["Conservative", "Base (Bayesian)", "Optimistic"],
        horizontal=True,
        key="mc_tier",
        index=0  # Default to Conservative
    )

    # Display tier explanation
    tier_key = 'conservative' if tier == 'Conservative' else ('base' if tier == 'Base (Bayesian)' else 'optimistic')
    if tier_key in tier_info:
        tier_data = tier_info[tier_key]
        
        st.info(f"**{tier} scenario**: {tier_data.get('description', '')}")
        
        if tier == "Base (Bayesian)":
            shrinkage_factor = tier_data.get('shrinkage_factor', 0.25)
            st.caption(
                f"Based on {n_months} months of backtest data. "
                f"Shrinkage factor: {shrinkage_factor:.0%} toward market return (10%). "
                f"This penalizes short backtest periods automatically."
            )
        else:
            st.caption(f"Formula: {tier_data.get('formula', '')}")
    
    # Transparency warnings for short backtest periods
    if n_months < 12:
        st.error(
            f"⚠️ **Fewer than 12 months of data ({n_months} months)** — "
            f"projections are highly speculative. "
            f"Results will change significantly as more data accumulates."
        )
    elif n_months < 24:
        st.warning(
            f"📊 **Conservative projection based on {n_months} months of track record.** "
            f"Confidence improves with longer data. "
            f"Results will become more stable as the backtest extends."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Scenario selector
    scenario = st.radio(
        "Projection Scenario",
        ["Actual Volatility", "Blended Volatility", "Stress Scenarios"],
        horizontal=True,
        key="mc_scenario"
    )

    fig = go.Figure()

    years = list(range(11))

    if scenario == "Actual Volatility":
        _add_actual_projections(fig, mc_result, years, initial_capital)
    elif scenario == "Blended Volatility":
        _add_blend_projections(fig, mc_result, years, initial_capital)
    else:
        _add_stress_projections(fig, mc_result, years, initial_capital)

    fig.update_layout(
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Years from Now",
            tickmode='array',
            tickvals=list(range(11)),
            ticktext=[f"+{y}yr" for y in range(11)],
            gridcolor='#334155',
            color='#94A3B8'
        ),
        yaxis=dict(
            title="Portfolio Value ($)",
            gridcolor='#334155',
            color='#94A3B8',
            tickformat='$,.0f'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color='#94A3B8')
        ),
        margin=dict(l=60, r=30, t=60, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show risk metrics
    _render_risk_metrics(mc_result)

    # Show projection comparison table
    _render_projection_metrics(mc_result, scenario)


def _add_actual_projections(
    fig: go.Figure,
    mc_result: Dict,
    years: List[int],
    initial_capital: float
):
    """Add actual volatility scenario projections to chart."""

    percentiles = mc_result['actual']['percentiles']

    p50_values = [percentiles.get(y, {}).get('p50', initial_capital) for y in years]
    p25_values = [percentiles.get(y, {}).get('p25', initial_capital) for y in years]
    p75_values = [percentiles.get(y, {}).get('p75', initial_capital) for y in years]
    p10_values = [percentiles.get(y, {}).get('p10', initial_capital) for y in years]
    p90_values = [percentiles.get(y, {}).get('p90', initial_capital) for y in years]
    p5_values = [percentiles.get(y, {}).get('p5', initial_capital) for y in years]
    p95_values = [percentiles.get(y, {}).get('p95', initial_capital) for y in years]

    spy_percentiles = mc_result['spy_baseline']['percentiles']
    spy_p50 = [spy_percentiles.get(y, {}).get('p50', initial_capital) for y in years]

    # 95-5 percentile band (widest)
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=p95_values + p5_values[::-1],
        fill='toself',
        fillcolor='rgba(16, 185, 129, 0.1)',
        line=dict(color='rgba(16, 185, 129, 0)'),
        name='95th-5th Percentile',
        showlegend=True
    ))

    # 90-10 percentile band
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=p90_values + p10_values[::-1],
        fill='toself',
        fillcolor='rgba(16, 185, 129, 0.15)',
        line=dict(color='rgba(16, 185, 129, 0)'),
        name='90th-10th Percentile',
        showlegend=True
    ))

    # 75-25 percentile band (IQR)
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=p75_values + p25_values[::-1],
        fill='toself',
        fillcolor='rgba(16, 185, 129, 0.25)',
        line=dict(color='rgba(16, 185, 129, 0)'),
        name='75th-25th Percentile (IQR)',
        showlegend=True
    ))

    # Median portfolio
    fig.add_trace(go.Scatter(
        x=years, y=p50_values,
        mode='lines',
        line=dict(color='#10B981', width=3, dash='solid'),
        name='Portfolio (Median)'
    ))

    # S&P 500 baseline
    fig.add_trace(go.Scatter(
        x=years, y=spy_p50,
        mode='lines',
        line=dict(color='#F59E0B', width=2, dash='dash'),
        name='S&P 500 (Median)'
    ))

    # Starting point
    fig.add_trace(go.Scatter(
        x=[0], y=[initial_capital],
        mode='markers',
        marker=dict(color='#3B82F6', size=10),
        name='Starting Value'
    ))


def _add_blend_projections(
    fig: go.Figure,
    mc_result: Dict,
    years: List[int],
    initial_capital: float
):
    """Add blended volatility scenario to chart."""

    percentiles = mc_result['blend']['percentiles']

    blend_p50 = [percentiles.get(y, {}).get('p50', initial_capital) for y in years]
    blend_p25 = [percentiles.get(y, {}).get('p25', initial_capital) for y in years]
    blend_p75 = [percentiles.get(y, {}).get('p75', initial_capital) for y in years]

    spy_percentiles = mc_result['spy_baseline']['percentiles']
    spy_p50 = [spy_percentiles.get(y, {}).get('p50', initial_capital) for y in years]

    # Actual portfolio for comparison
    actual_p50 = [mc_result['actual']['percentiles'].get(y, {}).get('p50', initial_capital) for y in years]

    # IQR band
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=blend_p75 + blend_p25[::-1],
        fill='toself',
        fillcolor='rgba(139, 92, 246, 0.25)',
        line=dict(color='rgba(139, 92, 246, 0)'),
        name='75th-25th Percentile',
        showlegend=True
    ))

    # Blended median
    fig.add_trace(go.Scatter(
        x=years, y=blend_p50,
        mode='lines',
        line=dict(color='#8B5CF6', width=3, dash='solid'),
        name='Blended (Median)'
    ))

    # Actual median for comparison
    fig.add_trace(go.Scatter(
        x=years, y=actual_p50,
        mode='lines',
        line=dict(color='#10B981', width=2, dash='dot'),
        name='Actual (Median)'
    ))

    # S&P 500 baseline
    fig.add_trace(go.Scatter(
        x=years, y=spy_p50,
        mode='lines',
        line=dict(color='#F59E0B', width=2, dash='dash'),
        name='S&P 500 (Median)'
    ))

    # Starting point
    fig.add_trace(go.Scatter(
        x=[0], y=[initial_capital],
        mode='markers',
        marker=dict(color='#3B82F6', size=10),
        name='Starting Value'
    ))


def _add_stress_projections(
    fig: go.Figure,
    mc_result: Dict,
    years: List[int],
    initial_capital: float
):
    """Add stress scenario projections to chart."""

    colors = {
        '2008_crash': '#EF4444',      # Red
        'covid_crash': '#F97316',      # Orange
        'dot_com': '#EAB308',         # Yellow
        'inflation_2022': '#6366F1'    # Indigo
    }

    # Add each stress scenario
    for scenario_key, scenario_data in mc_result.get('stress', {}).items():
        p50_values = [scenario_data['percentiles'].get(y, {}).get('p50', initial_capital) for y in years]

        fig.add_trace(go.Scatter(
            x=years, y=p50_values,
            mode='lines',
            line=dict(color=colors.get(scenario_key, '#64748B'), width=2, dash='dot'),
            name=scenario_data['name']
        ))

    # Normal market median
    actual_p50 = [mc_result['actual']['percentiles'].get(y, {}).get('p50', initial_capital) for y in years]
    fig.add_trace(go.Scatter(
        x=years, y=actual_p50,
        mode='lines',
        line=dict(color='#10B981', width=3),
        name='Normal Market'
    ))

    # S&P 500 baseline
    spy_p50 = [mc_result['spy_baseline']['percentiles'].get(y, {}).get('p50', initial_capital) for y in years]
    fig.add_trace(go.Scatter(
        x=years, y=spy_p50,
        mode='lines',
        line=dict(color='#F59E0B', width=2, dash='dash'),
        name='S&P 500 (Median)'
    ))

    # Starting point
    fig.add_trace(go.Scatter(
        x=[0], y=[initial_capital],
        mode='markers',
        marker=dict(color='#3B82F6', size=10),
        name='Starting Value'
    ))


def _render_risk_metrics(mc_result: Dict):
    """Render VaR and risk metrics."""

    st.markdown("#### 📊 Risk Metrics (10-Year Horizon)")

    # Import VaR calculation
    from gui.core.monte_carlo import calculate_var

    var_95 = calculate_var(mc_result, horizon=10, confidence_level=0.95)
    var_99 = calculate_var(mc_result, horizon=10, confidence_level=0.99)

    if var_95 and var_99:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "95% VaR",
                f"${abs(var_95['var_dollar']):,.0f}",
                f"{var_95['var_pct']*100:.1f}%",
                delta_color="inverse"
            )
            st.caption("5% chance of losing this much or more")

        with col2:
            st.metric(
                "99% VaR",
                f"${abs(var_99['var_dollar']):,.0f}",
                f"{var_99['var_pct']*100:.1f}%",
                delta_color="inverse"
            )
            st.caption("1% chance of losing this much or more")

        with col3:
            st.metric(
                "Expected Shortfall (95%)",
                f"${abs(var_95['cvar_dollar']):,.0f}",
                f"{var_95['cvar_pct']*100:.1f}%",
                delta_color="inverse"
            )
            st.caption("Avg loss in worst 5% scenarios")

        with col4:
            beat_prob_conservative = mc_result.get('beat_spy_probability_conservative', {}).get(10, 0.5)
            beat_prob_historical = mc_result.get('beat_spy_probability', {}).get(10, 0.5)
            correlation = mc_result.get('params', {}).get('correlation', 0.5)
            spy_backtest = mc_result.get('params', {}).get('spy_backtest_return', 0.10)
            
            # Show "Unfavorable" when probability is very low
            display_conservative = f"{beat_prob_conservative*100:.0f}%" if beat_prob_conservative >= 0.05 else "Unfavorable"
            
            # Show both beat probabilities
            st.metric(
                "Beat S&P (Symmetric)",
                display_conservative,
                f"Historical: {beat_prob_historical*100:.0f}%",
                delta_color="normal"
            )
            
            # Build tooltip with context
            tooltip_parts = [
                "Symmetric: same shrinkage applied to S&P",
                f"Historical: fixed 10% baseline",
                f"Correlation: {correlation:.2f}"
            ]
            if beat_prob_conservative < 0.05:
                tooltip_parts.append(f"S&P backtest ({spy_backtest*100:.0f}%) outperformed portfolio")
            st.caption(" | ".join(tooltip_parts))


def _render_projection_metrics(mc_result: Dict, scenario: str):
    """Render projection comparison metrics table."""

    st.markdown("#### 📈 Projection Comparison")

    correlation = mc_result.get('params', {}).get('correlation', 0.5)
    n_months = mc_result.get('params', {}).get('n_months', 12)

    horizons = [1, 3, 5, 10]

    data = []
    for h in horizons:
        actual = mc_result['actual']['percentiles'].get(h, {})
        blend = mc_result['blend']['percentiles'].get(h, {})
        spy = mc_result['spy_baseline']['percentiles'].get(h, {})

        beat_prob_historical = mc_result.get('beat_spy_probability', {}).get(h, 0.5)
        beat_prob_conservative = mc_result.get('beat_spy_probability_conservative', {}).get(h, 0.5)

        # Show "Unfavorable" when probability is very low
        sym_display = f"{beat_prob_conservative*100:.0f}%" if beat_prob_conservative >= 0.05 else "< 5%"
        hist_display = f"{beat_prob_historical*100:.0f}%"

        data.append({
            'Horizon': f"+{h}yr",
            'Portfolio (Median)': f"${actual.get('p50', 0):,.0f}",
            'Range (10th-90th)': f"${actual.get('p10', 0):,.0f} - ${actual.get('p90', 0):,.0f}",
            'S&P 500 (Median)': f"${spy.get('p50', 0):,.0f}",
            'Beat S&P (Symmetric)': sym_display,
            'Beat S&P (Historical)': hist_display,
        })

    df = pd.DataFrame(data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Horizon': st.column_config.TextColumn('Horizon', width='small'),
            'Portfolio (Median)': st.column_config.TextColumn('Portfolio', width='medium'),
            'Range (10th-90th)': st.column_config.TextColumn('Range', width='medium'),
            'S&P 500 (Median)': st.column_config.TextColumn('S&P 500', width='medium'),
            'Beat S&P (Symmetric)': st.column_config.TextColumn('Symmetric', width='small'),
            'Beat S&P (Historical)': st.column_config.TextColumn('Historical', width='small'),
        }
    )

    st.caption(
        "Beat S&P (Symmetric): Same shrinkage applied to both portfolio and S&P. Shows '< 5%' when S&P backtest outperformed. "
        "Beat S&P (Historical): Uses 10% long-run S&P average as benchmark."
    )


def render_stress_scenario_details(mc_result: Dict):
    """Render detailed stress scenario information."""

    st.markdown("#### 📉 Stress Scenario Details")

    st.info(
        "**Note:** Stress scenarios apply crash in Year 1, then model recovery pattern. "
        "This gives more realistic outcomes than applying crash every year."
    )

    for scenario_key, scenario_data in mc_result.get('stress', {}).items():
        with st.expander(f"📉 {scenario_data['name']}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Year 1 Crash", f"{scenario_data.get('annual_return', 0)*100:.0f}%")
            with col2:
                st.metric("Crash Volatility", f"{scenario_data.get('volatility', 0)*100:.0f}%")
            with col3:
                ten_year = scenario_data['percentiles'].get(10, {})
                st.metric("10-Year Median", f"${ten_year.get('p50', 0):,.0f}")

            # Recovery pattern description
            if scenario_key == 'covid_crash':
                st.caption("✅ V-shaped recovery: Sharp crash followed by rapid bounce-back")
            elif scenario_key == 'dot_com':
                st.caption("⚠️ L-shaped recovery: 3 consecutive years of decline, slow recovery")
            elif scenario_key == '2008_crash':
                st.caption("⚠️ U-shaped recovery: Gradual recovery over 3+ years")
            else:
                st.caption(scenario_data.get('description', ''))


def render_monte_carlo_summary(mc_result: Dict):
    """Render a compact summary of Monte Carlo results."""

    if not mc_result:
        return

    st.markdown("### 🎯 Key Takeaways")

    initial = mc_result['initial_capital']
    p10_10yr = mc_result['actual']['percentiles'].get(10, {}).get('p10', initial)
    p50_10yr = mc_result['actual']['percentiles'].get(10, {}).get('p50', initial)
    p90_10yr = mc_result['actual']['percentiles'].get(10, {}).get('p90', initial)
    beat_prob = mc_result.get('beat_spy_probability', {}).get(10, 0.5)

    # Calculate expected CAGR
    cagr_median = (p50_10yr / initial) ** (1/10) - 1

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **10-Year Projection:**
        - **Best case (90th):** ${p90_10yr:,.0f}
        - **Median:** ${p50_10yr:,.0f}
        - **Worst case (10th):** ${p10_10yr:,.0f}
        - **Median CAGR:** {cagr_median*100:.1f}%
        """)

    with col2:
        st.markdown(f"""
        **Risk Assessment:**
        - **Probability of beating S&P:** {beat_prob*100:.0f}
        - **1-in-10 chance of:** ${p10_10yr:,.0f} or less
        - **1-in-10 chance of:** ${p90_10yr:,.0f} or more
        """)


def render_distribution_histogram(mc_result: Dict, horizon: int = 10):
    """Render histogram of final portfolio values."""

    if horizon not in mc_result['actual']['percentiles']:
        return

    values = mc_result['actual']['percentiles'][horizon].get('all_values', [])
    if not values:
        return

    fig = go.Figure()

    # Add histogram
    fig.add_trace(go.Histogram(
        x=values,
        nbinsx=50,
        marker_color='#10B981',
        marker_line_color='#059669',
        marker_line_width=1,
        opacity=0.75,
        name='Portfolio Values'
    ))

    # Add percentile lines
    percentiles = mc_result['actual']['percentiles'][horizon]
    initial = mc_result['initial_capital']

    for label, value, color in [
        ('10th', percentiles['p10'], '#EF4444'),
        ('Median', percentiles['p50'], '#3B82F6'),
        ('90th', percentiles['p90'], '#10B981'),
    ]:
        fig.add_vline(
            x=value,
            line_dash="dash",
            line_color=color,
            annotation_text=f"{label}: ${value:,.0f}",
            annotation_position="top"
        )

    fig.update_layout(
        title=f"Distribution of Portfolio Values at {horizon} Years",
        xaxis_title="Portfolio Value ($)",
        yaxis_title="Frequency",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#334155', color='#94A3B8', tickformat='$,.0f'),
        yaxis=dict(gridcolor='#334155', color='#94A3B8'),
        showlegend=False,
        margin=dict(l=60, r=30, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)