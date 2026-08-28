"""Core data access: yfinance wrapper, key stats, technicals, fundamentals.

Everything here is a thin, cached layer over yfinance -- no analysis or
opinion, just "what does the data say." research(), buy_sell_signal()-style
verdicts live in signals.py and build on top of this module.
"""

import time

import numpy as np
import pandas as pd
import yfinance as yf

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


# ---------------------------------------------------------------------------
# Core data access
# ---------------------------------------------------------------------------

_TICKER_CACHE = {}  # symbol -> (Ticker object, fetch_time)
_TICKER_CACHE_TTL = 900  # 15 minutes


def get_ticker(symbol):
    """Return a yf.Ticker for symbol, reusing the same object for a while.

    A fresh yf.Ticker() per call means every stock_toolkit function that
    touches the same symbol (key_stats, technical_snapshot, risk_scan, ...)
    re-fetches .info/.history() independently -- fine at a handful of
    stocks, wasteful and slow at 50+. Reusing the object lets yfinance's
    own per-object caching eliminate that duplication.
    """
    now = time.time()
    cached = _TICKER_CACHE.get(symbol)
    if cached and (now - cached[1]) < _TICKER_CACHE_TTL:
        return cached[0]
    t = yf.Ticker(symbol)
    _TICKER_CACHE[symbol] = (t, now)
    return t


def get_sector_industry(symbol):
    """Lightweight sector/industry lookup (no news fetch), for grouping a watchlist."""
    info = get_ticker(symbol).info
    return {"sector": info.get("sector"), "industry": info.get("industry")}


def search_symbol(query, limit=5):
    """Resolve a company name (or partial ticker) to candidate tickers.

    Works across US, HK, and China A-share listings, e.g. search_symbol("apple")
    -> AAPL, search_symbol("tencent") -> 0700.HK, search_symbol("moutai") -> 600519.SS.
    """
    try:
        results = yf.Search(query, max_results=limit).quotes
    except Exception:
        return []
    out = []
    for r in results:
        if r.get("quoteType") != "EQUITY":
            continue
        out.append({
            "symbol": r.get("symbol"),
            "name": r.get("longname") or r.get("shortname"),
            "exchange": r.get("exchDisp"),
        })
    return out[:limit]


def to_jsonable(obj):
    """Recursively convert numpy/pandas objects to plain JSON-safe Python types."""
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, float) and np.isnan(obj):
        return None
    if hasattr(obj, "item"):  # numpy scalar fallback
        try:
            return obj.item()
        except Exception:
            return str(obj)
    if hasattr(obj, "isoformat"):  # datetime / Timestamp
        return obj.isoformat()
    return obj


def _g(d, key, default=None):
    v = d.get(key, default)
    return v if v is not None else default


def _pct_change(new, old):
    if new is None or old is None:
        return None
    if (isinstance(new, float) and np.isnan(new)) or (isinstance(old, float) and np.isnan(old)):
        return None
    if old == 0:
        return None
    try:
        return (new - old) / abs(old) * 100
    except (TypeError, ZeroDivisionError):
        return None


def format_financial_value(v):
    """Format a financial statement value for display.

    Large figures (revenue, income) get comma-separated whole numbers;
    small ones (EPS) keep 2 decimal places instead of rounding to a
    near-meaningless integer.
    """
    if v is None:
        return None
    if abs(v) < 1000:
        return f"{v:,.2f}"
    return f"{v:,.0f}"


def _row(df, *names):
    """First matching row (by label) from a yfinance statement DataFrame."""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


# ---------------------------------------------------------------------------
# 1) Research - company profile & recent news
# ---------------------------------------------------------------------------

def _fetch_news(ticker_obj, limit=5):
    news_items = []
    try:
        for n in (ticker_obj.news or [])[:limit]:
            c = n.get("content", n) if isinstance(n, dict) else {}
            provider = c.get("provider")
            news_items.append({
                "title": c.get("title"),
                "publisher": provider.get("displayName") if isinstance(provider, dict) else c.get("publisher"),
                "date": c.get("pubDate") or c.get("providerPublishTime"),
            })
    except Exception:
        pass
    return news_items


