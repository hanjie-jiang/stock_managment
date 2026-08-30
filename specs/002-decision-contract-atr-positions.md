# 002-decision-contract-atr-positions

## Problem

`buy_sell_signal()` gives a directional lean ("Leans BUY" / "Leans SELL" / "Mixed") and a
list of reasons, but nothing actionable: no price level to act at, no level that says "this
thesis was wrong," no sense of over what timeframe the signal is supposed to play out, and
no guidance on sizing (going all-in on the first "Leans BUY" is not how anyone here actually
invests). Separately, there's nowhere to record what a family member actually holds --
shares, cost basis, why they bought it -- so a signal today can't be checked against a real
position, and the reason for a purchase six months ago is only as durable as someone's
memory.

Session 5 identified three backlog items -- entry/invalidation/horizon/sizing fields on
`buy_sell_signal`, an ATR calculation to anchor them in each stock's own volatility instead
of arbitrary percentages, and a `positions.json` to hold the cost-basis/thesis side -- and
concluded they're coupled enough to spec as one feature: ATR is what makes the decision
fields computable rather than arbitrary, and both the signal and the position sit next to
each other in the dashboard. This also resolves the Session 4 backlog item that asked to
scope a "strategy-like" feature without specifics.

## Scope

**In scope:**
- ATR(14) added to `technical_snapshot()`.
- `buy_sell_signal()` gains `entry_zone`, `invalidation_level`, `invalidation_condition`,
  `suggested_first_tranche_pct`. (The `horizon` field originally scoped here is
  superseded by specs/003-horizon-tagged-signals.md -- see Design.)
- New `data/positions_store.py` + gitignored `data/positions.json`: one record per symbol
  (shares, cost basis, purchase date, free-text thesis and sell-trigger notes).
- Dashboard: position info shown next to live price for symbols the family actually holds,
  with an add/edit/remove flow mirroring the existing watchlist UI.
- A new `docs/METRICS.md` entry for ATR, following that file's existing "what it measures,
  why it can mislead" format (see `CLAUDE.md`).

**Out of scope:**
- Any broker/execution integration -- already rejected in the Session 5 discussion
  (credential exposure for a family-distributed app; doesn't cover the family's actual
  HK/A-share holdings). `positions.json` is filled in by hand.
- Automated alerting when `invalidation_level` is breached -- a natural follow-on once this
  exists, but a separate feature (would need a background job and a notification channel,
  neither of which exist yet).
- Backtesting whether these entry/invalidation formulas actually work historically -- the
  existing "Backtested strategy engine" deferred backlog item already covers building that
  capability; this spec produces heuristic, clearly-labeled numbers in the same spirit as
  `long_term_value_score`'s checklist, not validated ones.
- Multi-lot / tax-lot tracking (buying the same symbol at different prices on different
  dates as separate records) -- one record per symbol with a single average cost basis.
  Flagged in Open Questions since it's a real simplification, not an oversight.

## Design

### ATR(14) in `technical_snapshot()`

Average True Range measures how much a stock typically moves in a single session,
independent of direction -- it's what lets the entry/invalidation levels below scale to
each stock's own volatility instead of using one arbitrary percentage for a sleepy utility
and a volatile China ADR alike.

True range for a session is `max(high - low, abs(high - prev_close), abs(low - prev_close))`;
ATR14 is the 14-session rolling mean of true range. `technical_snapshot()` currently only
pulls `hist["Close"]` -- this needs `hist["High"]` and `hist["Low"]` too. Following the same
pattern the sma200 fix just established: **no silent fallback** -- ATR14 is `None` when
there are fewer than 15 sessions of history, exactly like `sma50`/`sma200` return `None`
under their own thresholds, never a substituted value.

New fields on the `technical_snapshot()` return dict:
- `atr14`: absolute value, same currency/unit as price.
- `atr14_pct`: `atr14 / last_price * 100` -- the version the decision-contract math below
  actually uses, since "1.5 ATR" means very different things at $8 and $800.

### Decision-contract fields on `buy_sell_signal()`

This is the real design fork, worth confirming before writing code -- the specific
multipliers below are illustrative heuristics, not backtested, in the same spirit as
`long_term_value_score`'s docstring already disclaims for its own thresholds.

