"""
style_utils.py — Claude ライクデザイン CSS
既存ページ（pages/xx_*.py）から呼ばれる load_custom_css() を提供する。
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

/* === Reset & Base === */
html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans JP', -apple-system, sans-serif;
    color: #1e293b;
}

/* === Hide Streamlit chrome === */
#MainMenu { visibility: hidden; }
footer { display: none; }
[data-testid="stHeader"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* === Dark Sidebar === */
[data-testid="stSidebar"] {
    background-color: #171717 !important;
    border-right: 1px solid #2a2a2a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] div { color: #d1d5db !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f9fafb !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] hr { border-color: #2a2a2a !important; margin: 0.75rem 0 !important; }

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #d1d5db !important;
    border: 1px solid #2e2e2e !important;
    border-radius: 8px !important;
    text-align: left;
    padding: 7px 12px;
    font-size: 0.875rem;
    width: 100%;
    box-shadow: none !important;
    transition: background 0.15s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #2a2a2a !important;
    border-color: #3a3a3a !important;
    color: #f9fafb !important;
    transform: none !important;
}

/* Sidebar selectbox */
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1f1f1f !important;
    border-color: #2e2e2e !important;
    color: #d1d5db !important;
    border-radius: 8px;
}

/* Sidebar page links */
[data-testid="stSidebar"] a {
    color: #9ca3af !important;
    text-decoration: none;
    font-size: 0.875rem;
    display: block;
    padding: 3px 2px;
    transition: color 0.15s;
}
[data-testid="stSidebar"] a:hover { color: #f9fafb !important; }

/* Caption */
[data-testid="stSidebar"] .stCaption { color: #6b7280 !important; font-size: 0.75rem !important; }
[data-testid="stSidebar"] .stSuccess { background: #14532d22 !important; border-color: #166534 !important; }
[data-testid="stSidebar"] .stWarning { background: #92400e22 !important; border-color: #78350f !important; }

/* === Main Content === */
.main { background: #fafafa; }
.main .block-container {
    max-width: 960px;
    padding: 1.5rem 2rem 4rem;
}

/* === Typography === */
h1 { font-size: 1.6rem !important; font-weight: 700 !important; color: #111827 !important; }
h2 { font-size: 1.25rem !important; font-weight: 600 !important; color: #1f2937 !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #374151 !important; }

/* === Buttons (main area) === */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.875rem;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    color: #374151;
    padding: 8px 16px;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.stButton > button:hover {
    border-color: #a5b4fc;
    color: #4f46e5;
    background: #eef2ff;
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}
.stButton > button[kind="primary"] {
    background: #4f46e5 !important;
    color: #ffffff !important;
    border-color: #4f46e5 !important;
    box-shadow: 0 3px 8px rgba(79,70,229,0.3);
}
.stButton > button[kind="primary"]:hover {
    background: #4338ca !important;
    border-color: #4338ca !important;
    box-shadow: 0 6px 16px rgba(79,70,229,0.4);
    transform: translateY(-1px);
}

/* === Containers (Cards) === */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border-color: #e5e7eb !important;
    background: #ffffff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    padding: 1.25rem !important;
}

/* === Metric === */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] { color: #6b7280; font-size: 0.8rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #111827; font-size: 1.6rem; font-weight: 800; }

/* === Tabs === */
[data-testid="stTabs"] [data-testid="stTab"] {
    font-size: 0.875rem;
    font-weight: 500;
    color: #6b7280;
    border-radius: 6px 6px 0 0;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #4f46e5 !important;
    border-bottom-color: #4f46e5 !important;
}

/* === Info / Success / Warning / Error === */
[data-testid="stAlert"] { border-radius: 10px; font-size: 0.875rem; }

/* === Form inputs === */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    border-radius: 8px;
    border-color: #d1d5db;
    font-size: 0.9rem;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #818cf8;
    box-shadow: 0 0 0 3px rgba(129,140,248,0.15);
}

/* === File uploader === */
[data-testid="stFileUploader"] {
    border: 2px dashed #e5e7eb;
    border-radius: 10px;
    background: #f9fafb;
    padding: 1rem;
}

/* === Divider === */
hr { border-color: #f0f0f0 !important; margin: 1rem 0 !important; }

/* === Expander === */
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    background: #ffffff;
}
[data-testid="stExpanderToggleIcon"] { color: #6b7280; }

/* === Page Nav (chapter steps) === */
.chapter-nav { display: flex; gap: 4px; overflow-x: auto; padding: 6px 4px; scrollbar-width: thin; }
.chapter-step.active { background: #eef2ff; box-shadow: 0 0 0 2px #4f46e5; }
.step-circle.active { border-color: #4f46e5; background: #4f46e5; }

/* === Status badges === */
.status-badge-lg {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: #f1f5f9;
    color: #475569;
}
.status-badge-lg.active { background: #dcfce7; color: #166534; }
</style>
"""


def load_custom_css() -> None:
    """既存ページから呼ぶ CSS ローダー。"""
    st.markdown(_CSS, unsafe_allow_html=True)
