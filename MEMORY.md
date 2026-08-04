# PedsEndoBrief — Memory

Current-state facts for PedsEndoBrief, the pediatric endocrinology literature dashboard
(named PedEndoLit until 2026-08-04; internal filenames still use the old name).

**How the docs fit together:** this file holds durable current-state facts only.
`DECISIONS.md` holds every standing decision with its rationale and status. `_log.md` holds
the detailed chronological record. `TASKS.md` holds open items and backlog.
`WEEKLY_REFRESH_RUNBOOK.md` holds the weekly run procedure. `HANDOFF.md` is the start-here
summary for a fresh session.

## What this is
A self-contained literature-surveillance dashboard that replaces the paid Perplexity
Computer workflow. Pulls pediatric endocrinology articles from 19 monitored journals
via PubMed (free NCBI E-utilities, accessed through the PubMed MCP), classifies each
with a rules-based classifier ported from the Perplexity spec, and renders a single
self-contained page. Live at https://pedsendobrief.org with optional accounts (saved
articles, notes, since-your-last-visit). Store: 1,306 articles as of 2026-08-04,
including 49 guidelines (all six ISPAD 2024 CPCG chapters).

## Architecture (the pipeline)
- **`journals.json`** — 19 monitored journals + PEDS_TERMS + Template A/B (peds-filter) flags. This file is the authority on the journal list (`PedEndoLit_Retrieval_Config.docx` still says 18).
- **`classifier.py`** — the rules classifier (v2.5-equivalent: v2.4.2 spec + diabetes framework + Gender Medicine + Calcium/Parathyroid split). Pure functions, unit-tested.
- **`build_dataset.py`** — fetch→classify→dedup(by PMID)→writes `pedendolit-data.json`. Merge-only by default; `--rebuild` reclassifies from the `--raw` file (run `merge_raw_sources.py` first — see runbook's REBUILD PITFALL). Decodes HTML entities at ingest. **`ARCHIVE_AFTER_DAYS = None` — archiving is OFF** (see DECISIONS.md before ever re-enabling).
- **`merge_raw_sources.py`** — rebuilds `comprehensive_raw.json` from every raw file on disk, richest-value-wins, seeded from the current store (45 articles exist in no raw file). Zero network calls. Treats PubMed's literal `[Abstract not available]` string as empty rather than storing it as body text.
- **`guideline_sweep.py`** — the monthly safety net for guidelines published *outside* the 19 monitored journals. Reuses `map_raw()` + `classify()`, drops PMIDs already stored, and writes `guideline_review_queue.md` + `guideline_candidates.json`. **Never writes to the store** — approved candidates go in via `build_dataset.py --raw guideline_candidates.json`. Procedure and query in the runbook.
- **`build_dashboard.py`** — reads the datastore, writes `index.html` (the published artifact) plus two identical convenience copies (`PedEndoLit-Dashboard.html` here, gitignored, and one at the `01_Clinical_Research/` level). Holds `WEB3FORMS_KEY`, the Supabase keys, `GOOGLE_ENABLED`, and the entire client app in `HTML_TEMPLATE` — **edit the template, never the generated HTML**.
- **`pedendolit-data.json`** — the datastore (keyed by PMID).
- **Weekly refresh** — scheduled task, Sundays ~9:01 AM ET, follows `WEEKLY_REFRESH_RUNBOOK.md`.

## Source-of-truth spec documents (in this folder)
- `PedEndoLit_Classifier_Spec_v2.4.2.docx` — full classification logic.
- `PedEndoLit_Retrieval_Config.docx` — original 18 journals + queries (stale: APEM was added 2026-07-24; `journals.json` is the authority).
- `PedEndoLit_Diabetes_Classification_Framework.docx` — diabetes subtype framework (v2.5.0).
- `all_articles_export.csv` — Perplexity's ground-truth export (historical entry-date source; no longer drives month bucketing).

## Taxonomy state
17 topics: Diabetes, Growth, Puberty, Thyroid, Adrenal, Obesity/Metabolic, General
Endocrinology, Bone/Calcium, Pituitary, Hyperinsulinism, Genetics, Calcium/Parathyroid,
DSD, PCOS, Gender Medicine, Cancer Late Effects, Lipids.
Diabetes subtypes: T1D, T1D·Stage, T2D, Technology(subtopic), MODY/Monogenic, CFRD,
GDM, Steroid-induced, General.
Month filter buckets by **publication date** (`pub_date`) — this file and DECISIONS.md are
authoritative; the runbook's entry-date description is stale.

## Publishing
- **Live at https://pedsendobrief.org** — GitHub Pages serving `main` branch root of the public repo. HTTPS enforced; cert auto-renews (current one expires 2026-11-02). The old `molonych-source.github.io/pedendolit/` URL 301-redirects.
- **This folder is the git repo.** Publishing = commit + push; Pages redeploys automatically (~10 min CDN cache).
- **DNS (Cloudflare):** four apex A records to GitHub Pages (185.199.108–111.153), `www` CNAME to `molonych-source.github.io`, plus the Resend email records (DKIM `resend._domainkey`, MX + SPF on `send`, DMARC `_dmarc`). **Every record stays "DNS only" (grey cloud)** — the proxy blocks GitHub's TLS issuance; Cloudflare nags to enable it, ignore it.
- **Bug/comment form:** Web3Forms (key in `build_dashboard.py`; safe to expose — send-only). Sandbox can't test the POST; use a real browser.

## Accounts & auth (current state)
- **Supabase project `oiafndmmdplvitrttene`** (ca-central-1, free tier). Tables: `saved_articles` (`user_id`, `pmid`, `saved_at`, `note`) and `user_prefs` (`user_id`, `last_seen_at`, `prev_seen_at`). Only PMIDs stored server-side; article text always comes from the embedded dataset. Uses the publishable key; emptying the keys in `build_dashboard.py` rebuilds a pure Phase 1 page.
- **RLS is the only thing separating users** — `loadSaved()` issues a bare select. Re-run the two-account isolation test after ANY policy change; a broken policy leaks everything while the UI looks normal. The `anon` role has zero table grants.
- **Google sign-in:** Google Cloud project `indigo-cider-471318-p8`, client "PedEndoLit web (Supabase)", client ID `774609386490-c3vucn75ttkggi9rsjvkufhdtr696tb5.apps.googleusercontent.com` (public by design), scopes exactly `openid email profile` (never add more — see DECISIONS.md), published to "In production". Redirect URI: `https://oiafndmmdplvitrttene.supabase.co/auth/v1/callback`. Supabase's Redirect URLs allow-list needs exact URLs — its wildcards split on `/`, so `…/path/*` does NOT match nested paths. Client secret lives only in the Supabase dashboard; Google can't show a secret after creation — if lost, use **Add secret** on the client, don't recreate it. Two secrets currently exist; deleting the old unused one is a TASKS item. `GOOGLE_ENABLED` in `build_dashboard.py` gates the button. Cosmetic: consent screen shows the supabase.co domain (brand verification skipped; fine for a pilot).
- **Email via Resend custom SMTP** (live 2026-08-04): `smtp.resend.com:465`, user `resend`, password = Resend API key (lives only in Supabase's SMTP settings; if lost, mint a new key and re-paste), sender `no-reply@pedsendobrief.org`. Sending domain verified in Resend (account under molonych@gmail.com, free tier 100/day). Email rate limit 30/hour.
- **Both auth emails use six-digit `{{ .Token }}` codes, not links** (templates edited in the Supabase dashboard — note templates are only editable once custom SMTP is configured). **Email OTP length is 6** (Sign In / Providers → Email; the project shipped at 8).
- **Email confirmation is ON.** New email/password signups enter a six-digit code before the account activates. Same-email identities (password + Google) link into one account by design.
- **Reset/confirmation UI** lives in `HTML_TEMPLATE`: `resetPasswordForEmail` → `verifyOtp(type:'recovery')` → `updateUser`, with a consumed-OTP guard; signup confirmation uses `verifyOtp(type:'signup')` + `resend()`.
- **Password policy:** minimum 6 characters, no composition rules (NIST — see DECISIONS.md). The "at least 6 characters" string is hardcoded in multiple template locations that must move together if the minimum changes.
- Supabase leaked-password protection is Pro-only — the free-tier toggle silently refuses to save.

## Known limitations / honest caveats
- "Other" is still the largest study-type bucket (400 of 1,273), mostly articles that genuinely lack PubMed type tags.
- 59 articles lack an abstract — all letters/editorials with none indexed in PubMed.
- A few DSD enzyme-deficiency terms (e.g. 17β-HSD3) aren't in the DSD keyword list, so those occasionally land in General Endocrinology.
- 28 backfilled articles had abstracts condensed (not verbatim) by a subagent during fetch; classification verified unaffected.
- Coverage is still thin before 2026 for non-guideline articles: the 2024–25 backfill was publication-type-scoped (guidelines only). A full Jan-2025 corpus backfill remains a TASKS item.
- Guideline coverage outside the 19 monitored journals depends on the monthly sweep being run and reviewed; it is not automatic.

## Operational traps (learned the hard way)
- **PubMed MCP `search_articles` errors at `max_results=500`** — use 200; it also caps fetch batches at 20 and persists large results to files (read those from disk). It also rejects a query with **more than 20 boolean operators**, so a 19-journal OR-clause must be split in two.
- **The MCP nests the PMID at `identifiers.pmid`** — a top-level `.get("pmid")` silently returns `None`, which reads as "nothing matches the store". Always map records through `build_dataset.map_raw()` rather than reading fields directly.
- **`classify()` returns only classification fields** — the caller merges them onto the article (`{**art, **res}`), as `build_dataset` does. Forgetting this yields records with a topic but no title.
- **Assemble backfill raw files from named fetch outputs, never a glob** of the MCP tool-results directory: that directory also holds exploratory searches, and globbing it once auto-merged 20 unmonitored-journal guidelines into the store.
- **Never read article text into context** — parse the spilled MCP files with Python and print only counts/titles. The raw-file format is the MCP record verbatim, so building a raw file is a JSON concatenation.
- **`--rebuild` reads the `--raw` file, not the store** — run `merge_raw_sources.py` first or the store shrinks to one week.
- **GitHub Pages' CDN caches by path and ignores query strings** — `?v=N` cache-busters prove nothing; verify deploys with a hard reload or `curl -H 'Cache-Control: no-cache'`.
- **Pages custom-domain DNS check can wedge "in progress"** even with correct DNS, blocking cert issuance forever — remove and re-add the custom domain to re-trigger it, then pull the CNAME commits GitHub makes.
- **Supabase dashboard forms can silently revert scripted edits** — a value set programmatically may show "saved" and then come back unchanged (React state). Type into the field for real and re-read the setting afterward.
- **Free-tier Supabase projects pause after ~1 week without API activity**, and a paused project makes sign-in fail. The weekly refresh doesn't touch Supabase — only real user traffic does. Resume from the dashboard; a keepalive ping is planned with the digest.
- **Local git caveat:** `~/Documents` is iCloud-synced, so `.git` lives inside a syncing folder. GitHub is the durable backup — push at every checkpoint; re-clone if git ever reports corruption.

## Contacts / accounts
- GitHub repo: https://github.com/molonych-source/pedendolit (public, account `molonych-source`). Live site https://pedsendobrief.org.
- Domain: pedsendobrief.org at Cloudflare Registrar (~$10/yr, auto-renew on).
- Supabase project `oiafndmmdplvitrttene`; Google Cloud project `indigo-cider-471318-p8`; Resend account under molonych@gmail.com.
- Web3Forms key: in `build_dashboard.py` (`WEB3FORMS_KEY`, `bb727558-…` — safe to expose, send-only).