**Superseded by specs/003-horizon-tagged-signals.md:** `lean` and `score` below now refer
to specs/003's fundamentals-only `lean`/`fundamental_score` (stable across days, moves
only when the underlying fundamentals change), not the original pooled score this spec
was first written against -- see specs/003's Design section for why. This spec no longer
computes its own `horizon` field; specs/003 provides `lean` (long-term) and
`technical_read` (short-term) directly, and 002 only needs the former to gate
`entry_zone`/`suggested_first_tranche_pct`.

**Recommended: ATR-anchored, tied to trend structure where one exists.**

- `entry_zone`: only populated when `lean == "Leans BUY"` (a SELL or Mixed/HOLD lean has
  nothing to enter). `[last_price - 1.0*atr14, last_price + 0.5*atr14]` -- a band around
  today's price sized to the stock's own daily noise, wide enough that a single day's wiggle
  doesn't fall outside it, narrow enough to still mean something.
- `invalidation_level` / `invalidation_condition`: `last_price - 2.0*atr14` by default
  ("daily close falls below {level}, roughly a 2-day-average move against the entry").
  If `sma200` exists and sits *above* that level, use `sma200 * 0.99` instead and describe
  it as "daily close falls below the 200-day moving average ({level})" -- a trend-line break
  is a more meaningful reason to be wrong than an arbitrary multiple of daily noise, when
  the two disagree. Computed whenever `above_sma200`/`atr14` are available, regardless of
  lean (a SELL-leaning stock the family already holds still benefits from an invalidation
  reference, even with no `entry_zone`).
- `suggested_first_tranche_pct`: only populated when `lean == "Leans BUY"`. Combines
  conviction (`|score|`) and relative volatility (`atr14_pct`): `50%` if `score >= 3` and
  `atr14_pct < 3`; `25%` if `atr14_pct > 6` (high relative volatility caps the first tranche
  regardless of score); `33%` otherwise. The idea is scaling in, not "how much to own
  total" -- a smaller first tranche for a choppier stock, a larger one when both conviction
  and calm volatility line up. Note: `score` here is now `fundamental_score` (max
  magnitude 4, per specs/003), not the original pooled score (max magnitude 6) this
  breakpoint was first written against -- `score >= 3` is a proportionally higher bar
  than it was when this spec was drafted; worth re-checking against real data once
  specs/003 ships rather than assuming the old breakpoint still lands right.

**Alternative: fixed, symbol-agnostic numbers** -- e.g. always `+-5%` for `entry_zone`,
always `-10%` for `invalidation_level`, always `33%` first tranche. Simpler to implement and
to explain to a non-technical user, but a fixed percentage means something very different
for a low-volatility utility than for a China ADR that moves 5% most weeks -- which is the
exact problem ATR exists to solve, so this alternative mostly defeats the point of adding
ATR at all. Listed for completeness, not recommended.

### `data/positions.json`

`data/positions_store.py` follows `data/watchlist_store.py`'s exact pattern: gitignored
`data/positions.json`, loaded/saved as a flat list of dicts. Unlike the watchlist, **no
default seed data** -- a position is real money, there's nothing sensible to default to,
so it starts as `[]`.

```json
{"symbol": "AAPL", "shares": 10, "cost_basis": 185.20, "purchase_date": "2026-03-14",
 "thesis": "...", "sell_trigger": "..."}
```

One record per symbol (shares + a single average cost basis across all purchases), not a
tax-lot ledger -- see Open Questions. `thesis` and `sell_trigger` are free text the family
member writes themselves, distinct from -- and shown alongside, not mixed with -- the
*computed* `invalidation_level`/`invalidation_condition` above. Session 5's backlog used the
name "invalidator" for this human field; renaming it to `sell_trigger` here to avoid reading
as the same thing as the computed `invalidation_level` (flagged in Open Questions since it's
a naming change from what was written down previously).

`data/positions.json` added to `.gitignore` next to the existing `data/watchlist.json`
line -- same reasoning (per-install real data, not code), and if anything a stronger case
for gitignoring since cost basis is more sensitive than a list of tickers someone follows.

### Dashboard

**Overview tab**, next to the existing price metric: if `positions_store` has a record for
the selected symbol, a small block showing shares, cost basis, unrealized gain/loss (both
$ and %, computed against `stats["price"]`), purchase date, and the `thesis`/`sell_trigger`
text. If no record exists, a collapsed "Add a position" expander with the same fields,
mirroring `render_sidebar`'s "Add a stock" flow. Edit/remove reuses the confirm-before-delete
pattern `render_sidebar` already has for watchlist removal (added in Session 4 after a real
accidental-data-loss bug) -- positions hold real financial data, at least as worth protecting
from a stray click as the watchlist.

