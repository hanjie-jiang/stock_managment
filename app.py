"""Family Stock Tracker -- simple, large-print dashboard.

Run with:
    streamlit run app.py

Today's Briefing uses a local Ollama model (free, no API key) -- see
README.md for setup. Everything else works with no setup at all.
"""

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Family Stock Tracker", page_icon="📈", layout="wide")
ui.apply_style()
ui.init_watchlist_state()

st.title("📈 Family Stock Tracker")

with st.sidebar:
    ui.render_sidebar()

if not st.session_state.watchlist:
    st.info("Add a stock from the left panel to get started.")
    st.stop()

pg = st.navigation([
    st.Page("pages/dashboard.py", title="Stock Dashboard", icon="📊", default=True),
    st.Page("pages/briefing.py", title="Today's Briefing", icon="📰"),
])
pg.run()
