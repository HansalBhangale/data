"""
Predictive Asset Allocation System — Landing Page

Entry point for the Streamlit multi-page application.
Stunning cyberpunk/fintech hero page with animated background,
feature showcase, and how-it-works walkthrough.
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
/* ── Hide default Streamlit chrome (already in get_custom_css but belt+braces) */
header, footer, #MainMenu { visibility: hidden !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════════════════
   BACKGROUND FX
══════════════════════════════════════════════════════ */

/* Animated orb layer  */
.bg-orb {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}
.bg-orb-purple {
    width: 780px;
    height: 780px;
    background: radial-gradient(circle, rgba(112,0,255,0.22) 0%, transparent 70%);
    top: -320px;
    left: -250px;
    animation: orbDrift1 20s ease-in-out infinite;
}
.bg-orb-cyan {
    width: 640px;
    height: 640px;
    background: radial-gradient(circle, rgba(0,242,255,0.11) 0%, transparent 70%);
    bottom: -200px;
    right: -180px;
    animation: orbDrift2 16s ease-in-out infinite;
}
.bg-orb-mid {
    width: 420px;
    height: 420px;
    background: radial-gradient(circle, rgba(0,255,157,0.05) 0%, transparent 70%);
    top: 40%;
    left: 55%;
    animation: orbDrift3 24s ease-in-out infinite;
}
@keyframes orbDrift1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50%       { transform: translate(70px, 55px) scale(1.06); }
}
@keyframes orbDrift2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50%       { transform: translate(-55px, -70px) scale(1.08); }
}
@keyframes orbDrift3 {
    0%, 100% { transform: translate(-50%, -50%) scale(1); }
    50%       { transform: translate(-42%, -58%) scale(1.12); }
}

/* Scrolling cyber grid */
.cyber-grid {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(0,242,255,0.024) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,242,255,0.024) 1px, transparent 1px);
    background-size: 64px 64px;
    animation: gridScroll 28s linear infinite;
    pointer-events: none;
    z-index: 0;
}
@keyframes gridScroll {
    from { background-position: 0 0; }
    to   { background-position: 64px 64px; }
}


/* ══════════════════════════════════════════════════════
   HERO SECTION
══════════════════════════════════════════════════════ */

.hero {
    position: relative;
    z-index: 2;
    text-align: center;
    padding: 5.5rem 2rem 1.5rem;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 7px 22px;
    background: rgba(0,242,255,0.07);
    border: 1px solid rgba(0,242,255,0.32);
    border-radius: 100px;
    color: #00f2ff;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 2.2rem;
    animation: fadeSlideDown 0.7s ease-out both;
}
.hero-badge::before {
    content: '⚡';
    font-size: 0.8rem;
}

.hero-title {
    font-size: clamp(2.8rem, 6.8vw, 5.8rem);
    font-weight: 900;
    line-height: 1.06;
    letter-spacing: -2px;
    color: #e0e6ed;
    margin: 0 0 1.6rem;
    animation: fadeSlideUp 0.9s ease-out 0.18s both;
}

/* Glowing cyan accent for "ASSET ALLOCATION" */
.hero-title .glow {
    display: inline-block;
    color: #00f2ff;
    text-shadow:
        0 0 24px rgba(0,242,255,0.75),
        0 0 60px rgba(0,242,255,0.45),
        0 0 100px rgba(0,242,255,0.22);
    animation: cyanBreath 3.8s ease-in-out infinite;
}
@keyframes cyanBreath {
    0%, 100% {
        text-shadow:
            0 0 24px rgba(0,242,255,0.75),
            0 0 60px rgba(0,242,255,0.45),
            0 0 100px rgba(0,242,255,0.22);
    }
    50% {
        text-shadow:
            0 0 40px rgba(0,242,255,0.98),
            0 0 90px rgba(0,242,255,0.65),
            0 0 150px rgba(0,242,255,0.32),
            0 0 200px rgba(0,242,255,0.12);
    }
}

.hero-tagline {
    font-size: clamp(1rem, 2.1vw, 1.22rem);
    color: #8a99ad;
    line-height: 1.8;
    letter-spacing: 0.3px;
    max-width: 520px;
    margin: 0 auto 2rem;
    animation: fadeSlideUp 0.9s ease-out 0.32s both;
}
.hero-tagline strong { color: #c8d4e0; font-weight: 600; }


/* ══════════════════════════════════════════════════════
   CTA BUTTON OVERRIDES
══════════════════════════════════════════════════════ */

/* Primary — cyan-to-purple gradient */
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #00c4ff 0%, #7000ff 100%) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 4px 22px rgba(0,196,255,0.38) !important;
    font-size: 0.93rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.8px !important;
    transition: all 0.28s ease !important;
}
button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #18d4ff 0%, #8a1aff 100%) !important;
    box-shadow: 0 6px 30px rgba(0,196,255,0.58) !important;
    transform: translateY(-2px) !important;
}

/* Secondary — outlined cyan */
button[kind="secondary"],
[data-testid="stBaseButton-secondary"] {
    background: rgba(0,242,255,0.05) !important;
    border: 1.5px solid rgba(0,242,255,0.42) !important;
    color: #00f2ff !important;
    box-shadow: 0 0 16px rgba(0,242,255,0.12) !important;
    font-size: 0.93rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.8px !important;
    transition: all 0.28s ease !important;
}
button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(0,242,255,0.12) !important;
    border-color: rgba(0,242,255,0.7) !important;
    box-shadow: 0 0 28px rgba(0,242,255,0.32) !important;
    transform: translateY(-2px) !important;
}


/* ══════════════════════════════════════════════════════
   STATS BAR
══════════════════════════════════════════════════════ */

.stats-bar {
    display: flex;
    justify-content: center;
    gap: 3.5rem;
    flex-wrap: wrap;
    margin: 1.8rem 0 3.8rem;
    position: relative;
    z-index: 2;
    animation: fadeIn 1.1s ease-out 0.65s both;
}
.stat-item { text-align: center; }
.stat-num {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.9rem;
    font-weight: 700;
    color: #00f2ff;
    text-shadow: 0 0 18px rgba(0,242,255,0.45);
    line-height: 1.1;
}
.stat-lbl {
    display: block;
    font-size: 0.68rem;
    color: #8a99ad;
    text-transform: uppercase;
    letter-spacing: 2.2px;
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
        rgba(0,242,255,0.22),
        rgba(112,0,255,0.22),
        transparent
    );
    margin: 0.5rem 0 3.8rem;
    position: relative;
    z-index: 2;
}


/* ══════════════════════════════════════════════════════
   SECTION HEADINGS
══════════════════════════════════════════════════════ */

.s-head {
    text-align: center;
    font-size: clamp(1.65rem, 3.2vw, 2.25rem);
    font-weight: 800;
    color: #e0e6ed;
    letter-spacing: -0.6px;
    position: relative;
    z-index: 2;
    margin-bottom: 0.4rem;
}
.s-sub {
    text-align: center;
    font-size: 0.92rem;
    color: #8a99ad;
    position: relative;
    z-index: 2;
    margin-bottom: 2.5rem;
    line-height: 1.6;
}


/* ══════════════════════════════════════════════════════
   FEATURE CARDS
══════════════════════════════════════════════════════ */

.feat-card {
    background: rgba(11, 15, 24, 0.88);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.055);
    border-radius: 20px;
    padding: 2rem 1.75rem;
    min-height: 210px;
    position: relative;
    z-index: 2;
    overflow: hidden;
    transition: all 0.38s cubic-bezier(0.4, 0, 0.2, 1);
}
.feat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 5%; right: 5%;
    height: 1.5px;
    background: linear-gradient(90deg, transparent, var(--fc-glow, #00f2ff), transparent);
    opacity: 0.55;
    transition: opacity 0.38s ease;
}
.feat-card:hover {
    border-color: rgba(0,242,255,0.2);
    box-shadow:
        0 22px 60px rgba(0,0,0,0.55),
        0 0 40px rgba(0,242,255,0.06);
    transform: translateY(-5px);
}
.feat-card:hover::before { opacity: 1; }

.feat-icon {
    display: block;
    font-size: 2.3rem;
    margin-bottom: 1.1rem;
    filter: drop-shadow(0 0 8px rgba(0,242,255,0.3));
}
.feat-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e0e6ed;
    margin-bottom: 0.55rem;
    letter-spacing: 0.1px;
}
.feat-desc {
    font-size: 0.875rem;
    color: #8a99ad;
    line-height: 1.68;
}
.feat-pill {
    display: inline-block;
    margin-top: 1.1rem;
    padding: 4px 13px;
    border-radius: 100px;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
.pill-cyan   { background:rgba(0,242,255,0.1);  color:#00f2ff;  border:1px solid rgba(0,242,255,0.32); }
.pill-purple { background:rgba(112,0,255,0.1);  color:#a060ff;  border:1px solid rgba(112,0,255,0.32); }
.pill-green  { background:rgba(0,255,157,0.1);  color:#00ff9d;  border:1px solid rgba(0,255,157,0.32); }


/* ══════════════════════════════════════════════════════
   HOW IT WORKS — STEPS
══════════════════════════════════════════════════════ */

.hiw-step {
    text-align: center;
    padding: 0.8rem 1.2rem;
    position: relative;
    z-index: 2;
}
.hiw-num {
    width: 58px;
    height: 58px;
    border-radius: 16px;
    background: linear-gradient(140deg, #7000ff 0%, #3200bb 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.3rem;
    font-weight: 800;
    color: #fff;
    margin: 0 auto 1.2rem;
    box-shadow: 0 0 26px rgba(112,0,255,0.5), 0 4px 14px rgba(0,0,0,0.3);
}
.hiw-title {
    font-size: 1.0rem;
    font-weight: 700;
    color: #e0e6ed;
    margin-bottom: 0.5rem;
}
.hiw-desc {
    font-size: 0.865rem;
    color: #8a99ad;
    line-height: 1.68;
}

/* Connector arrow between steps */
.hiw-arrow {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 2.4rem;
    position: relative;
    z-index: 2;
    font-size: 1.55rem;
    color: rgba(112,0,255,0.55);
    animation: arrowPulse 2.4s ease-in-out infinite;
}
@keyframes arrowPulse {
    0%, 100% { color: rgba(112,0,255,0.4); }
    50%       { color: rgba(0,242,255,0.7); }
}


/* ══════════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════════ */

.lp-footer {
    position: relative;
    z-index: 2;
    text-align: center;
    padding: 2.8rem 1rem 2rem;
    margin-top: 4.5rem;
    border-top: 1px solid rgba(255,255,255,0.055);
    color: #8a99ad;
    font-size: 0.8rem;
    letter-spacing: 0.5px;
}
.lp-footer .brand {
    color: #00f2ff;
    font-weight: 700;
    text-shadow: 0 0 12px rgba(0,242,255,0.35);
}
.lp-footer .sep { margin: 0 0.5rem; opacity: 0.4; }


/* ══════════════════════════════════════════════════════
   KEYFRAME LIBRARY
══════════════════════════════════════════════════════ */

@keyframes fadeSlideDown {
    from { opacity: 0; transform: translateY(-18px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(30px); }
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
    border-radius: 10px;
    transition: background 0.2s ease;
}
[data-testid="stSidebarContent"] [data-testid="stPageLink-NavLink"]:hover {
    background: rgba(0,242,255,0.08) !important;
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
        <div class="sidebar-header">⚡ PAAS</div>
        <p style="
            color:#8a99ad;
            font-size:0.7rem;
            margin:-0.3rem 0 0.8rem;
            letter-spacing:1.8px;
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
        "<p style='color:#8a99ad;font-size:0.75rem;font-weight:700;"
        "letter-spacing:1.5px;text-transform:uppercase;margin-bottom:0.4rem;'>"
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
                background: rgba(0,242,255,0.07);
                border: 1px solid rgba(0,242,255,0.2);
                border-radius: 12px;
                padding: 9px 14px;
                margin-bottom: 0.6rem;
            ">
                <span style="color:#00f2ff;font-size:0.88rem;font-weight:600;">
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
            st.page_link("pages/3_Create_Portfolio.py", label="📊  Create Portfolio")
        else:
            st.markdown(
                "<span style='color:#8a99ad;font-size:0.85rem;padding-left:4px;'>"
                "📊 Create Portfolio <em style='font-size:0.7rem;'>(soon)</em></span>",
                unsafe_allow_html=True,
            )

        if my_page.exists():
            st.page_link("pages/4_My_Portfolios.py", label="💼  My Portfolios")
        else:
            st.markdown(
                "<span style='color:#8a99ad;font-size:0.85rem;padding-left:4px;'>"
                "💼 My Portfolios <em style='font-size:0.7rem;'>(soon)</em></span>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown(
        """
        <p style="color:#8a99ad;font-size:0.73rem;line-height:1.7;padding:0 2px;">
            AI risk profiling &nbsp;·&nbsp; Smart allocation<br>
            Backtesting &nbsp;·&nbsp; S&amp;P 500 comparison
        </p>
    """,
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  BACKGROUND DECORATIONS  (rendered first so content stacks above)
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<div class="bg-orb bg-orb-purple"></div>
<div class="bg-orb bg-orb-cyan"></div>
<div class="bg-orb bg-orb-mid"></div>
<div class="cyber-grid"></div>
""",
    unsafe_allow_html=True,
)


