"""Opinionated signals built on top of market_data: buy/sell lean, risk
flags, long-term value checklist, and side-by-side comparison.
"""

import numpy as np
import pandas as pd

from .market_data import _row, get_ticker, key_stats, technical_snapshot


# ---------------------------------------------------------------------------
# 2) Buy-in worth check / 3) Sell timing - combined signal
# ---------------------------------------------------------------------------

def buy_sell_signal(symbol):
    stats = key_stats(symbol)
    tech = technical_snapshot(symbol) or {}

    bullish, bearish, notes = [], [], []

    if stats["upside_to_target_pct"] is not None:
        if stats["upside_to_target_pct"] > 15:
            bullish.append(f"Analyst target implies {stats['upside_to_target_pct']:.1f}% upside")
        elif stats["upside_to_target_pct"] < -10:
            bearish.append(f"Price is {abs(stats['upside_to_target_pct']):.1f}% above analyst target")

    if stats["forward_pe"] and stats["trailing_pe"]:
        if stats["forward_pe"] < stats["trailing_pe"] * 0.9:
            bullish.append("Forward P/E well below trailing P/E (earnings expected to grow into price)")
        elif stats["forward_pe"] > stats["trailing_pe"] * 1.1:
            bearish.append("Forward P/E above trailing P/E (earnings expected to soften)")

    rp = tech.get("range_position_pct")
    if rp is not None:
        if rp < 25:
            bullish.append(f"Trading near 52-week low ({rp:.0f}% of range) - potential value entry, or a falling knife")
        elif rp > 90:
            bearish.append(f"Trading near 52-week high ({rp:.0f}% of range) - momentum strong but less margin of safety")

    rsi = tech.get("rsi14")
    if rsi is not None and not np.isnan(rsi):
        if rsi < 30:
            bullish.append(f"RSI14 = {rsi:.0f} (oversold)")
        elif rsi > 70:
            bearish.append(f"RSI14 = {rsi:.0f} (overbought)")

    if tech.get("above_sma50") and tech.get("above_sma200"):
        bullish.append("Price above both 50-day and 200-day moving averages (uptrend)")
    elif tech.get("above_sma50") is False and tech.get("above_sma200") is False:
        bearish.append("Price below both 50-day and 200-day moving averages (downtrend)")

    if stats["revenue_growth"] and stats["revenue_growth"] < 0:
        bearish.append(f"Revenue growth negative ({stats['revenue_growth']*100:.1f}%)")
    if stats["earnings_growth"] and stats["earnings_growth"] < 0:
        bearish.append(f"Earnings growth negative ({stats['earnings_growth']*100:.1f}%)")

    score = len(bullish) - len(bearish)
    if score >= 2:
        lean = "Leans BUY"
    elif score <= -2:
        lean = "Leans SELL / avoid adding"
    else:
        lean = "Mixed / HOLD - no strong signal either way"

    return {
        "symbol": symbol,
        "lean": lean,
        "score": score,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "stats": stats,
        "technicals": tech,
    }


def print_buy_sell_signal(symbol):
    r = buy_sell_signal(symbol)
    print(f"{symbol}: {r['lean']}  (signal score {r['score']:+d})")
    print("Bullish:")
    for b in r["bullish_signals"]:
        print(f"  + {b}")
    print("Bearish:")
    for b in r["bearish_signals"]:
        print(f"  - {b}")
    if not r["bullish_signals"] and not r["bearish_signals"]:
        print("  (no strong signals detected)")


# ---------------------------------------------------------------------------
# 4) Compare stocks side by side
# ---------------------------------------------------------------------------

def compare_stocks(symbols):
    rows = [key_stats(s) for s in symbols]
    df = pd.DataFrame(rows).set_index("symbol")
    cols = [
        "name", "price", "trailing_pe", "forward_pe", "peg_ratio", "price_to_book",
        "ev_to_ebitda", "profit_margin", "roe", "revenue_growth", "earnings_growth",
        "debt_to_equity", "current_ratio", "dividend_yield", "beta",
        "upside_to_target_pct", "analyst_recommendation",
    ]
    return df[[c for c in cols if c in df.columns]]


# ---------------------------------------------------------------------------
# 5) Risk scan
# ---------------------------------------------------------------------------

