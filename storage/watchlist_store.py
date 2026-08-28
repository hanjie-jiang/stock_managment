"""Local persistence for the user's watchlist.

Stored as watchlist.json next to this file -- gitignored, since it's
per-user data (which stocks someone tracks), not code. Each entry is
{"symbol", "name", "sector", "industry"}; sector/industry are cached at
add-time so the UI can group by sector without refetching on every load.
"""

import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")

_DEFAULT_WATCHLIST = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": None, "industry": None},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": None, "industry": None},
    {"symbol": "600519.SS", "name": "Kweichow Moutai", "sector": None, "industry": None},
    {"symbol": "0700.HK", "name": "Tencent Holdings", "sector": None, "industry": None},
    {"symbol": "BABA", "name": "Alibaba Group", "sector": None, "industry": None},
]


def load_watchlist():
    if os.path.exists(_PATH):
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f)
    save_watchlist(_DEFAULT_WATCHLIST)
    return [dict(w) for w in _DEFAULT_WATCHLIST]


def save_watchlist(watchlist):
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)
