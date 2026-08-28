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
staying outside the toolkit package. Both, plus `auto_shutdown.py`, moved into a small
`shell/` package shortly after this feature shipped, once the repo root had accumulated
enough loose presentation-layer modules to warrant it -- same package, same reasoning,
just grouped together instead of loose at root). Holds a flat dict of
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

**Today's Briefing (`stock_toolkit/briefing.py`) -- English is always the generation
language; Chinese is a translated derivative. IMPLEMENTED, superseding both this
section's original per-market-native-generation draft and the always-English-then-
translate draft that preceded it.** The per-market design below was the plan going into
implementation; live testing against `qwen2.5:7b` and `qwen2.5:14b` before writing the
final code overturned it.

Both sub-tasks -- `score_news_relevance`'s per-headline relevance judgment and
`explain_daily_move`'s one-sentence synthesis -- were tested asking Qwen to generate
Chinese directly from raw facts (headlines, price move). Both reliably produced garbled
or hallucinated output (English bleeding into a Chinese-only prompt, a mangled numbered-
line format, and in one case inventing that `0700.HK` was Meituan instead of Tencent),
regardless of model size, and Ollama's `format: "json"` structured-output constraint only
fixed the first sub-task's formatting, not the second's factual grounding. Pure
translation of an already-written English sentence, by contrast, tested reliably correct
across several varied sentences on `qwen2.5:7b`. So: **`local_llm_complete` (English,
`llama3.1:8b`) generates for every stock regardless of market, unchanged from before this
feature** -- `translate_to_zh` (new, `qwen2.5:7b`, JSON-mode) translates the result to
Chinese afterward, applied to both `explanation` and each `considered[i]["reason"]`
(including skipped headlines, not just used ones, so the audit trail doesn't read as
half-translated). `translation_available()` checks the model is actually pulled before
attempting translation, falling back to English-only display (with a small notice) on an
install that hasn't pulled it -- same resilience pattern as `ollama_available()`.

`funds.py`'s `explain_fund_move` needed the equivalent of "produce both languages," but
not via Qwen -- it's a deterministic (no-LLM) template, so both language versions are
built directly as plain string formatting, which is simpler and more exact than routing
already-correct text through a translation call.

**Storage.** Simpler than the per-market draft's `lang`-tagged design, since there's now
only one source language: each briefing result carries `explanation` (English, always)
and `explanation_zh` (Chinese, or `None` if translation wasn't available at generation
time); each `considered[i]` carries `reason`/`reason_zh` the same way. `pages/briefing.py`
shows the `_zh` field when the viewer's toggle is Chinese, falling back to the English
field if the translation is `None`. `briefing_history.jsonl` (the committed permanent
archive) archives both fields per entry -- English is always present; Chinese is present
whenever the translation model was available at generation time.

**Dependency footprint, smaller than either earlier draft assumed.** `llama3.1:8b` is
needed by every install, as before this feature (nothing changed about English
generation). `qwen2.5:7b` is needed only by an install that actually displays Chinese --
an all-English install never calls `translate_to_zh` and never needs to pull it. This is
narrower than both the per-market draft (which assumed every install needing both US and
HK/China stocks needs both models) and the original always-English-then-translate draft's
assumption -- the dependency now follows the *viewer's* language choice, not the
watchlist's market mix.

## Non-technical-user impact

This is the whole point of the feature for the dad's install: he opens the app and
everything -- labels, buttons, the "Why this signal?" reasoning, risk flags, and the
daily briefing -- is in Chinese by default, no setup step and no toggle needed unless he
wants to peek at the English version. The toggle itself is a new UI element he'll see
(a radio at the very top of the sidebar) -- kept visually simple, consistent with the
large-print/high-contrast style `ui_common.py` already applies for older users. If his
install hasn't pulled `qwen2.5:7b`, Today's Briefing falls back to English with a small
caption explaining why (see README) -- everything else on the dashboard still renders in
Chinese regardless, since only the Briefing's translation depends on that model.

## Acceptance criteria

- A language toggle is visible at the top of the sidebar; clicking it switches all
  static text (labels, buttons, tab names, headers) across `app.py`, both `pages/`
  scripts, and `ui_common.py` immediately, no restart. IMPLEMENTED.
- The choice persists: closing and relaunching the app on the same install reopens in
  the last-selected language. IMPLEMENTED (`data/settings_store.py`).
- `data/settings.json` is created on first run (like `watchlist.json`), gitignored,
  and defaults to `"en"` if absent. IMPLEMENTED.
- The "Why?" tab's bullish/bearish points, risk flags, the long-term value checklist,
  the buy/sell lean, the risk level, and the value-score verdict all render in the
  selected language with correct numbers substituted in. IMPLEMENTED (structured
  `{code, params, text}` entries in `signals.py`, rendered via `i18n.reason_text`/
  `i18n.code_text`).
- Today's Briefing always generates in English (`llama3.1:8b`, every stock, every
  market -- unchanged from before this feature) and translates to Chinese
  (`qwen2.5:7b`) for both the top-line explanation and every per-headline
  `considered[i]["reason"]` (used and skipped alike). IMPLEMENTED -- supersedes the
  market-based native-generation criterion this originally stated; see Design.
- A viewer's toggle shows the `_zh` field when set to Chinese, falling back to the
  English field when translation wasn't available at generation time (model not
  pulled, or the call failed) -- never a blank. IMPLEMENTED (`translation_available()`
  guard in `briefing.py`; fallback logic in `pages/briefing.py`).
- `briefing_history.jsonl` archives both `explanation`/`explanation_zh` per entry.
  IMPLEMENTED.
- `print_buy_sell_signal`, `print_risk_scan`, `print_long_term_value_score`, and the
  notebook's existing usage of `stock_toolkit` continue to work unchanged (English,
  same as today) -- confirms the structured-code approach didn't break the toolkit's
  non-dashboard consumers. VERIFIED (offline fixture tests, `tests/test_market_data.py`
  plus a manual run against the AAPL fixture).
- Switching language does not lose the current watchlist, selected stock, or chart time
  range. IMPLEMENTED (language lives in its own `st.session_state.lang` key).

## Open questions

All three resolved during implementation:

- **Design fork (structured reason codes vs. a `lang` parameter):** resolved --
  structured reason codes, as recommended above.
- **Qwen tag choice:** resolved, with a result that changed the Design section above.
  `qwen2.5:7b` and `qwen2.5:14b` were both live-tested generating Chinese directly from
  raw facts (the per-market draft's plan) and both reliably produced garbled or
  hallucinated output; `qwen2.5:7b` translating an already-written English sentence
  tested reliable instead. `qwen2.5:7b` (not `14b`) is what's wired in, since the
  translation task -- the one that actually works -- didn't need the larger model's
  extra capacity in testing.
- **Market-classification rule (`.HK`/`.SS`/`.SZ` = Chinese source of truth):**
  moot -- superseded by the always-English-generation finding above. No per-market
  classification exists in the shipped code; every stock generates in English and
  translates the same way regardless of listing market.
