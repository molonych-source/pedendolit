# PedEndoLit Dashboard — Tasks & Ideas

Running list of ideas, enhancements, and open items for the dashboard. Drop new
thoughts under **Ideas / Backlog** anytime; we promote them to **Active** when we
work on them. Durable facts and decisions live in `MEMORY.md` (same folder).

## Active

- [ ] **Expand the database back to January 2025** — backfill all 16 journals Jan 2025–present with the same strict peds filter + v2.5 classifier. Large fetch (~2,000–3,000 candidate PMIDs); needs paginated/month-sliced searches (the search MCP truncates at max_results, errors at 500). Plan: delegate the bulk fetch to a subagent. STARTED then paused 2026-05-29 — pick up on request.

## Ideas / Backlog
<!-- Unprioritized. Add freely; we'll triage. -->

- [ ] **Time-boxed "Recent" default view** — open the dashboard to "what's new in the last 7/30 days" instead of the full archive. Highest-leverage change for actually keeping up. (From clinician-review 2026-05-29.)
- [ ] **Fix `is_new` seeding** — currently all 878 are flagged new (backfill artifact). Seed it to a real recent window (e.g. last 30 days) so the "New this period" view is trustworthy before weekly refreshes catch up. (Clinician-review top-2.)
- [ ] **Default landing = Practice-Altering + High only** — or make that an easy one-click "must-read" view (99 articles vs 348). (Clinician-review.)
- [ ] **Read-later / mark-as-read / done state** — let a reader triage and remember what they've already seen across visits. (Clinician-review.)
- [ ] **Show bottom-line on the collapsed card for PA + High tiers** — 30-second triage without expanding. Consider auto-expanding the 7 PA items. (Clinician-review.)
- [ ] **Better-type the "Other" study-type bucket (~264)** — improve evidence-level signal at a glance, or surface evidence level differently. (Clinician-review.)
- [ ] **Email / RSS digest of new PA+High items** — keep up without opening the page. (Clinician-review.)
- [ ] **Saved specialty sub-views** — e.g. default to Diabetes + Growth without re-filtering each visit. (Clinician-review.)
- [ ] **Auto-publish to GitHub Pages** — scheduled task commits the updated `index.html` to the repo each week so the live site stays current with no manual upload. Needs repo URL + a one-time access token. (Offered 2026-05-29, not set up.)
- [ ] **Expand DSD keyword coverage** — enzyme-deficiency terms (e.g. 17β-HSD3, 5-alpha reductase) so those route to DSD instead of General Endocrinology.

## Done
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
