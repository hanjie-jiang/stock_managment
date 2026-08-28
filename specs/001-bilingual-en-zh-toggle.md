# 001-bilingual-en-zh-toggle

## Problem

The user asked: "i would like to change between english and chinese seamlessly so that
my dad and me could both use it." The dashboard is currently English-only, top to
bottom -- static labels, the generated buy/sell reasoning, risk flags, the long-term
value checklist, and the Ollama-written daily briefing. The user's dad is a
non-technical family member (the dashboard's primary design target per `ui_common.py`)
who needs to read this in Chinese; the user reads it in English. Both need to use the
same app, ideally each on their own install, without maintaining two forks.

## Scope

**In scope:**
- A sidebar language toggle (English / Chinese) that switches all visible text
  immediately, no restart required.
- A per-install default language, remembered across restarts, so the dad's PC opens in
  Chinese and the user's opens in English without re-toggling every launch.
- Translation of everything a viewer reads: static UI chrome (labels, buttons, headers,
  tab names) in `app.py`, `ui_common.py`, `pages/dashboard.py`, `pages/briefing.py`; the
  generated reasoning sentences in `stock_toolkit/signals.py` (`bullish_signals`,
  `bearish_signals`, `risk_flags`, the value checklist); and the Ollama-generated
  Today's Briefing explanation text.

**Out of scope:**
- Translating data pulled from yfinance itself (company names, industry/sector labels,
  analyst recommendation strings like `"buy"`/`"hold"`) -- these come from the data
  source as English/English-coded values and stay as-is; only the surrounding
  presentation is bilingual.
- Number/currency formatting conventions (thousands separators, date formats) --
  numbers stay as they render today regardless of language.
- Translating `README.md`, `CLAUDE.md`, or other developer-facing docs.
- A third language, or a generic i18n framework for arbitrary future languages -- this
  is English/Chinese specifically, matching the two people who use this app.

## Design

**Language storage.** New `data/settings_store.py` following the exact pattern of
`data/watchlist_store.py`: a gitignored `data/settings.json` holding
`{"language": "en"}` or `{"language": "zh"}`, defaulting to `"en"` if the file doesn't
exist yet. Gitignored for the same reason `watchlist.json` is -- it's this install's
local preference, not code. Add `data/settings.json` to `.gitignore` alongside the
existing `data/watchlist.json` line.

**Sidebar toggle.** A small language switcher at the top of `ui_common.render_sidebar`
(two buttons or a `st.radio`, "English" / "中文"). On change: write to
`st.session_state.lang`, persist via `settings_store.save_settings()`, `st.rerun()`.
`ui_common.init_watchlist_state` grows a sibling `init_language_state()` that loads the
saved default into `st.session_state.lang` once per session, called from `app.py`
alongside the existing `ui.init_watchlist_state()`.

**Static UI text.** New `i18n.py` (plain module next to `ui_common.py`, not inside
`stock_toolkit` -- this is presentation, same reasoning `ui_common.py` already gives for
staying outside the toolkit package). Holds a flat dict of
`{"en": {key: text}, "zh": {key: text}}` and a lookup helper, e.g. `t(key, **kwargs)`
reading `st.session_state.lang` and doing `.format(**kwargs)` on the matched string.
Every hardcoded string currently in `app.py`, `ui_common.py`, `pages/dashboard.py`, and
`pages/briefing.py` gets replaced with a `t("...")` call and a new dict entry in both
languages.

**Generated signal/risk/checklist text (`stock_toolkit/signals.py`).** This is the real
design fork, and the one most worth confirming before writing code:

- **Recommended: structured reason codes.** Each entry in `bullish_signals`,
  `bearish_signals`, `risk_flags`, and the value checklist becomes a dict
  `{"code": "analyst_upside", "params": {"pct": 18.4}, "text": "Analyst target implies
  18.4% upside"}` instead of a plain string. `text` keeps today's English sentence
  (backward-compatible with `print_buy_sell_signal`, `print_risk_scan`,
  `print_long_term_value_score`, and the notebook, none of which need to change). The
  dashboard looks up `code` in a new `i18n.py` template table to render the sentence in
  the active language, formatted with `params`. Keeps `stock_toolkit` free of a `lang`
  parameter threaded through every function, and keeps the English string as the single
  source of truth for the toolkit's own prints/notebook use.
- **Alternative: a `lang` parameter.** `buy_sell_signal(symbol, lang="en")` etc. build
  the sentence in the requested language directly, with English/Chinese branches
  duplicated at each `bullish.append(...)` site. Simpler data shape (still plain
  strings), but duplicates every phrase inline in the toolkit, couples
  `stock_toolkit` to presentation language, and means every call site (dashboard,
  notebook, tests, the two `compare`/`risk` pages) needs to start passing `lang`
  through.

  Recommendation is the structured-code approach -- flagged in Open Questions for
  confirmation before implementation, since it changes the return shape of three public
  `stock_toolkit` functions.

**Today's Briefing (`stock_toolkit/briefing.py`) -- source-of-truth language is per-stock,
by market, not per-viewer.** Revised design, replacing the earlier
always-English-then-translate draft: which language the explanation is *generated* in
depends on which market the stock trades on, not on who's viewing it.

- **US-market stocks** (no `.HK`/`.SS`/`.SZ` suffix -- this includes US-listed Chinese
  ADRs like BABA/JD/PDD, since the split is by listing market, not company nationality;
  confirm this reading matches intent, see Open Questions): generated in English by the
  existing `llama3.1:8b`, exactly as today. English is the source of truth.
- **HK/China-market stocks** (`.HK`, `.SS`, `.SZ` suffix): generated in Chinese by Qwen
  instead -- both `score_news_relevance`'s per-headline relevance judgment/reason and
  `explain_daily_move`'s final one-sentence explanation are produced directly in
  Chinese, reasoning over whatever language the underlying yfinance headlines happen to
  be in. Chinese is the source of truth for these stocks. Rationale: the news driving a
  Moutai or Tencent move is often native to a Chinese-reading model's strengths, and
  generating natively in Chinese avoids a round-trip (headlines -> English reasoning ->
  Chinese translation) that risks losing nuance a direct Chinese read wouldn't.

A small helper (e.g. `_source_lang_for_symbol(symbol)`) in `briefing.py` makes this
call from the suffix. Whichever language wasn't the source gets a translation pass via
Qwen (en->zh for US stocks, zh->en for HK/China stocks) -- applied to both the top-line
`explanation` and each `considered[i]["reason"]`, since a half-translated audit trail
(explanation in one language, per-headline reasons still in the other) would look
broken. `funds.py`'s `explain_fund_move` needs the same per-market routing for
consistency, as part of implementation.

**Storage.** `data/briefing_cache.json` entries gain a `lang` field recording the
source language plus a translated counterpart, e.g.
`{"lang": "zh", "explanation": "<Chinese, source>", "explanation_translated":
"<English>", "considered": [{"headline": ..., "relevant": ..., "reason": "<Chinese>",
"reason_translated": "<English>"}, ...]}`. `pages/briefing.py` shows `explanation`/
`reason` when `st.session_state.lang` matches the entry's `lang`, otherwise the
`_translated` counterpart. `briefing_history.jsonl` (the committed permanent archive)
now archives the *source* text plus its `lang` tag per entry -- genuinely mixed-language
across the file (US-stock entries in English, HK/China-stock entries in Chinese), which
is a more honest "what was actually said" record than forcing a single language. The
deferred forward-return-calibration backlog item will need to read `lang` when it's
eventually built, but it isn't built yet, so no immediate impact.

**Dependency footprint, symmetric now.** Because model choice is tied to the stock's
market rather than the viewer's display language, *both* installs need *both* models
pulled as soon as the watchlist spans both markets -- which the default watchlist
already does (AAPL/MSFT are US; `600519.SS`/`0700.HK` are China/HK). This isn't "the
dad's install needs an extra model" as the earlier draft framed it -- it's "anyone using
this app across US and HK/China stocks needs both models," regardless of which language
they read in.

## Non-technical-user impact

This is the whole point of the feature for the dad's install: he opens the app and
everything -- labels, buttons, the "Why this signal?" reasoning, risk flags, and the
daily briefing -- is in Chinese by default, no setup step and no toggle needed unless he
wants to peek at the English version. The toggle itself is a new UI element he'll see
(two buttons/a radio in the sidebar) -- keep it visually simple and at the very top of
the sidebar, consistent with the large-print/high-contrast style `ui_common.py` already
applies for older users. No new failure modes expected, other than: if Qwen's
Chinese generation or its translation quality is poor (see Open Questions), the briefing
text could read as awkward machine translation -- worth a real check with real headlines
before calling this done for the briefing piece specifically. Also worth noting: *both*
installs now need two local Ollama models pulled instead of one, since model choice
follows the stock's market rather than the viewer's language (see Design) -- a one-line
addition to the README's Ollama setup step, not a new concept for either of them to
understand (neither ever sees a model name).

## Acceptance criteria

- A language toggle is visible at the top of the sidebar; clicking it switches all
  static text (labels, buttons, tab names, headers) across `app.py`, both `pages/`
  scripts, and `ui_common.py` immediately, no restart.
- The choice persists: closing and relaunching the app on the same install reopens in
  the last-selected language.
- `data/settings.json` is created on first run (like `watchlist.json`), gitignored,
  and defaults to `"en"` if absent.
- The "Why?" tab's bullish/bearish points, the risk flags, and the long-term value
  checklist all render in the selected language with correct numbers substituted in.
- Today's Briefing for a US-market stock is generated in English by `llama3.1:8b`
  (unchanged from today); for an HK/China-market stock (`.HK`/`.SS`/`.SZ`), it's
  generated in Chinese by Qwen. Both the top-line explanation and each per-headline
  `considered[i]["reason"]` follow this split.
- Whichever language wasn't the source is filled in via a Qwen translation pass and
  cached alongside the source text; a viewer's toggle selects source-vs-translated
  per entry based on the entry's `lang`, never showing a half-translated mix within one
  briefing entry.
- `briefing_history.jsonl` archives the source-language text plus a `lang` tag per
  entry -- mixed-language across the file by design, matching each entry's actual
  source market.
- `print_buy_sell_signal`, `print_risk_scan`, `print_long_term_value_score`, and the
  notebook's existing usage of `stock_toolkit` continue to work unchanged (English,
  same as today) -- confirms the structured-code approach didn't break the toolkit's
  non-dashboard consumers.
