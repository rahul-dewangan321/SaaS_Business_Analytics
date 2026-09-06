"""
styles.py
---------
Modern dark-themed styling helpers for the dashboard.

Provides a cohesive neon-slate palette, reusable CSS and helper functions
to render styled metric cards, headers and buttons with a consistent look.
"""

# --- Neoprene / glassmorphism dark theme palette ---------------------------
BG_COLOR = "#0B0F1E"          # deep slate background
SURFACE_COLOR = "#151B2E"    # card surface
SURFACE_ALT = "#1C2440"      # slightly lighter surface
BORDER_COLOR = "#2A3352"
TEXT_COLOR = "#E8ECF8"
MUTED_COLOR = "#8C96B4"
ACCENT = "#7C5CFF"           # electric violet
ACCENT_2 = "#00C2FF"         # cyan
ACCENT_3 = "#FF6B9D"         # pink
ACCENT_4 = "#FFC24B"         # amber
ACCENT_5 = "#34D399"         # green
DANGER = "#FF5C7A"
SUCCESS = "#34D399"

CHART_COLORS = ["#7C5CFF", "#00C2FF", "#FF6B9D", "#FFC24B", "#34D399", "#F97316"]

PLOTLY_TEMPLATE = "plotly_dark"


def inject_global_css() -> str:
    """Return global CSS injected into the app for a modern look."""
    return f"""
    <style>
        /* ---------- Global ---------- */
        .stApp {{
            background-color: {BG_COLOR};
            background-image:
                radial-gradient(circle at 15% 5%, rgba(124,92,255,0.12), transparent 45%),
                radial-gradient(circle at 85% 10%, rgba(0,194,255,0.10), transparent 45%),
                radial-gradient(circle at 60% 90%, rgba(255,107,157,0.08), transparent 45%);
        }}
        /* Main block sizing */
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }}
        /* ---------- Typography ---------- */
        h1, h2, h3, h4 {{
            color: {TEXT_COLOR} !important;
            letter-spacing: -0.02em;
        }}
        .dashboard-title {{
            font-size: 2.1rem;
            font-weight: 800;
            background: linear-gradient(90deg, {ACCENT}, {ACCENT_2}, {ACCENT_3});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }}
        .dashboard-subtitle {{
            color: {MUTED_COLOR};
            margin-bottom: 1.2rem;
            font-size: 0.95rem;
        }}
        /* ---------- Cards ---------- */
        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, {SURFACE_COLOR}, {SURFACE_ALT});
            border: 1px solid {BORDER_COLOR};
            border-radius: 16px;
            padding: 1rem 1.2rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        div[data-testid="stMetric"]:hover {{
            border-color: {ACCENT};
            transform: translateY(-2px);
        }}
        div[data-testid="stMetric"] label {{
            color: {MUTED_COLOR} !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: {TEXT_COLOR} !important;
            font-weight: 700;
        }}
        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background-color: {SURFACE_COLOR};
            border-right: 1px solid {BORDER_COLOR};
        }}
        section[data-testid="stSidebar"] .stMarkdown h4 {{
            color: {ACCENT_2} !important;
            letter-spacing: 0.04em;
        }}
        /* ---------- Widgets ---------- */
        .stMultiSelect [data-baseweb="tag"] {{
            background-color: {ACCENT} !important;
        }}
        div[data-baseweb="select"] > div {{
            background-color: {SURFACE_ALT} !important;
            border-color: {BORDER_COLOR} !important;
        }}
        /* ---------- Tabs ---------- */
        button[data-baseweb="tab"] {{
            color: {MUTED_COLOR};
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {ACCENT_2} !important;
            border-bottom-color: {ACCENT} !important;
        }}
        /* ---------- Footers ---------- */
        .stFooter {{
            display: none;
        }}
        .footer-note {{
            color: {MUTED_COLOR};
            text-align: center;
            font-size: 0.8rem;
            margin-top: 2rem;
        }}
    </style>
    """


def metric_card_html(label: str, value: str, icon: str = "📊", accent: str = ACCENT) -> str:
    """Build a compact HTML metric card (used where st.metric feels heavy)."""
    return f"""
    <div style="
        background: linear-gradient(145deg, {SURFACE_COLOR}, {SURFACE_ALT});
        border:1px solid {BORDER_COLOR};
        border-left:4px solid {accent};
        border-radius:14px;
        padding:0.9rem 1.1rem;
        box-shadow:0 8px 22px rgba(0,0,0,0.3);
        margin-bottom:0.6rem;">
        <div style="color:{MUTED_COLOR};font-size:0.78rem;text-transform:uppercase;letter-spacing:0.06em;">
            {icon} {label}
        </div>
        <div style="color:{TEXT_COLOR};font-size:1.7rem;font-weight:800;">
            {value}
        </div>
    </div>
    """


def section_header(title: str, subtitle: str = "") -> str:
    """Styled section header used at the top of each page."""
    sub = f'<div style="color:{MUTED_COLOR};font-size:0.9rem;margin-bottom:0.8rem;">{subtitle}</div>' if subtitle else ""
    return f"""
    <div style="margin-top:1rem;margin-bottom:0.5rem;">
        <div style="font-size:1.35rem;font-weight:750;color:{TEXT_COLOR};">
            <span style="color:{ACCENT};">◆</span> {title}
        </div>
        {sub}
    </div>
    """
