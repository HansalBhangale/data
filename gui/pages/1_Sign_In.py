"""
PAAS — Sign In Page

Cyberpunk / fintech themed authentication page.
The entire centred block-container is styled as a single glass card.
"""

import sys
from pathlib import Path

# ── Path setup ── add the project root (data/) so `gui.*` imports resolve ────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
#  STUB CLASSES
#  Must be defined BEFORE any import that could trigger model unpickling.
# ═══════════════════════════════════════════════════════════════════════════


class PCABasedRiskScorer:
    def __init__(self, df=None):
        self.df = df


class EmpiricalCorrelationScorer:
    def __init__(self, df=None):
        self.df = df


# ── Standard imports ─────────────────────────────────────────────────────────
import streamlit as st

from gui.database import login_user
from gui.styles import get_custom_css

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  ── must be the very first Streamlit call
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PAAS | Sign In",
    page_icon="🔐",
    layout="centered",
)


# ═══════════════════════════════════════════════════════════════════════════
#  GLOBAL THEME
# ═══════════════════════════════════════════════════════════════════════════

st.markdown(get_custom_css(), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  AUTH-PAGE CSS
# ═══════════════════════════════════════════════════════════════════════════

AUTH_CSS = """
<style>
/* ── Hide Streamlit chrome ── */
header, footer, #MainMenu { visibility: hidden !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════
   BACKGROUND
══════════════════════════════════════════ */

/* Enhanced radial background to complement the card */
.stApp {
    background-image:
        radial-gradient(ellipse 800px 600px at 20% 10%,
            rgba(112, 0, 255, 0.22) 0%, transparent 60%),
        radial-gradient(ellipse 700px 600px at 85% 90%,
            rgba(0, 242, 255, 0.12) 0%, transparent 60%) !important;
}

/* Subtle animated cyber grid */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,242,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,242,255,0.02) 1px, transparent 1px);
    background-size: 52px 52px;
    animation: gridScroll 30s linear infinite;
    pointer-events: none;
    z-index: 0;
}
@keyframes gridScroll {
    from { background-position: 0 0; }
    to   { background-position: 52px 52px; }
}


/* ══════════════════════════════════════════
   GLASS CARD  (= the centred block container)
══════════════════════════════════════════ */

[data-testid="stMainBlockContainer"] {
    position: relative !important;
    z-index: 2 !important;
    background: rgba(9, 13, 21, 0.92) !important;
    backdrop-filter: blur(28px) !important;
    -webkit-backdrop-filter: blur(28px) !important;
    border: 1px solid rgba(255, 255, 255, 0.065) !important;
    border-radius: 28px !important;
    padding: 2.8rem 2.8rem 2.2rem !important;
    max-width: 460px !important;
    margin: 3.5rem auto 2rem !important;
    box-shadow:
        0 32px 72px rgba(0, 0, 0, 0.65),
        0 0   60px rgba(112, 0, 255, 0.09),
        inset 0 1px 0 rgba(255, 255, 255, 0.055) !important;
    overflow: visible !important;
}

/* Top gradient accent line */
[data-testid="stMainBlockContainer"]::before {
    content: '';
    position: absolute;
    top: 0; left: 8%; right: 8%;
    height: 1.5px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(112, 0, 255, 0.8),
        rgba(0, 242, 255, 0.8),
        transparent
    );
    border-radius: 100px;
    pointer-events: none;
}


/* ══════════════════════════════════════════
   FORM INPUTS
══════════════════════════════════════════ */

.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #e0e6ed !important;
    padding: 13px 16px !important;
    font-size: 0.95rem !important;
    font-family: 'Outfit', sans-serif !important;
    transition: border-color 0.22s ease, box-shadow 0.22s ease,
                background 0.22s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0, 242, 255, 0.52) !important;
    box-shadow: 0 0 0 3px rgba(0, 242, 255, 0.08) !important;
    background: rgba(0, 242, 255, 0.028) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder {
    color: rgba(138, 153, 173, 0.45) !important;
}
.stTextInput > label {
    color: #8a99ad !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}


/* ══════════════════════════════════════════
   FORM SUBMIT BUTTON
══════════════════════════════════════════ */

.stFormSubmitButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #00c4ff 0%, #7000ff 100%) !important;
    color: #fff !important;
    border: none !important;
    padding: 14px 24px !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 22px rgba(0, 196, 255, 0.32) !important;
    margin-top: 0.6rem !important;
    transition: all 0.28s ease !important;
}
.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #18d4ff 0%, #8a1aff 100%) !important;
    box-shadow: 0 6px 32px rgba(0, 196, 255, 0.55) !important;
    transform: translateY(-2px) !important;
}
.stFormSubmitButton > button:active {
    transform: translateY(0) !important;
}


/* ══════════════════════════════════════════
   SECONDARY NAV BUTTON  (→ Sign Up)
══════════════════════════════════════════ */

.nav-btn .stButton > button {
    background: transparent !important;
    border: 1.5px solid rgba(0, 242, 255, 0.35) !important;
    color: #00f2ff !important;
    box-shadow: 0 0 14px rgba(0, 242, 255, 0.1) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    padding: 10px 20px !important;
    border-radius: 12px !important;
    text-transform: none !important;
    transition: all 0.26s ease !important;
}
.nav-btn .stButton > button:hover {
    background: rgba(0, 242, 255, 0.08) !important;
    border-color: rgba(0, 242, 255, 0.65) !important;
    box-shadow: 0 0 24px rgba(0, 242, 255, 0.28) !important;
    transform: translateY(-1px) !important;
}


/* ══════════════════════════════════════════
   ALERT OVERRIDES
══════════════════════════════════════════ */

[data-testid="stAlert"] {
    border-radius: 12px !important;
    font-size: 0.9rem !important;
}


/* ══════════════════════════════════════════
   DIVIDER
══════════════════════════════════════════ */

.auth-divider {
    height: 1px;
    background: linear-gradient(
        90deg, transparent, rgba(255,255,255,0.09), transparent
    );
    margin: 1.4rem 0 1.2rem;
}


/* ══════════════════════════════════════════
   ANIMATIONS
══════════════════════════════════════════ */

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(22px); }
    to   { opacity: 1; transform: translateY(0); }
}
.anim-fade-up {
    animation: fadeUp 0.55s ease-out both;
}
</style>
"""

st.markdown(AUTH_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(
        '<div class="sidebar-header">⚡ PAAS</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.page_link("app.py", label="🏠  Home")
    st.page_link("pages/1_Sign_In.py", label="🔐  Sign In")
    st.page_link("pages/2_Sign_Up.py", label="🚀  Sign Up")

    if st.session_state.get("user_id"):
        st.markdown("---")
        create_page = Path(__file__).parent / "3_Create_Portfolio.py"
        my_page = Path(__file__).parent / "4_My_Portfolios.py"
        if create_page.exists():
            st.page_link("pages/3_Create_Portfolio.py", label="📊  Create Portfolio")
        if my_page.exists():
            st.page_link("pages/4_My_Portfolios.py", label="💼  My Portfolios")


# ═══════════════════════════════════════════════════════════════════════════
#  CARD HEADER — branding
# ═══════════════════════════════════════════════════════════════════════════

# NOTE: All HTML is kept on single lines with no blank lines inside blocks.
# CommonMark terminates a <div> HTML block on the first blank line it sees,
# which causes subsequent indented content to be rendered as a code block.
st.markdown(
    '<div class="anim-fade-up" style="text-align:center;margin-bottom:1.8rem;">'
    '<div style="display:inline-flex;align-items:center;justify-content:center;'
    "width:62px;height:62px;border-radius:18px;"
    "background:linear-gradient(140deg,#7000ff 0%,#00c4ff 100%);"
    "box-shadow:0 0 28px rgba(112,0,255,0.5),0 6px 18px rgba(0,0,0,0.4);"
    'font-size:1.7rem;margin-bottom:1rem;">⚡</div>'
    '<div style="font-size:0.65rem;font-weight:700;letter-spacing:4px;'
    "text-transform:uppercase;color:#00f2ff;"
    'text-shadow:0 0 14px rgba(0,242,255,0.4);margin-bottom:1.1rem;">'
    "Predictive Asset Allocation System</div>"
    '<h1 style="font-size:1.65rem;font-weight:800;color:#e0e6ed;'
    'letter-spacing:-0.4px;margin:0 0 0.3rem;">Welcome back</h1>'
    '<p style="font-size:0.875rem;color:#8a99ad;margin:0;line-height:1.5;">'
    "Sign in to access your portfolio dashboard</p>"
    "</div>",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGE PLACEHOLDER  (rendered above the form so errors appear in-card)
# ═══════════════════════════════════════════════════════════════════════════

msg_slot = st.empty()


# ═══════════════════════════════════════════════════════════════════════════
#  SIGN-IN FORM
# ═══════════════════════════════════════════════════════════════════════════

with st.form("paas_signin_form", clear_on_submit=False):
    email = st.text_input(
        "Email Address",
        placeholder="you@example.com",
        key="signin_email",
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="••••••••",
        key="signin_password",
    )
    submitted = st.form_submit_button(
        "🔐  Sign In",
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  FORM PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

if submitted:
    # ── Basic client-side validation ──────────────────────────────────────
    if not email.strip():
        msg_slot.error("⚠️  Please enter your email address.")
    elif not password:
        msg_slot.error("⚠️  Please enter your password.")
    else:
        # ── Call database auth ────────────────────────────────────────────
        result = login_user(email.strip(), password)

        if result.get("success"):
            # ── Persist auth in session state ─────────────────────────────
            st.session_state.user_id = result["user_id"]
            st.session_state.user_email = result["email"]
            st.session_state.user_name = result["name"]

            msg_slot.success(f"✅  Welcome back, **{result['name']}**!")

            # ── Navigate to dashboard (graceful fallback) ─────────────────
            create_page = Path(__file__).parent / "3_Create_Portfolio.py"
            if create_page.exists():
                st.switch_page("pages/3_Create_Portfolio.py")
            else:
                # Dashboard not built yet — go home with session intact
                st.switch_page("app.py")
        else:
            msg_slot.error(f"⚠️  {result.get('error', 'Authentication failed.')}")


# ═══════════════════════════════════════════════════════════════════════════
#  FOOTER LINKS
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<div class="auth-divider"></div>', unsafe_allow_html=True)

st.markdown(
    """
<p style="
    text-align: center;
    color: #8a99ad;
    font-size: 0.875rem;
    margin-bottom: 0.7rem;
">Don't have an account?</p>
""",
    unsafe_allow_html=True,
)

_, nav_col, _ = st.columns([1, 3, 1])
with nav_col:
    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button(
        "🚀  Create Account  →",
        use_container_width=True,
        key="nav_to_signup",
    ):
        st.switch_page("pages/2_Sign_Up.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
<p style="
    text-align: center;
    color: #8a99ad;
    font-size: 0.72rem;
    letter-spacing: 0.5px;
    margin-top: 1.4rem;
    opacity: 0.65;
">
    PAAS · Predictive Asset Allocation System
</p>
""",
    unsafe_allow_html=True,
)
