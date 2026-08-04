# PedEndoLit Dashboard — Memory

Project memory for the PedEndoLit pediatric endocrinology literature dashboard.
Durable facts, decisions, and architecture. For open ideas and to-dos see `TASKS.md`
in this same folder. For the weekly run procedure see `WEEKLY_REFRESH_RUNBOOK.md`.

## What this is
A self-contained literature-surveillance dashboard that replaces the paid Perplexity
Computer workflow. Pulls pediatric endocrinology articles from 19 monitored journals
via PubMed (free NCBI E-utilities, accessed through the PubMed MCP), classifies each
with a rules-based classifier ported from the Perplexity spec, and renders a single
self-contained `PedEndoLit-Dashboard.html` (data embedded; opens by double-click, no
server). Goal: drop the Perplexity subscription, run everything inside Cowork.

## Architecture (the pipeline)
- **`journals.json`** — 19 monitored journals + PEDS_TERMS + Template A/B (peds-filter) flags.
- **`classifier.py`** — the rules classifier (currently v2.5-equivalent: v2.4.2 spec + diabetes framework + Gender Medicine + Calcium/Parathyroid split). Pure functions, unit-tested.
- **`build_dataset.py`** — fetch→classify→dedup(by PMID)→60-day archive + is_new reset→writes `pedendolit-data.json`. `--rebuild` reclassifies all raw from scratch (use after classifier edits). Decodes HTML entities (`&#xa0;` etc.) at ingest.
- **`build_dashboard.py`** — reads the datastore, writes `index.html` (the published artifact, inside this folder = inside the git repo) plus two identical convenience copies: `PedEndoLit-Dashboard.html` here (gitignored) and one at the `01_Clinical_Research/` level. Holds the WEB3FORMS_KEY, the Supabase keys, and the entry-date override logic.
- **`pedendolit-data.json`** — the datastore (active + archived, keyed by PMID).
- **Weekly refresh** — scheduled task, Sundays ~9:01 AM ET, follows `WEEKLY_REFRESH_RUNBOOK.md`. Replaces the old Perplexity cron.

## Source-of-truth spec documents (in this folder)
- `PedEndoLit_Classifier_Spec_v2.4.2.docx` — full classification logic (exclusions, 25-branch topic waterfall, study types, 4-tier impact, board relevance, tags).
- `PedEndoLit_Retrieval_Config.docx` — the original 18 journals, exact PubMed queries, date window, dedup. Not yet updated for the 19th (APEM, added 2026-07-24 directly to `journals.json`) — see Key Decisions below.
- `PedEndoLit_Diabetes_Classification_Framework.docx` — diabetes subtype framework (v2.5.0).
- `all_articles_export.csv` — Perplexity's ground-truth article export (used as the entry-date source for the historical set).

