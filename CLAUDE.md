# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PedEndoLit is a self-contained literature-surveillance dashboard for pediatric
endocrinology. It replaces a paid Perplexity Computer workflow: it pulls articles
from 19 monitored journals via PubMed (NCBI E-utilities, accessed through the
PubMed MCP tool — not reachable directly from the shell), classifies each with a
rules-based classifier, and renders a single self-contained `PedEndoLit-Dashboard.html`
(data embedded, opens by double-click, no server required).

This is not a git repository and has no test suite, linter, or build system —
it's a small Python data pipeline plus one generated static HTML file. There is no
`npm test` / `pytest` / lint command to run; verification is done by reading the
`build_dataset.py` summary stats and spot-checking the generated dashboard in a browser.

**Read `MEMORY.md` first** for full project history, architecture decisions (and why),
taxonomy state, and known caveats — it's the durable source of truth. `TASKS.md` holds
open ideas/backlog. `WEEKLY_REFRESH_RUNBOOK.md` holds the operational weekly procedure.

## The pipeline (three-stage, run in order)

1. **Fetch** (agent-only step, not a script) — Claude calls the PubMed MCP
   `search_articles` / `get_article_metadata` per journal in `journals.json`,
   assembles results into `raw_articles.json`. This step requires the MCP because
   the sandbox shell cannot reach NCBI directly.
2. **`build_dataset.py`** — reads `raw_articles.json`, runs it through `classifier.py`,
   dedupes by PMID against the existing store, applies the 60-day archive cutoff and
   `is_new` reset, and writes `pedendolit-data.json` (the datastore: active + archived
   articles, keyed by PMID).
3. **`build_dashboard.py`** — reads `pedendolit-data.json`, writes the self-contained
   `PedEndoLit-Dashboard.html` (data embedded inline) plus a copy to
   `01_Clinical_Research/` and the publish copy `index.html`.

Commands:
```
python3 build_dataset.py [--run-date YYYY-MM-DD] [--raw raw_articles.json] [--rebuild]
python3 build_dashboard.py
```

- `build_dataset.py` is **merge-only by default**: existing PMIDs are skipped, only
  new ones from `--raw` are classified and added.
- `--rebuild` reclassifies **everything from scratch** — but it reads from the raw
  file (default `raw_articles.json`), NOT from the existing store. Since the normal
  weekly run overwrites `raw_articles.json` with only that week's fetch, running
  `--rebuild` right after a normal weekly run will wipe the store down to just that
  week. Before a `--rebuild`, pass `--raw comprehensive_raw.json` (the maintained
  cumulative source — see `WEEKLY_REFRESH_RUNBOOK.md` for how to keep it current).
  Only use `--rebuild` after editing `classifier.py`.
- `--run-date` overrides "today" (useful for testing/backfills); it drives the
  60-day archive cutoff and `review_period` labeling.

The full weekly procedure (date windows, MCP batching, PMID dedup) is in
`WEEKLY_REFRESH_RUNBOOK.md`. To trigger it, just ask: "run the PedEndoLit weekly refresh."

## Architecture / key files

