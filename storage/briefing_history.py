"""Permanent, append-only historical log of Today's Briefing results.

Unlike briefing_cache.json (today's fast-read snapshot -- overwritten
daily, gitignored, trivially regenerable), this file is the durable
record: once a day's headlines scroll out of yfinance's news feed, that
day's briefing explanation can't be reconstructed from scratch.
Deliberately NOT gitignored, so committing the repo backs it up.

Format: JSON Lines (one JSON object per line), append-only, oldest first.
Each line has the shape:
{"date": "2026-08-27", "symbol": "AAPL", "name": "Apple Inc.",
 "change_pct": 1.2, "explanation": "...", "considered": [...], "holdings": [...]}
-- the same data Today's Briefing already shows in the app, just kept
instead of overwritten.

Scope note: this module only stores and retrieves entries. It doesn't
compare them against what the stock actually did afterward -- that
"was this explanation actually right" forward-return calibration was a
deliberate scope cut (see README's Today's Briefing history section);
revisit if/when it's worth the added complexity (a backfill job, a
horizon choice, partial/pending records).
"""

import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefing_history.jsonl")


def append_entries(entries):
    """Append pre-built entries (each a dict with at least "date" and
    "symbol") to the log, skipping any (date, symbol) pair already
    archived. Idempotent per day -- safe to call more than once for the
    same date (e.g. the background job and an on-demand fill both ran).
    """
    if not entries:
        return
    existing = {(e["date"], e["symbol"]) for e in read_history()}
    fresh = [e for e in entries if (e["date"], e["symbol"]) not in existing]
    if not fresh:
        return
    with open(_PATH, "a", encoding="utf-8") as f:
        for entry in fresh:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(symbol=None, limit=None):
    """Return archived entries, oldest first.

    symbol: optionally filter to one symbol.
    limit: optionally cap to the most recent `limit` matching entries.
    """
    if not os.path.exists(_PATH):
        return []
    entries = []
    with open(_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if symbol is None or entry.get("symbol") == symbol:
                entries.append(entry)
    if limit is not None:
        entries = entries[-limit:]
    return entries
