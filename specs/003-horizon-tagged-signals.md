# 003-horizon-tagged-signals

## Problem

`buy_sell_signal()`'s headline `lean` pools every check into one
`score = len(bullish) - len(bearish)` thresholded at +-2 -- checks that move on price action
alone and can flip from a single day's close (RSI14, 52-week range position, SMA trend)
sit in the same score as checks that only change when a new quarterly print or analyst
note lands (analyst upside, forward/trailing P/E, revenue/earnings growth). Because the
fast checks can push the pooled score across the +-2 threshold on their own, the single
lean can flip between "Leans BUY" / "Mixed/HOLD" / "Leans SELL" day to day even though
nothing about the long-term case changed.

Raised directly by the user: "this signal should be for long term keep or sell, instead
of changing every day." Session 5's backlog already named this gap ("horizon-tagged
signals -- each bullish/bearish entry carries a horizon, score computed per horizon
instead of pooled") but it was never spec'd. specs/002 later added a lightweight
`horizon` field that labels which bucket of checks fired -- but it still reads off the
same pooled score, so it describes the noise without removing it (see Design).

Discussion while scoping this surfaced two more real gaps, both folded into this spec
rather than left as follow-ups, since they're the same underlying problem (jargon and
noise standing in for a clear long-term signal a non-technical family member can trust):
- `long_term_value_score()`'s `verdict` and `buy_sell_signal()`'s `lean` already answer
  two genuinely different questions ("is this a good business" vs. "is now a good price
  relative to expectations") but the dashboard's labels for them (`verdict`, `lean`) are
  developer jargon that mean nothing to the family reading them.
- Threshold-based checks (RSI, 52-week range, moving averages, ROE, D/E, etc.) are shown
  as bare numbers and category words ("oversold", "Manageable leverage") with no visible
  criteria -- a family member has no way to know what "oversold" or "ROE > 15%" actually
  means without reading `stock_toolkit/signals.py`'s source, which they never will.

## Scope

**In scope:**
- Tag each existing bullish/bearish check in `buy_sell_signal()` with the horizon bucket
  it already conceptually belongs to (technical vs. fundamental -- the same split
  specs/002 used for its now-superseded `horizon` field).
- Compute two independent scores instead of one pooled score: a stable, fundamentals-only
  `lean` (score threshold +-2) and a separate `technical_read` (short-term, expected to
  change day to day).
- User-facing labels, replacing bare jargon: `long_term_value_score()`'s existing
  dashboard label **"Long-Term Fit"** stays unchanged; `buy_sell_signal()`'s banner is
  relabeled **"Right Now"**; the new `technical_read` is surfaced as **"Today's Price
  Action"**, shown as a small caption/expander under the Right Now banner (not a fourth
  equal-weight metric tile).
- Inline plain-language criteria explainers for every threshold-based check shown in the
  dashboard -- not just the three technical ones this spec adds, but also
  `long_term_value_score()`'s existing checklist (ROE, margin, FCF, D/E, current ratio,
  revenue trend) and `buy_sell_signal()`'s fundamental bullets (P/E comparison, analyst
  upside) -- see Design.
- Update `print_buy_sell_signal()` and the dashboard's Why? tab to show `lean` and
  `technical_read` as two clearly separate things.
- Remove specs/002's two-bucket `horizon` field (superseded here) and re-anchor 002's
  `entry_zone`/`invalidation_level`/`suggested_first_tranche_pct` gating to this spec's
  fundamentals-only `lean`.

**Out of scope:**
- Merging `long_term_value_score()`'s `verdict` and `buy_sell_signal()`'s `lean` into one
  score -- considered and explicitly rejected during scoping. They measure different
  things (business quality with no price input, vs. valuation/expectations with no
  quality input) and collapsing them into one number would lose a real, meaningful
  distinction ("a wonderful business at a bad price" and "a cheap but weak business" are
  both real, different situations a family member should be able to see separately).
- Finer-grained horizon weighting beyond the existing two buckets (e.g. distinguishing
  RSI's few-day horizon from SMA200's six-month one) -- still just technical vs.
  fundamental; a finer breakdown is a future refinement if two buckets prove too coarse.
- Changing which checks exist or their individual thresholds (RSI 30/70, range position
  25/90, ROE 15%, etc.) -- this spec only changes how checks are combined and explained,
  not what they detect.
- Backtesting whether fundamentals-only scoring predicts outcomes better than the pooled
  score did -- same deferred "Backtested strategy engine" backlog item specs/002 already
  deferred to; this produces a clearly-labeled heuristic split, not a validated one.

## Design

### Two scores instead of one

Split along the same line specs/002 already drew for its now-removed `horizon` field:
- `fundamental_score`: `analyst_upside`/`analyst_downside`, `forward_pe_below_trailing`/
  `forward_pe_above_trailing`, `negative_revenue_growth`, `negative_earnings_growth`
  (`signals.py:34-48,73-78`) -- up to 4 checks, none of which move without a new
  quarterly print or a new analyst target.
