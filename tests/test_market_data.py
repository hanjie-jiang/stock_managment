"""Offline tests against captured fixtures (see tests/fixtures/). No network calls."""

from stock_toolkit import funds, market_data
from tests.fixtures.loader import patch_yfinance


def test_key_stats_reads_real_fields(monkeypatch):
    patch_yfinance(monkeypatch)
    stats = market_data.key_stats("AAPL")
    assert stats["symbol"] == "AAPL"
    assert stats["price"] is not None
    assert stats["trailing_pe"] is not None


def test_daily_price_move_drops_nan_placeholder_row(monkeypatch):
    patch_yfinance(monkeypatch)
    move = market_data.daily_price_move("AAPL")
    assert move is not None
    assert move["change_pct"] is not None


def test_technical_snapshot_computes_from_history(monkeypatch):
    patch_yfinance(monkeypatch)
    snap = market_data.technical_snapshot("AAPL")
    assert snap is not None
    assert snap["rsi14"] == snap["rsi14"]  # not NaN
    assert snap["sma50"] is not None


def test_quarterly_report_summary_a_share(monkeypatch):
    patch_yfinance(monkeypatch)
    r = market_data.quarterly_report_summary("600519.SS")
    assert r["symbol"] == "600519.SS"
    assert "lines" in r


def test_is_fund_true_for_etf(monkeypatch):
    patch_yfinance(monkeypatch)
    assert funds.is_fund("VOO") is True
    assert funds.is_fund("AAPL") is False


def test_fund_top_holdings_present(monkeypatch):
    patch_yfinance(monkeypatch)
    holdings = funds.get_fund_top_holdings("VOO")
    assert holdings
    assert all("symbol" in h and "weight" in h for h in holdings)
