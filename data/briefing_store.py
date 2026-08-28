"""Local cache for Today's Briefing results.

Written by tools/run_daily_briefing.py (the background job), read by
app.py. Gitignored -- this is generated data that's stale by the next day,
not worth version-controlling.
"""

import json
import os

from . import briefing_history

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefing_cache.json")


def load_cache():
    if os.path.exists(_PATH):
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_briefing(symbol, today_str):
    """Return the cached briefing for symbol if it's from today, else None."""
    entry = load_cache().get(symbol)
    if entry and entry.get("date") == today_str:
        return entry
    return None


def set_briefing(symbol, today_str, result):
    cache = load_cache()
    cache[symbol] = {**result, "date": today_str}
    save_cache(cache)


def archive_briefings(date_str, watchlist, results):
    """Append today's freshly-generated briefings to the permanent history
    log (briefing_history.jsonl) so they survive tomorrow's cache overwrite.
    Safe to call more than once for the same date -- already-archived
    (date, symbol) pairs are skipped (see briefing_history.append_entries).

    watchlist: list of {"symbol", "name", ...} dicts, for name lookup.
    results: {symbol: briefing result dict (change_pct/explanation/
    considered/holdings)}. Symbols with no usable price move (change_pct
    is None) are skipped -- nothing happened worth archiving.
    """
    names = {w["symbol"]: w.get("name") for w in watchlist}
    entries = []
    for symbol, result in results.items():
        if result.get("change_pct") is None:
            continue
        entries.append({
            "date": date_str,
            "symbol": symbol,
            "name": names.get(symbol),
            "change_pct": result.get("change_pct"),
            "explanation": result.get("explanation"),
            "explanation_zh": result.get("explanation_zh"),
            "considered": result.get("considered") or [],
            "holdings": result.get("holdings") or [],
        })
    briefing_history.append_entries(entries)
