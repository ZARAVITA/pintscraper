"""
Pinterest Niche Scraper — Streamlit App v5
==========================================
Fix v5 — Windows ProactorEventLoop :
    Sur Windows, asyncio utilise SelectorEventLoop par défaut,
    qui ne supporte pas les sous-processus (Playwright en a besoin).
    Solution : forcer ProactorEventLoop sur Windows, AVANT tout import async.
"""

import asyncio
import sys

# ─── FIX WINDOWS ────────────────────────────────────────────────────────────
# Doit être fait AVANT nest_asyncio et AVANT tout import Playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ────────────────────────────────────────────────────────────────────────────

import nest_asyncio
nest_asyncio.apply()

import logging
import traceback
from pathlib import Path

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
    page_title="Pinterest Niche Scraper",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700&family=DM+Serif+Display&display=swap');
:root { --red: #E60023; --dark: #111; --gray: #767676; --radius: 16px; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
header[data-testid="stHeader"] { display: none; }
section[data-testid="stSidebar"] { background: var(--dark); }
section[data-testid="stSidebar"] * { color: #fff !important; }
section[data-testid="stSidebar"] .stTextInput input { color: #000 !important; background: #fff !important; }
section[data-testid="stSidebar"] .stTextInput input::placeholder { color: #767676 !important; }
.main .block-container { padding-top: 2rem; max-width: 1400px; }
.hero-title { font-family: 'DM Serif Display', serif; font-size: 3rem; color: var(--dark); line-height: 1.1; }
.hero-sub { color: var(--gray); font-size: 1.1rem; font-weight: 300; margin-bottom: 2rem; }
.pin-accent { color: var(--red); }
.metric-card { background: #fff; border: 1px solid #ebebeb; border-radius: var(--radius); padding: 1.25rem 1.5rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.metric-value { font-size: 2rem; font-weight: 700; color: var(--red); line-height: 1; }
.metric-label { font-size: .8rem; color: var(--gray); text-transform: uppercase; letter-spacing: .08em; margin-top: .25rem; }
.status-box { background: #fff5f5; border-left: 4px solid var(--red); border-radius: 0 8px 8px 0; padding: .75rem 1rem; margin: .5rem 0; font-size: .9rem; }
.stButton > button { background: var(--red) !important; color: #fff !important; border: none !important; border-radius: 24px !important; padding: .6rem 2rem !important; font-weight: 500 !important; font-size: 1rem !important; width: 100%; transition: opacity .15s; }
.stButton > button:hover { opacity: .88 !important; }
.stDownloadButton > button { background: var(--dark) !important; color: #fff !important; border: none !important; border-radius: 24px !important; padding: .6rem 2rem !important; font-weight: 500 !important; width: 100%; }
.stProgress > div > div > div { background: var(--red) !important; }
.stTabs [data-baseweb="tab"] { border-radius: 24px !important; padding: .4rem 1.2rem !important; font-weight: 500 !important; }
.stTabs [aria-selected="true"] { background: var(--red) !important; color: #fff !important; }
.pin-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 1rem; }
.pin-card { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.1); width: 180px; flex-shrink: 0; transition: transform .2s; }
.pin-card:hover { transform: scale(1.03); }
.pin-card img { width: 100%; height: 220px; object-fit: cover; display: block; }
.pin-card-info { padding: 8px 10px; }
.pin-card-title { font-size: .78rem; font-weight: 500; color: #111; line-height: 1.3; max-height: 2.6em; overflow: hidden; }
.pin-card-score { font-size: .7rem; color: var(--red); margin-top: 4px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

for key, default in [("results_df", pd.DataFrame()), ("last_keyword", ""), ("scraping", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📌 Pinterest Scraper")

    keyword = st.text_input("🔍 Keyword / Niche", placeholder="e.g. fitness motivation")
    max_pins = st.slider("📊 Number of Pins", 10, 200, 40, 1)

    st.markdown("**⚙️ Options**")
    headless = st.checkbox("Headless browser", value=True, help="Décochez si 0 résultats.")
    scroll_pause = st.slider("Scroll pause (ms)", 1000, 5000, 2500, 100)

    start_btn = st.button("🚀 Start Scraping", disabled=st.session_state.scraping)

    if CHROMIUM_PATH:
        st.markdown(f"<small style='color:#4CAF50'>✅ Chromium: ...{CHROMIUM_PATH[-40:]}</small>", unsafe_allow_html=True)
    else:
        st.markdown("<small style='color:#FF9800'>⚠️ Chromium: chemin par défaut</small>", unsafe_allow_html=True)

    plat = "Windows ✅" if sys.platform == "win32" else sys.platform
    st.markdown(f"<small style='color:#888'>Platform: {plat}</small>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.markdown('<h1 class="hero-title">Pinterest <span class="pin-accent">Niche</span> Scraper</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Find high-performing pins — extract, score, and export for AI content creation.</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

if start_btn and keyword.strip():
    st.session_state.scraping = True
    st.session_state.results_df = pd.DataFrame()
    keyword_clean = keyword.strip()
    st.session_state.last_keyword = keyword_clean

    st.markdown("---")
    st.markdown(f"### 🔄 Scraping **{keyword_clean}** — cible {max_pins} pins…")

    progress_bar = st.progress(0)
    status_ph = st.empty()

    def on_progress(current, total):
        progress_bar.progress(min(int(current / total * 100), 100))
        status_ph.markdown(
            f'<div class="status-box">📌 Collecté <b>{current}</b> / <b>{total}</b> pins…</div>',
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

        with st.spinner("Lancement du navigateur…"):
            # Récupérer le loop courant (déjà ProactorEventLoop sur Windows grâce au fix du haut)
            loop = asyncio.get_event_loop()
            pins = loop.run_until_complete(_run())

        if not pins:
            st.warning(
                "⚠️ Aucun pin trouvé.\n\n"
                "**Solutions :**\n"
                "- Décochez *Headless browser* dans la sidebar\n"
                "- Augmentez *Scroll pause* à 4000+ ms\n"
                "- Essayez le keyword en anglais"
            )
        else:
            apply_scores(pins)
            df = pins_to_dataframe(pins)
            st.session_state.results_df = df
            progress_bar.progress(100)
            status_ph.markdown(
                f'<div class="status-box">✅ Terminé ! <b>{len(df)}</b> pins uniques collectés.</div>',
                unsafe_allow_html=True,
            )

    except BaseException:
        tb_str = traceback.format_exc()
        lines = [l for l in tb_str.strip().splitlines() if l.strip()]
        last_line = lines[-1] if lines else "Erreur inconnue"

        st.error(f"❌ {last_line}")

        with st.expander("🔍 Traceback complet", expanded=True):
            st.code(tb_str, language="python")

        tb_lower = tb_str.lower()
        if "notimplementederror" in tb_lower and "subprocess" in tb_lower:
            st.error("🪟 **Bug Windows asyncio** — ce fix aurait dû résoudre ça. Vérifiez que vous utilisez bien le nouveau app.py.")
        elif "executable" in tb_lower or "doesn't exist" in tb_lower:
            st.info("💡 Lancez `playwright install chromium` dans votre terminal (venv activé).")
        elif "login" in tb_lower:
            st.info("💡 Décochez *Headless browser*.")
        elif "timeout" in tb_lower:
            st.info("💡 Augmentez *Scroll pause*.")

    finally:
        st.session_state.scraping = False

elif start_btn:
    st.warning("Entrez un keyword avant de scraper.")

# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------

df = st.session_state.results_df

if not df.empty:
    kw = st.session_state.last_keyword
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, len(df), "Pins Collectés"),
        (c2, f"{df['score'].max():.4f}" if "score" in df.columns else "0", "Top Score"),
        (c3, f"{int(df['description'].str.strip().ne('').sum() / len(df) * 100)}%", "Avec Description"),
        (c4, df["image_url"].str.strip().ne("").sum(), "Avec Image"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="metric-value">{val}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Data Table", "🖼️ Pin Gallery", "📈 Score Chart"])

    with tab1:
        display_df = df.copy()
        display_df["pin_url"] = display_df["pin_url"].apply(lambda u: f"[Pin]({u})" if u else "")
        display_df["image_url"] = display_df["image_url"].apply(lambda u: f"[Image]({u})" if u else "")
        st.dataframe(display_df, use_container_width=True, height=500,
                     column_config={
                         "score": st.column_config.NumberColumn("Score", format="%.5f"),
                         "position": st.column_config.NumberColumn("Pos.", format="%d"),
                         "pin_url": st.column_config.LinkColumn("Pin URL"),
                         "image_url": st.column_config.LinkColumn("Image URL"),
                     })

    with tab2:
        preview = df[df["image_url"].str.strip() != ""].head(30)
        if preview.empty:
            st.info("Aucune image URL à afficher.")
        else:
            html = '<div class="pin-grid">'
            for _, r in preview.iterrows():
                html += (
                    f'<a href="{r.pin_url}" target="_blank" style="text-decoration:none">'
                    f'<div class="pin-card"><img src="{r.image_url}" onerror="this.style.display=\'none\'"/>'
                    f'<div class="pin-card-info"><div class="pin-card-title">{str(r.title)[:60]}</div>'
                    f'<div class="pin-card-score">Score: {r.score:.5f}</div></div></div></a>'
                )
            st.markdown(html + "</div>", unsafe_allow_html=True)

    with tab3:
        if "score" in df.columns and "position" in df.columns:
            st.line_chart(df[["position", "score"]].set_index("position"), use_container_width=True)

    st.markdown("---")
    st.markdown("### 💾 Exporter les résultats")
    col_a, col_b = st.columns([2, 3])
    with col_a:
        st.download_button(
            label="⬇️ Download Excel",
            data=dataframe_to_excel_bytes(df, kw),
            file_name=safe_filename(kw),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_b:
        st.markdown(
            f"<small style='color:#999'>{len(df)} pins · keyword, position, score, title, description, pin_url, image_url</small>",
            unsafe_allow_html=True,
        )

else:
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#aaa">
        <div style="font-size:4rem;margin-bottom:1rem">📌</div>
        <div style="font-size:1.2rem;font-weight:500;color:#333">Prêt à scraper</div>
        <div style="margin-top:.5rem;font-size:.95rem">Entrez un keyword et cliquez sur <b>Start Scraping</b>.</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:4rem;padding-top:1rem;border-top:1px solid #ebebeb;text-align:center;color:#bbb;font-size:.8rem">
Pinterest Niche Scraper · Playwright + Streamlit + Pandas · Educational use only.
</div>
""", unsafe_allow_html=True)