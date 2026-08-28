"""Stock research toolkit for family portfolio decisions.

Data source: yfinance, which covers US-listed stocks, Hong Kong-listed
stocks (".HK" suffix), mainland China A-shares (".SS" for Shanghai,
".SZ" for Shenzhen), and Chinese ADRs (e.g. BABA, JD, PDD) from one
free source with no API key.

Everything here is a decision-support signal built from public data,
not investment advice - numbers should be sanity-checked against the
company's actual filings before anyone acts on them.

Package layout (grouped by responsibility, not by feature number):
- market_data.py -- yfinance access, key stats, technicals, fundamentals,
  quarterly reports. No opinions, just "what does the data say."
- signals.py -- opinionated verdicts built on market_data: buy/sell lean,
  risk flags, long-term value checklist, side-by-side comparison.
- funds.py -- ETF/mutual fund handling (holdings-based move explanation
  instead of news search, which doesn't fit a diversified fund).
- briefing.py -- Today's Briefing: the local-LLM "why did this move"
  pipeline, dispatching to funds.py for ETFs.

Everything below is re-exported here so callers can keep doing
`import stock_toolkit as tk; tk.research(...)` regardless of which
submodule actually owns a given function.
"""

from .briefing import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    TRANSLATION_MODEL,
    daily_briefing_data,
    explain_daily_move,
    local_llm_complete,
    ollama_available,
    score_news_relevance,
    translate_to_zh,
    translation_available,
)
from .funds import explain_fund_move, get_fund_top_holdings, is_fund
from .market_data import (
    daily_price_move,
    format_financial_value,
    fundamentals,
    get_sector_industry,
    get_ticker,
    key_stats,
    price_history,
    print_quarterly_report_summary,
    print_research,
    quarterly_report_summary,
    research,
    search_symbol,
    technical_snapshot,
    to_jsonable,
)
from .signals import (
    buy_sell_signal,
    compare_stocks,
    long_term_value_score,
    print_buy_sell_signal,
    print_long_term_value_score,
    print_risk_scan,
    relative_rank,
    risk_scan,
)

__all__ = [
    "OLLAMA_MODEL",
    "OLLAMA_URL",
    "TRANSLATION_MODEL",
    "buy_sell_signal",
    "compare_stocks",
    "daily_briefing_data",
    "daily_price_move",
    "explain_daily_move",
    "explain_fund_move",
    "format_financial_value",
    "fundamentals",
    "get_fund_top_holdings",
    "get_sector_industry",
    "get_ticker",
    "is_fund",
    "key_stats",
    "local_llm_complete",
    "long_term_value_score",
    "ollama_available",
    "price_history",
    "print_buy_sell_signal",
    "print_long_term_value_score",
    "print_quarterly_report_summary",
    "print_research",
    "print_risk_scan",
    "quarterly_report_summary",
    "relative_rank",
    "research",
    "risk_scan",
    "score_news_relevance",
    "search_symbol",
    "technical_snapshot",
    "to_jsonable",
    "translate_to_zh",
    "translation_available",
]
