"""
Custom Theme and Styling for Predictive Asset Allocation System

Professional fintech design system.
"""

# Color palette — professional fintech
COLORS = {
    "primary": "#3B82F6",        # Refined blue
    "primary_light": "#60A5FA",  # Light blue
    "secondary": "#6366F1",      # Indigo
    "success": "#10B981",        # Green
    "danger": "#EF4444",         # Red
    "warning": "#F59E0B",        # Amber
    "bg_dark": "#0B0F19",        # Deep navy
    "bg_card": "rgba(15, 23, 42, 0.80)",  # Slate card
    "bg_surface": "rgba(30, 41, 59, 0.50)",  # Elevated surface
    "text": "#E2E8F0",           # Slate-200
    "text_secondary": "#94A3B8", # Slate-400
    "border": "rgba(255, 255, 255, 0.06)",
}

# Font families
FONTS = {
    "main": "Outfit, sans-serif",
    "mono": "JetBrains Mono, monospace",
}


def get_custom_css():
    """
    Returns custom CSS for the Streamlit app — professional fintech theme.
    """
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
        --primary: {COLORS["primary"]};
        --primary-light: {COLORS["primary_light"]};
        --secondary: {COLORS["secondary"]};
        --bg: {COLORS["bg_dark"]};
        --card-bg: {COLORS["bg_card"]};
        --surface: {COLORS["bg_surface"]};
        --text: {COLORS["text"]};
        --text-sec: {COLORS["text_secondary"]};
        --success: {COLORS["success"]};
        --danger: {COLORS["danger"]};
        --warning: {COLORS["warning"]};
        --border: {COLORS["border"]};
        --radius-card: 16px;
        --radius-input: 10px;
        --radius-btn: 10px;
    }}

    /* ────────────────────────────────────────────────
       BASE APP
    ──────────────────────────────────────────────── */
    .stApp {{
        background-color: var(--bg);
        background-image:
            radial-gradient(ellipse 900px 700px at 5% 5%, rgba(59,130,246,0.07) 0%, transparent 60%),
            radial-gradient(ellipse 600px 500px at 95% 95%, rgba(99,102,241,0.05) 0%, transparent 60%);
        font-family: '{FONTS["main"]}', sans-serif;
        color: var(--text);
    }}

    /* ────────────────────────────────────────────────
       GLASS CARDS
    ──────────────────────────────────────────────── */
    .glass-card {{
        background: var(--card-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border);
        border-radius: var(--radius-card);
        padding: 24px;
        margin-bottom: 20px;
        transition: border-color 0.2s ease;
    }}
    .glass-card:hover {{
        border-color: rgba(59,130,246,0.15);
    }}

    /* ────────────────────────────────────────────────
       SIDEBAR
    ──────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: rgba(8, 12, 21, 0.98) !important;
        border-right: 1px solid rgba(255,255,255,0.04);
    }}

    /* Hide Streamlit's auto-generated page navigation */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}

    .sidebar-header {{
        font-size: 1.3rem;
        font-weight: 800;
        color: var(--primary);
        margin-bottom: 0.3rem;
        letter-spacing: 0.5px;
    }}

    /* ────────────────────────────────────────────────
       METRIC VISUALS
    ──────────────────────────────────────────────── */
    .stat-val {{
        font-family: '{FONTS["mono"]}', monospace;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
        margin: 8px 0;
    }}
    .stat-label {{
        color: var(--text-sec);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }}

    /* Glow helpers — subtle, professional */
    .glow-text-primary  {{ color: var(--primary); }}
    .glow-text-secondary {{ color: var(--secondary); }}
    .glow-text-success  {{ color: var(--success); }}
    .glow-text-danger   {{ color: var(--danger); }}

    /* ────────────────────────────────────────────────
       BUTTONS
    ──────────────────────────────────────────────── */
    .stButton > button {{
        width: 100%;
        background: var(--primary) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 11px 22px !important;
        border-radius: var(--radius-btn) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    }}
    .stButton > button:hover {{
        background: var(--primary-light) !important;
        box-shadow: 0 4px 12px rgba(59,130,246,0.25) !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button:active {{
        transform: translateY(0) !important;
    }}

    /* ────────────────────────────────────────────────
       DATAFRAMES
    ──────────────────────────────────────────────── */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
    }}

    /* ────────────────────────────────────────────────
       DIVIDERS
    ──────────────────────────────────────────────── */
    .quantum-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(59,130,246,0.15), transparent);
        margin: 2rem 0;
    }}

    /* ────────────────────────────────────────────────
       HIDE STREAMLIT CHROME
    ──────────────────────────────────────────────── */
    [data-testid="stDecoration"] {{ display: none !important; }}
    [data-testid="stToolbar"] {{ visibility: hidden !important; }}
    #MainMenu {{ visibility: hidden !important; }}
    footer {{ visibility: hidden !important; }}

    header {{
        background: transparent !important;
        box-shadow: none !important;
    }}

    /* ────────────────────────────────────────────────
       METRIC CARDS
    ──────────────────────────────────────────────── */
    .metric-card {{
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
    }}

    /* Beat S&P Badge */
    .beat-spy-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1rem;
    }}
    .beat-spy-badge.success {{
        background: rgba(16, 185, 129, 0.12);
        border: 1.5px solid var(--success);
        color: var(--success);
    }}
    .beat-spy-badge.failure {{
        background: rgba(239, 68, 68, 0.12);
        border: 1.5px solid var(--danger);
        color: var(--danger);
    }}

    /* ────────────────────────────────────────────────
       SECTION HEADERS
    ──────────────────────────────────────────────── */
    .section-header {{
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: var(--text);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding-bottom: 0.5rem;
    }}

    /* ────────────────────────────────────────────────
       STREAMLIT METRICS — clean up default styles
    ──────────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px 16px;
    }}
    [data-testid="stMetricLabel"] {{
        color: var(--text-sec) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600 !important;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--text) !important;
        font-family: '{FONTS["mono"]}', monospace !important;
        font-weight: 600 !important;
    }}

    /* ────────────────────────────────────────────────
       SELECT / INPUT GLOBAL OVERRIDES
    ──────────────────────────────────────────────── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: var(--radius-input) !important;
        color: var(--text) !important;
    }}
    .stSelectbox label,
    .stMultiSelect label,
    .stSlider label,
    .stNumberInput label,
    .stCheckbox label {{
        color: var(--text-sec) !important;
        font-weight: 500 !important;
    }}

    /* Number inputs */
    .stNumberInput > div > div > input {{
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: var(--radius-input) !important;
        color: var(--text) !important;
    }}

    /* Slider */
    .stSlider > div > div > div > div {{
        background: var(--primary) !important;
    }}

