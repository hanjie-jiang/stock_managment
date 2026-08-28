"""Fund/ETF handling: news-relevance screening is the wrong tool for a
diversified fund, so this gives it a deterministic, holdings-based
explanation instead (see briefing.py, which dispatches here).
"""

from .market_data import daily_price_move, get_ticker


def is_fund(symbol):
    """True for ETFs/mutual funds, where "company news" doesn't really apply --
    a diversified fund's move reflects its underlying holdings, not its own catalyst.
    """
    return get_ticker(symbol).info.get("quoteType") in ("ETF", "MUTUALFUND")


def get_fund_top_holdings(symbol, top_n=8):
    """Top holdings (symbol, name, weight) for a fund, or None if unavailable."""
    try:
        holdings_df = get_ticker(symbol).funds_data.top_holdings
    except Exception:
        return None
    if holdings_df is None or holdings_df.empty:
        return None
    return [
        {"symbol": sym, "name": row.get("Name"), "weight": float(row.get("Holding Percent"))}
        for sym, row in holdings_df.head(top_n).iterrows()
    ]


def explain_fund_move(symbol, name, fund_change_pct):
    """Deterministic (no LLM) explanation for a fund's move: which top holdings
    moved the most today, weighted by their size in the fund. More defensible
    than free-form news search, which is the wrong tool for a diversified fund --
    there usually isn't a single "catalyst" the way there is for one company.

    Returns {"explanation": str, "holdings": [...]} -- "holdings" is the full
    per-holding data (weight, today's move, weighted contribution) for an audit
    trail, same spirit as the "considered" headlines list for single stocks.
    """
    holdings = get_fund_top_holdings(symbol)
    if not holdings:
        return {
            "explanation": "This is a fund, and holdings data wasn't available to break down today's move.",
            "holdings": [],
        }

    contributions = []
    for h in holdings:
        move = daily_price_move(h["symbol"])
        if move and move.get("change_pct") is not None:
            contributions.append({
                **h,
                "change_pct": move["change_pct"],
                "weighted_contribution": h["weight"] * move["change_pct"],
            })

    if not contributions:
        return {
            "explanation": "This is a fund, and today's per-holding price moves weren't available to break it down.",
            "holdings": holdings,
        }

    contributions.sort(key=lambda c: abs(c["weighted_contribution"]), reverse=True)
    top = contributions[:3]
    parts = [
        f"{c['name']} ({c['symbol']}, {c['weight']*100:.1f}% of the fund) {c['change_pct']:+.1f}%"
        for c in top
    ]
    explanation = (
        f"{name} is a diversified fund, so it moves with its underlying holdings rather than "
        f"its own news. Today's largest weighted movers among its top holdings: {'; '.join(parts)}."
    )
    return {"explanation": explanation, "holdings": contributions}
