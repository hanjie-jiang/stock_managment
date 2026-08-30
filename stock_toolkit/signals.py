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
    """Each entry in bullish_signals/bearish_signals is a structured
    {"code", "params", "text", "horizon"} dict, not a plain string -- `text`
    is always the English sentence (what print_buy_sell_signal/the notebook
    use unchanged); `code`/`params` let the dashboard render the same
    sentence in another language via i18n.reason_text() without
    stock_toolkit itself knowing about display language. See
    specs/001-bilingual-en-zh-toggle.md.

    `horizon` is "fundamental" (analyst target, P/E trend, revenue/earnings
    growth -- only changes when a new quarterly print or analyst note
    lands) or "technical" (52-week range position, RSI, moving-average
    trend -- can flip from a single day's close). Two independent scores are
    kept instead of one pooled score: `lean` is derived only from
    `fundamental_score`, so it's the stable long-term-keep-or-sell read;
    `technical_read` is derived only from `technical_score`, so it's the
    part expected to move day to day. Pooling both into one number (the
    original design here) meant a single day's RSI crossing 30/70 could
    flip the headline lean with nothing about the long-term case actually
    changing -- see specs/003-horizon-tagged-signals.md for the full
    rationale. `score` stays as a plain alias for `fundamental_score` so
    existing callers reading `r["score"]` keep working.

    Both scores use the same +-2 threshold: two of the (at most four
    fundamental / three technical) checks need to agree before calling
    BUY/SELL rather than Mixed/HOLD-or-neutral, so the lean reflects more
    than a single data point. A stock with thin analyst coverage (fewer
    fundamental checks even computable) landing on Mixed/HOLD more often is
    correct behavior, not a bug.
    """
    stats = key_stats(symbol)
    tech = technical_snapshot(symbol) or {}

    bullish, bearish = [], []

    def bull(code, text, horizon, **params):
        bullish.append({"code": code, "params": params, "text": text, "horizon": horizon})

    def bear(code, text, horizon, **params):
        bearish.append({"code": code, "params": params, "text": text, "horizon": horizon})

    if stats["upside_to_target_pct"] is not None:
        if stats["upside_to_target_pct"] > 15:
            pct = stats["upside_to_target_pct"]
            bull("analyst_upside", f"Analyst target implies {pct:.1f}% upside", "fundamental", pct=pct)
        elif stats["upside_to_target_pct"] < -10:
            pct = abs(stats["upside_to_target_pct"])
            bear("analyst_downside", f"Price is {pct:.1f}% above analyst target", "fundamental", pct=pct)

    if stats["forward_pe"] and stats["trailing_pe"]:
        if stats["forward_pe"] < stats["trailing_pe"] * 0.9:
            bull("forward_pe_below_trailing",
                 "Forward P/E well below trailing P/E (earnings expected to grow into price)",
                 "fundamental")
        elif stats["forward_pe"] > stats["trailing_pe"] * 1.1:
            bear("forward_pe_above_trailing",
                 "Forward P/E above trailing P/E (earnings expected to soften)",
                 "fundamental")

    rp = tech.get("range_position_pct")
    if rp is not None:
        if rp < 25:
            bull("near_52w_low",
                 f"Trading near 52-week low ({rp:.0f}% of range) - potential value entry, or a falling knife",
                 "technical", rp=rp)
        elif rp > 90:
            bear("near_52w_high",
                 f"Trading near 52-week high ({rp:.0f}% of range) - momentum strong but less margin of safety",
                 "technical", rp=rp)

    rsi = tech.get("rsi14")
    if rsi is not None and not np.isnan(rsi):
        if rsi < 30:
            bull("rsi_oversold", f"RSI14 = {rsi:.0f} (oversold)", "technical", rsi=rsi)
        elif rsi > 70:
            bear("rsi_overbought", f"RSI14 = {rsi:.0f} (overbought)", "technical", rsi=rsi)

    if tech.get("above_sma50") and tech.get("above_sma200"):
        bull("above_both_sma", "Price above both 50-day and 200-day moving averages (uptrend)", "technical")
    elif tech.get("above_sma50") is False and tech.get("above_sma200") is False:
        bear("below_both_sma", "Price below both 50-day and 200-day moving averages (downtrend)", "technical")

    if stats["revenue_growth"] and stats["revenue_growth"] < 0:
        pct = stats["revenue_growth"] * 100
        bear("negative_revenue_growth", f"Revenue growth negative ({pct:.1f}%)", "fundamental", pct=pct)
    if stats["earnings_growth"] and stats["earnings_growth"] < 0:
        pct = stats["earnings_growth"] * 100
        bear("negative_earnings_growth", f"Earnings growth negative ({pct:.1f}%)", "fundamental", pct=pct)

    def _score(horizon):
        return (sum(1 for b in bullish if b["horizon"] == horizon)
                - sum(1 for b in bearish if b["horizon"] == horizon))

    fundamental_score = _score("fundamental")
    technical_score = _score("technical")

    if fundamental_score >= 2:
        lean_code, lean = "lean_buy", "Leans BUY"
    elif fundamental_score <= -2:
        lean_code, lean = "lean_sell", "Leans SELL / avoid adding"
    else:
        lean_code, lean = "lean_hold", "Mixed / HOLD - no strong signal either way"

    if technical_score >= 2:
        technical_read_code, technical_read = "tech_bullish", "Bullish"
    elif technical_score <= -2:
        technical_read_code, technical_read = "tech_bearish", "Bearish"
    else:
        technical_read_code, technical_read = "tech_neutral", "Neutral"

    return {
        "symbol": symbol,
        "lean": lean,
        "lean_code": lean_code,
        "technical_read": technical_read,
        "technical_read_code": technical_read_code,
        "score": fundamental_score,
        "fundamental_score": fundamental_score,
        "technical_score": technical_score,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "stats": stats,
        "technicals": tech,
    }