- `technical_score`: `near_52w_low`/`near_52w_high`, `rsi_oversold`/`rsi_overbought`,
  `above_both_sma`/`below_both_sma` (`signals.py:50-71`) -- each can flip from a single
  day's close. SMA trend stays in this bucket (matching specs/002's original split):
  it's priced daily, even though a 50/200-day average moves slower in practice than RSI.

`lean`/`lean_code` (same keys, changed meaning) are derived from `fundamental_score`
alone, at a +-2 threshold: "Leans BUY" / "Leans SELL / avoid adding" / "Mixed / HOLD".
`score` stays as a plain alias for `fundamental_score` (not renamed/removed) so existing
callers (notebook, tests, prints) keep working without a required rewrite -- the
lower-risk option since nothing about `buy_sell_signal()`'s public shape actually needs
to change here.

New `technical_read`/`technical_read_code` fields are derived from `technical_score` the
same way, kept clearly distinct wherever shown.

`bullish_signals`/`bearish_signals` stay one combined list -- no individual check
changes -- but each dict gains a `"horizon": "technical" | "fundamental"` key so the
dashboard can group the existing bullet list by the two new headline numbers instead of
listing them flat.

**Supersedes specs/002's `horizon` field.** 002 proposed a lightweight two-bucket
`horizon` label computed by inspecting which buckets fired against the *pooled* score --
descriptive text bolted onto a number that still moved for the wrong reasons. This spec
replaces that mechanism: once implemented, 002's `horizon` field is dropped, and its
`entry_zone`/`invalidation_level`/`suggested_first_tranche_pct` key off this spec's
stable `lean` instead of the old pooled score.

**Threshold: +-2**, same as the original pooled-score threshold, kept deliberately (not
lowered to +-1) even though the fundamental bucket's max magnitude is now 4, not 6 --
requiring 2 of the 4 fundamental checks to agree before calling BUY or SELL means the
lean reflects more than one independent fundamental data point, which is the whole point
of moving away from single-input daily noise. The tradeoff: stocks with thin analyst
coverage (fewer of the 4 checks even computable) will land on Mixed/HOLD more often --
accepted as correct behavior (genuinely less fundamental signal available), not a bug.

### `verdict` and `lean` stay separate, distinctly labeled

Scoping discussion confirmed `long_term_value_score()`'s `verdict` ("is this a good
business," no price input -- ROE, margin, FCF, D/E, current ratio, revenue trend) and
`buy_sell_signal()`'s `lean` ("is now a good price relative to expectations" -- analyst
target vs. price, forward-vs-trailing P/E, growth direction) are complementary, not
redundant, and merging them would lose real information: a stock can legitimately be
`verdict: Strong` + `lean: Mixed/HOLD` (great business, not currently cheap) or
`verdict: Weak` + `lean: Leans BUY` (statistically cheap, shaky business) -- both are
meaningful and distinct. Internal field names (`lean`, `lean_code`, `verdict`,
`verdict_code`) are unchanged -- renaming a public function's return keys without a
behavior reason is the kind of unprompted refactor `CLAUDE.md` asks to confirm first,
and there's no behavior reason to do it here.

What changes is only the **display** layer:
- `long_term_value_score()`'s dashboard label stays **"Long-Term Fit"** (unchanged --
  already a reasonable plain-language label; see `dashboard.py:53`).
- `buy_sell_signal()`'s verdict-card banner (currently `t("signal_prefix", ...)`,
  `dashboard.py:61-64`) is relabeled **"Right Now"**.
- The new `technical_read` is surfaced as **"Today's Price Action"**: a small caption
  under the Right Now banner (not a fourth metric tile, avoiding re-cluttering the top of
  the dashboard the old single banner used to occupy), with an expander showing which
  technical checks fired and their plain-language criteria (see next section).

### Inline criteria explainers

`docs/METRICS.md` already has the plain-language explanation for nearly every threshold
this app uses (RSI, SMA, ROE, D/E, current ratio, P/E, etc.) -- but it's dev-facing
reference material, never rendered anywhere in the dashboard, so a family member has no
way to reach it. This spec adds a short, UI-facing criteria line for every
threshold-based check the dashboard displays, condensed from `docs/METRICS.md`'s
existing entries (that file's wording is the source of truth; these are UI-length
summaries of it, not a second independent explanation to keep in sync by hand):

- **RSI** (`rsi_oversold`/`rsi_overbought`): "Based on the last 14 trading days, scored
  0-100. Below 30 = oversold (dropped sharply, might bounce back). Above 70 = overbought
  (risen sharply, might pull back)."
- **52-week range position** (`near_52w_low`/`near_52w_high`): "Where the price sits
  between its highest and lowest point in the past year. Below 25% = near the yearly
  low. Above 90% = near the yearly high."
- **Moving-average trend** (`above_both_sma`/`below_both_sma`): "Compares today's price
  to its 50-day and 200-day averages. Above both = uptrend. Below both = downtrend."
- **ROE** (`roe_check`): "Net income as a percent of shareholder equity -- how much
  profit per dollar shareholders have invested. Above 15% is a common bar for
  above-average capital efficiency."
- **Debt/Equity** (`leverage_check`): "Total debt compared to shareholder equity. Below
  100 is read as manageable leverage here -- but normal ranges vary a lot by industry
  (utilities and banks normally run higher)."
