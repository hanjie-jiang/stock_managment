# Family Stock Tracker

A stock research toolkit for the family, covering both US and China-listed
stocks (A-shares, Hong Kong, and Chinese ADRs). Two ways to use it:

- **`app.py`** -- a large-print Streamlit dashboard with a plain-English chat
  assistant. Built for non-technical family members: search a stock by
  company name, see a clear buy/sell signal, risk flags, and a long-term
  value checklist, or just ask a question in the chat box.
- **`stock_managment.ipynb`** -- a Jupyter notebook covering the same
  capabilities for anyone who prefers working in code.

Both are powered by **`stock_toolkit.py`**, a small Python module built on
[`yfinance`](https://pypi.org/project/yfinance/) (free, no API key) that
covers:

1. Company research (profile, sector, recent news)
2. Buy-in signal (is it worth buying now?)
3. Sell-timing signal (is now a good time to sell?)
4. Side-by-side comparison across stocks
5. Risk scanning (volatility, leverage, drawdown, liquidity)
6. Long-term / value-investing checklist
7. Full fundamentals (income statement, balance sheet, cash flow)
8. Quarterly report reader (QoQ / YoY change on key line items)

> Everything here is data + heuristics, not investment advice -- verify
> anything decision-critical against the company's actual filings.

## Setup

Requires Python 3.11+.

**Windows (PowerShell), one step:**

```powershell
.\setup.ps1
```

**Manual setup (any OS):**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

Then edit `.env` and add your Anthropic API key (get one at
[console.anthropic.com](https://console.anthropic.com/settings/keys)) --
this is only needed for the chat assistant in `app.py`; the dashboard and
notebook otherwise work with no key or account setup at all.

## Running it

**Dashboard (recommended for most family members):**

```bash
streamlit run app.py
```

Opens in your browser. Search for a company by name in the sidebar to add
it to your watchlist -- no need to know ticker symbols.

**Notebook (for anyone comfortable with code):**

```bash
jupyter notebook notebooks/stock_managment.ipynb
```

## Ticker format reference

- US: `AAPL`, `MSFT`
- China A-share: `600519.SS` (Shanghai), `000858.SZ` (Shenzhen)
- Hong Kong: `0700.HK`
- China ADR (trades in the US): `BABA`, `JD`, `PDD`

The dashboard's search box handles this automatically -- these formats
only matter if you're using `stock_toolkit.py` directly.

## Project files

| File | Purpose |
|---|---|
| `stock_toolkit.py` | Core data + analysis functions, reused by both the app and the notebook |
| `app.py` | Streamlit dashboard + chat |
| `notebooks/stock_managment.ipynb` | Notebook walkthrough of all 8 capabilities |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your local `.env` (never commit the real `.env`) |
