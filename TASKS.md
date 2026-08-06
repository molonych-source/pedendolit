# PedEndoLit Dashboard — Tasks & Ideas

Running list of ideas, enhancements, and open items for the dashboard. Drop new
thoughts under **Ideas / Backlog** anytime; we promote them to **Active** when we
work on them. Durable facts and decisions live in `MEMORY.md` (same folder).

## Active

**Phase 3 plan agreed 2026-08-04.** A (foundation) is done. Next: B (features), C (mobile/perf), D (digest + sharing).

**Redesign roadmap agreed 2026-08-05** — site's primary job is a **weekly keep-up brief**, plus a "catch me up on *topic* since *date*" mode. Designing for an eventual **20,000 articles**. Six pieces; see `MEMORY.md` → "Scaling & the redesign roadmap" and `DECISIONS.md`.

- [x] ~~**F1 — deterministic regression check**~~ — done 2026-08-05. `check_classifier_regressions.py`; wired into both runbooks. See `_log.md`.
- [ ] **B — UI redesign.** Not started; no agreed design yet. The problem list is recorded in `MEMORY.md` ("Known UI problems") from a live review: four rows of filters before content, tier badge repeated inside its own tier group, boilerplate `Why PRACTICE-ALTERING` line, bottom line buried behind a click, tag noise, no time dimension, uniform type size with no hierarchy. **Next step is brainstorming/design, not code.**
- [ ] **C — catch-up mode ("what's new in *topic* since *date*").** Must be **coverage-aware**: dense coverage begins Jan 2026, so a naive date picker would silently under-report and look authoritative. The existing month filter is single-month equality (`a.month_key !== state.month`), not a since-range — that's a real gap, not a tweak.
- [ ] **A — async data-loading boundary.** Cheap now, expensive later: make every UI data access asynchronous while data is still embedded, so swapping in a Supabase-backed archive is plumbing rather than a rewrite. Do this *with* B.
- [ ] **D — backfill to 2015.** Now tractable: NCBI E-utilities is reachable directly (see `DECISIONS.md`), `efetch` takes 200 PMIDs/request, so ~20k articles ≈ ~100 requests ≈ minutes as a script. Needs: an NCBI API key, `tool=`/`email=` params, month-sliced chunking with a resumable manifest, and a classifier-QA pass on the result (20k articles through a rules classifier means proportionally more mislabels).
- [ ] **E — unattended scheduling.** `workflow` scope granted 2026-08-05, so the old blocker is cleared. Split deterministic work (fetch/classify/build/publish/regression-check — pure Python, GitHub Actions) from judgment work (the QA judge, which needs a model). Also carries the daily Supabase keepalive.
- [ ] **F2/F3 — LLM layers of automated QA.** Rules-based suspicion scoring to concentrate spend (abstract-only single-literal matches, the `General Endocrinology` catch-all, MeSH/topic disagreement — the `trace=True` hook already exposes these), then two judge loops: ~35 new articles weekly at ingest, plus a rotating audit of the archive. Add a `classifier.py` fingerprint to ledger entries so a classifier edit makes prior verdicts stale automatically. **Detection and alerting automatic; fixes stay human** — per the standing "reviewed, never auto-merged" decisions.