def print_buy_sell_signal(symbol):
    r = buy_sell_signal(symbol)
    print(f"{symbol}: Long-term lean = {r['lean']}  (fundamental score {r['fundamental_score']:+d})")
    print(f"       Short-term technical read = {r['technical_read']}  (technical score {r['technical_score']:+d})")
    print("Bullish:")
    for b in r["bullish_signals"]:
        print(f"  + [{b['horizon']}] {b['text']}")
    print("Bearish:")
    for b in r["bearish_signals"]:
        print(f"  - [{b['horizon']}] {b['text']}")
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


def _col(df, name):
    return df[name] if name in df.columns else pd.Series(index=df.index, dtype=float)


def relative_rank(df):
    """Ranks a peer set (e.g. one industry group from compare_stocks()) against
    each other on valuation, profitability, growth, and analyst upside -- unlike
    compare_stocks(), which just lists raw stats side by side. Needs 2+ rows;
    a dimension is skipped if fewer than 2 peers have data for it, and a peer
    missing a sub-metric just doesn't contribute it rather than being penalized.
    Risk/income fields (beta, debt/equity, current ratio, dividend yield) are
    left out on purpose -- those are a preference, not a "better/worse" axis.
    """
    empty = pd.DataFrame(columns=["rank", "out_of", "composite_percentile", "best_factor", "worst_factor"])
    if len(df) < 2:
        return empty

    pe = _col(df, "forward_pe").where(_col(df, "forward_pe").notna(), _col(df, "trailing_pe"))
    dimensions = {
        "valuation": ([pe, _col(df, "peg_ratio"), _col(df, "ev_to_ebitda")], False),
        "profitability": ([_col(df, "profit_margin"), _col(df, "roe")], True),
        "growth": ([_col(df, "revenue_growth"), _col(df, "earnings_growth")], True),
        "analyst upside": ([_col(df, "upside_to_target_pct")], True),
    }

    dim_percentiles = {}
    for name, (series_list, higher_is_better) in dimensions.items():
        sub_pcts = []
        for s in series_list:
            valid = s.dropna()
            if len(valid) < 2:
                continue
            sub_pcts.append((valid.rank(pct=True, ascending=higher_is_better) * 100).reindex(df.index))
        if sub_pcts:
            dim_percentiles[name] = pd.concat(sub_pcts, axis=1).mean(axis=1, skipna=True)

    if not dim_percentiles:
        return empty

    dim_frame = pd.DataFrame(dim_percentiles)
    result = pd.DataFrame({
        "composite_percentile": dim_frame.mean(axis=1, skipna=True).round(2),
        "best_factor": dim_frame.idxmax(axis=1, skipna=True),
        "worst_factor": dim_frame.idxmin(axis=1, skipna=True),
    }).dropna(subset=["composite_percentile"])

    result["rank"] = result["composite_percentile"].rank(method="min", ascending=False).astype(int)
    result["out_of"] = len(result)
    result = result.sort_values("rank")
    return result[["rank", "out_of", "composite_percentile", "best_factor", "worst_factor"]]