- Switching language does not lose the current watchlist, selected stock, or chart time
  range.

## Open questions

- **Confirm the design fork above** (structured reason codes vs. a `lang` parameter
  threaded through `stock_toolkit`) before implementation starts.
- **Pick and verify a real Qwen Ollama tag live** before locking it into the README/
  setup step -- `qwen2.5:7b` is a reasonable starting guess (known for solid Chinese
  output) but needs `ollama pull` and real checks before calling it settled: (a) does it
  produce natural, plain Chinese for both direct generation and translation, keeping
  tickers/numbers intact; (b) does it reliably follow the same structured
  `<number>: YES - <reason>` line format `score_news_relevance`'s parser expects, when
  instructed to answer in Chinese -- this is a formatting-following task layered on top
  of a language task, worth confirming it doesn't break the parser. Since both installs
  now need Qwen regardless of display language (see Design), also worth a live timing
  check on whether running `llama3.1:8b` and `qwen2.5:7b` alongside each other is
  reasonable on the dad's hardware -- if not, `qwen2.5:3b` is the fallback.
- **Confirm the market-classification rule.** `.HK`/`.SS`/`.SZ` suffix = Chinese source
  of truth; everything else (including US-listed Chinese ADRs like BABA/JD/PDD) = English
  source of truth, per "US stock market" vs. "HK or china stock market" in the request.
  Flagging since it's a real classification call, not because it seems likely to be
  wrong.