## Key decisions (and the why)
- **Stricter peds filter kept over matching Perplexity's count.** Perplexity's set is 960; ours is ~878. The gap is Perplexity letting non-pediatric noise through (erectile dysfunction, colorectal cancer, postmenopausal, personal essays). Our v2.4.2 classifier excludes those by design. Decision: keep the clean filter, accept the lower count. (Decided 2026-05-29.)
- **Month filter keyed on PUBLICATION date (pub_date).** REVERSED the earlier entry-date decision: entry-date bucketing put Jan–Mar articles under "June 2026" (when Perplexity indexed them), which confused the "Month" filter — a clinician expects "published in." Now month_key = pub_date month for every article; verified 0 mismatches between an article's month bucket and its displayed date. Trade-off accepted: the dropdown again lists older real publication months (back to 2023) for the handful of old-print articles, which is honest. The `all_articles_export.csv` entry-date override is no longer used for month bucketing. (Reversed 2026-05-30; original entry-date approach was 2026-05-29.)
- **Date scope restricted to 2026 (+ small 2025 tail) on the May-29 pass.** A NEXT step is in flight to expand back to Jan 2025 — see TASKS.md.
- **Impact segmented filter replaced by the tier-accordion grouping** — grouping by tier IS the impact filter; two controls for one dimension was redundant.
- **Analytics charts moved to their own tab** (Topic distribution, Evidence impact, Articles by journal); Feed is the default tab.
- **PubMed search MCP errors at max_results=500 — use 200.** No journal approaches 200 even over 5 months. (Noted in runbook.)
- **Turner & Prader-Willi intentionally live under Growth** (not a dedicated topic) — GH therapy is the dominant peds-endo touchpoint; the search box covers syndrome-level retrieval. (Decided 2026-05-29.)
- **Two classifier bugs found via pilot and fixed:** (1) incidental "IGF" / "MEN1" abstract mentions hijacking topic — fixed with subject-vs-mention guards; (2) Systematic Reviews showed the generic "Authoritative review" rationale — now have their own.
- **Added Annals of Pediatric Endocrinology & Metabolism (APEM) as the 19th monitored journal** (`Ann Pediatr Endocrinol Metab`, `peds_filter: false` — dedicated peds-endo journal like Horm Res Paediatr / J Clin Res Pediatr Endocrinol / J Pediatr Endocrinol Metab). Confirmed active and PubMed-indexed (89 articles since Jan 2025) before adding; ruled out International Journal of Pediatric Endocrinology (IJPE) as a candidate — PubMed shows no articles since ~2021, effectively dormant. Backfilled Jan 2026–present (matching the store's primary Jan–Jul 2026 coverage window for the other 18 journals) on 2026-07-24: 30 candidate PMIDs, 29 added, 1 excluded (erratum). `WEEKLY_REFRESH_RUNBOOK.md` updated to reflect 19 journals; `PedEndoLit_Retrieval_Config.docx` (the original spec doc) still says 18 and hasn't been regenerated. (Decided 2026-07-24.)

## Taxonomy state
17 topics: Diabetes, Growth, Puberty, Thyroid, Adrenal, Obesity/Metabolic, General
Endocrinology, Bone/Calcium, Pituitary, Hyperinsulinism, Genetics, Calcium/Parathyroid,
DSD, PCOS, Gender Medicine, Cancer Late Effects, Lipids.
Diabetes subtypes: T1D, T1D·Stage, T2D, Technology(subtopic), MODY/Monogenic, CFRD,
GDM, Steroid-induced, General.
Recently added: **Gender Medicine** (ABP Domain 16, pre-check before Puberty/DSD with a
DSD-context guard) and **Calcium/Parathyroid** split out of Bone/Calcium (both 2026-05-29).

## Publishing
- **Live at https://molonych-source.github.io/pedendolit/** — GitHub Pages, serving `main` branch root of https://github.com/molonych-source/pedendolit (public). Enabled 2026-08-04; before that the repo existed but Pages had never actually been switched on, so the site was never live despite handoff docs assuming it was.
- **This folder is the git repo.** Re-publishing = `git add`, `git commit`, `git push`; Pages redeploys automatically (~10 min CDN cache). No more manual file upload. Auto-publish on a schedule is still a TASKS.md item.
- **Bug/comment form**: Web3Forms (key `bb727558-...` is in `build_dashboard.py`; safe to expose — send-only). Reports email to Christian. First submission triggers a one-time Web3Forms verification email. Sandbox can't test the POST (proxy blocks api.web3forms.com) — test from a real browser.

## Phase 2: accounts + saved articles (live 2026-08-04)
- Supabase project **`oiafndmmdplvitrttene`** — `https://oiafndmmdplvitrttene.supabase.co`, region ca-central-1, free tier. One table, `public.saved_articles` (`user_id`, `pmid`, `saved_at`), created from `supabase_setup.sql`. Only PMIDs are stored, so the saved list can never drift out of sync with the weekly dataset.
- Uses the **publishable key** (`sb_publishable_…`) rather than the legacy `eyJ…` anon JWT; either works, the swap is one line in `build_dashboard.py` plus a rebuild.
- Emptying `SUPABASE_URL` / `SUPABASE_ANON_KEY` rebuilds a pure Phase 1 page — that's the feature's off switch.
- **Per-user scoping rests entirely on Row-Level Security**: `loadSaved()` issues a bare select with no `user_id` filter. Correct by design, but re-run the two-account isolation test after ANY policy change — a broken policy leaks every list while the UI looks normal.
- Email confirmation OFF (built-in sender is rate-limited), so addresses are unverified and signup is open. No password-reset UI — reset from Supabase → Authentication → Users.
- The `anon` role has zero table grants (explicitly revoked; Supabase's defaults would otherwise auto-grant).

## Data recovery + archive fix (2026-08-04)
- **The 60-day archive was a time bomb and is now OFF** (`ARCHIVE_AFTER_DAYS = None` in `build_dataset.py`). It keyed on `review_date` = when an article was ADDED, not published; the whole historical backfill shares `2026-06-28`, so all 1029 would have expired on one run. Simulated: 1287 → 258 articles on the 2026-08-30 run, → 35 by late September. The dashboard is a searchable corpus; "what's new" belongs per-user, not as a global purge.
- **74% of the store had no abstract** and had been classified on title alone. Cause: the previous `comprehensive_raw.json` (built by an unsaved ad-hoc script) held 1053 records but only 93 abstracts, while the original per-batch MCP fetches in `_tmp_batches/` still had full text. This — not the classifier — was why two-thirds of articles typed as "Other" with no bottom line.
- **`merge_raw_sources.py` fixes it with zero API calls.** Merges every local raw file, richest-value-wins per field. Seeds from the current store first because **45 published articles exist in no raw file at all** (including both Endocrine Society guidelines) and a rebuild without that seed would delete them.
- **`map_raw()` was silently dropping data**: never read the `citation` block (volume/issue/pages) or `identifiers.pmc`, and truncated authors at 6 — 174 records sat at exactly 6, so complete vs truncated was indistinguishable. All fixed.
- **Guideline detection was broken two ways**: `classify_study_type` tested meta-analysis and systematic review *before* guidelines (so the Endocrine Society precocious-puberty guideline typed as "Systematic Review"), and only looked at the first 120 chars against a narrow phrase list. Now guidelines are tested first, using `pub_types` + full title, with a guard excluding papers *about* guidelines (adherence/implementation/survey).
- **Result of reclassifying:** abstracts 336→853, clinical bottom lines 336→853, "Other" 853→590, guidelines 4→15, fully citable 308→852, board-relevant 69→142, volume/issue/pages 0→535, PMC ids 0→409. Store 1287→1280; all 7 removals correct (4 errata, 3 adult-medicine) and only detectable once abstracts existed.
- **Still outstanding:** ~430 articles have no abstract in any local file and need a real PubMed re-fetch — the paused job in `PedEndoLit Legacy Metadata Backfill Handoff.md`.

## Known limitations / honest caveats
- `is_new` means "added in the most recent run" — a global flag, so it cannot answer "what's new for me". Per-user last-seen is the Phase 3 fix.
- "Other" is still the largest study-type bucket (590 of 1280), mostly articles that genuinely lack PubMed type tags.
- A few DSD enzyme-deficiency terms (e.g. 17β-HSD3) aren't in the DSD keyword list, so those occasionally land in General Endocrinology.
- 28 backfilled articles had abstracts condensed (not verbatim) by a subagent during fetch; classification verified unaffected.

## Contacts / accounts
- Web3Forms key: in `build_dashboard.py` (`WEB3FORMS_KEY`).
- GitHub repo: https://github.com/molonych-source/pedendolit (public, account `molonych-source`). Live site https://molonych-source.github.io/pedendolit/.
- Supabase project `oiafndmmdplvitrttene` (free tier). **Free-tier projects pause after ~1 week with no API activity, and a paused project makes sign-in fail** — the weekly refresh doesn't touch Supabase, only real user traffic does. Resume from the Supabase dashboard.
- Local caveat: `~/Documents` is iCloud-synced, so `.git` lives inside a syncing folder. GitHub is the durable backup — push at every checkpoint; re-clone if git ever reports corruption.
