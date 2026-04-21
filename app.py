"""
PintScraper — Premium SaaS UI v3.0
Stripe / Linear / Vercel aesthetic.
Centered search hero, Enter key trigger, refined sidebar.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import nest_asyncio
nest_asyncio.apply()

import logging
import traceback
from datetime import datetime
from pathlib import Path
import base64

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from scraper.pinterest_scraper import PinterestScraper, CHROMIUM_PATH
from utils.export import dataframe_to_excel_bytes, safe_filename, pins_to_dataframe
from utils.scoring import apply_scores

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PintScraper",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%23E60023'/><circle cx='16' cy='13' r='5' fill='white'/><path d='M13 17.5c0 3 1 7 3 7s3-4 3-7' stroke='white' stroke-width='1.5' fill='none' stroke-linecap='round'/></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — Premium Design System
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   DESIGN TOKENS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
:root {
  /* Brand */
  --brand:        #E60023;
  --brand-dark:   #C0001E;

  /* Action (indigo — not red, avoids overuse) */
  --action:       #4F46E5;
  --action-hover: #4338CA;
  --action-light: #EEF2FF;

  /* Sidebar */
  --sb-bg:        #0F1117;
  --sb-surface:   #161B27;
  --sb-border:    #1E2535;
  --sb-text:      #94A3B8;
  --sb-text-hi:   #E2E8F0;
  --sb-muted:     #475569;
  --sb-accent:    #6366F1;

  /* App surface */
  --bg:           #F8F9FB;
  --surface:      #FFFFFF;
  --border:       #E2E8F0;
  --border-hi:    #CBD5E1;

  /* Text */
  --t1:           #0F172A;
  --t2:           #475569;
  --t3:           #94A3B8;

  /* Misc */
  --radius-sm:    6px;
  --radius:       10px;
  --radius-lg:    16px;
  --radius-xl:    24px;
  --shadow-sm:    0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow:       0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.04);
  --shadow-lg:    0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06);
  --mono:         'JetBrains Mono', monospace;
  --sans:         'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --transition:   all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   RESET & BASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
html, body, [class*="css"] {
  font-family: var(--sans) !important;
  background: var(--bg) !important;
  -webkit-font-smoothing: antialiased;
}
header[data-testid="stHeader"], footer, #MainMenu { display: none !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
.main { background: var(--bg) !important; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SIDEBAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
section[data-testid="stSidebar"] {
  background: var(--sb-bg) !important;
  border-right: 1px solid var(--sb-border) !important;
  min-width: 232px !important;
  max-width: 248px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }
section[data-testid="stSidebar"] * { color: var(--sb-text) !important; }

/* Sidebar — slider track (filled) */
section[data-testid="stSidebar"] .stSlider > div > div > div {
  background: var(--sb-accent) !important;
  height: 4px !important;
  border-radius: 4px !important;
}
/* Slider track (unfilled) */
section[data-testid="stSidebar"] .stSlider > div > div {
  height: 4px !important;
  border-radius: 4px !important;
  background: var(--sb-border) !important;
}
/* Slider thumb */
section[data-testid="stSidebar"] .stSlider > div > div > div > div {
  background: #FFFFFF !important;
  border: 2px solid var(--sb-accent) !important;
  width: 16px !important;
  height: 16px !important;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4) !important;
}
/* Hide ugly blue min/max boxes */
section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"],
section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] {
  display: none !important;
}
/* Slider current value */
section[data-testid="stSidebar"] .stSlider [data-testid="stSliderThumbValue"] {
  color: var(--sb-text-hi) !important;
  font-size: 12px !important;
  font-family: var(--mono) !important;
  background: var(--sb-surface) !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
}
/* Labels */
section[data-testid="stSidebar"] label {
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--sb-muted) !important;
}
/* Checkbox */
section[data-testid="stSidebar"] .stCheckbox label {
  font-size: 13px !important;
  font-weight: 400 !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  color: var(--sb-text) !important;
}
section[data-testid="stSidebar"] .stCheckbox [data-testid="stCheckbox"] {
  border-color: var(--sb-border) !important;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SEARCH HERO — main input + button
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
/* Hide label */
.hero-search .stTextInput label { display: none !important; }

/* Input field */
.hero-search .stTextInput input {
  height: 52px !important;
  font-size: 15px !important;
  font-family: var(--sans) !important;
  font-weight: 400 !important;
  color: var(--t1) !important;
  background: var(--surface) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 0 20px 0 48px !important;
  box-shadow: var(--shadow-sm) !important;
  transition: var(--transition) !important;
}
.hero-search .stTextInput input:focus {
  border-color: var(--action) !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.12), var(--shadow-sm) !important;
  outline: none !important;
}
.hero-search .stTextInput input::placeholder {
  color: var(--t3) !important;
  font-weight: 400 !important;
}

/* Run button */
.hero-search .stButton > button {
  height: 52px !important;
  padding: 0 28px !important;
  background: var(--action) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: var(--radius-lg) !important;
  font-family: var(--sans) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em !important;
  box-shadow: 0 2px 8px rgba(79,70,229,0.35) !important;
  transition: var(--transition) !important;
  white-space: nowrap !important;
  cursor: pointer !important;
}
.hero-search .stButton > button:hover {
  background: var(--action-hover) !important;
  box-shadow: 0 4px 16px rgba(79,70,229,0.45) !important;
  transform: translateY(-1px) !important;
}
.hero-search .stButton > button:active {
  transform: translateY(0) !important;
}
.hero-search .stButton > button:disabled {
  background: var(--border-hi) !important;
  color: var(--t3) !important;
  box-shadow: none !important;
  transform: none !important;
  cursor: not-allowed !important;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   TABS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  gap: 2px !important;
  border-bottom: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  padding: 10px 20px !important;
  font-family: var(--sans) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--t3) !important;
  transition: var(--transition) !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--t2) !important; }
.stTabs [aria-selected="true"] {
  color: var(--t1) !important;
  font-weight: 600 !important;
  border-bottom-color: var(--action) !important;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PROGRESS BAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--action), #818CF8) !important;
  border-radius: 4px !important;
}
.stProgress > div > div {
  background: var(--border) !important;
  border-radius: 4px !important;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   DATAFRAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
.stDataFrame {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  overflow: hidden !important;
  box-shadow: var(--shadow-sm) !important;
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

/* Topbar */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  height: 56px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.topbar-title { font-size: 14px; font-weight: 600; color: var(--t1); }
.topbar-sub   { font-size: 12px; color: var(--t3); margin-top: 1px; }

/* Status badge */
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px; font-weight: 500; letter-spacing: 0.01em;
}
.badge-idle    { background: #F1F5F9; color: #64748B; }
.badge-running { background: #FFF7ED; color: #C2410C; }
.badge-done    { background: #F0FDF4; color: #15803D; }
.dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.dot-idle    { background: #CBD5E1; }
.dot-running { background: #F97316; animation: pulse 1.4s ease-in-out infinite; }
.dot-done    { background: #22C55E; }
@keyframes pulse {
  0%,100% { opacity:1; transform:scale(1); }
  50%      { opacity:0.5; transform:scale(0.75); }
}

/* Hero search area */
.hero-wrap {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 28px 32px 20px;
}
.hero-label {
  font-size: 11px; font-weight: 600; color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.08em;
  margin-bottom: 10px;
}
.search-hint {
  font-size: 12px; color: var(--t3);
  margin-top: 8px;
  display: flex; align-items: center; gap: 16px;
}
.hint-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 11px; font-weight: 500; color: var(--t2);
  transition: var(--transition);
  cursor: default;
}
.hint-chip:hover { border-color: var(--border-hi); color: var(--t1); }

/* Search icon overlay */
.search-icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--t3);
  pointer-events: none;
  z-index: 10;
}

/* KPI cards */
.kpi-row { display: flex; gap: 12px; margin: 0 0 20px; }
.kpi-card {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  box-shadow: var(--shadow-sm);
  transition: var(--transition);
}
.kpi-card:hover { box-shadow: var(--shadow); border-color: var(--border-hi); }
.kpi-value { font-size: 22px; font-weight: 700; color: var(--t1); line-height: 1; font-family: var(--mono); }
.kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--t3); margin-top: 6px; }
.kpi-sub   { font-size: 11px; color: var(--t3); margin-top: 3px; }

/* Content */
.content { padding: 24px 32px; }

/* Progress box */
.progress-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 24px 16px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
}
.progress-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.progress-kw   { font-size: 14px; font-weight: 600; color: var(--t1); }
.progress-ct   { font-size: 13px; color: var(--t3); font-family: var(--mono); }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 72px 40px; text-align: center;
}
.empty-icon-wrap {
  width: 72px; height: 72px;
  background: var(--action-light);
  border-radius: var(--radius-xl);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 20px;
}
.empty-title { font-size: 16px; font-weight: 600; color: var(--t1); margin-bottom: 8px; }
.empty-sub   { font-size: 14px; color: var(--t3); max-width: 320px; line-height: 1.6; }

/* Gallery */
.gallery-grid { display: flex; flex-wrap: wrap; gap: 12px; padding: 4px 0 16px; }
.pin-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  width: 168px; flex-shrink: 0;
  transition: var(--transition);
  text-decoration: none;
  box-shadow: var(--shadow-sm);
}
.pin-card:hover { border-color: var(--border-hi); box-shadow: var(--shadow); transform: translateY(-2px); }
.pin-card img { width: 100%; height: 196px; object-fit: cover; display: block; }
.pin-card-body { padding: 10px 12px; }
.pin-card-title { font-size: 12px; color: var(--t1); font-weight: 500; line-height: 1.4; max-height: 2.8em; overflow: hidden; }
.pin-card-score { font-size: 11px; color: var(--t3); margin-top: 4px; font-family: var(--mono); }

/* Export card */
.export-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 22px;
  margin-top: 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  box-shadow: var(--shadow-sm);
}
.export-left { flex: 1; }
.export-title { font-size: 13px; font-weight: 600; color: var(--t1); }
.export-meta  { font-size: 12px; color: var(--t3); margin-top: 3px; }
.export-cols  { font-size: 11px; color: var(--t3); margin-top: 5px; font-family: var(--mono); }
.export-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 16px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--t1);
  text-decoration: none; white-space: nowrap;
  transition: var(--transition); flex-shrink: 0;
}
.export-btn:hover { border-color: var(--border-hi); box-shadow: var(--shadow-sm); color: var(--t1); }

/* Chart */
.chart-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--t3); margin-bottom: 12px; }

/* Sidebar custom styles */
.sb-logo {
  padding: 22px 18px 18px;
  border-bottom: 1px solid var(--sb-border);
}
.sb-logo-name {
  font-size: 14px; font-weight: 700; color: var(--sb-text-hi);
  letter-spacing: -0.01em;
  display: flex; align-items: center; gap: 8px;
}
.sb-brand-dot {
  width: 8px; height: 8px;
  background: var(--brand);
  border-radius: 3px; flex-shrink: 0;
}
.sb-tagline { font-size: 11px; color: var(--sb-muted); margin-top: 4px; }

.sb-section { padding: 18px 18px; border-bottom: 1px solid var(--sb-border); }
.sb-section-title {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--sb-muted); margin-bottom: 14px;
  display: flex; align-items: center; gap: 6px;
}

.sb-footer {
  padding: 16px 18px;
  position: absolute; bottom: 0; width: 100%; box-sizing: border-box;
}
.sb-version { font-size: 11px; color: var(--sb-border); font-family: var(--mono); }

/* Divider */
.divider { height: 1px; background: var(--border); margin: 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

for k, v in [
    ("results_df",   pd.DataFrame()),
    ("last_keyword", ""),
    ("scraping",     False),
    ("status",       "idle"),
    ("export_ts",    ""),
    ("trigger_run",  False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar — options only
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
      <div class="sb-logo-name">
        <span class="sb-brand-dot"></span>PintScraper
      </div>
      <div class="sb-tagline">Pinterest intelligence, simplified.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section"><div class="sb-section-title">Collection</div>', unsafe_allow_html=True)
    max_pins = st.slider("Pins to collect", 10, 200, 40, 1)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section"><div class="sb-section-title">Advanced</div>', unsafe_allow_html=True)
    headless     = st.checkbox("Headless mode", value=True)
    scroll_pause = st.slider("Scroll delay (ms)", 1000, 5000, 2500, 100)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="sb-footer">
      <div class="sb-version">v1.0.0</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Topbar
# ---------------------------------------------------------------------------

status     = st.session_state.status
kw_display = st.session_state.last_keyword
n_results  = len(st.session_state.results_df)

badge_map = {
    "idle":    ("badge-idle",    "dot-idle",    "Idle"),
    "running": ("badge-running", "dot-running", "Running"),
    "done":    ("badge-done",    "dot-done",    "Done"),
}
bc, dc, bt = badge_map.get(status, badge_map["idle"])

sub_map = {
    "idle":    "Enter a keyword below to discover trending pins.",
    "running": f"Collecting from Pinterest — '{kw_display}'",
    "done":    f"{n_results} pins collected · {st.session_state.export_ts}",
}

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="topbar-title">Dashboard</div>
    <div class="topbar-sub">{sub_map.get(status, '')}</div>
  </div>
  <div class="badge {bc}">
    <span class="dot {dc}"></span>{bt}
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero Search Strip
# ---------------------------------------------------------------------------

st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
st.markdown('<div class="hero-label">Keyword / Niche</div>', unsafe_allow_html=True)

# Search icon SVG overlay (positioned via JS because Streamlit doesn't allow overlay)
st.markdown("""
<style>
/* Inject search icon inside the input via CSS pseudo trick using a sibling wrapper */
.hero-search { position: relative; }
.hero-search::before {
  content: '';
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px; height: 18px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='8' stroke='%2394A3B8' stroke-width='2'/%3E%3Cpath d='m21 21-4.35-4.35' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
  background-size: contain;
  background-repeat: no-repeat;
  pointer-events: none;
  z-index: 9999;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-search">', unsafe_allow_html=True)

col_in, col_btn = st.columns([5, 1])
with col_in:
    keyword = st.text_input(
        "search",
        placeholder="Find trending Pinterest ideas...",
        label_visibility="collapsed",
        key="kw_input",
    )
with col_btn:
    is_scraping = st.session_state.scraping
    btn_label   = "Scraping..." if is_scraping else "Run scrape"
    start_btn   = st.button(
        btn_label,
        disabled=is_scraping,
        use_container_width=True,
        key="run_btn",
    )

st.markdown('</div>', unsafe_allow_html=True)  # hero-search

# Hint chips below search
st.markdown("""
<div class="search-hint">
  Try:
  <span class="hint-chip">fitness motivation</span>
  <span class="hint-chip">home decor 2025</span>
  <span class="hint-chip">ebook kids</span>
  <span class="hint-chip">vegan recipes</span>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # hero-wrap

# Enter key trigger via JS
st.markdown("""
<script>
(function() {
  function attachEnter() {
    const inputs = window.parent.document.querySelectorAll('input[data-testid="stTextInputRootElement"] input, .hero-search input');
    inputs.forEach(input => {
      if (input._pintEnterBound) return;
      input._pintEnterBound = true;
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          const btns = window.parent.document.querySelectorAll('button[kind="secondary"], button[data-testid="baseButton-secondary"]');
          const runBtn = Array.from(window.parent.document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Run scrape');
          if (runBtn && !runBtn.disabled) runBtn.click();
        }
      });
    });
  }
  // Try immediately and after delay
  attachEnter();
  setTimeout(attachEnter, 800);
  setTimeout(attachEnter, 2000);
  // Also observe DOM changes
  const obs = new MutationObserver(attachEnter);
  obs.observe(window.parent.document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

st.markdown('<div class="content">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Trigger scrape
# ---------------------------------------------------------------------------

if (start_btn or st.session_state.trigger_run) and keyword.strip():
    st.session_state.trigger_run   = False
    st.session_state.scraping      = True
    st.session_state.status        = "running"
    st.session_state.results_df    = pd.DataFrame()
    st.session_state.last_keyword  = keyword.strip()
    st.rerun()

elif start_btn and not keyword.strip():
    st.warning("Please enter a keyword to scrape.")

# ---------------------------------------------------------------------------
# Running state
# ---------------------------------------------------------------------------

if st.session_state.scraping and st.session_state.last_keyword:
    keyword_clean = st.session_state.last_keyword

    pin_count_ph = st.empty()
    progress_bar = st.progress(0)
    status_ph    = st.empty()

    pin_count_ph.markdown(f"""
    <div class="progress-box">
      <div class="progress-head">
        <div class="progress-kw">{keyword_clean}</div>
        <div class="progress-ct" id="pcount">0 / {max_pins}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    def on_progress(current, total):
        pct = min(int(current / total * 100), 100)
        progress_bar.progress(pct)
        status_ph.markdown(
            f'<div style="font-size:12px;color:var(--t3);font-family:var(--mono);margin-top:6px;">'
            f'{current} / {total} pins collected</div>',
            unsafe_allow_html=True,
        )

    try:
        async def _run():
            scraper = PinterestScraper(headless=headless, scroll_pause_ms=scroll_pause)
            return await scraper.scrape(
                keyword=keyword_clean,
                max_pins=max_pins,
                progress_callback=on_progress,
            )

        loop = asyncio.get_event_loop()
        pins = loop.run_until_complete(_run())

        if not pins:
            st.warning("No pins found. Try disabling headless mode or increasing scroll delay.")
            st.session_state.status = "idle"
        else:
            apply_scores(pins)
            df = pins_to_dataframe(pins)
            st.session_state.results_df = df
            st.session_state.status     = "done"
            st.session_state.export_ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
            progress_bar.progress(100)

    except BaseException:
        tb  = traceback.format_exc()
        msg = [l for l in tb.strip().splitlines() if l.strip()]
        st.error(f"Scraping failed: {msg[-1] if msg else 'unknown error'}")
        with st.expander("Error details"):
            st.code(tb, language="python")
        st.session_state.status = "idle"

    finally:
        st.session_state.scraping = False
        st.rerun()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

df = st.session_state.results_df

if not df.empty:
    n_pins    = len(df)
    top_score = df["score"].max() if "score" in df.columns else 0
    pct_desc  = int(df["description"].str.strip().ne("").sum() / n_pins * 100) if n_pins else 0
    pct_img   = int(df["image_url"].str.strip().ne("").sum()  / n_pins * 100) if n_pins else 0
    kw        = st.session_state.last_keyword

    # KPI row
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-value">{n_pins}</div>
        <div class="kpi-label">Pins collected</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{top_score:.4f}</div>
        <div class="kpi-label">Top score</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{pct_desc}%</div>
        <div class="kpi-label">With description</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{pct_img}%</div>
        <div class="kpi-label">With image URL</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Table", "Gallery", "Chart"])

    with tab1:
        display_df = df.copy().reset_index(drop=True)
        display_df.insert(0, "rank", range(1, len(display_df) + 1))
        display_df["pin_url"]   = display_df["pin_url"].apply(lambda u: u if u else "")
        display_df["image_url"] = display_df["image_url"].apply(lambda u: u if u else "")
        st.dataframe(
            display_df,
            use_container_width=True,
            height=460,
            column_config={
                "rank":      st.column_config.NumberColumn("Rank",     format="%d",     width="small"),
                "score":     st.column_config.NumberColumn("Score",    format="%.5f"),
                "position":  st.column_config.NumberColumn("Pos.",     format="%d",     width="small"),
                "pin_url":   st.column_config.LinkColumn("Pin URL",    display_text="Open"),
                "image_url": st.column_config.LinkColumn("Image URL",  display_text="View"),
                "keyword":   st.column_config.TextColumn("Keyword",    width="small"),
            },
        )

    with tab2:
        preview = df[df["image_url"].str.strip() != ""].head(36)
        if preview.empty:
            st.info("No images available for this result set.")
        else:
            html = '<div class="gallery-grid">'
            for _, r in preview.iterrows():
                title = str(r.get("title", ""))[:70]
                score = r.get("score", 0)
                img   = r.get("image_url", "")
                url   = r.get("pin_url", "#")
                html += (
                    f'<a href="{url}" target="_blank" class="pin-card">'
                    f'<img src="{img}" onerror="this.style.display=\'none\'"/>'
                    f'<div class="pin-card-body">'
                    f'<div class="pin-card-title">{title}</div>'
                    f'<div class="pin-card-score">{score:.5f}</div>'
                    f'</div></a>'
                )
            st.markdown(html + '</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="chart-label">Score by position</div>', unsafe_allow_html=True)
        if "score" in df.columns and "position" in df.columns:
            st.line_chart(
                df[["position", "score"]].set_index("position"),
                use_container_width=True,
                color="#4F46E5",
            )

    # Export
    excel_data = dataframe_to_excel_bytes(df, kw)
    filename   = safe_filename(kw)
    ts         = st.session_state.export_ts
    b64        = base64.b64encode(excel_data).decode()

    st.markdown(f"""
    <div class="export-card">
      <div class="export-left">
        <div class="export-title">Export data</div>
        <div class="export-meta">{n_pins} rows &nbsp;&middot;&nbsp; {ts}</div>
        <div class="export-cols">keyword · position · score · title · description · pin_url · image_url</div>
      </div>
      <a class="export-btn"
         href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"
         download="{filename}">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1v8M4 6l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 11h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        Download Excel
      </a>
    </div>
    """, unsafe_allow_html=True)

else:
    # Empty state
    if st.session_state.status != "running":
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon-wrap">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="14" cy="14" r="8" stroke="#4F46E5" stroke-width="2.5" fill="none"/>
              <path d="M20 20L27 27" stroke="#4F46E5" stroke-width="2.5" stroke-linecap="round"/>
              <path d="M14 10v8M10 14h8" stroke="#4F46E5" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="empty-title">Start your first scrape</div>
          <div class="empty-sub">Enter a keyword above to discover trending Pinterest content, ranked by performance.</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # content