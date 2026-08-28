# <NNN>-<short-feature-slug>

One file per feature, named `NNN-short-feature-slug.md` (zero-padded, incrementing). This
is the handoff channel from scoping (wherever that happens -- a chat, a claude.ai project)
to implementation in this repo. `CLAUDE.md` points here as the source of truth for new
feature intent, so a spec should stand on its own -- readable without the conversation
that produced it.

## Problem

What's missing or wrong today, for whom, and why it matters. Not the solution yet -- just
the gap. If this came from a specific request (the user, or a family member using the
dashboard), say what they actually asked for in their own words before translating it.

## Scope

**In scope:** what this feature covers.
**Out of scope:** what it deliberately doesn't, especially anything a reader might assume
is included. Naming the cut is as useful as naming the feature -- see this repo's own
history of scoping "history" down to archive-only (deferring forward-return calibration)
and "comparison" down to relative ranking (deferring a backtesting engine).

## Design

The approach: which module(s) it touches or adds, what the data flow looks like, and any
real design fork worth naming explicitly (there's usually more than one reasonable way to
build a feature -- say which was chosen and the one-line reason, not just the result).

Flag anything that needs confirming before implementation starts -- a scope question, a
UX tradeoff, a data source that needs verifying live before committing to it (this
project's own convention: don't assume a library/data claim works, check it once for
real).

## Non-technical-user impact

This dashboard is built for a non-technical family member first. Note anything that
touches what they'll see or click: does it add a new concept they'd need explained, change
an existing screen's layout, or introduce a new failure mode that needs a friendly
message instead of a raw error?

## Acceptance criteria

What "done" looks like, concretely enough that someone could check it without having
built the feature themselves. Prefer checkable statements ("Compare tab shows relative
rank for any industry group of 2+ stocks") over vague ones ("comparison is more useful").

## Open questions

Anything still undecided when this spec was written. Fine to leave items here -- better
than guessing and writing it down as settled.
