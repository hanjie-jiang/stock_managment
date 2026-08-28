"""Family Stock Tracker -- simple, large-print dashboard.

Run with:
    streamlit run app.py

Today's Briefing uses a local Ollama model (free, no API key) -- see
README.md for setup. Everything else works with no setup at all.
"""

from collections import defaultdict
from datetime import date

import streamlit as st

import stock_toolkit as tk
from storage import briefing_store as bs
from storage import watchlist_store as wls

st.set_page_config(page_title="Family Stock Tracker", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# Large-print, high-contrast styling for older users
# ---------------------------------------------------------------------------
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

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
    import html as _html

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


if "watchlist" not in st.session_state:
    st.session_state.watchlist = wls.load_watchlist()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


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


st.title("📈 Family Stock Tracker")


# ---------------------------------------------------------------------------
# Sidebar: watchlist management, grouped by industry (this list can get long --
# 50+ stocks is a real use case, not just 5)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header(f"Your stocks ({len(st.session_state.watchlist)})")

    for industry, items in sorted(group_by_industry(st.session_state.watchlist).items()):
        with st.expander(f"{industry} ({len(items)})"):
            for item in items:
                cols = st.columns([4, 1])
                cols[0].write(f"**{item['name']}**  \n{item['symbol']}")
                if cols[1].button("✕", key=f"remove_{item['symbol']}"):
                    st.session_state.watchlist = [
                        w for w in st.session_state.watchlist if w["symbol"] != item["symbol"]
                    ]
                    save_watchlist()
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


if not st.session_state.watchlist:
    st.info("Add a stock from the left panel to get started.")
    st.stop()


# ---------------------------------------------------------------------------
# Today's Briefing -- why each watchlist stock moved, in plain English.
# Reads from a cache pre-computed by scripts/run_daily_briefing.py (see README) so
# opening the dashboard is instant regardless of watchlist size -- at 50+
# stocks, generating live on every page load (2 local-LLM calls each) would
# take many minutes. Anything missing/stale can still be generated on demand.
# ---------------------------------------------------------------------------
def render_briefing_entry(w, briefing):
    sym = w["symbol"]
    change_pct = briefing["change_pct"]
    if change_pct is None:
        arrow, color, change_label = "→", "#666666", "n/a"
    elif change_pct > 0:
        arrow, color, change_label = "↑", "#155724", f"+{change_pct:.1f}%"
    elif change_pct < 0:
        arrow, color, change_label = "↓", "#721c24", f"{change_pct:.1f}%"
    else:
        arrow, color, change_label = "→", "#666666", "0.0%"
    # Content inside a raw HTML block (this <div>) isn't run through inline
    # markdown/math parsing, so $ here doesn't need escaping (and escaping it
    # shows a literal backslash instead) -- unlike the native st.markdown()
    # calls in the expander below, which do need it.
    explanation_text = briefing["explanation"] or "No explanation available."
    st.markdown(
        f"<div style='padding:0.7em 0 0.2em 0;'>"
        f"<span style='font-size:22px;font-weight:700;color:{color};'>"
        f"{arrow} {w['name']} ({sym})&nbsp;&nbsp;{change_label}</span><br>"
        f"<span style='font-size:18px;'>{explanation_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    considered = briefing.get("considered") or []
    holdings = briefing.get("holdings") or []
    if considered:
        used = sum(c["relevant"] for c in considered)
        with st.expander(f"Show the reasoning ({used}/{len(considered)} headlines used)"):
            for c in considered:
                mark = "USED" if c["relevant"] else "skipped"
                title = md_escape_dollars(c["headline"].get("title"))
                publisher = md_escape_dollars(c["headline"].get("publisher"))
                st.markdown(f"**[{mark}]** {title} *({publisher})*")
                st.caption(md_escape_dollars(c["reason"]))
    elif holdings:
        with st.expander(f"Show top holdings ({len(holdings)})"):
            rows = [{
                "Holding": f"{h['name']} ({h['symbol']})",
                "% of fund": f"{h['weight']*100:.1f}%",
                "Today's move": f"{h['change_pct']:+.1f}%" if h.get("change_pct") is not None else "n/a",
            } for h in holdings]
            render_table(rows)
    st.markdown("<hr style='margin:0.3em 0;'>", unsafe_allow_html=True)


st.subheader("📰 Today's Briefing")
if not tk.ollama_available():
    st.info(
        "Today's Briefing needs [Ollama](https://ollama.com) running locally with the "
        f"`{tk.OLLAMA_MODEL}` model (`ollama pull {tk.OLLAMA_MODEL}`). "
        "Everything else on this page works without it."
    )
else:
    today_str = date.today().isoformat()
    ready, missing = {}, []
    for w in st.session_state.watchlist:
        cached = bs.get_briefing(w["symbol"], today_str)
        if cached:
            ready[w["symbol"]] = cached
        else:
            missing.append(w)

    if missing:
        st.caption(
            f"{len(ready)}/{len(st.session_state.watchlist)} briefings ready for today. "
            f"{len(missing)} missing (run `python scripts/run_daily_briefing.py` to pre-generate all "
            "of them in the background, or generate just the missing ones now)."
        )
        if st.button(f"Generate the {len(missing)} missing briefings now"):
            from concurrent.futures import ThreadPoolExecutor, as_completed

            progress = st.progress(0.0, text="Starting...")
            done = 0
            fresh_results = {}
            with ThreadPoolExecutor(max_workers=4) as ex:
                futures = {ex.submit(tk.explain_daily_move, w["symbol"], w["name"]): w for w in missing}
                for fut in as_completed(futures):
                    w = futures[fut]
                    done += 1
                    try:
                        result = fut.result()
                        bs.set_briefing(w["symbol"], today_str, result)
                        fresh_results[w["symbol"]] = result
                    except Exception:
                        pass
                    progress.progress(done / len(missing), text=f"{done}/{len(missing)}: {w['symbol']}")
            progress.empty()
            bs.archive_briefings(today_str, st.session_state.watchlist, fresh_results)
            st.rerun()

    for industry, items in sorted(group_by_industry(st.session_state.watchlist).items()):
        industry_ready = sum(1 for w in items if w["symbol"] in ready)
        with st.expander(f"{industry} ({industry_ready}/{len(items)} ready)", expanded=len(items) <= 3):
            for w in items:
                sym = w["symbol"]
                if sym in ready:
                    render_briefing_entry(w, ready[sym])
                else:
                    st.markdown(f"**{w['name']} ({sym})** -- not generated yet.")

st.divider()

symbol_options = {f"{w['name']} ({w['symbol']})": w["symbol"] for w in st.session_state.watchlist}
selected_label = st.selectbox("Choose a stock to look at:", list(symbol_options.keys()))
symbol = symbol_options[selected_label]


# ---------------------------------------------------------------------------
# Dashboard for the selected stock
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_dashboard_data(sym):
    return {
        "key_stats": tk.key_stats(sym),
        "signal": tk.buy_sell_signal(sym),
        "risk": tk.risk_scan(sym),
        "value": tk.long_term_value_score(sym),
        "quarterly": tk.quarterly_report_summary(sym),
    }


with st.spinner(f"Fetching the latest data for {symbol}..."):
    data = load_dashboard_data(symbol)

stats = data["key_stats"]
signal = data["signal"]
risk = data["risk"]
value = data["value"]
quarterly = data["quarterly"]

st.header(f"{stats['name']} ({symbol})")

price = stats["price"]
currency = stats["currency"] or ""
col1, col2, col3 = st.columns(3)
col1.metric("Current price", f"{price:,.2f} {currency}" if price else "n/a")
col2.metric("Risk level", risk["risk_level"])
col3.metric("Long-term fit", value["score"])

verdict_class = "verdict-hold"
if "BUY" in signal["lean"]:
    verdict_class = "verdict-buy"
elif "SELL" in signal["lean"]:
    verdict_class = "verdict-sell"

st.markdown(
    f'<div class="verdict-card {verdict_class}">Signal: {signal["lean"]}</div>',
    unsafe_allow_html=True,
)

tab_overview, tab_reasons, tab_report, tab_compare = st.tabs(
    ["Overview", "Why?", "Latest Quarter", "Compare"]
)

with tab_overview:
    st.subheader("In plain terms")
    bullets = []
    if stats["upside_to_target_pct"] is not None:
        bullets.append(
            f"Wall Street analysts on average expect this stock to be worth "
            f"{stats['upside_to_target_pct']:+.0f}% from here over the next year."
        )
    if stats["dividend_yield"]:
        bullets.append(f"It pays a dividend yield of about {stats['dividend_yield']:.2f}%.")
    if risk["risk_flags"]:
        bullets.append("Risk checks found some things worth knowing about (see the 'Why?' tab).")
    else:
        bullets.append("No major risk flags from our checks.")
    bullets.append(f"Long-term value checklist: {value['score']} criteria passed -- {value['verdict']}.")
    for b in bullets:
        st.write(f"- {b}")

    st.subheader("Key numbers")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("P/E ratio", f"{stats['trailing_pe']:.1f}" if stats["trailing_pe"] else "n/a")
    c2.metric("Profit margin", f"{stats['profit_margin']*100:.1f}%" if stats["profit_margin"] else "n/a")
    c3.metric("Revenue growth", f"{stats['revenue_growth']*100:+.1f}%" if stats["revenue_growth"] else "n/a")
    c4.metric("Beta (volatility)", f"{stats['beta']:.2f}" if stats["beta"] else "n/a")

with tab_reasons:
    st.subheader("Why this signal?")
    if signal["bullish_signals"]:
        st.write("**Points in favor:**")
        for b in signal["bullish_signals"]:
            st.write(f"- {b}")
    if signal["bearish_signals"]:
        st.write("**Points of caution:**")
        for b in signal["bearish_signals"]:
            st.write(f"- {b}")
    if not signal["bullish_signals"] and not signal["bearish_signals"]:
        st.write("No strong signals detected either way.")

    st.subheader("Risk flags")
    if risk["risk_flags"]:
        for f in risk["risk_flags"]:
            st.write(f"- {f}")
    else:
        st.write("No risk flags from our checks.")

    st.subheader("Long-term value checklist")
    for c in value["checks"]:
        icon = "✅" if c["passed"] else ("❌" if c["passed"] is False else "❔")
        st.write(f"{icon} {c['check']}")

with tab_report:
    if "error" in quarterly:
        st.write(quarterly["error"])
    else:
        st.write(f"Quarter ended **{quarterly['latest_quarter_end']}**")
        if quarterly.get("note"):
            st.warning(quarterly["note"])
        rows = []
        for l in quarterly["lines"]:
            rows.append({
                "Line item": l["line_item"],
                "Latest quarter": tk.format_financial_value(l["latest_quarter"]) or "n/a",
                "vs. prior quarter": f"{l['qoq_change_pct']:+.1f}%" if l["qoq_change_pct"] is not None else "n/a",
                "vs. a year ago": f"{l['yoy_change_pct']:+.1f}%" if l["yoy_change_pct"] is not None else "n/a",
            })
        render_table(rows, columns=["Line item", "Latest quarter", "vs. prior quarter", "vs. a year ago"])

with tab_compare:
    import pandas as pd

    def _val(row, col):
        v = row.get(col)
        return None if pd.isna(v) else v

    @st.cache_data(ttl=900, show_spinner=False)
    def load_compare_data(symbols_tuple):
        return tk.compare_stocks(list(symbols_tuple))

    st.write("Comparing everything in your watchlist, grouped by industry:")
    all_symbols = [w["symbol"] for w in st.session_state.watchlist]
    industry_by_symbol = {w["symbol"]: w.get("industry") or "Other / Unclassified" for w in st.session_state.watchlist}
    with st.spinner(f"Fetching comparison data for {len(all_symbols)} stocks..."):
        compare_df = load_compare_data(tuple(all_symbols))

    rows_by_industry = defaultdict(list)
    for sym, row in compare_df.iterrows():
        price = _val(row, "price")
        pe = _val(row, "trailing_pe")
        margin = _val(row, "profit_margin")
        rev_growth = _val(row, "revenue_growth")
        div_yield = _val(row, "dividend_yield")
        beta = _val(row, "beta")
        recommendation = _val(row, "analyst_recommendation")
        rows_by_industry[industry_by_symbol.get(sym, "Other / Unclassified")].append({
            "Stock": f"{row['name']} ({sym})",
            "Price": f"{price:,.2f}" if price is not None else "n/a",
            "P/E ratio": f"{pe:.1f}" if pe is not None else "n/a",
            "Profit margin": f"{margin*100:.1f}%" if margin is not None else "n/a",
            "Revenue growth": f"{rev_growth*100:+.1f}%" if rev_growth is not None else "n/a",
            "Dividend yield": f"{div_yield:.2f}%" if div_yield is not None else "n/a",
            "Risk (beta)": f"{beta:.2f}" if beta is not None else "n/a",
            "Analyst view": recommendation.replace("_", " ").title() if recommendation else "n/a",
        })

    for industry in sorted(rows_by_industry):
        with st.expander(f"{industry} ({len(rows_by_industry[industry])})", expanded=len(rows_by_industry) <= 3):
            render_table(rows_by_industry[industry])

    with st.expander("Show full data (all metrics, ungrouped)"):
        compare_rows = compare_df.reset_index().to_dict("records")
        render_table(compare_rows, columns=["symbol"] + list(compare_df.columns))

