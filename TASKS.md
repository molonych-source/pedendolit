# PedEndoLit Dashboard — Tasks & Ideas

Running list of ideas, enhancements, and open items for the dashboard. Drop new
thoughts under **Ideas / Backlog** anytime; we promote them to **Active** when we
work on them. Durable facts and decisions live in `MEMORY.md` (same folder).

## Active

**Phase 3 plan agreed 2026-08-04.** A (foundation) is done. Next: B (features), C (mobile/perf), D (digest + sharing).

- [ ] **Phase 3B — since-your-last-visit, notes on saves, guidelines view, citation export.** Needs new `user_prefs` table (one row per user, `last_seen_at`) and a `note` column on `saved_articles`. The guidelines view is now viable (15 detected, was 4); citation export is now viable (852 fully citable, 535 with volume/issue/pages).
- [ ] **Phase 3C — mobile and performance.** `render()` rebuilds all ~1280 cards into one `innerHTML` (~35-50k DOM nodes) and the search box has **no debounce**, so every keystroke re-renders everything. Also: tap targets ~26px vs 44px minimum, `.tabs` has no `flex-wrap`, and open abstracts silently collapse on any re-render (inline `style.display`, no backing state Set).
- [ ] **Phase 3D — weekly email digest + public share links.** Needs a domain (~$10/yr) — `resend.dev` 403s to anyone but yourself and `github.io` can't be DNS-verified. GitHub Actions as scheduler (Python-native, manual-run button, browser logs), plus a **daily keepalive ping** since free Supabase projects pause after ~7 days idle and that would silently break sign-in. Blocker: `gh auth refresh -s workflow` — the current token can't push `.github/workflows/`.
- [x] ~~**Re-fetch metadata for the ~430 articles still lacking an abstract**~~ — done 2026-08-04 via the PubMed MCP. Only 59 remain without one, all letters/editorials with no abstract indexed. Supersedes the paused job in `PedEndoLit Legacy Metadata Backfill Handoff.md`.
- [ ] **Expand the database back to January 2025** — backfill all 19 journals Jan 2025–present with the same strict peds filter + classifier. Large fetch (~2,000–3,000 candidate PMIDs); needs paginated/month-sliced searches (the search MCP truncates at max_results, errors at 500). Plan: delegate the bulk fetch to a subagent. STARTED then paused 2026-05-29 — pick up on request.

## Ideas / Backlog
<!-- Unprioritized. Add freely; we'll triage. -->

- [ ] **Time-boxed "Recent" default view** — open the dashboard to "what's new in the last 7/30 days" instead of the full archive. Highest-leverage change for actually keeping up. (From clinician-review 2026-05-29.)
- [ ] ~~**Fix `is_new` seeding**~~ — superseded by Phase 3B. `is_new` is now accurate as "added in the most recent run", but it is a *global* flag and so can never answer "new to me". Per-user `last_seen_at` replaces it rather than fixing it.
- [ ] **Default landing = Practice-Altering + High only** — or make that an easy one-click "must-read" view (99 articles vs 348). (Clinician-review.)
- [ ] **Read-later / mark-as-read / done state** — let a reader triage and remember what they've already seen across visits. (Clinician-review.)
- [ ] **Show bottom-line on the collapsed card for PA + High tiers** — 30-second triage without expanding. Consider auto-expanding the 7 PA items. (Clinician-review.)
- [ ] **Better-type the "Other" study-type bucket (590 of 1280)** — down from 853 after the 2026-08-04 metadata recovery. The remainder is mostly articles that genuinely carry no PubMed type tag; further gains need the ~430-article re-fetch above, not classifier tweaks. (Clinician-review.)
- [ ] **Email / RSS digest of new PA+High items** — keep up without opening the page. (Clinician-review.)
- [ ] **Saved specialty sub-views** — e.g. default to Diabetes + Growth without re-filtering each visit. (Clinician-review.)
- [ ] **Auto-publish to GitHub Pages** — scheduled task commits the updated `index.html` to the repo each week so the live site stays current with no manual upload. Needs repo URL + a one-time access token. (Offered 2026-05-29, not set up.)
- [ ] **Expand DSD keyword coverage** — enzyme-deficiency terms (e.g. 17β-HSD3, 5-alpha reductase) so those route to DSD instead of General Endocrinology.

## Done
- [x] **Phase 3A: fixed the data foundation** — (1) defused the 60-day archive, which was set to cut the site from 1287 articles to 258 on the 2026-08-30 run and to 35 by late September; (2) recovered lost metadata from local files with zero API calls (abstracts 336→853, fully citable 308→852, volume/issue/pages 0→535, PMC ids 0→409); (3) fixed guideline misclassification (4→15 detected). Store 1287→1280, the 7 removals being correct exclusions newly visible once abstracts existed. — ✅ 2026-08-04
- [x] **Phase 2 shipped: accounts + personal saved-article lists** — Supabase schema + RLS created, credentials wired, GitHub Pages enabled, site live at https://molonych-source.github.io/pedendolit/. Verified end-to-end: signup/sign-in, save/un-save, session persistence across reload, per-user isolation (a different user ID sees 0 rows while the owner view sees all), signed-out visitors denied at the grant level, and the "no longer in the current list" fallback for archived PMIDs. — ✅ 2026-08-04
- [x] **Put the project under version control** — git repo in this folder, pushed to https://github.com/molonych-source/pedendolit (public). — ✅ 2026-08-04
- [x] **Add Annals of Pediatric Endocrinology & Metabolism as 19th monitored journal + backfill Jan 2026–present (29 articles)** — ✅ 2026-07-24
- [x] **Build the dashboard end-to-end** (classifier port, retrieval, 60-day seed, scheduled weekly refresh) — ✅ 2026-05-29
- [x] **Backfill Jan–May 2026 (~878 articles)** — ✅ 2026-05-29
- [x] **Fix Systematic Review impact-rationale bug** — ✅ 2026-05-29
- [x] **Add diabetes subtype / age-range filters + hide-LOW default** — ✅ 2026-05-29
- [x] **Add Diabetes Classification Framework (CFRD, Steroid-induced, T1D·Stage subtypes)** — ✅ 2026-05-29
- [x] **Collapsible tier groups + per-card expand + full-abstract reveal** — ✅ 2026-05-29
- [x] **Month dropdown filter (entry-date based)** — ✅ 2026-05-29
- [x] **mm/dd/yyyy date display on cards** — ✅ 2026-05-29
- [x] **Decode HTML entities in abstracts** — ✅ 2026-05-29
- [x] **Feed / Analytics tabs** — ✅ 2026-05-29
- [x] **Bug/comment report form (Web3Forms) in header** — ✅ 2026-05-29
- [x] **Add Gender Medicine topic + split Calcium/Parathyroid from Bone** — ✅ 2026-05-29
- [x] **Create MEMORY.md + TASKS.md for the project** — ✅ 2026-05-29
