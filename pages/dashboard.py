"""Per-stock dashboard: pick a stock, see its signal, reasoning, latest
quarter, and how it stacks up against its industry peers."""

import pandas as pd
import streamlit as st

import stock_toolkit as tk
from collections import defaultdict
from shell import ui_common as ui
from shell.i18n import code_text, dim_label, reason_text, t

symbol_names = {w["symbol"]: w["name"] for w in st.session_state.watchlist}
symbols = list(symbol_names.keys())

if st.session_state.get("selected_symbol") not in symbols:
    st.session_state.selected_symbol = symbols[0]

symbol = st.selectbox(
    t("choose_stock"),
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


with st.spinner(t("fetching_data", symbol=symbol)):
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
col1.metric(t("current_price"), f"{price:,.2f} {currency}" if price else t("na"))
col2.metric(t("risk_level"), code_text(risk["risk_level_code"], risk["risk_level"]))
col3.metric(t("long_term_fit"), value["score"])

verdict_class = "verdict-hold"
if "BUY" in signal["lean"]:
    verdict_class = "verdict-buy"
elif "SELL" in signal["lean"]:
    verdict_class = "verdict-sell"

lean_display = code_text(signal["lean_code"], signal["lean"])
st.markdown(
    f'<div class="verdict-card {verdict_class}">{t("signal_prefix", lean=lean_display)}</div>',
    unsafe_allow_html=True,
)

tab_overview, tab_reasons, tab_report, tab_compare = st.tabs(
    [t("tab_overview"), t("tab_reasons"), t("tab_report"), t("tab_compare")]
)

with tab_overview:
    st.subheader(t("price_history"))
    period_labels = {
        t("period_1mo"): "1mo", t("period_6mo"): "6mo", t("period_1y"): "1y", t("period_5y"): "5y",
    }
    period_label = st.radio(
        t("time_range"), list(period_labels.keys()), index=2, horizontal=True, key="chart_period"
    )

    @st.cache_data(ttl=900, show_spinner=False)
    def load_price_history(sym, period):
        return tk.price_history(sym, period=period)

    history = load_price_history(symbol, period_labels[period_label])
    if history is not None and not history.empty:
        ui.render_line_chart(history)
    else:
        st.write(t("no_price_history"))

    st.subheader(t("in_plain_terms"))
    bullets = []
    if stats["upside_to_target_pct"] is not None:
        bullets.append(t("bullet_analyst_upside", pct=stats["upside_to_target_pct"]))
    if stats["dividend_yield"]:
        bullets.append(t("bullet_dividend", **{"yield": stats["dividend_yield"]}))
    if risk["risk_flags"]:
        bullets.append(t("bullet_has_risk_flags"))
    else:
        bullets.append(t("bullet_no_risk_flags"))
    bullets.append(t("bullet_value_score", score=value["score"], verdict=code_text(value["verdict_code"], value["verdict"])))
    for b in bullets:
        st.write(f"- {b}")

    st.subheader(t("key_numbers"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("pe_ratio"), f"{stats['trailing_pe']:.1f}" if stats["trailing_pe"] else t("na"))
    c2.metric(t("profit_margin"), f"{stats['profit_margin']*100:.1f}%" if stats["profit_margin"] else t("na"))
    c3.metric(t("revenue_growth"), f"{stats['revenue_growth']*100:+.1f}%" if stats["revenue_growth"] else t("na"))
    c4.metric(t("beta"), f"{stats['beta']:.2f}" if stats["beta"] else t("na"))

with tab_reasons:
    st.subheader(t("why_this_signal"))
    if signal["bullish_signals"]:
        st.write(t("points_in_favor"))
        for b in signal["bullish_signals"]:
            st.write(f"- {reason_text(b)}")
    if signal["bearish_signals"]:
        st.write(t("points_of_caution"))
        for b in signal["bearish_signals"]:
            st.write(f"- {reason_text(b)}")
    if not signal["bullish_signals"] and not signal["bearish_signals"]:
        st.write(t("no_strong_signals"))

    st.subheader(t("risk_flags_header"))
    if risk["risk_flags"]:
        for f in risk["risk_flags"]:
            st.write(f"- {reason_text(f)}")
    else:
        st.write(t("no_risk_flags"))

    st.subheader(t("value_checklist_header"))
    for c in value["checks"]:
        icon = "✅" if c["passed"] else ("❌" if c["passed"] is False else "❔")
        st.write(f"{icon} {reason_text(c)}")

with tab_report:
    if "error" in quarterly:
        st.write(quarterly["error"])
    else:
        st.write(t("quarter_ended", date=quarterly["latest_quarter_end"]))
        if quarterly.get("note"):
            st.warning(quarterly["note"])
        rows = []
        for l in quarterly["lines"]:
            rows.append({
                t("col_line_item"): l["line_item"],
                t("col_latest_quarter"): tk.format_financial_value(l["latest_quarter"]) or t("na"),
                t("col_qoq"): f"{l['qoq_change_pct']:+.1f}%" if l["qoq_change_pct"] is not None else t("na"),
                t("col_yoy"): f"{l['yoy_change_pct']:+.1f}%" if l["yoy_change_pct"] is not None else t("na"),
            })
        ui.render_table(rows, columns=[t("col_line_item"), t("col_latest_quarter"), t("col_qoq"), t("col_yoy")])

with tab_compare:
    def _val(row, col):
        v = row.get(col)
        return None if pd.isna(v) else v

    @st.cache_data(ttl=900, show_spinner=False)
    def load_compare_data(symbols_tuple):
        return tk.compare_stocks(list(symbols_tuple))

    st.write(t("compare_intro"))
    all_symbols = [w["symbol"] for w in st.session_state.watchlist]
    industry_by_symbol = {w["symbol"]: w.get("industry") or "Other / Unclassified" for w in st.session_state.watchlist}
    with st.spinner(t("fetching_compare", count=len(all_symbols))):
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
                rel_rank = t("rank_single_stock")
            elif sym in ranks.index:
                r = ranks.loc[sym]
                rel_rank = t("rank_label", rank=r["rank"], out_of=r["out_of"], best_factor=dim_label(r["best_factor"]))
            else:
                rel_rank = t("rank_not_enough_data")
            rows_by_industry[industry].append({
                t("col_stock"): f"{row['name']} ({sym})",
                t("col_price"): f"{price:,.2f}" if price is not None else t("na"),
                t("pe_ratio"): f"{pe:.1f}" if pe is not None else t("na"),
                t("profit_margin"): f"{margin*100:.1f}%" if margin is not None else t("na"),
                t("revenue_growth"): f"{rev_growth*100:+.1f}%" if rev_growth is not None else t("na"),
                t("col_dividend_yield"): f"{div_yield:.2f}%" if div_yield is not None else t("na"),
                t("col_risk_beta"): f"{beta:.2f}" if beta is not None else t("na"),
                t("col_analyst_view"): recommendation.replace("_", " ").title() if recommendation else t("na"),
                t("col_relative_rank"): rel_rank,
            })

    for industry in sorted(rows_by_industry):
        with st.expander(t("industry_group_label", industry=industry, count=len(rows_by_industry[industry])), expanded=len(rows_by_industry) <= 3):
            ui.render_table(rows_by_industry[industry])

    with st.expander(t("show_full_data")):
        compare_rows = compare_df.reset_index().to_dict("records")
        ui.render_table(compare_rows, columns=["symbol"] + list(compare_df.columns))
