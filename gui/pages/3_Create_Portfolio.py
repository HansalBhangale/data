"""
Create Portfolio — Multi-page PAAS sub-page

Mirrors the core flow of app.py with three additions:
  • Auth guard (redirects unauthenticated visitors to Sign In)
  • Per-user sidebar with navigation and sign-out
  • "Save Portfolio" button that persists results to MongoDB
"""

# =============================================================================
# SYS.PATH SETUP — must come before ANY other imports so that the `gui`
# package (and its siblings) are resolvable when Streamlit executes this file.
# =============================================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# STUB CLASSES — must be defined *before* pickling/unpickling the risk model
# so that pickle can locate the class definitions during load.
# =============================================================================


class PCABasedRiskScorer:
    """Stub that satisfies pickle's class-lookup for the risk model."""

    def __init__(self, df=None):
        self.df = df


class EmpiricalCorrelationScorer:
    """Stub that satisfies pickle's class-lookup for the risk model."""

    def __init__(self, df=None):
        self.df = df


# =============================================================================
# STANDARD IMPORTS
# =============================================================================

import streamlit as st

from gui.components import (
    render_backtest_chart,
    render_beat_spy_badge,
    render_header,
    render_holdings_pie,
    render_holdings_table,
    render_metrics_comparison,
    render_performance_metrics,
    render_portfolio_summary,
    render_questionnaire,
    render_risk_gauge,
    render_risk_metrics_row,
    render_section_header,
)
from gui.core import (
    build_investor_portfolio,
    build_model_features,
    calculate_real_backtest,
    get_bucket_config,
    get_enhanced_investor_params,
    load_daily_prices,
    load_risk_model,
    predict_risk_score,
)
from gui.database import save_portfolio
from gui.styles import get_custom_css

# =============================================================================
# PAGE CONFIGURATION — must be the very first Streamlit call in the script.
# =============================================================================