def research(symbol):
    t = get_ticker(symbol)
    info = t.info
    profile = {
        "symbol": symbol,
        "name": info.get("longName"),
        "exchange": info.get("exchange"),
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "market_cap": info.get("marketCap"),
        "website": info.get("website"),
        "business_summary": info.get("longBusinessSummary"),
    }
    profile["recent_news"] = _fetch_news(t, limit=5)
    return profile


def print_research(symbol):
    p = research(symbol)
    print(f"{p['name']} ({p['symbol']}) - {p['exchange']} | {p['currency']}")
    print(f"Sector: {p['sector']} / {p['industry']} | Country: {p['country']}")
    print(f"Market cap: {p['market_cap']:,}" if p["market_cap"] else "Market cap: n/a")
    print(f"Employees: {p['employees']:,}" if p["employees"] else "")
    print(f"\n{p['business_summary']}\n")
    print("Recent headlines:")
    for n in p["recent_news"]:
        print(f"  - {n['title']} ({n['publisher']})")


# ---------------------------------------------------------------------------
# Shared: key stats snapshot used by several features
# ---------------------------------------------------------------------------

def key_stats(symbol):
    t = get_ticker(symbol)
    info = t.info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    target = info.get("targetMeanPrice")
    return {
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName"),
        "currency": info.get("currency"),
        "price": price,
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
        "price_to_book": info.get("priceToBook"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "profit_margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "free_cashflow": info.get("freeCashflow"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "beta": info.get("beta"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "analyst_target_mean": target,
        "analyst_recommendation": info.get("recommendationKey"),
        "num_analyst_opinions": info.get("numberOfAnalystOpinions"),
        "upside_to_target_pct": _pct_change(target, price),
    }


# ---------------------------------------------------------------------------
# Technical helpers used by buy/sell timing
# ---------------------------------------------------------------------------

def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def price_history(symbol, period="1y"):
    """Daily closing price series, for charting (technical_snapshot() only
    returns summary stats, not the underlying series)."""
    t = get_ticker(symbol)
    hist = t.history(period=period, auto_adjust=True)
    if hist.empty:
        return None
    return hist["Close"]


def technical_snapshot(symbol, period="1y"):
    t = get_ticker(symbol)
    hist = t.history(period=period, auto_adjust=True)
    if hist.empty:
        return None
    close = hist["Close"]
    sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    rsi14 = _rsi(close).iloc[-1]
    last_price = close.iloc[-1]
    high52 = close.max()
    low52 = close.min()
    range_position = (last_price - low52) / (high52 - low52) * 100 if high52 > low52 else None
    daily_ret = close.pct_change().dropna()
    annualized_vol = daily_ret.std() * np.sqrt(252) * 100 if not daily_ret.empty else None
    running_max = close.cummax()
    drawdown = (close / running_max - 1) * 100
    max_drawdown = drawdown.min()
    return {
        "last_price": last_price,
        "sma50": sma50,
        "sma200": sma50 if sma200 is None else sma200,
        "rsi14": rsi14,
        "range_position_pct": range_position,
        "annualized_volatility_pct": annualized_vol,
        "max_drawdown_pct": max_drawdown,
        "above_sma50": (last_price > sma50) if sma50 else None,
        "above_sma200": (last_price > sma200) if sma200 else None,
    }


# ---------------------------------------------------------------------------
# Daily move, for a "why did this move today" briefing
# ---------------------------------------------------------------------------

def daily_price_move(symbol):
    """Today's (or most recent session's) price change vs. the prior close."""
    t = get_ticker(symbol)
    hist = t.history(period="5d", auto_adjust=True)
    if hist.empty:
        return None
    # The most recent row can be a not-yet-populated placeholder (NaN OHLC) when
    # that market's session hasn't closed/reported yet -- drop incomplete rows.
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 2:
        return None
    last = hist.iloc[-1]
    prev_close = hist.iloc[-2]["Close"]
    last_date = hist.index[-1]
    return {
        "date": str(last_date.date()) if hasattr(last_date, "date") else str(last_date),
        "close": float(last["Close"]),
        "prev_close": float(prev_close),
        "change_pct": _pct_change(float(last["Close"]), float(prev_close)),
        "day_high": float(last["High"]),
        "day_low": float(last["Low"]),
    }


# ---------------------------------------------------------------------------
# 7) Fundamental analysis - full statements
# ---------------------------------------------------------------------------

def fundamentals(symbol, freq="annual"):
    t = get_ticker(symbol)
    if freq == "quarterly":
        return {
            "income_statement": t.quarterly_financials,
            "balance_sheet": t.quarterly_balance_sheet,
            "cashflow": t.quarterly_cashflow,
        }
    return {
        "income_statement": t.financials,
        "balance_sheet": t.balance_sheet,
        "cashflow": t.cashflow,
    }


# ---------------------------------------------------------------------------
# 8) Quarterly report reader - QoQ / YoY deltas on key lines
# ---------------------------------------------------------------------------

_KEY_LINES = [
    "Total Revenue", "Gross Profit", "Operating Income", "Net Income",
    "Diluted EPS", "EBITDA",
]

def quarterly_report_summary(symbol):
    t = get_ticker(symbol)
    inc = t.quarterly_financials
    cf = t.quarterly_cashflow
    if inc is None or inc.empty:
        return {"symbol": symbol, "error": "No quarterly data available"}

    cols = list(inc.columns)  # most recent first

    # The most recent column can be a partially-populated placeholder -- e.g.
    # only Diluted EPS reported so far, full income statement not yet
    # backfilled. Skip forward to the first column where most of the tracked
    # line items actually have data, so the whole report comes from one
    # internally-consistent quarter rather than mixing a stale statement with
    # a fresh EPS figure.
    def _is_populated(col):
        values = [_row(inc, name).get(col) for name in _KEY_LINES if _row(inc, name) is not None]
        non_nan = [v for v in values if not pd.isna(v)]
        return len(values) > 0 and len(non_nan) >= max(1, len(values) // 2)

    skipped = 0
    for i, col in enumerate(cols):
        if _is_populated(col):
            skipped = i
            cols = cols[i:]
            break
    else:
        return {"symbol": symbol, "error": "No populated quarterly data available"}

    latest_label = cols[0]
    prior_label = cols[1] if len(cols) > 1 else None
    yoy_label = cols[4] if len(cols) > 4 else None

    lines = []
    for name in _KEY_LINES:
        row = _row(inc, name)
        if row is None:
            continue
        latest = row.get(latest_label)
        prior = row.get(prior_label) if prior_label is not None else None
        yoy = row.get(yoy_label) if yoy_label is not None else None
        lines.append({
            "line_item": name,
            "latest_quarter": latest,
            "qoq_change_pct": _pct_change(latest, prior),
            "yoy_change_pct": _pct_change(latest, yoy),
        })

    fcf_latest = None
    if cf is not None and not cf.empty:
        ocf_row = _row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex_row = _row(cf, "Capital Expenditure")
        if ocf_row is not None and capex_row is not None:
            ocf = ocf_row.get(latest_label)
            capex = capex_row.get(latest_label)
            if ocf is not None and capex is not None:
                fcf_latest = ocf + capex  # capex is usually negative

    result = {
        "symbol": symbol,
        "latest_quarter_end": str(latest_label.date()) if hasattr(latest_label, "date") else str(latest_label),
        "lines": lines,
        "free_cash_flow_latest_quarter": fcf_latest,
    }
    if skipped > 0:
        result["note"] = (
            f"This data source is missing full financial-statement detail for the "
            f"{skipped} most recent quarter(s) -- showing the latest quarter with "
            f"complete figures instead. Check the company's own investor relations "
            f"filings for anything more current."
        )
    return result


def print_quarterly_report_summary(symbol):
    r = quarterly_report_summary(symbol)
    if "error" in r:
        print(f"{symbol}: {r['error']}")
        return
    print(f"{symbol} - quarter ended {r['latest_quarter_end']}")
    if r.get("note"):
        print(f"  NOTE: {r['note']}")
    for l in r["lines"]:
        qoq = f"{l['qoq_change_pct']:+.1f}% QoQ" if l["qoq_change_pct"] is not None else "QoQ n/a"
        yoy = f"{l['yoy_change_pct']:+.1f}% YoY" if l["yoy_change_pct"] is not None else "YoY n/a"
        value = format_financial_value(l["latest_quarter"]) or "n/a"
        print(f"  {l['line_item']:<18} {value:>18}   {qoq:>14}   {yoy:>14}")
    if r["free_cash_flow_latest_quarter"] is not None:
        print(f"  {'Free Cash Flow':<18} {format_financial_value(r['free_cash_flow_latest_quarter']):>18}")
