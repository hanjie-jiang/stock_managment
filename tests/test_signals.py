"""Offline tests for buy_sell_signal()'s fundamentals/technical split -- see
specs/003-horizon-tagged-signals.md. No network calls: key_stats() and
technical_snapshot() are monkeypatched directly with synthetic values, since
what's under test is how buy_sell_signal() combines them, not market_data
itself (covered separately in tests/test_market_data.py).
"""

from stock_toolkit import signals


def _stats(symbol="TEST", upside=None, forward_pe=None, trailing_pe=None,
           revenue_growth=None, earnings_growth=None):
    return {
        "symbol": symbol,
        "upside_to_target_pct": upside,
        "forward_pe": forward_pe,
        "trailing_pe": trailing_pe,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
    }


def _tech(range_position=None, rsi14=None, above_sma50=None, above_sma200=None):
    return {
        "range_position_pct": range_position,
        "rsi14": rsi14,
        "above_sma50": above_sma50,
        "above_sma200": above_sma200,
    }


def test_lean_reflects_only_fundamental_checks(monkeypatch):
    """Two strong fundamental checks (analyst upside, favorable forward P/E)
    should produce Leans BUY regardless of what the technical checks say."""
    monkeypatch.setattr(signals, "key_stats", lambda symbol: _stats(
        upside=20.0, forward_pe=15.0, trailing_pe=20.0,
    ))
    monkeypatch.setattr(signals, "technical_snapshot", lambda symbol: _tech(
        range_position=95, rsi14=75,  # both bearish technical checks
    ))

    r = signals.buy_sell_signal("TEST")

    assert r["lean"] == "Leans BUY"
    assert r["lean_code"] == "lean_buy"
    assert r["fundamental_score"] == 2
    assert r["score"] == r["fundamental_score"]
    assert r["technical_score"] == -2
    assert r["technical_read"] == "Bearish"
    assert r["technical_read_code"] == "tech_bearish"


def test_lean_unchanged_when_only_technical_inputs_move(monkeypatch):
    """The core fix this spec makes: swinging the technical inputs from
    bullish to bearish must not move `lean` at all -- only `technical_read`,
    since the daily price-action flip that used to change the headline lean
    is exactly what specs/003 removes."""
    monkeypatch.setattr(signals, "key_stats", lambda symbol: _stats(
        upside=20.0, forward_pe=15.0, trailing_pe=20.0,
    ))

    monkeypatch.setattr(signals, "technical_snapshot", lambda symbol: _tech(
        range_position=10, rsi14=20,  # both bullish technical checks
    ))
    bullish_day = signals.buy_sell_signal("TEST")

    monkeypatch.setattr(signals, "technical_snapshot", lambda symbol: _tech(
        range_position=95, rsi14=80,  # both bearish technical checks
    ))
    bearish_day = signals.buy_sell_signal("TEST")

    assert bullish_day["lean"] == bearish_day["lean"] == "Leans BUY"
    assert bullish_day["fundamental_score"] == bearish_day["fundamental_score"] == 2
    assert bullish_day["technical_read"] == "Bullish"
    assert bearish_day["technical_read"] == "Bearish"


def test_mixed_hold_when_fundamentals_split(monkeypatch):
    """One bullish and one bearish fundamental check cancel out (+-2
    threshold not met) -- Mixed/HOLD, not a coin-flip toward either side."""
    monkeypatch.setattr(signals, "key_stats", lambda symbol: _stats(
        upside=20.0,  # bullish
        forward_pe=25.0, trailing_pe=20.0,  # bearish (forward > trailing * 1.1)
    ))
    monkeypatch.setattr(signals, "technical_snapshot", lambda symbol: _tech())

    r = signals.buy_sell_signal("TEST")

    assert r["lean"] == "Mixed / HOLD - no strong signal either way"
    assert r["lean_code"] == "lean_hold"
    assert r["fundamental_score"] == 0


def test_each_signal_tagged_with_horizon(monkeypatch):
    monkeypatch.setattr(signals, "key_stats", lambda symbol: _stats(upside=20.0))
    monkeypatch.setattr(signals, "technical_snapshot", lambda symbol: _tech(range_position=10))

    r = signals.buy_sell_signal("TEST")

    horizons = {b["code"]: b["horizon"] for b in r["bullish_signals"] + r["bearish_signals"]}
    assert horizons["analyst_upside"] == "fundamental"
    assert horizons["near_52w_low"] == "technical"
