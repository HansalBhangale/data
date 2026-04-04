"""
Predictive Asset Allocation System — Landing Page

Entry point for the Streamlit multi-page application.
Professional fintech hero page with feature showcase and
how-it-works walkthrough.
"""

import sys
from pathlib import Path

# ── Path setup — must come before any local package imports ─────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Stub classes — required BEFORE any import that may unpickle models ───────
class PCABasedRiskScorer:
    """Stub for PCA-based risk scorer (unpickling only)."""

    def __init__(self, df=None):
        self.df = df


class EmpiricalCorrelationScorer:
    """Stub for empirical correlation scorer (unpickling only)."""

    def __init__(self, df=None):
        self.df = df


# ── Standard imports ─────────────────────────────────────────────────────────
import streamlit as st

from gui.styles import get_custom_css

# ═════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  ── must be the very first Streamlit call
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PAAS | Home",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═════════════════════════════════════════════════════════════════════════════
#  GLOBAL THEME
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(get_custom_css(), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  LANDING-PAGE-SPECIFIC CSS
# ═════════════════════════════════════════════════════════════════════════════

LANDING_CSS = """
<style>
footer, #MainMenu { visibility: hidden !important; }
header { background: transparent !important; box-shadow: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════════════════
   HERO SECTION
══════════════════════════════════════════════════════ */

.hero {
    position: relative;
    z-index: 2;
    text-align: center;
    padding: 4rem 2rem 1rem;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 18px;
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 100px;
    color: #60A5FA;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 2rem;
    animation: fadeSlideDown 0.5s ease-out both;
}

.hero-title {
    display: block;
    font-size: clamp(1.8rem, 3.8vw, 3.2rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -1.5px;
    color: #E2E8F0;
    margin: 0 0 1.4rem;
    animation: fadeSlideUp 0.6s ease-out 0.1s both;
}

.hero-title .accent {
    color: #3B82F6;
}

.hero-tagline {
    font-size: clamp(0.95rem, 1.8vw, 1.15rem);
    color: #94A3B8;
    line-height: 1.75;
    letter-spacing: 0.2px;
    max-width: 480px;
    margin: 0 auto 2rem;
    animation: fadeSlideUp 0.6s ease-out 0.2s both;
}
.hero-tagline strong { color: #CBD5E1; font-weight: 600; }


/* ══════════════════════════════════════════════════════
   CTA BUTTON OVERRIDES
══════════════════════════════════════════════════════ */

button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: #3B82F6 !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.25) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: #60A5FA !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.35) !important;
    transform: translateY(-1px) !important;
}

button[kind="secondary"],
[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 1.5px solid rgba(59,130,246,0.3) !important;
    color: #60A5FA !important;
    box-shadow: none !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}
button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(59,130,246,0.08) !important;
    border-color: rgba(59,130,246,0.5) !important;
    transform: translateY(-1px) !important;
}


/* ══════════════════════════════════════════════════════
   STATS BAR
══════════════════════════════════════════════════════ */

.stats-bar {
    display: flex;
    justify-content: center;
    gap: 3rem;
    flex-wrap: wrap;
    margin: 1.5rem 0 3rem;
    position: relative;
    z-index: 2;
    animation: fadeIn 0.8s ease-out 0.4s both;
}
.stat-item { text-align: center; }
.stat-num {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.7rem;
    font-weight: 700;
    color: #E2E8F0;
    line-height: 1.1;
}
.stat-lbl {
    display: block;
    font-size: 0.65rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 4px;
    font-weight: 600;
}


/* ══════════════════════════════════════════════════════
   DIVIDERS
══════════════════════════════════════════════════════ */

.qdiv {
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(59,130,246,0.12),
        rgba(99,102,241,0.12),
        transparent
    );
    margin: 0.5rem 0 3rem;
    position: relative;
    z-index: 2;
}


/* ══════════════════════════════════════════════════════
   SECTION HEADINGS
══════════════════════════════════════════════════════ */

.s-head {
    text-align: center;
    font-size: clamp(1.5rem, 3vw, 2.1rem);
    font-weight: 800;
    color: #E2E8F0;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 2;
    margin-bottom: 0.4rem;
}
.s-sub {
    text-align: center;
    font-size: 0.9rem;
    color: #94A3B8;
    position: relative;
    z-index: 2;
    margin-bottom: 2.5rem;
    line-height: 1.6;
}


/* ══════════════════════════════════════════════════════
   FEATURE CARDS
══════════════════════════════════════════════════════ */

.feat-card {
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 2rem 1.6rem;
    min-height: 200px;
    position: relative;
    z-index: 2;
    overflow: hidden;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;
}
.feat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 8%; right: 8%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--fc-accent, rgba(59,130,246,0.3)), transparent);
    opacity: 0.5;
    transition: opacity 0.25s ease;
}
.feat-card:hover {
    border-color: rgba(59,130,246,0.12);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.feat-card:hover::before { opacity: 1; }

.feat-icon {
    display: block;
    font-size: 2rem;
    margin-bottom: 1rem;
}
.feat-name {
    font-size: 1.02rem;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 0.5rem;
}
.feat-desc {
    font-size: 0.85rem;
    color: #94A3B8;
    line-height: 1.65;
}
.feat-pill {
    display: inline-block;
    margin-top: 1rem;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.63rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.pill-blue   { background:rgba(59,130,246,0.1); color:#60A5FA; border:1px solid rgba(59,130,246,0.2); }
.pill-indigo { background:rgba(99,102,241,0.1); color:#818CF8; border:1px solid rgba(99,102,241,0.2); }
.pill-green  { background:rgba(16,185,129,0.1); color:#34D399; border:1px solid rgba(16,185,129,0.2); }


/* ══════════════════════════════════════════════════════
   HOW IT WORKS — STEPS
══════════════════════════════════════════════════════ */

.hiw-step {
    text-align: center;
    padding: 0.6rem 1rem;
    position: relative;
    z-index: 2;
}
.hiw-num {
    width: 50px;
    height: 50px;
    border-radius: 14px;
    background: #3B82F6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 800;
    color: #fff;
    margin: 0 auto 1rem;
    box-shadow: 0 2px 12px rgba(59,130,246,0.3);
}
.hiw-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 0.4rem;
}
.hiw-desc {
    font-size: 0.84rem;
    color: #94A3B8;
    line-height: 1.65;
}

.hiw-arrow {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 2rem;
    position: relative;
    z-index: 2;
    font-size: 1.4rem;
    color: rgba(59,130,246,0.35);
}


/* ══════════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════════ */

.lp-footer {
    position: relative;
    z-index: 2;
    text-align: center;
    padding: 2.5rem 1rem 1.8rem;
    margin-top: 4rem;
    border-top: 1px solid rgba(255,255,255,0.04);
    color: #64748B;
    font-size: 0.78rem;
    letter-spacing: 0.3px;
}
.lp-footer .brand {
    color: #3B82F6;
    font-weight: 700;
}
.lp-footer .sep { margin: 0 0.5rem; opacity: 0.4; }


/* ══════════════════════════════════════════════════════
   KEYFRAME LIBRARY
══════════════════════════════════════════════════════ */

@keyframes fadeSlideDown {
    from { opacity: 0; transform: translateY(-14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}


/* ══════════════════════════════════════════════════════
   SIDEBAR LINK PILLS
══════════════════════════════════════════════════════ */

[data-testid="stSidebarContent"] [data-testid="stPageLink-NavLink"] {
    border-radius: 8px;
    transition: background 0.15s ease;
}
[data-testid="stSidebarContent"] [data-testid="stPageLink-NavLink"]:hover {
    background: rgba(59,130,246,0.08) !important;
}
</style>
"""

st.markdown(LANDING_CSS, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    # ── Branding ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="sidebar-header">📊 PAAS</div>
        <p style="
            color:#94A3B8;
            font-size:0.7rem;
            margin:-0.1rem 0 0.8rem;
            letter-spacing:1.5px;
            text-transform:uppercase;
        ">
            Predictive Asset Allocation
        </p>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Core navigation ───────────────────────────────────────────────────
    st.markdown(
        "<p style='color:#94A3B8;font-size:0.72rem;font-weight:600;"
        "letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.4rem;'>"
        "Navigation</p>",
        unsafe_allow_html=True,
    )
    st.page_link("app.py", label="🏠  Home")
    st.page_link("pages/1_Sign_In.py", label="🔐  Sign In")
    st.page_link("pages/2_Sign_Up.py", label="🚀  Get Started")

    # ── Authenticated links ───────────────────────────────────────────────
    if st.session_state.get("user_id"):
        st.markdown("---")
        uname = st.session_state.get("user_name", "User")
        st.markdown(
            f"""
            <div style="
                background: rgba(59,130,246,0.06);
                border: 1px solid rgba(59,130,246,0.12);
                border-radius: 10px;
                padding: 9px 14px;
                margin-bottom: 0.6rem;
            ">
                <span style="color:#60A5FA;font-size:0.85rem;font-weight:600;">
                    👤 {uname}
                </span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Only show links when the target pages actually exist
        create_page = Path(__file__).parent / "pages" / "3_Create_Portfolio.py"
        my_page = Path(__file__).parent / "pages" / "4_My_Portfolios.py"

        if create_page.exists():
            st.page_link("pages/3_Create_Portfolio.py", label="Create Portfolio")
        else:
            st.markdown(
                "<span style='color:#94A3B8;font-size:0.85rem;padding-left:4px;'>"
                "Create Portfolio <em style='font-size:0.7rem;'>(soon)</em></span>",
                unsafe_allow_html=True,
            )

        if my_page.exists():
            st.page_link("pages/4_My_Portfolios.py", label="💼  My Portfolios")
        else:
            st.markdown(
                "<span style='color:#94A3B8;font-size:0.85rem;padding-left:4px;'>"
                "💼 My Portfolios <em style='font-size:0.7rem;'>(soon)</em></span>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown(
        """
        <p style="color:#64748B;font-size:0.72rem;line-height:1.7;padding:0 2px;">
            AI risk profiling &nbsp;·&nbsp; Smart allocation<br>
            Backtesting &nbsp;·&nbsp; S&amp;P 500 comparison
        </p>
    """,
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  HERO SECTION
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    '<div class="hero">'
    '<div class="hero-badge">⚡  AI-POWERED INVESTMENT PLATFORM</div>'
    '<div class="hero-title">PREDICTIVE <span class="accent">ASSET ALLOCATION</span> SYSTEM</div>'
    '<div class="hero-tagline" style="text-align:center;max-width:480px;margin:0 auto 2rem;">'
    '<strong>AI-powered</strong> portfolio optimization.<br>'
    "Risk-aware. Data-driven."
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)


# ── CTA buttons ──────────────────────────────────────────────────────────────
_, c1, c2, _ = st.columns([2, 1, 1, 2])

with c1:
    if st.button(
        "🔐  Sign In",
        use_container_width=True,
        key="hero_cta_signin",
    ):
        st.switch_page("pages/1_Sign_In.py")

with c2:
    if st.button(
        "🚀  Get Started",
        use_container_width=True,
        type="primary",
        key="hero_cta_signup",
    ):
        st.switch_page("pages/2_Sign_Up.py")


# ── Stats bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="stats-bar">
    <div class="stat-item">
        <span class="stat-num">500+</span>
        <span class="stat-lbl">S&amp;P 500 Stocks</span>
    </div>
    <div class="stat-item">
        <span class="stat-num">3</span>
        <span class="stat-lbl">ML Models</span>
    </div>
    <div class="stat-item">
        <span class="stat-num">5</span>
        <span class="stat-lbl">Risk Profiles</span>
    </div>
    <div class="stat-item">
        <span class="stat-num">1Y+</span>
        <span class="stat-lbl">Backtest Data</span>
    </div>
</div>
<div class="qdiv"></div>
""",
    unsafe_allow_html=True,
)


# ═════════════════════════════════════════════════════════════════════════════
#  FEATURES SECTION
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<div class="s-head">
    Everything you need to invest
    <span style="color:#3B82F6;">smarter</span>
</div>
<div class="s-sub">
    Three powerful ML systems working in concert — from risk prediction to
    portfolio construction and performance benchmarking.
</div>
""",
    unsafe_allow_html=True,
)

fc1, fc2, fc3 = st.columns(3, gap="large")

with fc1:
    st.markdown(
        """
    <div class="feat-card" style="--fc-accent:rgba(59,130,246,0.3);">
        <span class="feat-icon">🧠</span>
        <div class="feat-name">AI Risk Profiling</div>
        <div class="feat-desc">
            Predicts your personal risk tolerance using a machine-learning
            model trained on real investor behavioural data — powered by
            PCA-based dimensionality reduction and ensemble scoring.
        </div>
        <span class="feat-pill pill-blue">Machine Learning</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fc2:
    st.markdown(
        """
    <div class="feat-card" style="--fc-accent:rgba(99,102,241,0.3);">
        <span class="feat-icon">📈</span>
        <div class="feat-name">Smart Allocation</div>
        <div class="feat-desc">
            Optimized across growth, value &amp; quality buckets using
            combined fundamental and technical factor signals.
            Capital is distributed intelligently to match your exact
            risk profile and investment horizon.
        </div>
        <span class="feat-pill pill-indigo">Multi-Factor</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fc3:
    st.markdown(
        """
    <div class="feat-card" style="--fc-accent:rgba(16,185,129,0.3);">
        <span class="feat-icon">📊</span>
        <div class="feat-name">Real Backtesting</div>
        <div class="feat-desc">
            Compare your portfolio's performance directly against the
            S&amp;P 500 using real historical price data.
            Full metrics: annual return, Sharpe ratio, max drawdown,
            alpha, beta &amp; more.
        </div>
        <span class="feat-pill pill-green">Historical Data</span>
    </div>
    """,
        unsafe_allow_html=True,
    )


st.markdown('<div class="qdiv" style="margin-top:3rem;"></div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  HOW IT WORKS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<div class="s-head" style="margin-top:1rem;">
    How it <span style="color:#6366F1;">works</span>
</div>
<div class="s-sub">
    From questionnaire to a fully optimized, backtested portfolio — in three steps.
</div>
""",
    unsafe_allow_html=True,
)

h1, arr1, h2, arr2, h3 = st.columns([5, 1, 5, 1, 5], gap="small")

with h1:
    st.markdown(
        """
    <div class="hiw-step">
        <div class="hiw-num">01</div>
        <div class="hiw-title">Answer the Questionnaire</div>
        <div class="hiw-desc">
            Share your financial profile — age, income, net worth, investment
            goals and existing asset mix.  Takes under two minutes.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with arr1:
    st.markdown('<div class="hiw-arrow">→</div>', unsafe_allow_html=True)

with h2:
    st.markdown(
        """
    <div class="hiw-step">
        <div class="hiw-num">02</div>
        <div class="hiw-title">AI Builds Your Portfolio</div>
        <div class="hiw-desc">
            Our ML model scores your risk tolerance.  The optimizer selects
            the highest-ranked S&amp;P 500 stocks and allocates your capital
            across growth, value and quality buckets.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with arr2:
    st.markdown('<div class="hiw-arrow">→</div>', unsafe_allow_html=True)

with h3:
    st.markdown(
        """
    <div class="hiw-step">
        <div class="hiw-num">03</div>
        <div class="hiw-title">Track &amp; Manage</div>
        <div class="hiw-desc">
            Explore your interactive portfolio dashboard, run backtests
            against the S&amp;P 500, and save multiple portfolios to
            compare different strategies over time.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  SECOND CTA ROW  (bottom of page)
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("<br>", unsafe_allow_html=True)
_, b1, b2, _ = st.columns([2, 1, 1, 2])

with b1:
    if st.button(
        "🔐  Sign In",
        use_container_width=True,
        key="bottom_cta_signin",
    ):
        st.switch_page("pages/1_Sign_In.py")

with b2:
    if st.button(
        "🚀  Create Account",
        use_container_width=True,
        type="primary",
        key="bottom_cta_signup",
    ):
        st.switch_page("pages/2_Sign_Up.py")


# ═════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<div class="lp-footer">
    <span class="brand">PAAS</span>
    <span class="sep">|</span>
    Predictive Asset Allocation System
    <span class="sep">·</span>
    AI-Powered Portfolio Optimization
    <span class="sep">·</span>
    Built with Streamlit &amp; Python
</div>
""",
    unsafe_allow_html=True,
)