- [ ] **Confirm the performance fix on a real phone.**
- [ ] **Delete the old unused Google client secret** — two are enabled on the OAuth client; only the newer one is in use by Supabase. Christian's hands (Google Cloud console, no API). Measured on desktop: DOM nodes 36,133→14,091, render 748ms→164ms, filter interaction ~750ms→200ms. Still worth checking on an actual handset, since that's where it mattered.
- [ ] **Phase 3D — weekly email digest + public share links.** Domain blocker RESOLVED 2026-08-04: `pedsendobrief.org` is verified in Resend and Supabase sends through it. GitHub Actions as scheduler (Python-native, manual-run button, browser logs), plus a **daily keepalive ping** since free Supabase projects pause after ~7 days idle and that would silently break sign-in. Remaining blocker: `gh auth refresh -s workflow` — the current token can't push `.github/workflows/`.
- [x] ~~**Finish HTTPS on pedsendobrief.org**~~ — done 2026-08-04. Stuck Pages DNS check cleared by remove/re-add of the custom domain; cert issued (expires 2026-11-02); HTTPS enforced; Google sign-in verified on the new domain.
- [x] ~~**Password reset via six-digit email codes**~~ — done 2026-08-04. Resend SMTP on the custom domain, `{{ .Token }}` templates, full reset UI live; verified end-to-end by Christian. OTP length corrected 8→6.
- [x] ~~**Re-enable email confirmation**~~ — done 2026-08-04, with a six-digit confirmation-code UI at signup. Closes the pre-account-takeover risk that open unverified signup carried.
- [x] ~~**Backfill the ISPAD 2024 Clinical Practice Consensus Guidelines**~~ — done 2026-08-04 as part of a full 2024–25 guideline backfill across all 19 monitored journals (+53 articles). Guidelines 15→49; ISPAD 3→10 including all six 2024 CPCG chapters. Root cause was the date window, not the filter — see `_log.md`.
- [x] ~~**First guideline sweeps, reviewed and applied**~~ — done 2026-08-04. Two rounds over the 2024–26 wide search (20 then 29 candidates): 25 approved, 24 rejected, all recorded in `guideline_decisions.json`. Guidelines 49 → 74.
- [x] ~~**Pre-2024 guideline backfill (dedicated journals)**~~ — done 2026-08-04. The 32 hits in the 5 dedicated peds-endo journals (2018–2023), 31 reviewed (1 already in store), 30 approved (all but a 2017 Korean dyslipidemia guideline). Includes the full ISPAD 2018 CPCG diabetes series. Guidelines 74 → 104; coverage now spans 2018 onward.
- [x] ~~**Wide all-journals pre-2024 sweep**~~ — done 2026-08-04. 104 reviewed (two parallel Sonnet subagents), 41 accept / 21 borderline / 42 reject, Christian approved 45 (incl. 7 borderline overrides). Guidelines 104 → 149. **This closes every guideline-hunting angle identified this session** — remaining coverage work is the recurring monthly sweep, not backlog.
- [x] ~~**Classifier QA sweep, round 1**~~ — done 2026-08-05, all 6 found fixed. Built the pipeline (`classifier_qa_sample.py` / `build_classifier_qa_review.py` / `apply_classifier_qa.py`, procedure in `CLASSIFIER_QA_RUNBOOK.md`), ran it on the 64-article Diabetes+Guideline/Consensus batch that surfaced the bug. Judge flagged 6 wrong (found a 6th beyond the 5 known: an EASL-EASD-EASO MASLD guideline). Fixed 4 via `classifier.py` (Hyperinsulinism substring/ordering bug — bare "hyperinsulinism" hoisted into the pre-check branch; Turner syndrome and a genuinely multi-system thalassemia guideline hoisted into pre-checks before Diabetes) — verified via a full-store topic-diff (7 total moves, all reviewed correct, including 2 beneficial side effects: a Prader-Willi/diazoxide article that was wrongly Hyperinsulinism, and a Turner-population glycemia study). The remaining 2 (Vitamin D CPG, MASLD guideline) had no safe rule-based fix — every keyword/title guard tested misrouted more genuinely-correct Diabetes articles than it fixed — so, per Christian's call, fixed via a new targeted per-PMID override (`apply_classifier_qa.py --accept-residual` + `build_dataset.py`'s `apply_topic_overrides()`) instead of forcing a bad general rule. Verified in `index.html`, not just the datastore. 9 total topic changes vs. the pre-session baseline, zero collateral.
- [ ] **Classifier QA sweep, round 2** — the Gender Medicine/GnRH item and the DSD keyword gap below weren't part of round 1's sample (a different batch); run a fresh sample scoped to those, plus a broad taxonomy-wide sweep to catch anything else, per `CLASSIFIER_QA_RUNBOOK.md`.
  - [ ] **Fix the Gender Medicine misclassification of GnRH-analog guidelines** — PMID 31319416 (2018 international GnRH-analog consensus for precocious puberty) was filed under Gender Medicine instead of Puberty; the pre-check likely keys on "GnRH analog" phrasing shared with gender-affirming-care literature. Single occurrence, article content unaffected — see `classify_topic` in `classifier.py`.
- [ ] **Run the monthly guideline sweep** — 60-day rolling window; full procedure and agent prompt in `WEEKLY_REFRESH_RUNBOOK.md`. Nothing pending right now (both sweeps cleared).
- [ ] **Consider promoting recurring keeper journals into `journals.json`** — if the sweep keeps surfacing approved guidelines from the same journal, monitor it directly instead of relying on the sweep.
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
- [x] **Rebranded to PedsEndoBrief on a custom domain** — https://pedsendobrief.org (Cloudflare Registrar). DNS, GitHub Pages, Supabase redirect URLs and the Google OAuth origin all updated; old github.io URL 301-redirects. Only user-facing strings renamed; internal filenames left alone deliberately. — ✅ 2026-08-04
- [x] **Phase 3C: rendering performance** — collapsed tiers and abstract text now build lazily. Measured before/after on the live page: 36,133→14,091 DOM nodes, 748→164ms initial render, ~750→200ms per filter interaction. — ✅ 2026-08-04
- [x] **Google sign-in live** — "Continue with Google" alongside email/password. No domain, no email provider, no cost, and no Google verification review (basic scopes only). Gives genuinely verified email addresses, which email/password signups don't while confirmation is off, and removes the password-reset problem entirely for anyone who uses it. Verified end-to-end: sign-in, provider recorded as `google`, save written, RLS isolation still passing. — ✅ 2026-08-04
- [x] **Phase 3B: since-your-last-visit, private notes on saves, guidelines filter, citation/Zotero export** — plus two long-standing bugs fixed (open abstracts collapsing on every re-render; search re-rendering on every keystroke) and phone tap-target/layout improvements. Verified live: RLS isolation on the new `user_prefs` table, note round-trip, guidelines filter (15 of 1273), citation copy. — ✅ 2026-08-04
- [x] **Fetched the missing abstracts from PubMed** — 427 articles re-fetched via the PubMed MCP. Only 59 still lack an abstract, all letters/editorials with none indexed. Abstracts 336→1214, fully citable 308→1266. — ✅ 2026-08-04
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
