"""Today's Briefing: a two-stage, auditable "why did this move" explanation.

1. Score each recent headline's relevance to THIS company's move, independently
   (score_news_relevance).
2. Synthesize a one-sentence explanation using only headlines judged relevant
   (explain_daily_move).

Funds/ETFs skip straight to a holdings-based breakdown (see funds.py) --
news-relevance screening is the wrong tool for a diversified fund, which
doesn't have a single-company catalyst to find.

Runs on a local Ollama model -- free, private, no API key.
"""

import re

import requests

from .funds import explain_fund_move, is_fund
from .market_data import _fetch_news, daily_price_move, get_ticker

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


def daily_briefing_data(symbol, news_limit=6):
    """Everything needed to explain today's move: the price change + recent news."""
    return {
        "symbol": symbol,
        "price_move": daily_price_move(symbol),
        "news": _fetch_news(get_ticker(symbol), limit=news_limit),
    }


def _parse_relevance_response(text, n_headlines):
    """Parse lines like '1: YES - reason' into per-headline (relevant, reason)."""
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
    """Two-stage, auditable explanation of today's price move (see module docstring).

    Returns {"change_pct": float|None, "explanation": str|None, "considered": [...],
    "holdings": [...]} -- "considered"/"holdings" are the audit trail (whichever
    applies), useful for showing your work rather than asking anyone to just
    trust a single free-form answer.
    """
    data = daily_briefing_data(symbol, news_limit=news_limit)
    move = data["price_move"]
    if move is None or move.get("change_pct") is None:
        return {"change_pct": None, "explanation": None, "considered": [], "holdings": []}

    if is_fund(symbol):
        result = explain_fund_move(symbol, name, move["change_pct"])
        return {
            "change_pct": move["change_pct"],
            "explanation": result["explanation"],
            "considered": [],
            "holdings": result["holdings"],
        }

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

    return {"change_pct": move["change_pct"], "explanation": explanation, "considered": scored, "holdings": []}
