# PedEndoLit — Weekly Refresh Runbook

This is the procedure the weekly scheduled task follows. It replaces the old
Perplexity `peds_endo_weekly_update.py` cron. Everything runs inside Claude/Cowork.

## Which model to run this on
The weekly refresh and the monthly guideline sweep are **mechanical**: search, fetch,
merge, rebuild. There is no design judgment in them, and nearly all their cost is
PubMed metadata. **Run them on Sonnet, or delegate the fetch to a subagent** so the
metadata lands in that context instead of the main one. Reserve the stronger model for
work that changes *how* articles are judged — `classifier.py` edits, taxonomy changes,
diagnosing a coverage gap.

**Token rule for any fetch step:** never read article text into context. The MCP spills
large results to files under `.claude/projects/.../tool-results/`; parse those with
Python and print only counts and titles. The raw-file format IS the MCP metadata record
verbatim, so assembling a raw file is a JSON concatenation, not a transformation.

## Why a Claude task and not a plain cron
PubMed (NCBI E-utilities) is reachable from the **PubMed MCP tool**, which only the
Claude agent can call — the sandbox shell cannot reach NCBI directly. So the weekly
job is an agent task: Claude calls the MCP to fetch, then a local Python script
classifies and rebuilds the dashboard. No Perplexity, no external server.

## Files (all in `01_Clinical_Research/Resources/PedEndoLit/` — this folder IS the git repo)
- `journals.json` — 19 monitored journals + PEDS_TERMS + Template A/B flags
- `classifier.py` — v2.4.2 classifier (faithful port of reclassify_v2.py)
- `build_dataset.py` — classifies raw articles, dedupes by PMID, applies 60-day archive + is_new reset, writes `pedendolit-data.json`
- `build_dashboard.py` — renders the dashboard HTML (data embedded)
- `pedendolit-data.json` — the datastore (active + archived articles, keyed by PMID)
- `index.html` — the PUBLISHED dashboard; this is what GitHub Pages serves
- `PedEndoLit-Dashboard.html` — identical convenience copy, gitignored (also copied to `01_Clinical_Research/`)

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
8. **Publish** — the site is live, so this step is no longer optional:
   `git add -A && git commit -m "Weekly refresh <YYYY-MM-DD>" && git push`
   GitHub Pages redeploys on its own within a minute or two (~10 min CDN cache).
   Live at https://molonych-source.github.io/pedendolit/
9. Report: new article count, new practice-altering items, exclusions fired.

Nothing in the weekly refresh touches Supabase — user accounts and saved lists are
independent of the article pipeline. Saved PMIDs that get archived out of the dataset
show up as "no longer in the current list" stubs rather than breaking.

## Monthly guideline sweep (run once a month)

The weekly refresh is journal-scoped: it can only ever see the 19 journals in
`journals.json`. Societies do publish peds-endo guidelines elsewhere, so this sweep is
the safety net. It is **publication-type-scoped across all journals** and its results
are **reviewed, never auto-merged** — the query runs about 35% precision (the rest is
dermatology, urology, nephrology, ophthalmology).

1. Call `search_articles` with a rolling **60-day** window (overlapping, so nothing
   falls between runs), `max_results = 200`:

```
(Practice Guideline[Publication Type] OR Guideline[Publication Type] OR Consensus Development Conference[Publication Type])
AND (child[MeSH] OR adolescent[MeSH] OR pediatric[tiab] OR paediatric[tiab])
AND (endocrin*[tiab] OR diabetes[tiab] OR thyroid[tiab] OR puberty[tiab]
     OR "growth hormone"[tiab] OR adrenal[tiab] OR obesity[tiab] OR calcium[tiab]
     OR "bone density"[tiab] OR pituitary[tiab] OR "sex development"[tiab]
     OR hypoglycemia[tiab])
```

   Note: the MCP caps a query at **20 boolean operators** — split into two searches if
   you extend the term list.
2. Fetch metadata for the PMIDs, assemble them into `sweep_raw.json` (a plain list of
   MCP records — no transformation).
3. `python3 guideline_sweep.py --raw sweep_raw.json`
   Drops PMIDs already in the store **and** any already ruled on in
   `guideline_decisions.json`, classifies the rest, writes `guideline_candidates.json`
   (plus `guideline_review_queue.md`, a plain-text view).
