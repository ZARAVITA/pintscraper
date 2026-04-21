"""
Pinterest Niche Scraper — Streamlit App
========================================
Run with:
    streamlit run app.py
"""

import logging
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure local modules are importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from scraper.pinterest_scraper import scrape_sync
from utils.export import dataframe_to_excel_bytes, safe_filename
from utils.scoring import apply_scores
from utils.export import pins_to_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Pinterest Niche Scraper",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Pinterest-inspired, clean and professional
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&family=DM+Serif+Display&display=swap');

    :root {
        --pinterest-red: #E60023;
        --pinterest-dark: #111111;
        --pinterest-gray: #767676;
        --pinterest-light: #F9F9F9;
        --card-radius: 16px;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* Hide default Streamlit header */
    header[data-testid="stHeader"] { display: none; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--pinterest-dark);
        border-right: none;
    }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stSlider > div > div > div { background: var(--pinterest-red) !important; }

    /* Main content */
    .main .block-container { padding-top: 2rem; max-width: 1400px; }

    /* Hero header */
    .hero-title {
        font-family: 'DM Serif Display', serif;
        font-size: 3rem;
        color: var(--pinterest-dark);
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }
    .hero-subtitle {
        color: var(--pinterest-gray);
        font-size: 1.1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }
    .pin-accent {
        color: var(--pinterest-red);
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #EBEBEB;
        border-radius: var(--card-radius);
        padding: 1.25rem 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--pinterest-red);
        line-height: 1;
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--pinterest-gray);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.25rem;
    }

    /* Status messages */
    .status-box {
        background: #FFF5F5;
        border-left: 4px solid var(--pinterest-red);
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        color: var(--pinterest-dark);
    }

    /* Buttons */
    .stButton > button {
        background: var(--pinterest-red) !important;
        color: white !important;
        border: none !important;
        border-radius: 24px !important;
        padding: 0.6rem 2rem !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
        transition: opacity 0.15s ease !important;
        width: 100%;
    }
    .stButton > button:hover { opacity: 0.88 !important; }

    /* Download button */
    .stDownloadButton > button {
        background: var(--pinterest-dark) !important;
        color: white !important;
        border: none !important;
        border-radius: 24px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 500 !important;
        width: 100%;
    }

    /* DataFrame */
    .stDataFrame { border-radius: var(--card-radius); overflow: hidden; }

    /* Pin image previews */
    .pin-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 1rem; }
    .pin-card {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        width: 180px;
        flex-shrink: 0;
        transition: transform 0.2s ease;
    }
    .pin-card:hover { transform: scale(1.03); }
    .pin-card img { width: 100%; height: 220px; object-fit: cover; display: block; }
    .pin-card-info { padding: 8px 10px; }
    .pin-card-title { font-size: 0.78rem; font-weight: 500; color: #111; line-height: 1.3; max-height: 2.6em; overflow: hidden; }
    .pin-card-score { font-size: 0.7rem; color: var(--pinterest-red); margin-top: 4px; font-weight: 700; }

    /* Progress */
    .stProgress > div > div > div { background: var(--pinterest-red) !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 24px !important;
        padding: 0.4rem 1.2rem !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--pinterest-red) !important;
        color: white !important;
    }

    /* Input */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border-color: #EBEBEB !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    
    
    /* Fix input text color in sidebar */
    section[data-testid="stSidebar"] .stTextInput input {
    color: black !important;   /* ou blue */
    background-color: white !important;
    }
    
    /* Placeholder */
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: #767676 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