# ---------------------------------------------------------------------------
# 5) Risk scan
# ---------------------------------------------------------------------------

def risk_scan(symbol):
    stats = key_stats(symbol)
    tech = technical_snapshot(symbol, period="2y") or {}
    info = get_ticker(symbol).info

    flags = []

    def flag(code, text, **params):
        flags.append({"code": code, "params": params, "text": text})

    if stats["beta"] and stats["beta"] > 1.5:
        flag("high_beta", f"High beta ({stats['beta']:.2f}) - more volatile than the market", beta=stats["beta"])
    if stats["debt_to_equity"] and stats["debt_to_equity"] > 150:
        flag("high_leverage", f"High leverage - debt/equity {stats['debt_to_equity']:.0f}", de=stats["debt_to_equity"])
    if stats["current_ratio"] and stats["current_ratio"] < 1:
        flag("low_current_ratio",
             f"Current ratio {stats['current_ratio']:.2f} < 1 - potential short-term liquidity strain",
             cr=stats["current_ratio"])
    vol = tech.get("annualized_volatility_pct")
    if vol and vol > 45:
        flag("high_volatility", f"High annualized volatility ({vol:.0f}%)", vol=vol)
    dd = tech.get("max_drawdown_pct")
    if dd and dd < -40:
        flag("deep_drawdown", f"Deep historical drawdown seen ({dd:.0f}% peak-to-trough in the lookback window)", dd=dd)
    short_pct = info.get("shortPercentOfFloat")
    if short_pct and short_pct > 0.1:
        flag("elevated_short_interest", f"Elevated short interest ({short_pct*100:.1f}% of float)", pct=short_pct * 100)
    if stats["profit_margin"] is not None and stats["profit_margin"] < 0:
        flag("unprofitable", "Currently unprofitable (negative margin)")

    if len(flags) >= 3:
        risk_level_code, risk_level = "risk_high", "HIGH"
    elif flags:
        risk_level_code, risk_level = "risk_moderate", "MODERATE"
    else:
        risk_level_code, risk_level = "risk_low", "LOW (by these checks)"

    return {
        "symbol": symbol,
        "beta": stats["beta"],
        "annualized_volatility_pct": vol,
        "max_drawdown_pct": dd,
        "debt_to_equity": stats["debt_to_equity"],
        "current_ratio": stats["current_ratio"],
        "short_percent_of_float": short_pct,
        "risk_flags": flags,
        "risk_level": risk_level,
        "risk_level_code": risk_level_code,
    }


def print_risk_scan(symbol):
    r = risk_scan(symbol)
    print(f"{symbol}: risk level = {r['risk_level']}")
    print(f"  beta={r['beta']}, ann. volatility={r['annualized_volatility_pct']}, "
          f"max drawdown={r['max_drawdown_pct']}, D/E={r['debt_to_equity']}, current ratio={r['current_ratio']}")
    for f in r["risk_flags"]:
        print(f"  ! {f['text']}")


# ---------------------------------------------------------------------------
# 6) Long-term value-investing checklist
# ---------------------------------------------------------------------------