4. **Relevance review — dispatch a Sonnet subagent** with the prompt below. It writes
   `guideline_verdicts.json`. This is the step that supplies the two gates the pipeline
   lacks (*is it pediatric* and *is it endocrinology*) — `classify_topic` ends in an
   unconditional `return "General Endocrinology"`, so an off-topic guideline is never
   rejected by the classifier, only mislabelled.
5. `python3 build_review_page.py` → `guideline_review.html`. Open it by double-click.
6. **Christian ticks and clicks Submit** → downloads `approved_pmids.json`.
7. `python3 apply_approvals.py` (defaults to `~/Downloads/approved_pmids.json`), then the
   three commands it prints: `build_dataset.py --raw guideline_approved_raw.json`,
   `merge_raw_sources.py`, `build_dashboard.py`.

Approving a guideline from an unmonitored journal is a deliberate, per-article choice.
If one journal keeps producing keepers, that is the signal to add it to `journals.json`
instead.

### The review agent prompt (step 4)

Point it at `guideline_candidates.json` and require this output shape in
`guideline_verdicts.json`:

```json
{"reviewed_by":"agent",
 "verdicts":{"<pmid>":{"verdict":"accept|borderline|reject",
                       "confidence":"high|medium|low",
                       "reason":"one sentence for a clinician",
                       "topic":"one of the 17 topics, or null if rejected"}}}
```

The prompt must contain:
- the **17-topic taxonomy** as the definition of in-scope endocrinology (see `MEMORY.md`);
- **both gates, explicitly**: pediatric (or transition-age) AND endocrine/metabolic as the
  *subject*, not an incidental mention;
- instruction to **reject** other specialties' guidelines that merely touch a hormone or
  metabolic word (hemophilia, dermatitis, glomerulonephritis, ophthalmic syndromes);
- instruction to use **borderline rather than guess** when the endocrine claim is real but
  peripheral (female athlete triad, adolescent gynecology, cardiovascular prevention);
- a note that **non-English guidelines still count** — a Chinese or Russian national T1D
  or CAH guideline is core peds endo;
- a self-validation step: reload the written JSON, assert one verdict per candidate and
  that every verdict is one of the three allowed strings.

The page shows each verdict and its reason, pre-ticks only `accept`, and keeps `reject`
collapsed but still tickable — the agent triages, the physician decides.

## Deciding WHAT to change before a re-classify
Before editing `classify_topic()` on a hunch, run the classifier QA sweep
(`CLASSIFIER_QA_RUNBOOK.md`) — it samples already-classified articles, has a judge
subagent flag likely topic mismatches, and produces a root-cause report grouped by
`current_topic → target_topic` with a title/abstract trigger-location signal, so the fix
targets the actual bug instead of a guess.

## Re-classify everything (only when classifier.py changes)

> **CRITICAL — REBUILD PITFALL:** `--rebuild` reads from the `--raw` file, NOT from
> the existing store (`pedendolit-data.json`). The normal weekly procedure overwrites
> `raw_articles.json` with only that week's fetch, so `--rebuild` without an explicit
> `--raw comprehensive_raw.json` will WIPE the store down to that one week.

Always run these two commands in order:

```
python3 merge_raw_sources.py                       # refresh the cumulative source
python3 build_dataset.py --run-date <YYYY-MM-DD> --raw comprehensive_raw.json --rebuild
python3 build_dashboard.py
```

`merge_raw_sources.py` rebuilds `comprehensive_raw.json` from every raw file on disk
(the named sources plus `_tmp_batches/*.json`), keeping the richest value for each
field per PMID. It **seeds from the current store first**, so a rebuild can never
delete an article that exists only in `pedendolit-data.json` — 45 published articles
were in that position, including both Endocrine Society guidelines. Use `--dry-run`
to preview the field counts before writing.

This replaced an unsaved ad-hoc script whose output had lost most of its abstracts:
1053 records but only 93 abstracts, which is why 74% of the store had been classified
on title alone. Reclassifying against the recovered metadata (2026-08-04) took
abstracts 336→853, guidelines 4→15, and "Other" study types 853→590.

`--rebuild` preserves each article's original `review_date`. Expect a small drop in
article count: exclusion rules (errata, adult-only) fire correctly once abstracts are
present. Check what was dropped rather than assuming — `git diff` the store.

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