def risk_scan(symbol):
    stats = key_stats(symbol)
    tech = technical_snapshot(symbol, period="2y") or {}
    info = get_ticker(symbol).info

    flags = []
    if stats["beta"] and stats["beta"] > 1.5:
        flags.append(f"High beta ({stats['beta']:.2f}) - more volatile than the market")
    if stats["debt_to_equity"] and stats["debt_to_equity"] > 150:
        flags.append(f"High leverage - debt/equity {stats['debt_to_equity']:.0f}")
    if stats["current_ratio"] and stats["current_ratio"] < 1:
        flags.append(f"Current ratio {stats['current_ratio']:.2f} < 1 - potential short-term liquidity strain")
    vol = tech.get("annualized_volatility_pct")
    if vol and vol > 45:
        flags.append(f"High annualized volatility ({vol:.0f}%)")
    dd = tech.get("max_drawdown_pct")
    if dd and dd < -40:
        flags.append(f"Deep historical drawdown seen ({dd:.0f}% peak-to-trough in the lookback window)")
    short_pct = info.get("shortPercentOfFloat")
    if short_pct and short_pct > 0.1:
        flags.append(f"Elevated short interest ({short_pct*100:.1f}% of float)")
    if stats["profit_margin"] is not None and stats["profit_margin"] < 0:
        flags.append("Currently unprofitable (negative margin)")

    return {
        "symbol": symbol,
        "beta": stats["beta"],
        "annualized_volatility_pct": vol,
        "max_drawdown_pct": dd,
        "debt_to_equity": stats["debt_to_equity"],
        "current_ratio": stats["current_ratio"],
        "short_percent_of_float": short_pct,
        "risk_flags": flags,
        "risk_level": "HIGH" if len(flags) >= 3 else ("MODERATE" if flags else "LOW (by these checks)"),
    }


def print_risk_scan(symbol):
    r = risk_scan(symbol)
    print(f"{symbol}: risk level = {r['risk_level']}")
    print(f"  beta={r['beta']}, ann. volatility={r['annualized_volatility_pct']}, "
          f"max drawdown={r['max_drawdown_pct']}, D/E={r['debt_to_equity']}, current ratio={r['current_ratio']}")
    for f in r["risk_flags"]:
        print(f"  ! {f}")


# ---------------------------------------------------------------------------
# 6) Long-term value-investing checklist
# ---------------------------------------------------------------------------

def long_term_value_score(symbol):
    t = get_ticker(symbol)
    info = t.info
    fin = t.financials  # annual
    checks = []

    def add(label, passed, detail=""):
        checks.append({"check": label, "passed": bool(passed), "detail": detail})

    roe = info.get("returnOnEquity")
    add("ROE > 15%", roe is not None and roe > 0.15, f"ROE={roe}")

    margin = info.get("profitMargins")
    add("Positive profit margin", margin is not None and margin > 0, f"margin={margin}")

    fcf = info.get("freeCashflow")
    add("Positive free cash flow", fcf is not None and fcf > 0, f"FCF={fcf}")

    d2e = info.get("debtToEquity")
    add("Manageable leverage (D/E < 100)", d2e is not None and d2e < 100, f"D/E={d2e}")

    rev_growth = info.get("revenueGrowth")
    add("Revenue growing YoY", rev_growth is not None and rev_growth > 0, f"revenue growth={rev_growth}")

    earn_growth = info.get("earningsGrowth")
    add("Earnings growing YoY", earn_growth is not None and earn_growth > 0, f"earnings growth={earn_growth}")

    rev_row = _row(fin, "Total Revenue")
    consistent_growth = None
    if rev_row is not None and len(rev_row.dropna()) >= 3:
        vals = rev_row.dropna().iloc[::-1]  # oldest -> newest
        diffs = vals.diff().dropna()
        consistent_growth = (diffs > 0).sum() >= len(diffs) - 1  # allow one down year
    add("Multi-year revenue trend mostly up", consistent_growth, "based on annual revenue history")

    curr_ratio = info.get("currentRatio")
    add("Current ratio > 1.2 (financial cushion)", curr_ratio is not None and curr_ratio > 1.2, f"current ratio={curr_ratio}")

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    verdict = "Strong long-term candidate" if passed >= total - 1 else \
              "Reasonable candidate, some weak spots" if passed >= total * 0.6 else \
              "Weak fit for long-term/value criteria on these checks"

    return {"symbol": symbol, "score": f"{passed}/{total}", "verdict": verdict, "checks": checks}


def print_long_term_value_score(symbol):
    r = long_term_value_score(symbol)
    print(f"{symbol}: {r['score']} - {r['verdict']}")
    for c in r["checks"]:
        mark = "PASS" if c["passed"] else ("FAIL" if c["passed"] is False else "?")
        print(f"  [{mark}] {c['check']}  ({c['detail']})")
