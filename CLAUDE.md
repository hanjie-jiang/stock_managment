# Family Stock Tracker

Free and local only -- no paid data sources, no API keys. `yfinance` (no key) and a local
Ollama model are the only external dependencies that matter; keep it that way unless the
user explicitly decides otherwise.

## Where the reasoning lives

Rationale for design choices is written at the point of implementation -- module and
function docstrings, and comments next to the workaround they explain (e.g. the NaN-row
skip in `daily_price_move`, the layer split between `market_data.py` and `signals.py`).
Read the docstring before changing behavior; the comment explaining a workaround is the
specification for it, not incidental color.

When you add new rationale, put it at the point of implementation too. Do not create a
parallel decisions/rationale doc for it -- rationale that lives next to the code it
explains gets updated by whoever next changes that code, because it's in their diff;
rationale in a separate file doesn't, and a stale explanation is worse than no explanation
at all.

`docs/METRICS.md` is the one exception, and only for what it actually covers: it's an
educational reference (what a metric measures, why it can mislead, sector caveats), not a
record of the thresholds themselves -- those stay in `signals.py`'s own docstrings, next
to the numbers they explain.

## Ask before refactoring

"Refactoring" here means restructuring or renaming working code without a
behavior-changing reason to do it right now -- splitting a file, renaming a public
function, extracting a helper nobody asked for. Bug fixes, requested features, and edits
required to implement the current ask are not refactoring and don't need this. Ask first:
this repo's own history shows restructuring compounds fast (a package split, a later
multipage rewrite) -- worth confirming the shape before doing it, not after.

## Conventions

- No emoji, anywhere -- code, commit messages, docs, chat.
- `specs/` is the source of truth for new feature intent -- check for a relevant spec
  before designing a new feature from scratch, and write one for anything nontrivial.

## Running it

- Dashboard: `streamlit run app.py`
- Daily briefing background job: `python scripts/run_daily_briefing.py`
- Notebook: `jupyter notebook notebooks/stock_managment.ipynb`
