"""Stock research toolkit for family portfolio decisions.

Data source: yfinance, which covers US-listed stocks, Hong Kong-listed
stocks (".HK" suffix), mainland China A-shares (".SS" for Shanghai,
".SZ" for Shenzhen), and Chinese ADRs (e.g. BABA, JD, PDD) from one
free source with no API key.

Everything here is a decision-support signal built from public data,
not investment advice - numbers should be sanity-checked against the
company's actual filings before anyone acts on them.
"""

import numpy as np
import pandas as pd
import requests
import yfinance as yf

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


# ---------------------------------------------------------------------------
# Core data access
# ---------------------------------------------------------------------------

def get_ticker(symbol):
    return yf.Ticker(symbol)


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
# Daily move + news, for a "why did this move today" briefing
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


def daily_briefing_data(symbol, news_limit=6):
    """Everything needed to explain today's move: the price change + recent news."""
    return {
        "symbol": symbol,
        "price_move": daily_price_move(symbol),
        "news": _fetch_news(get_ticker(symbol), limit=news_limit),
    }


# ---------------------------------------------------------------------------
# Local LLM (Ollama) -- free, private, no API key. Used for the daily
# briefing's plain-English "why did this move" explanation.
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"


def ollama_available():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def local_llm_complete(prompt, system=None, model=OLLAMA_MODEL, timeout=30):
    """Send a prompt to a locally-running Ollama model and return its text response."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _parse_relevance_response(text, n_headlines):
    """Parse lines like '1: YES - reason' into per-headline (relevant, reason)."""
    import re

    results = [None] * n_headlines
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*[:.)]\s*(YES|NO)\b\s*[-:]?\s*(.*)", line.strip(), re.IGNORECASE)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if 0 <= idx < n_headlines:
            results[idx] = {"relevant": m.group(2).upper() == "YES", "reason": m.group(3).strip()}
    return results


def score_news_relevance(symbol, name, change_pct, news_items):
    """Ask the local model to judge, headline by headline, whether it could plausibly
    explain today's price move -- independently, not as one holistic guess.

    Returns a list aligned with news_items: [{"headline": ..., "relevant": bool,
    "reason": str}, ...]. A headline whose judgment couldn't be parsed is treated
    conservatively as not relevant, with a note saying so.
    """
    if not news_items:
        return []
    headlines_block = "\n".join(
        f"{i+1}. [{n.get('date')}] {n.get('title')} ({n.get('publisher')})"
        for i, n in enumerate(news_items)
    )
    prompt = (
        f"Company: {name} ({symbol})\n"
        f"Today's price move: {change_pct:+.2f}%\n\n"
        f"Headlines:\n{headlines_block}\n\n"
        "For EACH numbered headline, judge whether it could plausibly be a direct cause "
        "of THIS company's price move today. A headline qualifies ONLY if it is specifically "
        "about this company's own business, earnings, guidance, products, or a company-specific "
        "event -- not just its broader sector, a competitor, a supplier/customer mentioned in "
        "passing, or a generic market-wide story. Judge each headline independently; don't let "
        "one YES or NO bias the others.\n\n"
        "Reply with exactly one line per headline, in this exact format and nothing else:\n"
        "<number>: YES - <short reason>\n"
        "or\n"
        "<number>: NO - <short reason>"
    )
    system = (
        "You are a precise, skeptical financial analyst screening news for relevance. "
        "Judge each headline on its own merits -- don't default to NO out of blanket caution, "
        "and don't default to YES out of eagerness to find a story. A headline that names the "
        "company directly and describes something happening to its business (earnings, a "
        "product, a deal, regulation, a lawsuit, guidance) is a real YES even if brief."
    )
    response = local_llm_complete(prompt, system=system)
    parsed = _parse_relevance_response(response, len(news_items))
    out = []
    for i, n in enumerate(news_items):
        p = parsed[i]
        out.append({
            "headline": n,
            "relevant": bool(p and p["relevant"]),
            "reason": p["reason"] if p else "(model's judgment on this headline couldn't be parsed -- treated as not relevant)",
        })
    return out


def explain_daily_move(symbol, name, news_limit=6):
    """Two-stage, auditable explanation of today's price move:

    1. Score each recent headline's relevance to THIS company's move, independently.
    2. Synthesize a one-sentence explanation using only headlines judged relevant.

    Returns {"change_pct": float|None, "explanation": str|None, "considered": [...]} --
    "considered" is the full per-headline scoring trail, useful for showing your work
    rather than asking anyone to just trust a single free-form answer.
    """
    data = daily_briefing_data(symbol, news_limit=news_limit)
    move = data["price_move"]
    if move is None or move.get("change_pct") is None:
        return {"change_pct": None, "explanation": None, "considered": []}

    scored = score_news_relevance(symbol, name, move["change_pct"], data["news"])
    relevant = [s for s in scored if s["relevant"]]

    if not relevant:
        explanation = "No specific company news stands out -- this looks like it's just moving with the broader market."
    else:
        relevant_lines = "\n".join(
            f"- {s['headline'].get('title')} ({s['headline'].get('publisher')}): {s['reason']}"
            for s in relevant
        )
        prompt = (
            f"Company: {name} ({symbol})\n"
            f"Price change: {move['change_pct']:+.2f}%\n\n"
            f"Relevant news (already screened for being specifically about this company):\n"
            f"{relevant_lines}\n\n"
            "In ONE short, plain-English sentence for a non-technical reader, explain why "
            "this stock likely moved today, based on this news. Weigh whether the news "
            "actually seems big enough to plausibly cause a move of this size (e.g. a modest "
            "insider sale or a minor product tweak usually would NOT explain a multi-percent "
            "move by itself) -- if it seems disproportionately small, say the news may only "
            "be a partial factor rather than stating it as the full cause."
        )
        system = (
            "You write very short, honest, plain-language explanations of daily stock price "
            "moves for a non-technical family member. Respond with just the one sentence, no "
            "preamble. Don't overstate a minor news item as a full explanation for a large move."
        )
        explanation = local_llm_complete(prompt, system=system)

    return {"change_pct": move["change_pct"], "explanation": explanation, "considered": scored}


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