#Ajout---------fin------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "results_df" not in st.session_state:
    st.session_state.results_df = pd.DataFrame()
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = ""
if "scraping" not in st.session_state:
    st.session_state.scraping = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📌 Pinterest Scraper")
    keyword = st.text_input(
        "🔍 Keyword / Niche",
        placeholder="e.g. fitness motivation",
        help="The niche or topic to search on Pinterest.",
    )

    max_pins = st.slider(
        "📊 Number of Pins",
        min_value=10,
        max_value=200,
        value=40,
        step=1,
        help="Target number of pins to scrape. More pins = longer scrape time.",
    )
    #st.markdown("---")
    st.markdown("**⚙️ Options**")

    headless = st.checkbox("Headless browser", value=True, help="Run browser invisibly (recommended).")
    scroll_pause = st.slider(
        "Scroll pause (ms)",
        min_value=1000,
        max_value=5000,
        value=2000,
        step=100,
        help="Delay between scrolls. Increase if you get fewer results than expected.",
    )

    #st.markdown("---")
    start_btn = st.button("🚀 Start Scraping", disabled=st.session_state.scraping)

    #st.markdown("---")
    st.markdown(
        "<small style='color:#888'>Built with Playwright + Streamlit.<br>Respect Pinterest's ToS.</small>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main area — Hero header
# ---------------------------------------------------------------------------

st.markdown(
    '<h1 class="hero-title">Pinterest <span class="pin-accent">Niche</span> Scraper</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-subtitle">Find high-performing pins in any niche — extract, score, and export for AI content creation.</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Scraping logic
# ---------------------------------------------------------------------------

if start_btn and keyword.strip():
    st.session_state.scraping = True
    st.session_state.results_df = pd.DataFrame()

    keyword_clean = keyword.strip()
    st.session_state.last_keyword = keyword_clean

    st.markdown("---")
    st.markdown(f"### 🔄 Scraping **{keyword_clean}** — target {max_pins} pins…")

    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    pins_collected = [0]

    def progress_callback(current, total):
        pins_collected[0] = current
        pct = min(int((current / total) * 100), 100)
        progress_bar.progress(pct)
        status_placeholder.markdown(
            f'<div class="status-box">📌 Collected <b>{current}</b> / <b>{total}</b> pins…</div>',
            unsafe_allow_html=True,
        )

    try:
        with st.spinner("Launching browser and loading Pinterest…"):
            # Run the scraper (sync wrapper around async Playwright)
            from scraper.pinterest_scraper import PinterestScraper
            import asyncio

            async def _run():
                scraper = PinterestScraper(
                    headless=headless,
                    scroll_pause_ms=scroll_pause,
                )
                return await scraper.scrape(
                    keyword=keyword_clean,
                    max_pins=max_pins,
                    progress_callback=progress_callback,
                )

            pins = asyncio.run(_run())

        if not pins:
            st.warning(
                "⚠️ No pins were found. Pinterest may have blocked the request, "
                "shown a login wall, or the keyword returned no results. "
                "Try disabling headless mode or increasing scroll pause."
            )
        else:
            # Apply scoring
            apply_scores(pins)

            # Convert to DataFrame
            df = pins_to_dataframe(pins)
            st.session_state.results_df = df

            progress_bar.progress(100)
            status_placeholder.markdown(
                f'<div class="status-box">✅ Done! Collected <b>{len(df)}</b> unique pins.</div>',
                unsafe_allow_html=True,
            )

    except Exception as exc:
        st.error(f"❌ Scraping failed: {exc}")
        logger.exception("Scraping error")
    finally:
        st.session_state.scraping = False

elif start_btn and not keyword.strip():
    st.warning("Please enter a keyword before scraping.")

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

df = st.session_state.results_df

if not df.empty:
    keyword_display = st.session_state.last_keyword

    st.markdown("---")

    # --- KPI Cards ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{len(df)}</div>'
            f'<div class="metric-label">Pins Collected</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        top_score = df["score"].max() if "score" in df.columns else 0
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{top_score:.4f}</div>'
            f'<div class="metric-label">Top Score</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        has_desc = df["description"].str.strip().ne("").sum() if "description" in df.columns else 0
        pct = int(has_desc / len(df) * 100) if len(df) else 0
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{pct}%</div>'
            f'<div class="metric-label">With Description</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        has_img = df["image_url"].str.strip().ne("").sum() if "image_url" in df.columns else 0
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{has_img}</div>'
            f'<div class="metric-label">With Image URL</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📋 Data Table", "🖼️ Pin Gallery", "📈 Score Chart"])

    with tab1:
        st.markdown(f"#### Results for **{keyword_display}** (sorted by score ↓)")

        # Clickable URLs — render pin_url as markdown link
        display_df = df.copy()
        display_df["pin_url"] = display_df["pin_url"].apply(
            lambda u: f"[Open Pin]({u})" if u else ""
        )
        display_df["image_url"] = display_df["image_url"].apply(
            lambda u: f"[Image]({u})" if u else ""
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            column_config={
                "score": st.column_config.NumberColumn("Score", format="%.5f"),
                "position": st.column_config.NumberColumn("Pos.", format="%d"),
                "pin_url": st.column_config.LinkColumn("Pin URL"),
                "image_url": st.column_config.LinkColumn("Image URL"),
            },
        )

    with tab2:
        st.markdown("#### Top Pins Preview")
        preview_df = df[df["image_url"].str.strip() != ""].head(30)

        if preview_df.empty:
            st.info("No image URLs found to preview.")
        else:
            # Render as HTML grid for tight masonry-like layout
            cards_html = '<div class="pin-grid">'
            for _, row in preview_df.iterrows():
                title = (row.get("title") or "")[:60]
                score = row.get("score", 0)
                img = row.get("image_url", "")
                url = row.get("pin_url", "#")
                cards_html += (
                    f'<a href="{url}" target="_blank" style="text-decoration:none">'
                    f'<div class="pin-card">'
                    f'<img src="{img}" onerror="this.style.display=\'none\'" />'
                    f'<div class="pin-card-info">'
                    f'<div class="pin-card-title">{title}</div>'
                    f'<div class="pin-card-score">Score: {score:.5f}</div>'
                    f"</div></div></a>"
                )
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)

    with tab3:
        st.markdown("#### Score Distribution")
        if "score" in df.columns and "position" in df.columns:
            chart_df = df[["position", "score"]].set_index("position")
            st.line_chart(chart_df, use_container_width=True)
            st.caption(
                "Score drops as position increases. Repeated pins (same image) "
                "receive a bonus, causing occasional spikes."
            )

    # --- Export ---
    st.markdown("---")
    st.markdown("### 💾 Export Results")

    excel_bytes = dataframe_to_excel_bytes(df, keyword_display)
    filename = safe_filename(keyword_display)

    col_a, col_b = st.columns([2, 3])
    with col_a:
        st.download_button(
            label=f"⬇️ Download Excel — {filename}",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_b:
        st.markdown(
            f"<small style='color:#999'>Contains {len(df)} pins · "
            f"Columns: keyword, position, score, title, description, pin_url, image_url</small>",
            unsafe_allow_html=True,
        )

else:
    # Empty state
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 2rem; color: #AAAAAA;">
            <div style="font-size:4rem; margin-bottom:1rem;">📌</div>
            <div style="font-size:1.2rem; font-weight:500; color:#333;">Ready to scrape</div>
            <div style="margin-top:0.5rem; font-size:0.95rem;">
                Enter a keyword in the sidebar and click <b>Start Scraping</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top:4rem; padding-top:1rem; border-top:1px solid #EBEBEB;
                text-align:center; color:#BBBBBB; font-size:0.8rem;">
        Pinterest Niche Scraper · Built with Playwright + Streamlit + Pandas
        · For educational & research use only.
    </div>
    """,
    unsafe_allow_html=True,
)