"""Family Stock Tracker -- simple, large-print dashboard.

Run with:
    streamlit run app.py

Today's Briefing uses a local Ollama model (free, no API key) -- see
README.md for setup. Everything else works with no setup at all.
"""

import streamlit as st

from webapp import auto_shutdown
from webapp import ui_common as ui
from webapp.i18n import t

st.set_page_config(page_title="Family Stock Tracker", page_icon="📈", layout="wide")
auto_shutdown.init()
ui.apply_style()
ui.init_language_state()
ui.init_watchlist_state()

st.title(f"📈 {t('app_title')}")

with st.sidebar:
    ui.render_sidebar()

if not st.session_state.watchlist:
    st.info(t("add_stock_prompt"))
    st.stop()

pg = st.navigation([
    st.Page("pages/dashboard.py", title=t("nav_dashboard"), icon="📊", default=True),
    st.Page("pages/briefing.py", title=t("nav_briefing"), icon="📰"),
])
pg.run()
