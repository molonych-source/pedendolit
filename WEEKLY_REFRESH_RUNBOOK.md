# PedEndoLit — Weekly Refresh Runbook

This is the procedure the weekly scheduled task follows. It replaces the old
Perplexity `peds_endo_weekly_update.py` cron. Everything runs inside Claude/Cowork.

## Why a Claude task and not a plain cron
PubMed (NCBI E-utilities) is reachable from the **PubMed MCP tool**, which only the
Claude agent can call — the sandbox shell cannot reach NCBI directly. So the weekly
job is an agent task: Claude calls the MCP to fetch, then a local Python script
classifies and rebuilds the dashboard. No Perplexity, no external server.

## Files (all in `01_Clinical_Research/Resources/PedEndoLit/`)
- `journals.json` — 19 monitored journals + PEDS_TERMS + Template A/B flags
- `classifier.py` — v2.4.2 classifier (faithful port of reclassify_v2.py)
- `build_dataset.py` — classifies raw articles, dedupes by PMID, applies 60-day archive + is_new reset, writes `pedendolit-data.json`
- `build_dashboard.py` — renders `PedEndoLit-Dashboard.html` (self-contained, data embedded)
- `pedendolit-data.json` — the datastore (active + archived articles, keyed by PMID)
- `PedEndoLit-Dashboard.html` — the dashboard (also copied to `01_Clinical_Research/`)

## Weekly procedure (run every Sunday)
1. Compute the date window: `today − 14 days` → `today`, field `[pdat]`.
2. For each of the 19 journals in `journals.json`, call the PubMed MCP `search_articles`:
   - query: `("<abbr>"[Journal])`; if `peds_filter` is true, AND the PEDS_TERMS clause.
   - date_from/date_to = the 14-day window; datetype = `pdat`; sort = `pub_date`; max_results = 200.
   - IMPORTANT: use max_results = 200, not 500 — the PubMed MCP `search_articles` tool errors (HTTP 500) when max_results = 500. No monitored journal approaches 200 hits even over 5 months, so 200 is safely above the ceiling.
3. Collect all returned PMIDs, dedupe.
4. Fetch metadata in batches via MCP `get_article_metadata` (batches of ~18 PMIDs).
   The MCP persists large results to files under `.claude/projects/.../tool-results/`;
   read those from the sandbox rather than pulling into context.
5. Assemble `raw_articles.json` from the fetched metadata (dedupe by PMID).
6. Run: `python3 build_dataset.py --run-date <YYYY-MM-DD>`
   - This MERGES (does not rebuild): existing PMIDs are skipped, only new ones added.
   - It applies the 60-day archive cutoff and resets `is_new` so only this week's
     additions are flagged NEW.
7. Run: `python3 build_dashboard.py` to regenerate the HTML.
8. Report: new article count, new practice-altering items, exclusions fired.

## Re-classify everything (only when classifier.py changes)

> **CRITICAL — REBUILD PITFALL:** `--rebuild` reads from `raw_articles.json`, NOT
> from the existing store (`pedendolit-data.json`). The normal weekly procedure
> overwrites `raw_articles.json` with only that week's fetch. If you run `--rebuild`
> after a normal weekly run, you will WIPE the store down to only the articles in
> the current `raw_articles.json`.
>
> Before running `--rebuild`, you MUST build a comprehensive source file:
> ```
> python3 - << 'EOF'
> # Run from the PedEndoLit/ directory
> import json, csv, re
> # ... see comprehensive_raw.json reconstruction script in session history
> # The standard sources: all_articles_export.csv + backfill_inline_supplement.json
> # + raw_supplement_jes.json + raw_articles.json → comprehensive_raw.json
> EOF
> python3 build_dataset.py --run-date <YYYY-MM-DD> --raw comprehensive_raw.json --rebuild
> ```
>
> `comprehensive_raw.json` (built 2026-06-28) is kept in the PedEndoLit folder as
> the canonical cumulative source. Before each future rebuild, append the current
> `raw_articles.json` to it rather than replacing it.

`python3 build_dataset.py --run-date <YYYY-MM-DD> --raw comprehensive_raw.json --rebuild`
Reclassifies all articles in the comprehensive source from scratch, preserving each
article's original `review_date` so archive math stays correct. Use this after any
edit to classifier logic; do NOT use it for normal weekly runs.

## Notes / known-correct behaviors
- A journal returning 0 results in a given week is normal (e.g. `Thyroid` is mostly
  adult; in short windows it often has no peds-tagged articles). Not an error.
- Very recent articles may lack MeSH tags (indexing lag); Template B peds filtering
  can therefore miss a few until they're indexed — they get picked up on a later run
  only if still inside the 14-day window, matching the original tool's behavior.
- All content filtering (errata, case reports, adult-only, basic science, hard-excludes)
  happens in `classifier.py` post-retrieval, exactly as the retrieval spec specifies.

## Month dating (entry-date vs print-date)
The month filter is keyed on PubMed ENTRY date, not print date, to match how the
original Perplexity collection dated articles (an article printed in 2024 but indexed
in 2026 is a 2026 entry). For the historical backfill this is sourced from
`all_articles_export.csv` (Perplexity's export) when present — `build_dashboard.py`
reads it as an entry-date override keyed by PMID. Newly fetched weekly articles are
recent, so their PubMed `pub_date` already reflects the current month and no override
is needed; they date correctly on their own. The CSV only matters for the historical
set and can stay in the PedEndoLit folder indefinitely.

## Manual run
Just tell Claude: "run the PedEndoLit weekly refresh" — it will follow this runbook.
