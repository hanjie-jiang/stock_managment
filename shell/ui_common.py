"""Shared UI plumbing used by app.py and the pages/ scripts.

Kept as a plain module (not a package) since it's small and specific to this
app's Streamlit layer -- stock_toolkit stays UI-free.
"""

import html as _html
from collections import defaultdict

import matplotlib
import streamlit as st

matplotlib.use("Agg")  # headless -- no display available on a server/service
import matplotlib.pyplot as plt

import stock_toolkit as tk
from data import settings_store as ss
from data import watchlist_store as wls

from .i18n import t

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


def render_line_chart(series):
    """Render a single-series line chart via matplotlib + st.pyplot(), not
    st.line_chart()/st.area_chart()/st.bar_chart() -- like render_table() above,
    Streamlit's built-in chart widgets serialize data through Altair's arrow-based
    path (convert_anything_to_arrow_bytes in vega_charts.py), which needs pyarrow --
    blocked by the same Application Control policy render_table() already works
    around (confirmed by hitting the exact DLL-blocked error live on this machine).
    matplotlib has no such dependency. Caller is responsible for the empty/None
    case, same division of labor as the st.line_chart() call this replaced.
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(series.index, series.values, color="#1f6feb", linewidth=1.8)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=12)
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)


def init_language_state():
    if "lang" not in st.session_state:
        st.session_state.lang = ss.load_settings().get("language", "en")


def set_language(lang):
    st.session_state.lang = lang
    ss.save_settings({"language": lang})


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


def render_language_toggle():
    """Language switcher at the very top of the sidebar -- kept visually
    simple and prominent, consistent with the large-print/high-contrast
    style applied for older users."""
    current = st.session_state.get("lang", "en")
    options = ["en", "zh"]
    labels = {"en": "English", "zh": "中文"}
    choice = st.radio(
        t("language_label"),
        options,
        index=options.index(current),
        format_func=lambda code: labels[code],
        horizontal=True,
        key="lang_toggle",
    )
    if choice != current:
        set_language(choice)
        st.rerun()


def render_sidebar():
    """Watchlist management, grouped by industry (this list can get long --
    50+ stocks is a real use case, not just 5)."""
    render_language_toggle()
    st.header(t("your_stocks", count=len(st.session_state.watchlist)))

    for industry, items in sorted(group_by_industry(st.session_state.watchlist).items()):
        with st.expander(t("industry_group_label", industry=industry, count=len(items))):
            for item in items:
                if st.session_state.get("confirm_remove") == item["symbol"]:
                    st.write(t("remove_confirm", name=item["name"]))
                    if st.button(t("yes_remove"), key=f"confirm_remove_{item['symbol']}", use_container_width=True):
                        st.session_state.watchlist = [
                            w for w in st.session_state.watchlist if w["symbol"] != item["symbol"]
                        ]
                        save_watchlist()
                        st.session_state.confirm_remove = None
                        st.rerun()
                    if st.button(t("cancel"), key=f"cancel_remove_{item['symbol']}", use_container_width=True):
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
    st.subheader(t("add_a_stock"))
    query = st.text_input(t("type_company_name"), placeholder=t("type_company_placeholder"))
    if query:
        matches = tk.search_symbol(query, limit=5)
        if not matches:
            st.write(t("no_matches"))
        for m in matches:
            label = f"{m['name']} ({m['symbol']}, {m['exchange']})"
            if st.button(t("add_button", label=label), key=f"add_{m['symbol']}"):
                if not any(w["symbol"] == m["symbol"] for w in st.session_state.watchlist):
                    with st.spinner(t("looking_up_industry")):
                        sector_info = tk.get_sector_industry(m["symbol"])
                    st.session_state.watchlist.append({
                        "symbol": m["symbol"],
                        "name": m["name"],
                        "sector": sector_info["sector"],
                        "industry": sector_info["industry"],
                    })
                    save_watchlist()
                st.rerun()
