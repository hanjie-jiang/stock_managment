"""Today's Briefing -- why each watchlist stock moved, in plain English.

Reads from a cache pre-computed by tools/run_daily_briefing.py (see README) so
opening this page is instant regardless of watchlist size -- at 50+ stocks,
generating live on every page load (2 local-LLM calls each) would take many
minutes. Anything missing/stale can still be generated on demand.
"""

from datetime import date

import streamlit as st

import stock_toolkit as tk
import ui_common as ui
from data import briefing_store as bs


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
                title = ui.md_escape_dollars(c["headline"].get("title"))
                publisher = ui.md_escape_dollars(c["headline"].get("publisher"))
                st.markdown(f"**[{mark}]** {title} *({publisher})*")
                st.caption(ui.md_escape_dollars(c["reason"]))
    elif holdings:
        with st.expander(f"Show top holdings ({len(holdings)})"):
            rows = [{
                "Holding": f"{h['name']} ({h['symbol']})",
                "% of fund": f"{h['weight']*100:.1f}%",
                "Today's move": f"{h['change_pct']:+.1f}%" if h.get("change_pct") is not None else "n/a",
            } for h in holdings]
            ui.render_table(rows)
    st.markdown("<hr style='margin:0.3em 0;'>", unsafe_allow_html=True)


st.subheader("📰 Today's Briefing")
if not tk.ollama_available():
    st.info(
        "Today's Briefing needs [Ollama](https://ollama.com) running locally with the "
        f"`{tk.OLLAMA_MODEL}` model (`ollama pull {tk.OLLAMA_MODEL}`). "
        "Everything else in this app works without it."
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
            f"{len(missing)} missing (run `python tools/run_daily_briefing.py` to pre-generate all "
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

    for industry, items in sorted(ui.group_by_industry(st.session_state.watchlist).items()):
        industry_ready = sum(1 for w in items if w["symbol"] in ready)
        with st.expander(f"{industry} ({industry_ready}/{len(items)} ready)"):
            for w in items:
                sym = w["symbol"]
                if sym in ready:
                    render_briefing_entry(w, ready[sym])
                else:
                    st.markdown(f"**{w['name']} ({sym})** -- not generated yet.")