- **`journals.json`** — the 19 monitored journals, each with `abbr` (used verbatim
  in the PubMed `[Journal]` field tag) and `peds_filter` (true = AND in `PEDS_TERMS`,
  a MeSH/title-abstract clause, aka "Template B"; false = journal is peds-endo-dedicated
  and doesn't need the filter, aka "Template A").
- **`classifier.py`** — pure functions, no I/O; a faithful port of the original
  `reclassify_v2.py` (spec v2.4.2 + Diabetes Classification Framework + Gender Medicine
  + Calcium/Parathyroid split). `classify(art)` runs, in order: exclusion rules →
  topic/subtopic (25-branch waterfall in `classify_topic`) → study type → 4-tier impact
  (`classify_impact`, with a negative-outcome cap) → diabetes subtype → age range →
  society detection → board relevance → clinical bottom line → tags → open-access →
  rationale text. Input is a dict with `title, abstract, journal, journal_abbr,
  pub_types, authors, doi, pmid`; output merges the classification onto that dict.
  Edit this file to change classification logic — then `--rebuild` (see above).
- **`build_dataset.py`** — pipeline stage 2 (see above). Also decodes HTML/XML
  entities in titles/abstracts at ingest (`_clean`), since PubMed metadata contains
  raw entities like `&#xa0;`.
- **`build_dashboard.py`** — pipeline stage 3. Contains the `WEB3FORMS_KEY` (bug/comment
  report form — safe to expose, send-only) and the Phase 2 Supabase config stubs
  (`SUPABASE_URL` / `SUPABASE_ANON_KEY`, currently empty — see Phase 2 below). Also
  contains the historical entry-date CSV override logic (`ENTRY_DATE_CSV`) — see the
  Month dating note below, since the runbook and `MEMORY.md` disagree on current behavior.
- **`pedendolit-data.json`** — the datastore. Top-level: `generated`, `review_period`,
  `last_run_date`, `articles` (list, keyed by `pmid`). Article fields include `title`,
  `abstract`, `journal`/`journal_abbr`, `authors`, `doi`, `pub_date`, `url`, `topic`,
  `study_type`, `ev_level`, `impact`, `board_relevant`, `tags`, `access`,
  `clinical_bottom_line`, `is_new`, `is_archived`.
- **`backfill_legacy_metadata.py`** — one-off/rare-use script for patching legacy
  article records from a raw MCP metadata dump (`--raw`, `--dry-run` supported).
  Not part of the normal weekly cycle.

## Taxonomy

17 topics (Diabetes, Growth, Puberty, Thyroid, Adrenal, Obesity/Metabolic, General
Endocrinology, Bone/Calcium, Pituitary, Hyperinsulinism, Genetics, Calcium/Parathyroid,
DSD, PCOS, Gender Medicine, Cancer Late Effects, Lipids) and 8 diabetes subtypes
(T1D, T1D·Stage, T2D, Technology, MODY/Monogenic, CFRD, GDM, Steroid-induced, General).
See `MEMORY.md` for the full rationale behind recent taxonomy changes (Gender Medicine,
Calcium/Parathyroid split, Turner/Prader-Willi placement under Growth).

## Things that will bite you

- **Month dating discrepancy**: `WEEKLY_REFRESH_RUNBOOK.md` describes month bucketing
  as entry-date-based (via the `all_articles_export.csv` override in
  `build_dashboard.py`); `MEMORY.md`'s "Key decisions" log says this was **reversed**
  on 2026-05-30 to publication-date (`pub_date`)-based bucketing, verified with 0
  mismatches. Treat `MEMORY.md` as authoritative for current behavior; the runbook
  section is stale and hasn't been corrected.
- **`--rebuild` wipes the store to the current `raw_articles.json`** if run without
  `--raw comprehensive_raw.json` — see pipeline notes above and the runbook's
  "REBUILD PITFALL" callout.
- **PubMed MCP `search_articles` errors (HTTP 500) at `max_results=500`** — always
  use 200; no monitored journal approaches that volume even over a multi-month window.
- **`is_new` currently flags all articles** (a backfill artifact from the initial
  bulk load) — it self-corrects as weekly refreshes run, but don't trust a
  "what's new" view built on it until then (see `TASKS.md`).
- Two large intermediate/output JSON files (`comprehensive_raw.json`,
  `pedendolit-data.json`) are the real state; the various `*.prev.json` and
  `*backfill*.json` files are point-in-time snapshots/inputs from past sessions,
  not live inputs to the pipeline.

## Phase 2 (in progress, not yet built)

Adding user accounts + personal saved-article lists via Supabase, bolted onto the
existing static site (no rebuild/migration off the current GitHub Pages deployment).
Design is decided but not yet implemented — see `PedEndoLit Phase 2 Handoff.md` and
`PedEndoLit Phase 2 Supabase Setup Guide.md` for the full plan. Key points if resuming
this work:
- Store only `pmid` + `user_id` + `saved_at` in Supabase (`supabase_setup.sql` has the
  table + RLS policies, safe to re-run) — never duplicate full article data into the DB,
  since the article set is regenerated weekly from `pedendolit-data.json`.
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` in `build_dashboard.py` are empty; while empty,
  the dashboard builds exactly as it does today (no sign-in, no Saved tab).
- A saved PMID that later drops out of the weekly dataset must degrade gracefully
  (not yet implemented).

## Publishing

Static file, hosted on GitHub Pages (public). The publish artifact is `index.html`
(the URL root serves it) — regenerated by `build_dashboard.py`. Re-publishing after
any change means re-uploading `index.html` to the repo, keeping the same filename to
preserve the URL. Auto-publish (a scheduled task committing weekly) has been discussed
but is not yet set up — see `TASKS.md`.
