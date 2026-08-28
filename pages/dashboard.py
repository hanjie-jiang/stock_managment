"""Per-stock dashboard: pick a stock, see its signal, reasoning, latest
quarter, and how it stacks up against its industry peers."""

import pandas as pd
import streamlit as st

import stock_toolkit as tk
import ui_common as ui
from collections import defaultdict

symbol_names = {w["symbol"]: w["name"] for w in st.session_state.watchlist}
symbols = list(symbol_names.keys())

if st.session_state.get("selected_symbol") not in symbols:
    st.session_state.selected_symbol = symbols[0]

symbol = st.selectbox(
    "Choose a stock to look at:",
    symbols,
    format_func=lambda s: f"{symbol_names[s]} ({s})",
    key="selected_symbol",
)


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
    st.subheader("Price history")
    period_labels = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "5 Years": "5y"}
    period_label = st.radio(
        "Time range", list(period_labels.keys()), index=2, horizontal=True, key="chart_period"
    )

    @st.cache_data(ttl=900, show_spinner=False)
    def load_price_history(sym, period):
        return tk.price_history(sym, period=period)

    history = load_price_history(symbol, period_labels[period_label])
    if history is not None and not history.empty:
        st.line_chart(history)
    else:
        st.write("No price history available.")

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
        ui.render_table(rows, columns=["Line item", "Latest quarter", "vs. prior quarter", "vs. a year ago"])

with tab_compare:
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

    symbols_by_industry = defaultdict(list)
    for sym in compare_df.index:
        symbols_by_industry[industry_by_symbol.get(sym, "Other / Unclassified")].append(sym)

    rows_by_industry = defaultdict(list)
    for industry, symbols in symbols_by_industry.items():
        ranks = tk.relative_rank(compare_df.loc[symbols]) if len(symbols) >= 2 else None
        for sym in symbols:
            row = compare_df.loc[sym]
            price = _val(row, "price")
            pe = _val(row, "trailing_pe")
            margin = _val(row, "profit_margin")
            rev_growth = _val(row, "revenue_growth")
            div_yield = _val(row, "dividend_yield")
            beta = _val(row, "beta")
            recommendation = _val(row, "analyst_recommendation")
            if ranks is None:
                rel_rank = "n/a (only stock in this industry)"
            elif sym in ranks.index:
                r = ranks.loc[sym]
                rel_rank = f"#{r['rank']} of {r['out_of']} -- best on {r['best_factor']}"
            else:
                rel_rank = "not enough data to rank"
            rows_by_industry[industry].append({
                "Stock": f"{row['name']} ({sym})",
                "Price": f"{price:,.2f}" if price is not None else "n/a",
                "P/E ratio": f"{pe:.1f}" if pe is not None else "n/a",
                "Profit margin": f"{margin*100:.1f}%" if margin is not None else "n/a",
                "Revenue growth": f"{rev_growth*100:+.1f}%" if rev_growth is not None else "n/a",
                "Dividend yield": f"{div_yield:.2f}%" if div_yield is not None else "n/a",
                "Risk (beta)": f"{beta:.2f}" if beta is not None else "n/a",
                "Analyst view": recommendation.replace("_", " ").title() if recommendation else "n/a",
                "Relative rank": rel_rank,
            })

    for industry in sorted(rows_by_industry):
        with st.expander(f"{industry} ({len(rows_by_industry[industry])})", expanded=len(rows_by_industry) <= 3):
            ui.render_table(rows_by_industry[industry])

    with st.expander("Show full data (all metrics, ungrouped)"):
        compare_rows = compare_df.reset_index().to_dict("records")
        ui.render_table(compare_rows, columns=["symbol"] + list(compare_df.columns))