def long_term_value_score(symbol):
    """Checklist-style long-term/value screen. Each check is a widely-cited textbook
    heuristic, not a tuned or backtested threshold -- see docs/METRICS.md for what each
    metric actually measures and why it can mislead.

    All seven thresholds are sector-blind by design (this function doesn't know the
    symbol's industry), which is a real limitation, not an oversight: a utility carrying
    2x the debt of a software company isn't "worse", it's normal for a capital-intensive,
    regulated business with stable cash flows. Same story for current ratio in asset-light
    service businesses that run on negative working capital by design. Treat a low score
    here as "worth a closer, sector-aware look", not as a verdict on its own.

    - ROE > 15%: the common "above-average capital efficiency" bar (the Buffett-style
      heuristic). Inflates under high leverage or aggressive buybacks (shrinks the equity
      denominator without operating improvement) -- pair with the D/E check below rather
      than reading ROE alone.
    - D/E < 100 (debt roughly at or below equity): a rough "not overleveraged" line.
      Realistic normal ranges vary by an order of magnitude across sectors (utilities and
      financials routinely run well above this; asset-light software companies routinely
      run near zero).
    - Current ratio > 1.2: short-term assets moderately exceed short-term liabilities, a
      conventional liquidity-cushion threshold. Less meaningful for subscription/service
      businesses that collect cash upfront and carry deferred revenue as a liability --
      a "low" ratio there can be a sign of strength, not distress.
    """
    t = get_ticker(symbol)
    info = t.info
    fin = t.financials  # annual
    checks = []

    def add(code, label, passed, detail=""):
        # "check"/"detail" stay the plain English label print_long_term_value_score
        # and the notebook already use; "code"/"text" are additive, for i18n.reason_text()
        # to render the label (never the numeric detail) in another language.
        checks.append({
            "code": code, "params": {}, "text": label,
            "check": label, "passed": bool(passed), "detail": detail,
        })

    roe = info.get("returnOnEquity")
    add("roe_check", "ROE > 15%", roe is not None and roe > 0.15, f"ROE={roe}")

    margin = info.get("profitMargins")
    add("margin_check", "Positive profit margin", margin is not None and margin > 0, f"margin={margin}")

    fcf = info.get("freeCashflow")
    add("fcf_check", "Positive free cash flow", fcf is not None and fcf > 0, f"FCF={fcf}")

    d2e = info.get("debtToEquity")
    add("leverage_check", "Manageable leverage (D/E < 100)", d2e is not None and d2e < 100, f"D/E={d2e}")

    rev_growth = info.get("revenueGrowth")
    add("revenue_growth_check", "Revenue growing YoY", rev_growth is not None and rev_growth > 0, f"revenue growth={rev_growth}")

    earn_growth = info.get("earningsGrowth")
    add("earnings_growth_check", "Earnings growing YoY", earn_growth is not None and earn_growth > 0, f"earnings growth={earn_growth}")

    rev_row = _row(fin, "Total Revenue")
    consistent_growth = None
    if rev_row is not None and len(rev_row.dropna()) >= 3:
        vals = rev_row.dropna().iloc[::-1]  # oldest -> newest
        diffs = vals.diff().dropna()
        consistent_growth = (diffs > 0).sum() >= len(diffs) - 1  # allow one down year
    add("revenue_trend_check", "Multi-year revenue trend mostly up", consistent_growth, "based on annual revenue history")

    curr_ratio = info.get("currentRatio")
    add("current_ratio_check", "Current ratio > 1.2 (financial cushion)", curr_ratio is not None and curr_ratio > 1.2, f"current ratio={curr_ratio}")

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed >= total - 1:
        verdict_code, verdict = "verdict_strong", "Strong long-term candidate"
    elif passed >= total * 0.6:
        verdict_code, verdict = "verdict_reasonable", "Reasonable candidate, some weak spots"
    else:
        verdict_code, verdict = "verdict_weak", "Weak fit for long-term/value criteria on these checks"

    return {"symbol": symbol, "score": f"{passed}/{total}", "verdict": verdict, "verdict_code": verdict_code, "checks": checks}


def print_long_term_value_score(symbol):
    r = long_term_value_score(symbol)
    print(f"{symbol}: {r['score']} - {r['verdict']}")
    for c in r["checks"]:
        mark = "PASS" if c["passed"] else ("FAIL" if c["passed"] is False else "?")
        print(f"  [{mark}] {c['check']}  ({c['detail']})")
