# Fixtures

Real `yfinance` responses, captured once and replayed offline so `stock_toolkit` can be
tested deterministically without a live network call or the day-to-day noise of real
market data.

## What's captured

One JSON file per symbol in `data/`, each holding that symbol's `.info`, 5-day and 1-year
`.history()`, quarterly/annual financials, cashflow, and the first 5 news items -- plus
top holdings for the one ETF. Symbols were picked to cover the toolkit's real edge cases,
not just a happy path:

| Symbol | Why this one |
|---|---|
| `AAPL` | Plain US large-cap -- the baseline case |
| `VOO` | ETF -- exercises `funds.py` (`is_fund`, `get_fund_top_holdings`, `explain_fund_move`) |
| `600519.SS` | China A-share |
| `0700.HK` | Hong Kong stock |
| `AMZN` | Has, in this project's own history, sometimes carried a partially-populated "placeholder" most-recent quarterly column -- see `quarterly_report_summary`'s docstring |

## Using them in a test

```python
from tests.fixtures.loader import patch_yfinance

def test_something(monkeypatch):
    patch_yfinance(monkeypatch)
    result = market_data.key_stats("AAPL")
    ...
```

`patch_yfinance` replaces `stock_toolkit.market_data.yf.Ticker` with a `FakeTicker` that
reads from the matching `data/<symbol>.json` instead of hitting the network -- everything
built on `get_ticker()` (which is everything in this toolkit) runs against the captured
snapshot unmodified. See `tests/test_market_data.py` for working examples.

## Regenerating

```bash
python tests/fixtures/capture_fixtures.py
```

Needs live network access (it's the one script in this folder that's meant to hit
`yfinance` for real). Review the diff before committing -- these are real market snapshots
that go stale and drift as `yfinance`'s own fields change, not something to regenerate
reflexively. Add a symbol to `capture_fixtures.py`'s `SYMBOLS` dict if a new test needs one
`patch_yfinance` doesn't already cover.

## Adding a new period to `.history()`

`FakeTicker.history()` only serves the periods actually captured (`5d`, `1y`). If a test
needs a different period (e.g. `5y` for the dashboard's price-history chart), add it to
`capture_fixtures.py`'s `capture()` function and re-run the capture script.
