"""
PAAS — Sign Up Page

Cyberpunk / fintech themed registration page.
The entire centred block-container is styled as a single glass card.
"""

import re
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

from gui.database import register_user
from gui.styles import get_custom_css

# ═══════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  ── must be the very first Streamlit call
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PAAS | Sign Up",
    page_icon="🚀",
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

/* Accent gradient — purple-dominant for Sign Up, mirrored from Sign In */
.stApp {
    background-image:
        radial-gradient(ellipse 700px 600px at 80% 10%,
            rgba(0, 242, 255, 0.14) 0%, transparent 60%),
        radial-gradient(ellipse 800px 700px at 15% 90%,
            rgba(112, 0, 255, 0.22) 0%, transparent 60%) !important;
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
    max-width: 480px !important;
    margin: 3rem auto 2rem !important;
    box-shadow:
        0 32px 72px rgba(0, 0, 0, 0.65),
        0 0   60px rgba(0, 196, 255, 0.07),
        inset 0 1px 0 rgba(255, 255, 255, 0.055) !important;
    overflow: visible !important;
}

/* Top gradient accent line — cyan-dominant for Sign Up */
[data-testid="stMainBlockContainer"]::before {
    content: '';
    position: absolute;
    top: 0; left: 8%; right: 8%;
    height: 1.5px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(0, 242, 255, 0.85),
        rgba(112, 0, 255, 0.85),
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

/* Validation-state borders */
.input-ok  .stTextInput > div > div > input {
    border-color: rgba(0, 255, 157, 0.45) !important;
    box-shadow: 0 0 0 3px rgba(0, 255, 157, 0.07) !important;
}
.input-err .stTextInput > div > div > input {
    border-color: rgba(255, 0, 85, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(255, 0, 85, 0.07) !important;
}


/* ══════════════════════════════════════════
   PASSWORD STRENGTH METER
══════════════════════════════════════════ */

.pw-meter-wrap {
    margin-top: 6px;
    margin-bottom: 2px;
}
.pw-meter-bar {
    height: 3px;
    border-radius: 100px;
    transition: width 0.35s ease, background 0.35s ease;
}
.pw-meter-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.8px;
    margin-top: 4px;
}


/* ══════════════════════════════════════════
   FORM SUBMIT BUTTON
══════════════════════════════════════════ */

.stFormSubmitButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #00f2ff 0%, #7000ff 100%) !important;
    color: #fff !important;
    border: none !important;
    padding: 14px 24px !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 22px rgba(0, 242, 255, 0.3) !important;
    margin-top: 0.6rem !important;
    transition: all 0.28s ease !important;
}
.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #18ffff 0%, #8a1aff 100%) !important;
    box-shadow: 0 6px 32px rgba(0, 242, 255, 0.52) !important;
    transform: translateY(-2px) !important;
}
.stFormSubmitButton > button:active {
    transform: translateY(0) !important;
}


/* ══════════════════════════════════════════
   SECONDARY NAV BUTTON  (→ Sign In)
══════════════════════════════════════════ */