- **Current ratio** (`current_ratio_check`): "Short-term assets divided by short-term
  liabilities. Above 1.2 means a comfortable cushion to cover near-term bills."
- **Margin / FCF / revenue trend checks**: pass/fail already reads plainly ("Positive
  profit margin", "Positive free cash flow", "Multi-year revenue trend mostly up") --
  add one line per check on what's being compared (e.g. FCF: "Cash left over after
  running and maintaining the business, after capital spending").
- **Forward vs. trailing P/E** (`forward_pe_below_trailing`/`above_trailing`): "Compares
  what the stock costs against expected next-year earnings vs. the last 12 months'
  earnings -- forward P/E well below trailing suggests earnings are expected to grow
  into the price."
- **Analyst upside/downside** (`analyst_upside`/`analyst_downside`): "How far the current
  price sits from the average Wall Street analyst price target. Analyst targets skew
  optimistic industry-wide (see `docs/METRICS.md`), so treat this as one data point, not
  a prediction."

Placement: for `technical_read`'s three checks, an expander under the "Today's Price
Action" caption (see above). For `long_term_value_score`'s checklist and `lean`'s
fundamental bullets (already rendered as a flat bullet list in the Why? tab,
`dashboard.py:113-134`), each bullet gains its criteria line directly beneath it (e.g. as
`st.caption()`), consistent with how `specs/002`'s own Non-technical-user-impact section
already asked for a first-time explainer line for its new fields.

## Non-technical-user impact

This is the core of what this spec changes for the family, not a side effect: the
headline banner should hold steady across days unless something in the quarterly
numbers or analyst targets actually shifted, "Right Now" and "Long-Term Fit" read as two
distinct, plainly-labeled ideas instead of one vague "signal," "Today's Price Action" is
clearly marked as the part expected to move daily so a change there doesn't read as "the
long-term case changed," and every number with a pass/fail judgment behind it (oversold,
overbought, manageable leverage, etc.) has its actual criteria visible on screen instead
of requiring someone to already know what those words mean.

## Acceptance criteria

- `buy_sell_signal()` returns `fundamental_score` and `technical_score` as separate
  integers; `score` remains as an alias for `fundamental_score`. IMPLEMENTED
  (`stock_toolkit/signals.py`).
- `lean`/`lean_code` are derived only from `fundamental_score` at a +-2 threshold;
  `technical_read`/`technical_read_code` are derived only from `technical_score` at the
  same threshold. IMPLEMENTED.
- Each entry in `bullish_signals`/`bearish_signals` gains a `"horizon"` key
  (`"technical"` or `"fundamental"`). IMPLEMENTED.
- `print_buy_sell_signal()` prints `lean` and `technical_read` as two clearly separate
  lines. IMPLEMENTED.
- Dashboard: banner labeled "Right Now" (was the unlabeled verdict card); existing
  "Long-Term Fit" metric tile unchanged; a new "Today's Price Action" caption/expander
  under the banner shows `technical_read` and which technical checks fired. IMPLEMENTED
  (`pages/dashboard.py`).
- Every threshold-based check rendered in the dashboard (technical checks,
  `long_term_value_score`'s checklist, `lean`'s fundamental bullets) shows a
  plain-language criteria line alongside it, per the list in Design. IMPLEMENTED
  (`shell/i18n.py`'s `CRITERIA_TEXT`/`criteria_text()`).
- specs/002's `horizon` field is removed from that spec's design, acceptance criteria,
  and open questions (superseded here); its `entry_zone`/`invalidation_level`/
  `suggested_first_tranche_pct` gating is updated to reference this spec's
  fundamentals-only `lean`. IMPLEMENTED (done in the same session this spec's own design
  was updated, ahead of this spec's code -- see specs/002).
- `shell/i18n.py` gains entries (English and Chinese) for `technical_read`'s codes and
  for every new criteria-explainer string, mirroring the existing `lean_code`/
  `REASON_TEMPLATES` pattern. IMPLEMENTED.
- Existing tests and notebook usage of `buy_sell_signal()`'s `lean`/`score` keys keep
  working unchanged in shape; `score`'s underlying value changes (now equals
  `fundamental_score`, not the old pooled score) -- a deliberate behavior change.
  IMPLEMENTED (`tests/test_signals.py`, new -- covers the split scoring, the "technical
  inputs alone can't move `lean`" property directly, Mixed/HOLD on a fundamental split,
  and horizon tagging; full suite passes, 15/15).

## Open questions

None remaining for `buy_sell_signal()`'s scoring/labeling design -- threshold, score
aliasing, SMA bucket placement, the verdict/lean split, display labels, and explainer
placement were all confirmed during scoping (see Design). Remaining open items belong to
specs/002, not here:
- specs/002's `entry_zone`/`invalidation_level` still need a decision on whether they
  should populate when `lean` is Mixed/HOLD but `technical_read` is bullish (a stock the
  long-term case doesn't clearly favor yet, but that's showing short-term strength) --
  deferred to specs/002, which already depends on this spec shipping first.
