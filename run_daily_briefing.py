"""Background job: pre-compute Today's Briefing for the whole watchlist and
cache the results, so opening the dashboard reads instantly instead of
waiting on live generation -- the more stocks on the watchlist, the more
this matters (2 local-LLM calls per stock).

Run once a day (see README.md for Windows Task Scheduler setup):

    python run_daily_briefing.py

Needs Ollama running locally, same as the live briefing.
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import briefing_store as bs
import stock_toolkit as tk
import watchlist_store as ws

MAX_WORKERS = 4


def main():
    if not tk.ollama_available():
        print(f"Ollama isn't running locally (expected at {tk.OLLAMA_URL}) -- start it first.")
        sys.exit(1)

    watchlist = ws.load_watchlist()
    if not watchlist:
        print("Watchlist is empty -- nothing to do.")
        return

    today_str = date.today().isoformat()
    print(f"Generating Today's Briefing for {len(watchlist)} stocks ({today_str})...")

    results = {}
    failures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(tk.explain_daily_move, w["symbol"], w["name"]): w
            for w in watchlist
        }
        done = 0
        for fut in as_completed(futures):
            w = futures[fut]
            done += 1
            try:
                result = fut.result()
                results[w["symbol"]] = result
                pct = result.get("change_pct")
                pct_str = f"{pct:+.1f}%" if pct is not None else "n/a"
                print(f"[{done}/{len(watchlist)}] {w['symbol']:<10} {pct_str}")
            except Exception as e:
                failures.append(w["symbol"])
                print(f"[{done}/{len(watchlist)}] {w['symbol']:<10} FAILED ({e})")

    cache = bs.load_cache()
    for symbol, result in results.items():
        cache[symbol] = {**result, "date": today_str}
    bs.save_cache(cache)

    print(f"\nSaved {len(results)}/{len(watchlist)} briefings to briefing_cache.json")
    if failures:
        print(f"Failed (kept previous cached value, if any): {', '.join(failures)}")


if __name__ == "__main__":
    main()
