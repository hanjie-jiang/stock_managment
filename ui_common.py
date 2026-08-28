"""Shared UI plumbing used by app.py and the pages/ scripts.

Kept as a plain module (not a package) since it's small and specific to this
app's Streamlit layer -- stock_toolkit stays UI-free.
"""

import html as _html
from collections import defaultdict

import streamlit as st

import stock_toolkit as tk
from data import watchlist_store as wls

PAGE_STYLE = """
<style>
html, body, [class*="css"]  { font-size: 20px !important; }
h1 { font-size: 40px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 24px !important; }
.stButton button { font-size: 20px !important; padding: 0.6em 1.2em !important; }
.stTextInput input, .stSelectbox div[data-baseweb="select"] { font-size: 20px !important; }
div[data-testid="stMetricValue"] { font-size: 28px !important; }
div[data-testid="stMetricLabel"] { font-size: 18px !important; }
.verdict-card {
    padding: 1.2em; border-radius: 12px; margin-bottom: 1em;
    font-size: 22px; font-weight: 600;
}
.verdict-buy { background-color: #d4edda; color: #155724; }
.verdict-sell { background-color: #f8d7da; color: #721c24; }
.verdict-hold { background-color: #fff3cd; color: #856404; }
</style>
"""


def apply_style():
    """Large-print, high-contrast styling for older users."""
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)


def md_escape_dollars(text):
    """Escape literal $ so st.markdown doesn't mistake e.g. "HK$300...HK$445"
    for a paired LaTeX math span (a real bug this app hit with real headlines).
    """
    return (text or "").replace("$", "\\$")


def render_table(rows, columns=None):
    """Render a list of dicts as a plain HTML table.

    st.dataframe/st.table both require pyarrow, which is blocked by an
    Application Control policy on this machine -- this sidesteps that.
    """
    if not rows:
        st.write("No data available.")
        return
    columns = columns or list(rows[0].keys())

    def fmt(v):
        if v is None:
            return "n/a"
        if isinstance(v, float):
            return f"{v:,.2f}"
        return _html.escape(str(v))

    header_html = "".join(
        f"<th style='text-align:left;padding:6px 12px;border-bottom:2px solid #999;'>{_html.escape(str(c))}</th>"
        for c in columns
    )
    body_html = "".join(
        "<tr>" + "".join(
            f"<td style='padding:6px 12px;border-bottom:1px solid #ddd;'>{fmt(row.get(c))}</td>"
            for c in columns
        ) + "</tr>"
        for row in rows
    )
    st.markdown(
        f"<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;font-size:18px;'>"
        f"<thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def init_watchlist_state():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = wls.load_watchlist()


def save_watchlist():
    wls.save_watchlist(st.session_state.watchlist)


def group_by_industry(watchlist):
    """Group watchlist entries by industry (more specific than sector -- e.g.
    "Communication Services" lumps telecom carriers, newspapers, social media,
    and video game companies together; industry actually separates them)."""
    groups = defaultdict(list)
    for item in watchlist:
        groups[item.get("industry") or "Other / Unclassified"].append(item)
    return dict(groups)


def render_sidebar():
    """Watchlist management, grouped by industry (this list can get long --
    50+ stocks is a real use case, not just 5)."""
    st.header(f"Your stocks ({len(st.session_state.watchlist)})")

    for industry, items in sorted(group_by_industry(st.session_state.watchlist).items()):
        with st.expander(f"{industry} ({len(items)})"):
            for item in items:
                if st.session_state.get("confirm_remove") == item["symbol"]:
                    st.write(f"Remove **{item['name']}**?")
                    if st.button("Yes, remove", key=f"confirm_remove_{item['symbol']}", use_container_width=True):
                        st.session_state.watchlist = [
                            w for w in st.session_state.watchlist if w["symbol"] != item["symbol"]
                        ]
                        save_watchlist()
                        st.session_state.confirm_remove = None
                        st.rerun()
                    if st.button("Cancel", key=f"cancel_remove_{item['symbol']}", use_container_width=True):
                        st.session_state.confirm_remove = None
                        st.rerun()
                    continue

                cols = st.columns([4, 1])
                is_selected = st.session_state.get("selected_symbol") == item["symbol"]
                if cols[0].button(
                    f"{item['name']} ({item['symbol']})",
                    key=f"select_{item['symbol']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_symbol = item["symbol"]
                    st.switch_page("pages/dashboard.py")
                if cols[1].button("✕", key=f"remove_{item['symbol']}"):
                    st.session_state.confirm_remove = item["symbol"]
                    st.rerun()

    st.divider()
    st.subheader("Add a stock")
    query = st.text_input("Type a company name", placeholder="e.g. Apple, Tencent, Moutai")
    if query:
        matches = tk.search_symbol(query, limit=5)
        if not matches:
            st.write("No matches found. Try a different spelling.")
        for m in matches:
            label = f"{m['name']} ({m['symbol']}, {m['exchange']})"
            if st.button(f"Add {label}", key=f"add_{m['symbol']}"):
                if not any(w["symbol"] == m["symbol"] for w in st.session_state.watchlist):
                    with st.spinner("Looking up industry..."):
                        sector_info = tk.get_sector_industry(m["symbol"])
                    st.session_state.watchlist.append({
                        "symbol": m["symbol"],
                        "name": m["name"],
                        "sector": sector_info["sector"],
                        "industry": sector_info["industry"],
                    })
                    save_watchlist()
                st.rerun()