st.set_page_config(
    page_title="PAAS | Create Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply the shared cyberpunk theme at module level so it is in the DOM even
# when st.stop() is called early (e.g. auth guard).
st.markdown(get_custom_css(), unsafe_allow_html=True)


# =============================================================================
# HELPERS
# =============================================================================


def _render_sidebar() -> None:
    """Render the authenticated user's navigation sidebar."""
    with st.sidebar:
        uname = st.session_state.get('user_name', 'User')
        uemail = st.session_state.get('user_email', '')
        st.markdown(
            f"""<div style="
                background: rgba(59,130,246,0.06);
                border: 1px solid rgba(59,130,246,0.12);
                border-radius: 10px;
                padding: 12px 14px;
                margin-bottom: 0.6rem;
            ">
                <div style="color:#E2E8F0;font-size:0.92rem;font-weight:600;">👤 {uname}</div>
                <div style="color:#94A3B8;font-size:0.75rem;margin-top:2px;">{uemail}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.divider()

        st.page_link(
            "pages/3_Create_Portfolio.py",
            label="📊  Create Portfolio",
        )
        st.page_link(
            "pages/4_My_Portfolios.py",
            label="📁  My Portfolios",
        )

        st.divider()

        if st.button("🚪 Sign Out", use_container_width=True):
            for key in [
                "user_id",
                "user_email",
                "user_name",
                "risk_score",
                "portfolio_result",
                "backtest_result",
            ]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")


def _init_session_state() -> None:
    """Ensure required session-state keys exist."""
    defaults = {
        "risk_score": None,
        "portfolio_result": None,
        "backtest_result": None,
        "run_portfolio": False,
        "portfolio_saved": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _generate_portfolio(user_inputs) -> None:
    """
    Run the full portfolio-generation pipeline and store results in
    st.session_state.  Called once per questionnaire submission.
    """
    # ── Step 1 · Map raw questionnaire answers to model features ─────────
    features = build_model_features(
        age=user_inputs["age"],
        education=user_inputs["education"],
        occupation=user_inputs["occupation"],
        income_range=user_inputs["income"],
        networth_range=user_inputs["networth"],
        assets_range=user_inputs["assets"],
        has_emergency=user_inputs["has_emergency"],
        has_savings=user_inputs["has_savings"],
        has_mutual=user_inputs["has_mutual"],
        has_retirement=user_inputs["has_retirement"],
    )

    # ── Step 2 · Load risk model and predict investor risk score ─────────
    risk_model, feature_names = load_risk_model()
    # feature_names can be None when model loading fails; predict_risk_score
    # handles empty lists by returning the neutral fallback score of 50.
    risk_score = predict_risk_score(features, risk_model, feature_names or [])
    st.session_state.risk_score = risk_score

    # ── Step 3 · Build portfolio ─────────────────────────────────────────
    portfolio = build_investor_portfolio(
        risk_score=risk_score,
        capital=user_inputs["capital"],
        use_enhanced=True,
        use_sentiment=True,
    )

    if "error" in portfolio:
        st.error(f"Portfolio Error: {portfolio['error']}")
        st.session_state.portfolio_result = None
        st.session_state.backtest_result = None
        return

    st.session_state.portfolio_result = portfolio
    # A new portfolio was generated — reset the "already saved" flag so the
    # save button becomes active again.
    st.session_state.portfolio_saved = False

    # ── Step 4 · Calculate real backtest ─────────────────────────────────
    daily_prices, spy_daily = load_daily_prices()

    if not daily_prices.empty and not spy_daily.empty:
        backtest = calculate_real_backtest(
            portfolio=portfolio,
            daily_prices=daily_prices,
            spy_daily=spy_daily,
            start_date="2024-01-01",
        )
        st.session_state.backtest_result = backtest
    else:
        st.session_state.backtest_result = None


def _render_risk_section(
    risk_score: float, category: str, equity_pct: float, buckets
) -> None:
    """Render the Risk Assessment section."""
    render_section_header("RISK ASSESSMENT")

    col1, col2 = st.columns([1, 2])
    with col1:
        render_risk_gauge(risk_score, category)
    with col2:
        render_risk_metrics_row(risk_score, category, equity_pct, buckets)

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)


def _render_allocation_section(portfolio) -> None:
    """Render the Portfolio Allocation section."""
    render_section_header("PORTFOLIO ALLOCATION")

    col1, col2 = st.columns([1, 2])
    with col1:
        render_holdings_pie(portfolio)
    with col2:
        render_holdings_table(portfolio)

    st.markdown("<br>", unsafe_allow_html=True)
    render_portfolio_summary(portfolio)

    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)


def _render_performance_section(backtest) -> None:
    """Render the Performance vs S&P 500 section."""
    render_section_header("PERFORMANCE vs S&P 500")

    if backtest and backtest.get("n_periods", 0) > 0:
        render_beat_spy_badge(backtest)
        render_backtest_chart(backtest)
        render_performance_metrics(backtest)
        st.markdown("<br>", unsafe_allow_html=True)
        render_metrics_comparison(backtest)
    else:
        st.warning(
            "⚠️ Backtest data not available. "
            "Please ensure price data is loaded correctly."
        )


def _render_save_button(
    portfolio,
    backtest,
    risk_score: float,
    category: str,
    capital: float,
) -> None:
    """
    Render the centered Save Portfolio button and handle the save action.

    Uses st.session_state['portfolio_saved'] to show a persistent success
    banner without requiring another click.
    """
    st.markdown('<div class="quantum-divider"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Persistent success/error banners (survive reruns)
    if st.session_state.get("save_error"):
        st.error(f"Failed to save: {st.session_state.pop('save_error')}")

    if st.session_state.get("portfolio_saved"):
        st.success(
            "✅ Portfolio saved! View it in **My Portfolios**.",
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        button_label = (
            "✔ Already Saved"
            if st.session_state.get("portfolio_saved")
            else "💾 Save Portfolio"
        )
        if st.button(
            button_label,
            use_container_width=True,
            key="save_portfolio_btn",
            disabled=bool(st.session_state.get("portfolio_saved")),
        ):
            result = save_portfolio(
                user_id=st.session_state.user_id,
                portfolio=portfolio,
                risk_score=risk_score,
                risk_category=category,
                capital=capital,
                backtest=backtest or {},
            )
            if result["success"]:
                st.session_state.portfolio_saved = True
                st.rerun()
            else:
                st.session_state["save_error"] = result.get("error", "Unknown error")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# MAIN APPLICATION
# =============================================================================


def main() -> None:
    """
    Main page logic.

    Execution order:
      1. Auth guard — redirect unauthenticated users before rendering anything.
      2. Sidebar — user card + navigation + sign-out.
      3. Header — branding banner.
      4. Questionnaire — investor profiling form (always visible).
      5. Pipeline — runs when the generate button is clicked.
      6. Results — risk gauge, portfolio allocation, backtest chart.
      7. Save button — persist the generated portfolio to MongoDB.
    """

    # ── 1 · Auth guard ────────────────────────────────────────────────────
    if not st.session_state.get("user_id"):
        st.warning("🔒 Please sign in to access this page.")
        if st.button("Go to Sign In"):
            st.switch_page("pages/1_Sign_In.py")
        st.stop()

    # ── 2 · Sidebar ───────────────────────────────────────────────────────
    _render_sidebar()

    # ── 3 · Header ────────────────────────────────────────────────────────
    render_header()

    # ── 4 · Session state ─────────────────────────────────────────────────
    _init_session_state()

    # ── 5 · Questionnaire ─────────────────────────────────────────────────
    # render_questionnaire() renders the full form and sets
    # st.session_state.run_portfolio = True before calling st.rerun(),
    # so the pipeline block below will execute on the next script run.
    user_inputs = render_questionnaire()

    # ── 6 · Pipeline ──────────────────────────────────────────────────────
    if st.session_state.get("run_portfolio", False):
        # Reset the flag immediately so it does not fire again on the next
        # rerun that displays the results.
        st.session_state.run_portfolio = False
        _generate_portfolio(user_inputs)

    # ── 7 · Pull results from session state ───────────────────────────────
    portfolio = st.session_state.get("portfolio_result")
    backtest = st.session_state.get("backtest_result")
    risk_score = st.session_state.get("risk_score")

    # ── 8 · Render results ────────────────────────────────────────────────
    if portfolio and "allocations" in portfolio:
        # Derive display parameters from the risk score.
        params = get_enhanced_investor_params(risk_score)
        bucket_config = get_bucket_config(risk_score)
        category = params.get("category", "Unknown")
        equity_pct = params.get("base_equity", 0) * 100
        buckets = bucket_config.get("buckets", [])

        _render_risk_section(risk_score, category, equity_pct, buckets)
        _render_allocation_section(portfolio)
        _render_performance_section(backtest)

        # ── 9 · Save button ───────────────────────────────────────────────
        _render_save_button(
            portfolio=portfolio,
            backtest=backtest,
            risk_score=risk_score,
            category=category,
            capital=user_inputs["capital"],
        )

    elif risk_score is not None and portfolio is None:
        # Generation was attempted but the pipeline returned an error.
        st.error(
            "⚠️ Failed to generate portfolio. "
            "Please check that all data files are available and try again."
        )

    else:
        # No generation has been triggered yet — show a helpful prompt.
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(
            "👆 Fill in the investor questionnaire above and click "
            "**🚀 GENERATE PORTFOLIO** to build your personalised allocation."
        )


# =============================================================================
# ENTRY POINT
# Streamlit executes multi-page scripts at module scope, so we call main()
# unconditionally rather than guarding with `if __name__ == "__main__"`.
# =============================================================================

main()
