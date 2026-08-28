# Family Stock Tracker

A stock research toolkit for the family, covering both US and China-listed
stocks (A-shares, Hong Kong, and Chinese ADRs). Two ways to use it:

- **`app.py`** -- a large-print Streamlit dashboard. Built for non-technical
  family members: search a stock by company name, see a clear buy/sell
  signal, risk flags, a long-term value checklist, and a daily "why did
  this move" briefing.
- **`stock_managment.ipynb`** -- a Jupyter notebook covering the same
  capabilities for anyone who prefers working in code.

Both are powered by **`stock_toolkit/`**, a small Python package built on
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
9. Today's Briefing -- a daily "why did this stock move" explanation, generated
   locally by [Ollama](https://ollama.com) (free, private, no API key)

> Everything here is data + heuristics, not investment advice -- verify
> anything decision-critical against the company's actual filings.

## For a family member (no coding required)

If you just want to use the dashboard on your own PC, without touching any
code:

1. On the GitHub page for this repo, click the green **Code** button, then
   **Download ZIP**.
2. Unzip it anywhere (e.g. your Desktop).
3. Double-click **`Install.bat`** inside the unzipped folder.
   - If Windows shows a blue "Windows protected your PC" screen, click
     **More info** then **Run anyway** -- this is normal for a downloaded
     script and safe for a file you trust.
   - Click **Yes** on any permission prompts.
   - This installs Python and [Ollama](https://ollama.com) if you don't
     already have them, sets up the app, and downloads the local AI model
     (about 5 GB -- this is the slow part, let it finish).
4. When it's done, look for a **"Family Stock Dashboard"** icon on your
   Desktop. Double-click it any time to open the dashboard in your browser.
   Keep that window open while you're using it; closing it stops the app.

The installer also schedules the daily briefing to prepare itself every
morning at 7am, so it's usually ready before you open the app.

The dashboard starts with a small 5-stock demo watchlist. To get the same
watchlist as everyone else in the family, ask whoever set this up to send
you their `storage/watchlist.json` file to drop into your `storage/`
folder -- or just add the same stocks yourself using the search box in the
sidebar.

## Setup (for development)

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
```

The dashboard and notebook work immediately with no account or API key --
everything is either free (`yfinance`) or local (Ollama).

**Optional: Today's Briefing** (the daily "why did this stock move"
explanation) needs [Ollama](https://ollama.com) running locally:

```bash
winget install Ollama.Ollama      # or download from ollama.com
ollama pull llama3.1:8b
```

Everything else on the dashboard works without this -- Today's Briefing just
shows a setup reminder instead until Ollama is running.

**If your watchlist is large (20+ stocks):** Today's Briefing needs 2 local-LLM
calls per stock, which adds up. Instead of generating it live on every page
load, pre-generate it once a day as a background job:

```bash
python scripts/run_daily_briefing.py
```

The dashboard then reads instantly from the cache it writes
(`storage/briefing_cache.json`). Anything missing/stale can still be
generated on-demand from a button in the app. To run this automatically
every morning on Windows, register a scheduled task (once):

```powershell
schtasks /create /tn "StockTrackerBriefing" /tr "'C:\path\to\.venv\Scripts\python.exe' 'C:\path\to\scripts\run_daily_briefing.py'" /sc daily /st 07:00
```

(adjust the paths to match your setup; remove with `schtasks /delete /tn "StockTrackerBriefing"`)

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
only matter if you're using `stock_toolkit` directly.

## Watchlists of any size

The watchlist persists to `storage/watchlist.json` (survives restarts) and is
grouped by industry everywhere -- sidebar, Compare tab, Today's Briefing --
so it stays usable whether you're tracking 5 stocks or 50+. Sector/industry
is looked up once per stock (when it's added) and cached in that file, not
refetched on every page load.

## Project layout

```
Install.bat                One-time setup for a family member's own PC (no coding)
Launch-Dashboard.bat       Opens the dashboard -- what the Desktop shortcut runs
app.py                    Streamlit dashboard (entry point: streamlit run app.py)
stock_toolkit/            Core data + analysis package, reused by the app, the
                           notebook, and the background briefing job
  market_data.py            yfinance access, key stats, technicals, fundamentals,
                             quarterly reports -- no opinions, just "what the data says"
  signals.py                 Opinionated verdicts built on market_data: buy/sell lean,
                             risk flags, long-term value checklist, comparison
  funds.py                   ETF/mutual fund handling (holdings-based move explanation)
  briefing.py                 Today's Briefing: the local-LLM "why did this move" pipeline
storage/                  Local JSON persistence
  watchlist_store.py         Persists the watchlist to watchlist.json (committed)
  briefing_store.py           Reads/writes the Today's Briefing cache (gitignored)
  briefing_history.py         Appends each day's briefing to a permanent log (committed)
scripts/
  run_daily_briefing.py      Background job: pre-generates Today's Briefing for the
                             whole watchlist (see "Optional: Today's Briefing" above)
  install_dashboard.ps1      Installer logic behind Install.bat
notebooks/
  stock_managment.ipynb      Notebook walkthrough of all capabilities
requirements.txt
```

`stock_toolkit`'s `__init__.py` re-exports everything, so both the app and
the notebook just do `import stock_toolkit as tk` / `import stock_toolkit as st`
without needing to know which submodule a given function actually lives in.

## Today's Briefing history

`storage/briefing_cache.json` only ever holds *today's* briefings -- it's
overwritten daily and gitignored because it's trivially regenerable.
Every briefing that gets generated (by the background job or the app's
"generate missing" button) is also appended to
`storage/briefing_history.jsonl`, a permanent, append-only log (one JSON
line per day per stock: date, price move, and the explanation/headlines or
fund holdings behind it). It's **not** gitignored, so committing the repo
backs it up -- unlike the cache, a day's headlines can't be refetched once
they scroll out of Yahoo Finance's news feed, so this is the only copy.

Currently this is archive-only: it preserves what the briefing said, but
doesn't compare that against what the stock did afterward. Actively
calibrating the explanations against realized forward performance (e.g.
"was the news that seemed to explain a move actually followed by more
movement in that direction, or did it fade") would need a separate
backfill job and was deliberately deferred -- worth revisiting once
there's enough history to make it useful.
