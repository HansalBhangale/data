"""
Custom Theme and Styling for Predictive Asset Allocation System
"""

# Color palette
COLORS = {
    'primary': '#00f2ff',      # Cyan
    'secondary': '#7000ff',     # Purple
    'success': '#00ff9d',      # Green
    'danger': '#ff0055',       # Red
    'warning': '#ffaa00',      # Orange
    'bg_dark': '#0a0e14',      # Dark background
    'bg_card': 'rgba(16, 20, 30, 0.7)',  # Glass card
    'text': '#e0e6ed',         # Text color
    'text_secondary': '#8a99ad',  # Secondary text
}

# Font families
FONTS = {
    'main': 'Outfit, sans-serif',
    'mono': 'JetBrains Mono, monospace',
}


def get_custom_css():
    """
    Returns custom CSS for the Streamlit app.
    """
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
        --primary: {COLORS['primary']};
        --secondary: {COLORS['secondary']};
        --bg: {COLORS['bg_dark']};
        --card-bg: {COLORS['bg_card']};
        --text: {COLORS['text']};
        --success: {COLORS['success']};
        --danger: {COLORS['danger']};
    }}

    .stApp {{
        background-color: var(--bg);
        background-image: 
            radial-gradient(at 0% 0%, rgba(112, 0, 255, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(0, 242, 255, 0.1) 0px, transparent 50%);
        font-family: '{FONTS['main']}', sans-serif;
        color: var(--text);
    }}

    /* Glass Cards */
    .glass-card {{
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .glass-card:hover {{
        border-color: rgba(0, 242, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
    }}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: rgba(8, 10, 15, 0.98) !important;
        border-right: 1px solid rgba(0, 242, 255, 0.1);
    }}
    
    .sidebar-header {{
        font-size: 1.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
        letter-spacing: 1px;
    }}

    /* Metric Visuals */
    .stat-val {{
        font-family: '{FONTS['mono']}', monospace;
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
        margin: 10px 0;
    }}
    
    .stat-label {{
        color: {COLORS['text_secondary']};
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }}

    /* Glow Elements */
    .glow-text-primary {{ text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); color: var(--primary); }}
    .glow-text-secondary {{ text-shadow: 0 0 10px rgba(112, 0, 255, 0.5); color: var(--secondary); }}
    .glow-text-success {{ text-shadow: 0 0 10px rgba(0, 255, 157, 0.5); color: var(--success); }}
    .glow-text-danger {{ text-shadow: 0 0 10px rgba(255, 0, 85, 0.5); color: var(--danger); }}

    /* Custom Button */
    .stButton > button {{
        width: 100%;
        background: linear-gradient(135deg, var(--secondary) 0%, #4a00aa 100%) !important;
        color: white !important;
        border: none !important;
        padding: 12px 24px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(112, 0, 255, 0.3) !important;
    }}
    
    .stButton > button:hover {{
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(112, 0, 255, 0.5) !important;
        background: linear-gradient(135deg, #821aff 0%, #5a00cc 100%) !important;
    }}

    /* Dataframe Styling */
    .stDataFrame {{
        border-radius: 15px;
        overflow: hidden;
    }}

    /* Section Divider */
    .quantum-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 242, 255, 0.3), transparent);
        margin: 2rem 0;
    }}

    /* Hide redundant elements */
    header {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Metric cards */
    .metric-card {{
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
    }}

    /* Beat S&P Badge */
    .beat-spy-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.1rem;
    }}
    
    .beat-spy-badge.success {{
        background: rgba(0, 255, 157, 0.15);
        border: 2px solid var(--success);
        color: var(--success);
    }}
    
    .beat-spy-badge.failure {{
        background: rgba(255, 0, 85, 0.15);
        border: 2px solid var(--danger);
        color: var(--danger);
    }}

    /* Section Headers */
    .section-header {{
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: var(--text);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
    }}
</style>
"""