# ═════════════════════════════════════════════════════════════════════════════
#  HERO SECTION
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<div class="hero">
    <div class="hero-badge">AI-POWERED INVESTMENT PLATFORM</div>
    <h1 class="hero-title">
        PREDICTIVE<br>
        <span class="glow">ASSET ALLOCATION</span><br>
        SYSTEM
    </h1>
    <p class="hero-tagline">
        <strong>AI-powered</strong> portfolio optimization.<br>
        Risk-aware. Data-driven.
    </p>
</div>
""",
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
    <span style="color:#00f2ff;">smarter</span>
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
    <div class="feat-card" style="--fc-glow:#00f2ff;">
        <span class="feat-icon">🧠</span>
        <div class="feat-name">AI Risk Profiling</div>
        <div class="feat-desc">
            Predicts your personal risk tolerance using a machine-learning
            model trained on real investor behavioural data — powered by
            PCA-based dimensionality reduction and ensemble scoring.
        </div>
        <span class="feat-pill pill-cyan">Machine Learning</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fc2:
    st.markdown(
        """
    <div class="feat-card" style="--fc-glow:#a060ff;">
        <span class="feat-icon">📈</span>
        <div class="feat-name">Smart Allocation</div>
        <div class="feat-desc">
            Optimized across growth, value &amp; quality buckets using
            combined fundamental and technical factor signals.
            Capital is distributed intelligently to match your exact
            risk profile and investment horizon.
        </div>
        <span class="feat-pill pill-purple">Multi-Factor</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fc3:
    st.markdown(
        """
    <div class="feat-card" style="--fc-glow:#00ff9d;">
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
    How it <span style="color:#7000ff;">works</span>
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
