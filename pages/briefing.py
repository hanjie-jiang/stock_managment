"""Today's Briefing -- why each watchlist stock moved, in plain English.

Reads from a cache pre-computed by jobs/run_daily_briefing.py (see README) so
opening this page is instant regardless of watchlist size -- at 50+ stocks,
generating live on every page load (2 local-LLM calls each) would take many
minutes. Anything missing/stale can still be generated on demand.
"""

from datetime import date

import streamlit as st

import stock_toolkit as tk
from data import briefing_store as bs
from shell import ui_common as ui
from shell.i18n import get_lang, t


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
    # explanation_zh/reason_zh are only present when the translation model was
    # reachable at generation time (see briefing.py's translate_to_zh) --
    # fall back to the English source rather than showing a blank.
    zh = get_lang() == "zh"
    # Content inside a raw HTML block (this <div>) isn't run through inline
    # markdown/math parsing, so $ here doesn't need escaping (and escaping it
    # shows a literal backslash instead) -- unlike the native st.markdown()
    # calls in the expander below, which do need it.
    explanation_text = (briefing.get("explanation_zh") if zh else None) or briefing["explanation"] or t("no_explanation")
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
        with st.expander(t("show_reasoning", used=used, total=len(considered))):
            for c in considered:
                mark = t("mark_used") if c["relevant"] else t("mark_skipped")
                title = ui.md_escape_dollars(c["headline"].get("title"))
                publisher = ui.md_escape_dollars(c["headline"].get("publisher"))
                st.markdown(f"**[{mark}]** {title} *({publisher})*")
                reason_text = (c.get("reason_zh") if zh else None) or c["reason"]
                st.caption(ui.md_escape_dollars(reason_text))
    elif holdings:
        with st.expander(t("show_top_holdings", count=len(holdings))):
            rows = [{
                t("col_holding"): f"{h['name']} ({h['symbol']})",
                t("col_pct_of_fund"): f"{h['weight']*100:.1f}%",
                t("col_todays_move"): f"{h['change_pct']:+.1f}%" if h.get("change_pct") is not None else t("na"),
            } for h in holdings]
            ui.render_table(rows)
    st.markdown("<hr style='margin:0.3em 0;'>", unsafe_allow_html=True)


st.subheader(f"📰 {t('briefing_header')}")
if not tk.ollama_available():
    st.info(t("ollama_unavailable", model=tk.OLLAMA_MODEL))
else:
    if get_lang() == "zh" and not tk.translation_available():
        st.caption(
            f"提示：未检测到翻译模型 `{tk.TRANSLATION_MODEL}`"
            f"（运行 `ollama pull {tk.TRANSLATION_MODEL}`），下方简报暂时显示英文原文。"
        )
    today_str = date.today().isoformat()
    ready, missing = {}, []
    for w in st.session_state.watchlist:
        cached = bs.get_briefing(w["symbol"], today_str)
        if cached:
            ready[w["symbol"]] = cached
        else:
            missing.append(w)

    if missing:
        st.caption(t(
            "briefings_ready_status",
            ready=len(ready), total=len(st.session_state.watchlist), missing=len(missing),
        ))
        if st.button(t("generate_missing_button", missing=len(missing))):
            from concurrent.futures import ThreadPoolExecutor, as_completed

            progress = st.progress(0.0, text=t("progress_starting"))
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
                    progress.progress(done / len(missing), text=t("progress_status", done=done, total=len(missing), symbol=w["symbol"]))
            progress.empty()
            bs.archive_briefings(today_str, st.session_state.watchlist, fresh_results)
            st.rerun()

    for industry, items in sorted(ui.group_by_industry(st.session_state.watchlist).items()):
        industry_ready = sum(1 for w in items if w["symbol"] in ready)
        with st.expander(t("industry_briefing_label", industry=industry, ready=industry_ready, total=len(items))):
            for w in items:
                sym = w["symbol"]
                if sym in ready:
                    render_briefing_entry(w, ready[sym])
                else:
                    st.markdown(t("not_generated_yet", name=w["name"], symbol=sym))
