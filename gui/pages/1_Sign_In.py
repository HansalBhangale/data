"""
PAAS — Sign In Page

Professional fintech themed authentication page.
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
    initial_sidebar_state="expanded",
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
footer, #MainMenu { visibility: hidden !important; }
header { background: transparent !important; box-shadow: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ══════════════════════════════════════════
   BACKGROUND
══════════════════════════════════════════ */

.stApp {
    background-image:
        radial-gradient(ellipse 700px 500px at 20% 10%,
            rgba(59,130,246,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 600px 500px at 80% 90%,
            rgba(99,102,241,0.06) 0%, transparent 60%) !important;
}


/* ══════════════════════════════════════════
   GLASS CARD  (= the centred block container)
══════════════════════════════════════════ */

[data-testid="stMainBlockContainer"] {
    position: relative !important;
    z-index: 2 !important;
    background: rgba(15, 23, 42, 0.92) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 20px !important;
    padding: 2.5rem 2.5rem 2rem !important;
    max-width: 440px !important;
    margin: 3rem auto 2rem !important;
    box-shadow:
        0 20px 50px rgba(0, 0, 0, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
    overflow: visible !important;
}

/* Top accent line */
[data-testid="stMainBlockContainer"]::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(59,130,246,0.4),
        rgba(99,102,241,0.4),
        transparent
    );
    border-radius: 100px;
    pointer-events: none;
}


/* ══════════════════════════════════════════
   FORM INPUTS
══════════════════════════════════════════ */

.stTextInput > div > div > input {
    background: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
    padding: 12px 16px !important;
    font-size: 0.92rem !important;
    font-family: 'Outfit', sans-serif !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(59,130,246,0.45) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.08) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder {
    color: rgba(148, 163, 184, 0.4) !important;
}
.stTextInput > label {
    color: #94A3B8 !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}


/* ══════════════════════════════════════════
   FORM SUBMIT BUTTON
══════════════════════════════════════════ */

.stFormSubmitButton > button {
    width: 100% !important;
    background: #3B82F6 !important;
    color: #fff !important;
    border: none !important;
    padding: 12px 24px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 2px 10px rgba(59,130,246,0.25) !important;
    margin-top: 0.5rem !important;
    transition: all 0.2s ease !important;
}
.stFormSubmitButton > button:hover {
    background: #60A5FA !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.35) !important;
    transform: translateY(-1px) !important;
}
.stFormSubmitButton > button:active {
    transform: translateY(0) !important;
}


/* ══════════════════════════════════════════
   SECONDARY NAV BUTTON  (→ Sign Up)
══════════════════════════════════════════ */

.nav-btn .stButton > button {
    background: transparent !important;
    border: 1.5px solid rgba(59,130,246,0.25) !important;
    color: #60A5FA !important;
    box-shadow: none !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 10px 20px !important;
    border-radius: 10px !important;
    text-transform: none !important;
    transition: all 0.2s ease !important;
}
.nav-btn .stButton > button:hover {
    background: rgba(59,130,246,0.06) !important;
    border-color: rgba(59,130,246,0.45) !important;
    transform: translateY(-1px) !important;
}


/* ══════════════════════════════════════════
   ALERT OVERRIDES
══════════════════════════════════════════ */

[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.88rem !important;
}


/* ══════════════════════════════════════════
   DIVIDER
══════════════════════════════════════════ */

.auth-divider {
    height: 1px;
    background: linear-gradient(
        90deg, transparent, rgba(255,255,255,0.06), transparent
    );
    margin: 1.4rem 0 1.2rem;
}


/* ══════════════════════════════════════════
   ANIMATIONS
══════════════════════════════════════════ */

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.anim-fade-up {
    animation: fadeUp 0.4s ease-out both;
}
</style>
"""

st.markdown(AUTH_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(
        '<div class="sidebar-header">📊 PAAS</div>',
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

st.markdown(
    '<div class="anim-fade-up" style="text-align:center;margin-bottom:1.6rem;">'
    '<div style="display:inline-flex;align-items:center;justify-content:center;'
    "width:56px;height:56px;border-radius:14px;"
    "background:#3B82F6;"
    "box-shadow:0 4px 16px rgba(59,130,246,0.3);"
    'font-size:1.5rem;margin-bottom:0.8rem;">🔐</div>'
    '<div style="font-size:0.62rem;font-weight:600;letter-spacing:3px;'
    "text-transform:uppercase;color:#60A5FA;"
    'margin-bottom:1rem;">'
    "Predictive Asset Allocation System</div>"
    '<h1 style="font-size:1.5rem;font-weight:800;color:#E2E8F0;'
    'letter-spacing:-0.3px;margin:0 0 0.3rem;">Welcome back</h1>'
    '<p style="font-size:0.85rem;color:#94A3B8;margin:0;line-height:1.5;">'
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
    color: #94A3B8;
    font-size: 0.85rem;
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
    color: #64748B;
    font-size: 0.7rem;
    letter-spacing: 0.3px;
    margin-top: 1.4rem;
    opacity: 0.7;
">
    PAAS · Predictive Asset Allocation System
</p>
""",
    unsafe_allow_html=True,
)
