"""Turn captured JSON fixtures back into yfinance-shaped objects for offline tests.

Usage in a test:

    from tests.fixtures.loader import patch_yfinance

    def test_daily_price_move(monkeypatch):
        patch_yfinance(monkeypatch)
        move = market_data.daily_price_move("AAPL")
        assert move["change_pct"] is not None

`patch_yfinance` replaces `stock_toolkit.market_data.yf.Ticker` with a factory that reads
from tests/fixtures/data/<symbol>.json instead of hitting the network, so anything built
on `get_ticker()` (i.e. everything in this toolkit) runs against a fixed, real, offline
snapshot.
"""

import json
import os

import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _safe_name(symbol):
    return symbol.replace(".", "_")


def available_symbols():
    return [
        f[: -len(".json")]
        for f in os.listdir(_DATA_DIR)
        if f.endswith(".json")
    ]


def load_fixture(symbol):
    path = os.path.join(_DATA_DIR, f"{_safe_name(symbol)}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No captured fixture for {symbol!r} at {path}. "
            f"Run tests/fixtures/capture_fixtures.py to add it, or use one of: "
            f"{available_symbols()}"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _df_from_split(split):
    if split is None:
        return pd.DataFrame()
    df = pd.DataFrame(data=split["data"], index=split["index"], columns=split["columns"])
    # Financial-statement frames are indexed by line-item label but have date columns;
    # history frames are the other way around -- try to parse each axis as dates, keep
    # whichever isn't a line-item label if it fails.
    try:
        df.columns = pd.to_datetime(df.columns, format="mixed")
    except (ValueError, TypeError):
        pass
    try:
        df.index = pd.to_datetime(df.index, format="mixed")
    except (ValueError, TypeError):
        pass
    return df


class _FakeFundsData:
    def __init__(self, top_holdings_split):
        self.top_holdings = _df_from_split(top_holdings_split)


class FakeTicker:
    """Drop-in stand-in for yf.Ticker, backed by a captured fixture."""

    def __init__(self, symbol):
        self._data = load_fixture(symbol)
        self.info = self._data["info"]
        self.news = self._data.get("news") or []
        self.quarterly_financials = _df_from_split(self._data.get("quarterly_financials"))
        self.quarterly_cashflow = _df_from_split(self._data.get("quarterly_cashflow"))
        self.financials = _df_from_split(self._data.get("financials"))
        if "top_holdings" in self._data:
            self.funds_data = _FakeFundsData(self._data["top_holdings"])

    def history(self, period="1y", auto_adjust=True, **kwargs):
        key = f"history_{period}"
        if key not in self._data:
            raise NotImplementedError(
                f"Fixture for {self._data['symbol']!r} only has "
                f"{[k for k in self._data if k.startswith('history_')]} -- "
                f"re-run capture_fixtures.py if period={period!r} is newly needed."
            )
        return _df_from_split(self._data[key])


def patch_yfinance(monkeypatch, module=None):
    """Monkeypatch stock_toolkit.market_data's yf.Ticker to build FakeTickers instead of
    hitting the network. Also clears market_data's process-level ticker cache first, so a
    real Ticker from an earlier (non-fixture) test can't leak into a fixture-backed one.
    """
    if module is None:
        from stock_toolkit import market_data as module
    module._TICKER_CACHE.clear()
    monkeypatch.setattr(module.yf, "Ticker", FakeTicker)
