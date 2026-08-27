"""Local cache for Today's Briefing results.

Written by run_daily_briefing.py (the background job), read by app.py.
Gitignored -- this is generated data that's stale by the next day, not
worth version-controlling.
"""

import json
import os

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
