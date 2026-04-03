"""
My Portfolios — Multi-page PAAS sub-page

Displays all portfolios saved by the authenticated user.
Each portfolio is shown as a cyberpunk glass-card with:
  • Rich metric rows (risk, capital, holdings, equity/cash split)
  • Backtest summary badge + performance metrics
  • Top-5 holdings table
  • Delete action with two-step confirmation
  • Rebalance placeholder (coming soon)
"""

# =============================================================================
# SYS.PATH SETUP — must come before ANY other imports so that the `gui`
# package is resolvable when Streamlit executes this file as a page.
# =============================================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# STUB CLASSES — required before any gui.core import that unpickles the risk
# model, even though this page does not load the model itself.
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

from datetime import datetime

import pandas as pd
import streamlit as st

from gui.database import delete_portfolio, get_user_portfolios
from gui.styles import get_custom_css

# =============================================================================
# PAGE CONFIGURATION — must be the very first Streamlit call in the script.
# =============================================================================

st.set_page_config(
    page_title="PAAS | My Portfolios",
    page_icon="📁",
    layout="wide",
)

# Apply the shared cyberpunk theme at module level so it is in the DOM even
# when st.stop() is called early (e.g. auth guard).
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Additional page-level CSS tweaks
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Tighten the gap between the glass-card header and the metric row */
        .portfolio-metrics-wrapper {
            margin-top: -6px;
            padding: 16px 4px 8px 4px;
        }

        /* Subtle left border accent on each metric card in this page */
        .portfolio-metrics-wrapper [data-testid="stMetric"] {
            border-left: 2px solid rgba(0, 242, 255, 0.25);
            padding-left: 10px;
        }

        /* Backtest badge row spacing */
        .bt-badge-row {
            margin: 10px 0 14px 0;
        }

        /* Holdings label */
        .holdings-label {
            color: #8a99ad;
            font-size: 0.80rem;
            text-transform: uppercase;
            letter-spacing: 1.4px;
            font-weight: 600;
            margin: 14px 0 4px 0;
        }

        /* Action button row spacing */
        .action-row {
            margin-top: 16px;
            margin-bottom: 4px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# HELPERS
# =============================================================================


def _risk_color(category: str) -> str:
    """Return a theme colour that matches the risk category."""
    cat = (category or "").lower()
    if "ultra" in cat:
        return "#00f2ff"
    if "conservative" in cat:
        return "#00f2ff"
    if "moderate" in cat:
        return "#7000ff"
    if "growth" in cat:
        return "#ffaa00"
    if "aggressive" in cat:
        return "#ff0055"
    return "#00f2ff"


def _fmt_datetime(value) -> str:
    """Return a human-readable datetime string from various input types."""
    if not value:
        return "Unknown date"
    try:
        if hasattr(value, "strftime"):
            # Already a datetime object (e.g. from MongoDB's BSON)
            return value.strftime("%B %d, %Y at %H:%M UTC")
        # Coerce ISO string — handle both offset-aware and naive variants
        iso = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%B %d, %Y at %H:%M UTC")
    except Exception:
        return str(value)


# =============================================================================
# SIDEBAR
# =============================================================================


def _render_sidebar() -> None:
    """Render the authenticated user's navigation sidebar."""
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('user_name', 'User')}")
        st.markdown(f"*{st.session_state.get('user_email', '')}*")
        st.divider()

        st.page_link(
            "pages/3_Create_Portfolio.py",
            label="📊 Create Portfolio",
            icon="📊",
        )
        st.page_link(
            "pages/4_My_Portfolios.py",
            label="📁 My Portfolios",
            icon="📁",
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


# =============================================================================
# PORTFOLIO CARD
# =============================================================================


def _render_portfolio_card(p, idx: int) -> None:
    """
    Render a single saved portfolio as a layered glass-card.

    Layout
    ------
    [HTML glass-card]  → name, risk-category badge, created date
    [st widgets]       → metric row, backtest badge, backtest metrics,
                         holdings table, action buttons
    [st.divider]       → separates cards
    """
    # ── Unpack document fields ────────────────────────────────────────────
    portfolio_id: str = p.get("_id", f"portfolio_{idx}")
    name: str = p.get("name", f"Portfolio #{idx + 1}")
    risk_category: str = p.get("risk_category", "Unknown")
    risk_score: float = p.get("risk_score", 0.0)
    capital: float = p.get("capital", 0.0)
    equity_weight: float = p.get("equity_weight", 0.0)
    cash_weight: float = p.get("cash_weight", 0.0)
    n_holdings: int = p.get("n_holdings", 0)
    buckets = p.get("buckets", [])
    created_at = p.get("created_at", "")
    allocations = p.get("allocations", [])
    backtest = p.get("backtest_summary", {}) or {}

    risk_color = _risk_color(risk_category)
    created_str = _fmt_datetime(created_at)

    # ── Session-state keys (scoped to this portfolio) ─────────────────────
    confirm_key = f"confirm_delete_{portfolio_id}"
    rebalance_key = f"show_rebalance_{portfolio_id}"

    # ── CARD HEADER — rendered as HTML so it picks up glass-card styling ──
    st.markdown(
        f"""
        <div class="glass-card" style="padding-bottom: 10px; margin-bottom: 0;">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                flex-wrap: wrap;
                gap: 12px;
            ">
                <div>
                    <h2 style="
                        color: #00f2ff;
                        font-weight: 800;
                        margin: 0 0 6px 0;
                        font-size: 1.45rem;
                        text-shadow: 0 0 14px rgba(0, 242, 255, 0.45);
                        letter-spacing: 0.4px;
                        line-height: 1.2;
                    ">{name}</h2>
                    <p style="
                        color: #8a99ad;
                        font-size: 0.82rem;
                        margin: 0;
                        letter-spacing: 0.5px;
                    ">🕐 Created {created_str}</p>
                </div>
                <span style="
                    color: {risk_color};
                    font-weight: 700;
                    font-size: 0.87rem;
                    background: rgba(0, 0, 0, 0.35);
                    padding: 6px 16px;
                    border-radius: 20px;
                    border: 1px solid {risk_color}55;
                    white-space: nowrap;
                    align-self: flex-start;
                    text-shadow: 0 0 8px {risk_color}88;
                    letter-spacing: 0.5px;
                ">{risk_category}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── PORTFOLIO METRICS ROW ─────────────────────────────────────────────
    # Rendered as native Streamlit widgets (outside the HTML div above).
    st.markdown(
        '<div class="portfolio-metrics-wrapper">',
        unsafe_allow_html=True,
    )
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Risk Score", f"{risk_score:.0f} / 100")
        with c2:
            st.metric("Capital", f"${capital:,.0f}")
        with c3:
            st.metric("Holdings", n_holdings if n_holdings else "—")
        with c4:
            st.metric("Equity %", f"{equity_weight:.0f}%")
        with c5:
            st.metric("Cash %", f"{cash_weight:.0f}%")
        with c6:
            bucket_str = str(buckets) if buckets else "—"
            st.metric("Buckets", bucket_str)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── BACKTEST METRICS ──────────────────────────────────────────────────
    if backtest:
        beat_spy: bool = backtest.get("beat_spy", False)
        ann_ret: float = backtest.get("annual_return", 0.0)
        vol: float = backtest.get("annual_volatility", 0.0)
        sharpe: float = backtest.get("sharpe_ratio", 0.0)
        alpha: float = backtest.get("alpha", 0.0)
        total_ret: float = backtest.get("total_return", 0.0)
        spy_total: float = backtest.get("spy_total_return", 0.0)

        # Outperformance expressed as difference in total returns
        outperf: float = total_ret - spy_total
        badge_class = "success" if beat_spy else "failure"
        direction_icon = "✓" if beat_spy else "✗"
        vs_label = "BEATS" if beat_spy else "BELOW"
        outperf_str = f"{outperf * 100:+.1f}%"

        # Beat S&P badge (HTML for custom styling)
        st.markdown(
            f"""
            <div class="bt-badge-row">
                <span class="beat-spy-badge {badge_class}">
                    <span style="font-size: 1.25rem;">{direction_icon}</span>
                    {vs_label} S&amp;P 500 &nbsp;({outperf_str} total return)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Backtest scalar metrics
        with st.container():
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1:
                st.metric("Annual Return", f"{ann_ret * 100:.1f}%")
            with bc2:
                st.metric("Volatility", f"{vol * 100:.1f}%")
            with bc3:
                st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            with bc4:
                st.metric("Alpha", f"{alpha * 100:.1f}%")

    # ── TOP-5 HOLDINGS TABLE ──────────────────────────────────────────────
    if allocations:
        rows = [
            {
                "Ticker": a.get("ticker", "—"),
                "Risk Bucket": a.get("risk_bucket", "—"),
                "Final Score": round(a.get("final_score", 0), 3),
                "Momentum": round(a.get("momentum_score", 0), 3),
                "Quality": round(a.get("quality_score", 0), 3),
                "Weight %": f"{a.get('weight_pct', 0):.1f}%",
                "Capital": f"${a.get('capital_allocated', 0):,.0f}",
            }
            for a in allocations
        ]
        df_all = pd.DataFrame(rows)

        st.markdown(
            f"<p class='holdings-label'>▸ All Holdings ({len(allocations)})</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            df_all,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Risk Bucket": st.column_config.TextColumn("Bucket", width="medium"),
                "Final Score": st.column_config.NumberColumn("Score", format="%.3f"),
                "Momentum": st.column_config.NumberColumn("Momentum", format="%.3f"),
                "Quality": st.column_config.NumberColumn("Quality", format="%.3f"),
                "Weight %": st.column_config.TextColumn("Weight %", width="small"),
                "Capital": st.column_config.TextColumn("Capital", width="medium"),
            },
        )

    # ── ACTION BUTTONS ────────────────────────────────────────────────────
    st.markdown('<div class="action-row">', unsafe_allow_html=True)
    btn_c1, btn_c2, _spacer = st.columns([1, 1, 2])

    # ── Delete (with two-step confirmation) ──────────────────────────────
    with btn_c1:
        if not st.session_state.get(confirm_key, False):
            # First click: arm the confirmation
            if st.button(
                "🗑️ Delete",
                key=f"del_{portfolio_id}",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = True
                st.rerun()
        else:
            # Second step: show confirmation prompt
            st.warning("⚠️ Are you sure? This cannot be undone.")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button(
                    "✅ Yes",
                    key=f"yes_{portfolio_id}",
                    use_container_width=True,
                ):
                    result = delete_portfolio(
                        portfolio_id,
                        st.session_state.user_id,
                    )
                    if result.get("success"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    else:
                        st.error(
                            f"Delete failed: {result.get('error', 'Unknown error')}"
                        )
            with no_col:
                if st.button(
                    "❌ Cancel",
                    key=f"no_{portfolio_id}",
                    use_container_width=True,
                ):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

    # ── Rebalance (toggle placeholder) ───────────────────────────────────
    with btn_c2:
        if st.button(
            "⚖️ Rebalance",
            key=f"reb_{portfolio_id}",
            use_container_width=True,
        ):
            st.session_state[rebalance_key] = not st.session_state.get(
                rebalance_key, False
            )
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Rebalance info shown outside the column so it spans full width
    if st.session_state.get(rebalance_key, False):
        st.info(
            "⚖️ **Rebalance feature coming soon!**  "
            "You will be able to rebalance your portfolio against the latest "
            "model scores and market conditions."
        )

    st.divider()


# =============================================================================
# MAIN APPLICATION
# =============================================================================


def main() -> None:
    """
    Main page logic.

    Execution order:
      1. Auth guard — stop and redirect unauthenticated visitors.
      2. Sidebar — user card + navigation + sign-out.
      3. Page header — title, subtitle, divider.
      4. Load portfolios from MongoDB via gui.database.
      5. Empty state — prompt to create the first portfolio.
      6. Portfolio cards — glass-card per portfolio, newest first.
    """

    # ── 1 · Auth guard ────────────────────────────────────────────────────
    if not st.session_state.get("user_id"):
        st.warning("🔒 Please sign in to access this page.")
        if st.button("Go to Sign In"):
            st.switch_page("pages/1_Sign_In.py")
        st.stop()

    # ── 2 · Sidebar ───────────────────────────────────────────────────────
    _render_sidebar()

    # ── 3 · Page header ───────────────────────────────────────────────────
    st.markdown("## 📁 My Portfolios")
    st.markdown("All portfolios you've created.")
    st.divider()

    # ── 4 · Load portfolios ───────────────────────────────────────────────
    portfolios = get_user_portfolios(st.session_state.user_id)

    # ── 5 · Empty state ───────────────────────────────────────────────────
    if not portfolios:
        st.info(
            "📭 You haven't created any portfolios yet. "
            "Generate your first portfolio to see it here."
        )
        if st.button("➕ Create Your First Portfolio", use_container_width=False):
            st.switch_page("pages/3_Create_Portfolio.py")
        return

    # ── 6 · Portfolio count summary ───────────────────────────────────────
    n = len(portfolios)
    st.markdown(
        f"<p style='"
        f"color: #8a99ad; font-size: 0.88rem; margin-bottom: 1.5rem; "
        f"letter-spacing: 0.5px;"
        f"'>📦 {n} portfolio{'s' if n != 1 else ''} saved — "
        f"sorted newest first</p>",
        unsafe_allow_html=True,
    )

    # ── 7 · Render one card per portfolio ─────────────────────────────────
    for idx, portfolio_doc in enumerate(portfolios):
        _render_portfolio_card(portfolio_doc, idx)


# =============================================================================
# ENTRY POINT
# Streamlit executes multi-page scripts at module scope, so we call main()
# unconditionally rather than guarding with `if __name__ == "__main__"`.
# =============================================================================

main()