**"Why?" tab**: `entry_zone`, `invalidation_level`/`invalidation_condition`, `horizon`, and
`suggested_first_tranche_pct` render right after the existing bullish/bearish points list,
each only shown when not `None` (a SELL-leaning stock shows the invalidation reference and
horizon but no entry zone or tranche size, per the Design section above).

## Non-technical-user impact

The dad's install gains a per-stock block showing what he actually owns and whether he's up
or down, right next to the price he already looks at -- no new concept beyond "shares" and
"cost", both filled in once when he adds a position. The "Why?" tab's new fields (entry
zone, invalidation level, first-tranche size -- horizon now comes from
specs/003-horizon-tagged-signals.md instead) are the more novel piece: they read as
plain sentences with a number and a reason ("daily close falls below $142.10, the 200-day
average"), not jargon, but they are new ideas (scaling in, a specific dollar level to be
"wrong" at) that didn't exist in the app before -- worth a short plain-language explainer
line under that section the first time it ships, e.g. "This isn't a prediction -- it's one
reasonable way to think about size and risk, based on this stock's own typical daily
swings." No new failure modes beyond the usual "yfinance/Ollama unreachable" -- ATR uses the
same `hist` object `technical_snapshot()` already fetches, no new network call.

## Acceptance criteria

- `technical_snapshot()` returns `atr14` and `atr14_pct`, both `None` (never a substituted
  value) when there are fewer than 15 sessions of history.
- `buy_sell_signal()` returns `entry_zone` (a `[low, high]` pair) and
  `suggested_first_tranche_pct` only when `lean == "Leans BUY"`; both `None` otherwise.
- `buy_sell_signal()` returns `invalidation_level` and `invalidation_condition` whenever
  `atr14`/`above_sma200` are available, independent of lean.
- `print_buy_sell_signal()` and any other existing consumer of `buy_sell_signal()`'s return
  dict continue to work unchanged -- new keys are additive, nothing existing is renamed or
  removed.
- `data/positions.json` is created on first write (like `watchlist.json`), gitignored,
  defaults to an empty list (no seed data).
- The dashboard's Overview tab shows shares/cost-basis/unrealized-gain for a symbol with a
  position on file, and an "Add a position" form for one without.
- Removing a position requires the same confirm-before-delete step the watchlist already
  has.
- `docs/METRICS.md` gains an ATR entry under "## Technicals" describing what it measures and
  its caveats (lagging, a volatility read not a directional one); the actual multipliers
  used stay in `signals.py`'s docstring, per `CLAUDE.md`'s convention.

## Open questions

- **Confirm this spec now depends on specs/003-horizon-tagged-signals.md shipping
  first.** `entry_zone`/`suggested_first_tranche_pct`/`horizon`-gating all read `lean`,
  which specs/003 redefines from a pooled score to a fundamentals-only one -- implementing
  002 against the current `lean` (pooled, flips daily per the user's original complaint)
  and then re-wiring it once 003 lands is possible but means doing the gating logic twice;
  implementing 003 first and building 002 directly against the stable `lean` avoids that
  rework. Recommendation is 003 before 002.
- **Confirm the entry/invalidation/tranche formula** (ATR-anchored, as recommended above)
  before implementation -- the specific multipliers (1.0/0.5/2.0 x ATR, the tranche-pct
  breakpoints) are a first pass, not backtested, and the `score >= 3` tranche breakpoint
  specifically needs re-checking against specs/003's narrower `fundamental_score` range
  (see Design note above).
- **Confirm single average-cost-basis-per-symbol is sufficient** rather than a full
  multi-lot ledger -- a family member who bought the same stock twice at different prices
  would need to average it themselves before entering it.
- **Confirm renaming the human-written field from "invalidator" (Session 5's backlog
  wording) to `sell_trigger`** in `positions.json`, to avoid reading as the same thing as
  the computed `invalidation_level`/`invalidation_condition`.
- **Confirm where the position editor lives** -- this spec proposes inline in the Overview
  tab (next to price, where it's most relevant); a dedicated "Positions" section/page is the
  alternative if the Overview tab gets too busy once this and the bilingual toggle both
  land.
