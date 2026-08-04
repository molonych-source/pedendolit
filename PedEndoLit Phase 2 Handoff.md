# PedEndoLit Phase 2 Handoff

> **SUPERSEDED — kept for historical context only.** Phase 2 shipped 2026-08-04 and is
> live at https://molonych-source.github.io/pedendolit/. The path recommended below
> (bolt Supabase onto the static site rather than rebuild in Lovable) is what was built,
> and the open questions listed here are resolved. For current state see `CLAUDE.md` and
> `MEMORY.md`; for setup and testing detail see `PedEndoLit Phase 2 Supabase Setup Guide.md`.

**Status:** In progress — architecture recommended, awaiting Christian's confirmation of the build path before drafting the step-by-step plan.
**Started:** This thread continues the earlier "PedEndoLit Web App — Plan & Conversation Handoff." · **Handoff written:** 2026-07-24

## Goal

Add Phase 2 to PedEndoLit: let members of the pediatric endocrinology community **create accounts and save individual articles** to a personal list. Phase 1 (the public, read-only dashboard) is already built and shared publicly via GitHub. No patient data is involved, so there are no HIPAA hosting constraints. Christian has no coding experience, so the build path must not require him to hand-write code — Claude generates any code to paste, and setup steps are point-and-click.

## Key decisions

- **Phase 1 is already live on GitHub** (static HTML). Phase 2 builds on top of it, not a rebuild. (This updates the prior handoff, which had assumed Phase 1 wasn't shipped yet.)
- **Recommended path: bolt Supabase onto the existing static site** rather than rebuild in Lovable. Rationale: preserves the working, free GitHub deployment and existing weekly pipeline; Supabase's browser library adds login + saved lists to a static page with no server; effectively $0 at pilot scale. Lovable was compared and set aside — it would discard the working deployment, add a recurring bill, and require reworking the weekly refresh, in exchange for future feature velocity Phase 2 doesn't need yet. **Not yet formally confirmed by Christian** — he was still asking clarifying questions when the thread paused.
- **Store only PMIDs in the database, not full article copies.** The article set is regenerated weekly, so duplicating it into the DB would create a sync problem. PMIDs are stable, so a save made today still resolves after the next weekly refresh.
- **Database is deliberately tiny:** one `saved_articles` table with `user_id`, `pmid`, `saved_at`. Supabase Auth handles users. Row-Level Security ensures each person sees only their own saved list.

## Work done

- Read `01_Clinical_Research/Resources/PedEndoLit/pedendolit-data.json` to confirm the real data shape (see Context below). No files created or changed this session — the thread was design/discussion.
- Reviewed the prior handoff `01_Clinical_Research/Resources/PedEndoLit/PedEndoLit-WebApp-Plan-and-Handoff.md`.

## Open questions

1. **Confirm the build path** — bolt Supabase onto the current GitHub site (recommended) vs. rebuild in Lovable. This is the one decision that gates the next step.
2. **Site name** — not chosen. (Prior handoff listed this open; still open. May be moot if the existing GitHub URL is kept for Phase 2.)
3. Whether a **simple privacy policy** is wanted once accounts exist (worth having, not blocking).

## Next steps

1. Get Christian's confirmation on the build path (question 1 above).
2. Assuming bolt-on: draft the Phase 2 plan in plain English — (a) create a Supabase project, (b) create the `saved_articles` table, (c) turn on and **test** Row-Level Security with two accounts, (d) paste-in code block adding login + a per-article Save button + a "My saved articles" view to the existing dashboard HTML.
3. Design the graceful-degradation behavior for a saved PMID that has dropped out of the current weekly dataset (show "no longer in current list" instead of breaking).

## Context to carry forward

- **Live data file:** `01_Clinical_Research/Resources/PedEndoLit/pedendolit-data.json` — top-level keys `generated`, `review_period`, `last_run_date`, `articles`. `articles` is a list of **947** records.
- **Article record shape (relevant fields):** `pmid` (stable ID, the save key), `title`, `abstract`, `journal` / `journal_abbr`, `authors`, `doi`, `pub_date`, `url`, `topic`, `study_type`, `ev_level`, `impact`, `board_relevant`, `tags`, `access`, `clinical_bottom_line`, `is_new`, `is_archived`, `excluded`.
- **Topic distribution (why "save by topic" matters):** Diabetes 445, Growth 122, Puberty 79, Thyroid 65, Adrenal 50, General Endo 38, Obesity/Metabolic 36, plus smaller categories.
- **Pipeline:** dashboard built weekly from 16 PubMed journals (`journals.json`), via `build_dataset.py` → `build_dashboard.py` → `PedEndoLit-Dashboard.html`. Prior handoff notes that a real web server can call PubMed's E-utilities directly, so the weekly refresh can become an automatic timer with no Claude in the loop.
- **Failure modes already identified to design in:** (1) a saved PMID that later drops from the weekly set must degrade gracefully; (2) RLS misconfiguration is the classic Supabase mistake — must be tested with two separate accounts; (3) Supabase's default auth email sender is rate-limited — fine for a pilot, needs a real email provider if it grows.
- **Supabase cost:** free tier covers dozens of users; ~$25/month paid tier only if it grows.

## How to resume

Paste this file's contents (or attach it) at the start of a new conversation and say "continue from this handoff." The immediate ask is to confirm the build path, then draft the Phase 2 step-by-step plan.
