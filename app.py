"""Family Stock Tracker -- simple, large-print dashboard.

Run with:
    streamlit run app.py

Today's Briefing uses a local Ollama model (free, no API key) -- see
README.md for setup. Everything else works with no setup at all.
"""

from datetime import date

import streamlit as st

import stock_toolkit as tk

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
    st.session_state.watchlist = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "600519.SS", "name": "Kweichow Moutai"},
        {"symbol": "0700.HK", "name": "Tencent Holdings"},
        {"symbol": "BABA", "name": "Alibaba Group"},
    ]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("📈 Family Stock Tracker")


# ---------------------------------------------------------------------------
# Sidebar: watchlist management
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Your stocks")

    for item in list(st.session_state.watchlist):
        cols = st.columns([4, 1])
        cols[0].write(f"**{item['name']}**  \n{item['symbol']}")
        if cols[1].button("✕", key=f"remove_{item['symbol']}"):
            st.session_state.watchlist = [
                w for w in st.session_state.watchlist if w["symbol"] != item["symbol"]
            ]
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
                    st.session_state.watchlist.append({"symbol": m["symbol"], "name": m["name"]})
                st.rerun()


if not st.session_state.watchlist:
    st.info("Add a stock from the left panel to get started.")
    st.stop()


# ---------------------------------------------------------------------------
# Today's Briefing -- why each watchlist stock moved, in plain English.
# Uses a local Ollama model (free, private, no API key) instead of a paid API.
# ---------------------------------------------------------------------------
def generate_daily_move_explanation(symbol, data):
    """One honest, plain-English sentence explaining today's price move, or None."""
    move = data["price_move"]
    if move is None or move.get("change_pct") is None:
        return None, None
    news_lines = "\n".join(
        f"- {n['title']} ({n['publisher']})" for n in data["news"] if n.get("title")
    ) or "No recent news found."
    prompt = (
        f"Stock: {symbol}\n"
        f"Price change: {move['change_pct']:+.2f}% (from {move['prev_close']:.2f} to {move['close']:.2f})\n"
        f"Day range: {move['day_low']:.2f} - {move['day_high']:.2f}\n\n"
        f"Recent news headlines:\n{news_lines}\n\n"
        "In ONE short, plain-English sentence, explain why this stock likely moved today. "
        "Ground it in the headlines above only if they plausibly explain a move of this size. "
        "If none of the headlines look like a real stock-specific catalyst, say plainly that it "
        "looks like the stock is just moving with the broader market, rather than inventing a reason."
    )
    system = (
        "You write very short, honest, plain-language explanations of daily stock price "
        "moves for a non-technical family member. Never invent a news catalyst that isn't "
        "supported by the provided headlines -- it's fine and expected to say a move looks "
        "like broad market noise with no specific cause. Respond with just the one sentence, "
        "no preamble."
    )
    explanation = tk.local_llm_complete(prompt, system=system)
    return move["change_pct"], explanation


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_daily_briefing(symbol, cache_date):
    briefing_data = tk.daily_briefing_data(symbol)
    change_pct, explanation = generate_daily_move_explanation(symbol, briefing_data)
    return {"change_pct": change_pct, "explanation": explanation}


st.subheader("📰 Today's Briefing")
if not tk.ollama_available():
    st.info(
        "Today's Briefing needs [Ollama](https://ollama.com) running locally with the "
        f"`{tk.OLLAMA_MODEL}` model (`ollama pull {tk.OLLAMA_MODEL}`). "
        "Everything else on this page works without it."
    )
else:
    today_str = date.today().isoformat()
    with st.spinner("Checking today's news for your watchlist..."):
        for w in st.session_state.watchlist:
            sym = w["symbol"]
            try:
                briefing = cached_daily_briefing(sym, today_str)
            except Exception as e:
                briefing = {"change_pct": None, "explanation": f"Couldn't fetch a briefing right now ({e})."}
            change_pct = briefing["change_pct"]
            if change_pct is None:
                arrow, color, change_label = "→", "#666666", "n/a"
            elif change_pct > 0:
                arrow, color, change_label = "↑", "#155724", f"+{change_pct:.1f}%"
            elif change_pct < 0:
                arrow, color, change_label = "↓", "#721c24", f"{change_pct:.1f}%"
            else:
                arrow, color, change_label = "→", "#666666", "0.0%"
            st.markdown(
                f"<div style='padding:0.7em 0;border-bottom:1px solid #eee;'>"
                f"<span style='font-size:22px;font-weight:700;color:{color};'>"
                f"{arrow} {w['name']} ({sym})&nbsp;&nbsp;{change_label}</span><br>"
                f"<span style='font-size:18px;'>{briefing['explanation'] or 'No explanation available.'}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

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

    st.write("Comparing everything in your watchlist:")
    all_symbols = [w["symbol"] for w in st.session_state.watchlist]
    compare_df = tk.compare_stocks(all_symbols)

    friendly_rows = []
    for sym, row in compare_df.iterrows():
        price = _val(row, "price")
        pe = _val(row, "trailing_pe")
        margin = _val(row, "profit_margin")
        rev_growth = _val(row, "revenue_growth")
        div_yield = _val(row, "dividend_yield")
        beta = _val(row, "beta")
        recommendation = _val(row, "analyst_recommendation")
        friendly_rows.append({
            "Stock": f"{row['name']} ({sym})",
            "Price": f"{price:,.2f}" if price is not None else "n/a",
            "P/E ratio": f"{pe:.1f}" if pe is not None else "n/a",
            "Profit margin": f"{margin*100:.1f}%" if margin is not None else "n/a",
            "Revenue growth": f"{rev_growth*100:+.1f}%" if rev_growth is not None else "n/a",
            "Dividend yield": f"{div_yield:.2f}%" if div_yield is not None else "n/a",
            "Risk (beta)": f"{beta:.2f}" if beta is not None else "n/a",
            "Analyst view": recommendation.replace("_", " ").title() if recommendation else "n/a",
        })
    render_table(friendly_rows)

    with st.expander("Show full data (all metrics)"):
        compare_rows = compare_df.reset_index().to_dict("records")
        render_table(compare_rows, columns=["symbol"] + list(compare_df.columns))

