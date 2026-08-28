"""Capture real yfinance responses to JSON fixtures under tests/fixtures/data/.

Run manually to (re)capture -- not part of the test run itself, since it needs live
network access and its output is meant to be committed and read back deterministically:

    python tests/fixtures/capture_fixtures.py

Symbols are chosen to cover the toolkit's real edge cases, not just a happy path:
AAPL (plain US large-cap), VOO (ETF -- exercises funds.py), 600519.SS (China A-share),
0700.HK (Hong Kong), and AMZN (known, in this project's own history, to sometimes carry a
partially-populated "placeholder" most-recent quarterly column -- see
stock_toolkit/market_data.py's quarterly_report_summary docstring).
"""

import json
import os
import sys

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from stock_toolkit.market_data import to_jsonable  # reuse the same NaN/numpy-safe conversion the app uses

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

SYMBOLS = {
    "AAPL": "US large-cap stock",
    "VOO": "ETF (exercises funds.py / is_fund / top holdings)",
    "600519.SS": "China A-share",
    "0700.HK": "Hong Kong stock",
    "AMZN": "US stock with a history of partially-populated quarterly columns",
}


def _df_to_jsonable(df):
    """A DataFrame -> a JSON-safe 'split' dict (index/columns/data), reconstructible
    with pd.DataFrame(**loaded). None if the frame is missing/empty."""
    if df is None or df.empty:
        return None
    split = df.to_dict(orient="split")
    return to_jsonable(split)


def _safe_name(symbol):
    return symbol.replace(".", "_")


def capture(symbol):
    t = yf.Ticker(symbol)
    info = t.info
    payload = {
        "symbol": symbol,
        "info": to_jsonable(info),
        "history_5d": _df_to_jsonable(t.history(period="5d", auto_adjust=True)),
        "history_1y": _df_to_jsonable(t.history(period="1y", auto_adjust=True)),
        "quarterly_financials": _df_to_jsonable(t.quarterly_financials),
        "quarterly_cashflow": _df_to_jsonable(t.quarterly_cashflow),
        "financials": _df_to_jsonable(t.financials),
        "news": to_jsonable((t.news or [])[:5]),
    }
    if info.get("quoteType") in ("ETF", "MUTUALFUND"):
        try:
            payload["top_holdings"] = _df_to_jsonable(t.funds_data.top_holdings)
        except Exception:
            payload["top_holdings"] = None
    return payload


def main():
    os.makedirs(_DATA_DIR, exist_ok=True)
    for symbol, note in SYMBOLS.items():
        print(f"Capturing {symbol} ({note})...")
        payload = capture(symbol)
        out_path = os.path.join(_DATA_DIR, f"{_safe_name(symbol)}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"  -> {out_path}")
    print("Done. Review the diff before committing -- yfinance's fields do change over time.")


if __name__ == "__main__":
    main()