</style>
<script>
(function() {{
    /* ── 1. Clear stuck localStorage on first load ── */
    try {{
        var lsKey = null;
        for (var i = 0; i < localStorage.length; i++) {{
            var k = localStorage.key(i);
            if (k && k.toLowerCase().indexOf('sidebarcollapsed') !== -1) {{
                lsKey = k;
                break;
            }}
        }}
        if (lsKey && localStorage.getItem(lsKey) === 'true') {{
            localStorage.removeItem(lsKey);
        }}
    }} catch(e) {{}}

    /* ── 2. Sidebar toggle button ── */
    function isSidebarCollapsed() {{
        var collapsed = document.querySelector('[data-testid="collapsedControl"]');
        if (collapsed && collapsed.offsetParent !== null) return true;

        var sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {{
            var w = sidebar.getBoundingClientRect().width;
            if (w < 30) return true;
        }}
        return false;
    }}

    function clickExpand() {{
        var ctrl = document.querySelector('[data-testid="collapsedControl"]');
        if (ctrl) {{
            ctrl.style.pointerEvents = 'auto';
            var expandBtn = ctrl.querySelector('button');
            if (expandBtn) {{
                expandBtn.click();
                setTimeout(function() {{
                    ctrl.style.pointerEvents = 'none';
                }}, 300);
                return true;
            }}
        }}
        return false;
    }}

    function clickCollapse() {{
        var collapseBtn =
            document.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
            document.querySelector('[data-testid="stSidebar"] button[kind="header"]') ||
            document.querySelector('[data-testid="stSidebar"] [data-testid="baseButton-header"]');
        if (collapseBtn) {{
            var parent = collapseBtn.closest('[data-testid="stSidebarCollapseButton"]');
            if (parent) parent.style.pointerEvents = 'auto';
            collapseBtn.click();
            if (parent) {{
                setTimeout(function() {{
                    parent.style.pointerEvents = 'none';
                }}, 300);
            }}
            return true;
        }}
        return false;
    }}

    function setupSidebarToggle() {{
        if (document.getElementById('st-custom-sidebar-btn')) return;

        var btn = document.createElement('button');
        btn.id = 'st-custom-sidebar-btn';
        btn.title = 'Toggle sidebar';
        btn.innerHTML = '&#9776;';

        btn.addEventListener('click', function(e) {{
            e.preventDefault();
            e.stopPropagation();

            if (isSidebarCollapsed()) {{
                if (!clickExpand()) {{
                    try {{
                        for (var i = 0; i < localStorage.length; i++) {{
                            var k = localStorage.key(i);
                            if (k && k.toLowerCase().indexOf('sidebarcollapsed') !== -1) {{
                                localStorage.setItem(k, 'false');
                            }}
                        }}
                    }} catch(ex) {{}}
                    window.location.reload();
                }}
            }} else {{
                clickCollapse();
            }}
        }});

        document.body.appendChild(btn);
    }}

    /* ── 3. Initialize ── */
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', setupSidebarToggle);
    }} else {{
        setupSidebarToggle();
    }}

    var _observer = new MutationObserver(function() {{
        setupSidebarToggle();
    }});
    _observer.observe(document.body, {{ childList: true }});
}})();
</script>
"""