.nav-btn .stButton > button {
    background: transparent !important;
    border: 1.5px solid rgba(112, 0, 255, 0.4) !important;
    color: #a060ff !important;
    box-shadow: 0 0 14px rgba(112, 0, 255, 0.1) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    padding: 10px 20px !important;
    border-radius: 12px !important;
    text-transform: none !important;
    transition: all 0.26s ease !important;
}
.nav-btn .stButton > button:hover {
    background: rgba(112, 0, 255, 0.1) !important;
    border-color: rgba(112, 0, 255, 0.7) !important;
    box-shadow: 0 0 24px rgba(112, 0, 255, 0.28) !important;
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
   INLINE VALIDATION HINTS
══════════════════════════════════════════ */

.hint-ok  { color: #00ff9d; font-size: 0.75rem; margin-top: 3px; font-weight: 600; }
.hint-err { color: #ff0055; font-size: 0.75rem; margin-top: 3px; font-weight: 600; }
.hint-neu { color: #8a99ad; font-size: 0.75rem; margin-top: 3px; }


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
   FEATURE CHECKLIST
══════════════════════════════════════════ */

.feature-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 1.2rem 0 0.4rem;
}
.feature-item {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 0.82rem;
    color: #8a99ad;
}
.feature-item .check {
    color: #00ff9d;
    font-size: 0.75rem;
    flex-shrink: 0;
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
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value.strip()))


def _password_strength(pw: str) -> tuple[int, str, str]:
    """
    Return (score 0-4, label, hex colour) for a password.

    Score breakdown:
      +1  length >= 8
      +1  contains a digit
      +1  contains a lowercase letter
      +1  contains an uppercase letter or symbol
    """
    if not pw:
        return 0, "", "#8a99ad"

    score = 0
    if len(pw) >= 8:
        score += 1
    if re.search(r"\d", pw):
        score += 1
    if re.search(r"[a-z]", pw):
        score += 1
    if re.search(r"[A-Z!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pw):
        score += 1

    labels = ["", "Weak", "Fair", "Good", "Strong"]
    colours = ["#8a99ad", "#ff0055", "#ffaa00", "#00f2ff", "#00ff9d"]
    return score, labels[score], colours[score]


# ═══════════════════════════════════════════════════════════════════════════
#  CARD HEADER — branding
# ═══════════════════════════════════════════════════════════════════════════

# NOTE: No blank lines inside <div> blocks — CommonMark terminates a type-6
# HTML block on the first blank line, causing indented content to become a
# code block. All HTML is kept on single lines to prevent this.
st.markdown(
    '<div class="anim-fade-up" style="text-align:center;margin-bottom:1.6rem;">'
    '<div style="display:inline-flex;align-items:center;justify-content:center;'
    "width:62px;height:62px;border-radius:18px;"
    "background:linear-gradient(140deg,#00c4ff 0%,#7000ff 100%);"
    "box-shadow:0 0 28px rgba(0,196,255,0.5),0 6px 18px rgba(0,0,0,0.4);"
    'font-size:1.7rem;margin-bottom:1rem;">🚀</div>'
    '<div style="font-size:0.65rem;font-weight:700;letter-spacing:4px;'
    "text-transform:uppercase;color:#00f2ff;"
    'text-shadow:0 0 14px rgba(0,242,255,0.4);margin-bottom:1.1rem;">'
    "Predictive Asset Allocation System</div>"
    '<h1 style="font-size:1.65rem;font-weight:800;color:#e0e6ed;'
    'letter-spacing:-0.4px;margin:0 0 0.3rem;">Create your account</h1>'
    '<p style="font-size:0.875rem;color:#8a99ad;margin:0;line-height:1.5;">'
    "Get your AI-powered portfolio in under 2 minutes</p>"
    "</div>",
    unsafe_allow_html=True,
)


# ── Mini feature teaser inside the card ──────────────────────────────────────
st.markdown(
    """
<div class="feature-list">
    <div class="feature-item">
        <span class="check">✦</span>
        <span>Personalised ML risk scoring based on your financial profile</span>
    </div>
    <div class="feature-item">
        <span class="check">✦</span>
        <span>Optimized S&amp;P 500 portfolio across growth, value &amp; quality</span>
    </div>
    <div class="feature-item">
        <span class="check">✦</span>
        <span>Real backtesting vs S&amp;P 500 with full performance metrics</span>
    </div>
</div>
<div style="height:1px;background:linear-gradient(90deg,transparent,
    rgba(0,242,255,0.18),transparent);margin:1.4rem 0;"></div>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGE PLACEHOLDER  (rendered above the form)
# ═══════════════════════════════════════════════════════════════════════════

msg_slot = st.empty()


# ═══════════════════════════════════════════════════════════════════════════
#  SIGN-UP FORM
# ═══════════════════════════════════════════════════════════════════════════

with st.form("paas_signup_form", clear_on_submit=False):
    name = st.text_input(
        "Full Name",
        placeholder="Jane Smith",
        key="signup_name",
    )

    email = st.text_input(
        "Email Address",
        placeholder="you@example.com",
        key="signup_email",
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Minimum 6 characters",
        key="signup_password",
    )

    confirm = st.text_input(
        "Confirm Password",
        type="password",
        placeholder="Repeat your password",
        key="signup_confirm",
    )

    # ── Live password-strength hint (shown while form is filling) ──────────
    if password:
        score, label, colour = _password_strength(password)
        bar_pct = score * 25  # 0 – 100 %
        st.markdown(
            f'<div class="pw-meter-wrap">'
            f'<div style="background:rgba(255,255,255,0.07);border-radius:100px;height:3px;overflow:hidden;">'
            f'<div class="pw-meter-bar" style="width:{bar_pct}%;background:{colour};"></div>'
            f"</div>"
            f'<span class="pw-meter-label" style="color:{colour};">{label}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Passwords-match live hint ──────────────────────────────────────────
    if confirm and password:
        if password == confirm:
            st.markdown(
                '<p class="hint-ok">✓ Passwords match</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p class="hint-err">✗ Passwords do not match</p>',
                unsafe_allow_html=True,
            )

    submitted = st.form_submit_button(
        "🚀  Create Account",
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  FORM PROCESSING  &  VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

if submitted:
    # ── 1. Field-presence checks ──────────────────────────────────────────
    if not name.strip():
        msg_slot.error("⚠️  Please enter your full name.")

    elif not email.strip():
        msg_slot.error("⚠️  Please enter your email address.")

    elif not _valid_email(email):
        msg_slot.error("⚠️  Please enter a valid email address  (e.g. you@example.com).")

    elif not password:
        msg_slot.error("⚠️  Please choose a password.")

    elif len(password) < 6:
        msg_slot.error("⚠️  Password must be at least 6 characters long.")

    elif not confirm:
        msg_slot.error("⚠️  Please confirm your password.")

    elif password != confirm:
        msg_slot.error("⚠️  Passwords do not match — please try again.")

    else:
        # ── 2. Attempt registration ───────────────────────────────────────
        # Note: register_user signature is (email, password, name)
        result = register_user(
            email=email.strip().lower(),
            password=password,
            name=name.strip(),
        )

        if result.get("success"):
            # ── 3. Persist auth in session state ──────────────────────────
            st.session_state.user_id = result["user_id"]
            st.session_state.user_email = email.strip().lower()
            st.session_state.user_name = name.strip()

            msg_slot.success(f"✅  Account created! Welcome, **{name.strip()}**.")

            # ── 4. Navigate to dashboard (graceful fallback) ───────────────
            create_page = Path(__file__).parent / "3_Create_Portfolio.py"
            if create_page.exists():
                st.switch_page("pages/3_Create_Portfolio.py")
            else:
                # Dashboard not built yet — go home with session intact
                st.switch_page("app.py")

        else:
            msg_slot.error(
                f"⚠️  {result.get('error', 'Registration failed. Please try again.')}"
            )


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
">Already have an account?</p>
""",
    unsafe_allow_html=True,
)

_, nav_col, _ = st.columns([1, 3, 1])
with nav_col:
    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button(
        "🔐  Sign In  →",
        use_container_width=True,
        key="nav_to_signin",
    ):
        st.switch_page("pages/1_Sign_In.py")
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
