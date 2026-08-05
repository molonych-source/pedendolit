# PedsEndoBrief — Project Log

Reverse-chronological record of what happened and when. Rationale for standing choices lives
in `DECISIONS.md`; current-state facts live in `MEMORY.md`. Backfilled 2026-08-04 from the
git history (33 commits to that date) and the dated sections formerly in `MEMORY.md`.

---

### [2026-08-04] pre-2024 guideline backfill (ISPAD 2018 series)

Ran the high-precision option priced earlier: publication-type-scoped search restricted to
the 5 journals already dedicated to peds-endo (Horm Res Paediatr, Pediatr Diabetes,
J Clin Res Pediatr Endocrinol, Ann Pediatr Endocrinol Metab, J Pediatr Endocrinol Metab),
2018–2023. 32 hits; 1 already in the store; 31 reviewed.

- **Agent review: 31/31 accept, 0 borderline, 0 reject** — confirms the precision hypothesis
  (journal-dedicated scope ≈100% vs. the wide sweep's ~35%). 22 of the 31 are chapters of the
  **ISPAD 2018 Clinical Practice Consensus Guidelines** diabetes series; the rest: the ISPAD
  DKA COVID-era addendum, an EASD/ISPAD CGM-and-exercise statement, the 2018 international
  GnRH-analog consensus, three growth-diagnostic consensus papers, and a 2017 Korean pediatric
  dyslipidemia guideline.
- **Christian approved 30 of 31**, declining only the Korean dyslipidemia guideline as the
  most peripheral item — country-specific and the oldest (2017) in the batch.
- Store 1331 → **1361**; guidelines 74 → **104**. Guideline coverage now spans **2018 onward**
  in the monitored journals, on top of the 2024–2026 cross-journal sweep coverage.
- **Found:** the classifier's Gender Medicine pre-check mis-caught the GnRH-analog consensus
  (PMID 31319416, about precocious puberty) and filed it as Gender Medicine instead of
  Puberty — likely triggered by "GnRH analog" phrasing shared with gender-affirming-care
  literature. Article inclusion/content is correct; only the topic label is off. Logged as a
  known limitation rather than fixed immediately (single occurrence, not blocking).
- Not yet run: the wide all-journals sweep for 2018–2023 (139 hits, ~35% precision, ~45–50
  likely keepers) — priced but deferred pending interest.

### [2026-08-04] finished the wide sweep + priced the pre-2024 backfill

- **Found and closed a coverage hole of my own making.** The wide 2024–2026 all-journals
  guideline search had returned 63 hits, but the audit only pulled metadata for about half
  before moving on — 30 PMIDs had never been examined, stored, or ruled on. Fetched and
  reviewed the remainder (29; PMID 40029956 no longer resolves on PubMed).
- **Agent review: 12 accept / 6 borderline / 11 reject** — a richer batch than the first,
  because the original half had been picked arbitrarily rather than by relevance. Christian
  approved 14 (all 12 accepts plus the SIAMS/SIEDP andrology guideline and ESHRE testicular
  tissue cryopreservation), with **no overrides in either direction** — full agreement with
  the agent's accepts and rejects.
- Notable additions: congenital hypopituitarism, the French SFEDP consensus on endocrine
  management of transgender adolescents, CMAJ pediatric obesity CPG, Polish pediatric thyroid
  carcinoma, French preclinical stage 1–2 T1D screening, German pediatric diabetes, China 2025
  pediatric T2D, two Argentine guidelines, and an endocrine-screening framework for pediatric
  thalassemia — correctly accepted from a *hematology* journal because endocrine surveillance
  is the subject, in contrast to the hemophilia guideline the agent rejected earlier.
- Store 1317 → **1331**; guidelines 60 → **74**; Gender Medicine now 7 articles.
  49 decisions on record (25 approved / 24 rejected).
- **Priced a pre-2024 guideline backfill** (2018–2023, publication-type scoped): 32 hits in
  the 5 dedicated peds-endo journals (where the ISPAD 2018 and 2022 consensus series live),
  91 across all 19 monitored journals (the extra ~59 skew adult — that search has no peds
  filter), 139 for the wide all-journals query at ~35% precision. Recommended starting with
  the 32. Not yet run.

### [2026-08-04] agent-reviewed approvals (late evening, follow-on)

Christian asked for the sweep candidates to be triaged automatically for peds-endo relevance
and presented as a page with checkboxes he could submit.

- **Why an agent and not rules** (confirmed by reading `classifier.py`): `classify_topic` ends
  at line 348 with an unconditional `return "General Endocrinology", None`, so an off-topic
  guideline is never rejected — only mislabelled, which is exactly why hemophilia read
  "Obesity/Metabolic" and atopic dermatitis read "Calcium/Parathyroid". Pediatric scoping
  lives only in the PubMed query (`peds_terms` in `journals.json`), which a wide sweep
  bypasses. `is_excluded_v2` is a ~35-phrase blacklist, not a specialty filter. And MeSH —
  curated, reliable — is fetched and stored but **completely unused** in classification.
- **Built:** `guideline_sweep.py` gains decision-memory skipping; new `build_review_page.py`
  (self-contained checkbox page, agent reasoning per card, MeSH evidence line, three tiers,
  Submit → Blob download) and `apply_approvals.py` (records every decision, emits the approved
  raw file, prints the merge commands rather than running them).
- **First real run:** a Sonnet subagent judged all 20 candidates — 8 accept, 3 borderline,
  9 reject — and placed every obvious reject correctly (hemophilia A, atopic dermatitis,
  endometriosis, Axenfeld-Rieger, glomerulonephritis, home respiratory support, digital media,
  pediatric sports statement, all-ages I-131 parameter). Borderlines were the genuinely
  arguable ones: female athlete triad, EAU/ESPU urology transition (has a DSD chapter),
  Italian cardiovascular prevention.
- **Verified in Chrome**: pre-ticking, section-scoped select all/none, override on a collapsed
  reject, counter sync, and the real download landing in `~/Downloads/approved_pmids.json`
  with 8 approved / 12 rejected. Round-tripped through `apply_approvals.py` (idempotent on
  re-run), merged the 8, and confirmed a re-run of the sweep now reports 20 previously-decided
  and an empty queue.
- Store 1306 → **1314**; guidelines 49 → **57**. The 8 additions are the first articles ever
  admitted from unmonitored journals, each by explicit approval.
- **Christian then reviewed the page himself and approved 11 of 20** — the 8 recommended plus
  both DSD-adjacent borderlines (EAU/ESPU urology transition, Female Athlete Triad) and one
  override of an agent reject (the ACR I-131 thyroid practice parameter, which the agent had
  called all-ages radiology; the physician judged it relevant). Final: store **1317**,
  guidelines **60**. This is the override path working as designed — the agent triages, the
  clinician decides, and both borderline calls went the way the agent flagged as arguable.
- Two rough edges hit while applying his file, both fixed: `guideline_sweep.py` crashed on
  `--decisions /dev/null` (now tolerates an unreadable/empty decisions file, which is also the
  documented way to rebuild the full candidate list); and because a prior sweep run had left
  `guideline_candidates.json` empty, `apply_approvals.py` initially found no raw records —
  its "pmid not in candidates" warning caught it rather than silently writing nothing useful.

### [2026-08-04] guideline-coverage-audit (late evening)

Christian asked why the ISPAD guidelines were missing, whether ADA guidelines were present,
and how to guarantee no important peds-endo guideline is missed. The audit found **three
independent causes**, not one.

- **Cause 1 — date window (ISPAD).** The ISPAD Clinical Practice Consensus Guidelines 2024
  are published in *Horm Res Paediatr*, which **was already monitored**, in Dec 2024 – Jan
  2025. The store's coverage began ~Jan 2026 (pub years: 2024×21, 2025×91, 2026×1160) and
  held **zero** Horm Res Paediatr 2024–25 articles against 208 on PubMed. Nothing was wrong
  with the filter or classifier — those articles were never fetched.
- **Cause 2 — classifier title patterns (ADA).** The ADA Standards of Care peds chapter
  (PMID 41358890) *was* in the store but typed `Review`/`HIGH`. PubMed tags it only
  `Journal Article, Review`, and the title regex had no "standards of care" pattern. Also
  missing: "consensus report", and ISPAD's "Clinical Practice **Consensus** Guidelines 2024"
  (the intervening word breaks `\bclinical practice guidelines?\b`; the year breaks the
  preposition pattern). Fixed and verified 9 positives / 6 negatives; the rebuild changed
  **exactly one** article, the intended one.
- **Cause 3 — journal-scoped architecture.** Cross-checking confirmed the pipeline works:
  every guideline in a monitored journal within the window was captured (4/4 sampled). But a
  publication-type sweep across all journals found 22 peds-endo guidelines in 2026 alone,
  16 of them not in the store — all in unmonitored journals.

**Work done:** classifier fix (784fd53); 2024–25 guideline backfill across all 19 monitored
journals, +53 articles (3db0eae); `guideline_sweep.py` + review queue (341b08d). Guidelines
15 → 49; ISPAD 3 → 10, including all six 2024 CPCG chapters. Store 1273 → 1306.

**Mistake made and corrected:** the backfill assembled its raw file by globbing *every* saved
PubMed result, which swept in the exploratory wide-sweep searches — 20 guidelines from
unmonitored journals (hemophilia A, endometriosis, atopic dermatitis, Axenfeld-Rieger,
glomerulonephritis…) auto-merged into the store, the exact auto-add the design forbids. They
were reverted out of both the store and `comprehensive_raw.json` and rerouted to the review
queue. Lesson recorded in DECISIONS.md: assemble backfill raw files from *named* fetch
outputs, never a glob.

**Traps found:**
- The PubMed MCP nests the PMID at `identifiers.pmid`; a top-level `.get("pmid")` silently
  returns `None`. This produced a false "0 articles in store" reading mid-audit and is the
  same class of bug that once hit `map_raw()`. Always go through `map_raw()`.
- `classify()` returns **only** classification fields; the caller must merge them onto the
  article (`{**art, **res}`). The first review queue rendered topics with no titles.
- The MCP rejects a query with **more than 20 boolean operators** — a 19-journal OR-clause
  must be split.

**Token/model note:** Christian asked whether this work needed the top model. Conclusion
recorded in DECISIONS.md and the runbook — the fetch/merge loop is mechanical and belongs on
Sonnet or in a subagent; the stronger model earns its keep on diagnosis and classifier logic.

### [2026-08-04] https-resend-auth (evening session)

- **HTTPS finished on pedsendobrief.org.** The certificate was never provisioned because the
  GitHub Pages DNS check was stuck "in progress" despite DNS being verifiably correct. Fix:
  removed and re-added the custom domain in Settings → Pages (via browser). Cert issued within
  minutes (expires 2026-11-02, auto-renews); HTTPS enforcement enabled; http→https 301 and
  www→apex redirects verified. The remove/re-add made GitHub commit `Delete CNAME` +
  `Create CNAME` (53bf59c, cbd3cba) — pulled into local.
- **Google sign-in verified end-to-end on the new HTTPS domain** by Christian.
- **Resend set up for transactional email.** Account created by Christian (molonych@gmail.com,
  free tier 100/day); domain `pedsendobrief.org` added (us-east-1) with manual DNS: DKIM TXT
  `resend._domainkey`, MX + SPF TXT on `send`, DMARC TXT `_dmarc` (`v=DMARC1; p=none;`).
  Records added at Cloudflare (all DNS-only), verified live with dig, domain **Verified** in
  Resend ~18 min after creation. "Enable Receiving" skipped.
- **Supabase custom SMTP configured** (Christian pasted the API key): `smtp.resend.com:465`,
  user `resend`, sender `no-reply@pedsendobrief.org` / "PedsEndoBrief". Saving custom SMTP
  auto-raised the email rate limit 2→30/hour and unlocked template editing (templates are not
  editable before custom SMTP exists).
- **Both email templates rewritten to six-digit `{{ .Token }}` codes** (reset password +
  confirm signup), replacing the default `{{ .ConfirmationURL }}` links.
- **OTP length trap found and fixed:** first two test emails carried 8-digit codes — this
  project's "Email OTP length" was 8, not the documented default 6. Set to 6 in Sign In /
  Providers → Email. Second trap: setting the field by scripted value assignment appeared to
  save but silently reverted (React state); real keystrokes committed it. Third test email
  delivered a 6-digit code in seconds.
- **Password reset + signup confirmation UI shipped** (eb8ec91): "Forgot password?" →
  email → code → new password via `resetPasswordForEmail` → `verifyOtp(type:'recovery')` →
  `updateUser`, with a consumed-OTP guard so a spent code isn't re-verified if `updateUser`
  fails; signup confirmation mirrors it with `verifyOtp(type:'signup')` + `resend()`. Built in
  `HTML_TEMPLATE`, caught a name collision locally (`rstatus` already used by the bug-report
  form → renamed `pwstatus`; whole inline script now node --check'd), tested all view states
  locally, deployed, and **verified end-to-end by Christian on the live site**.
- **Email confirmation switched ON** (Sign In / Providers → Confirm email), closing the
  pre-account-takeover hole (see DECISIONS.md).
- **ISPAD gap diagnosed:** the ISPAD 2024 Clinical Practice Consensus Guidelines (~25 chapters,
  Horm Res Paediatr, late 2024) predate the dataset's coverage — the store has zero Horm Res
  Paediatr 2024–2025 articles (by pub year: 2024×21, 2025×91, 2026×1160). Targeted backfill
  added to TASKS.md.
- Docs updated (82e2af5); HANDOFF.md restructure into _log.md/DECISIONS.md agreed.

### [2026-08-04] rename-domain-google-perf (afternoon sessions)

- **Rebranded to PedsEndoBrief** on https://pedsendobrief.org (0caf02e, a914e2b; domain via
  Cloudflare Registrar ~$10/yr, auto-renew). Only user-facing strings renamed; internal
  filenames and the repo name deliberately unchanged. DNS: four apex A records to GitHub Pages
  + `www` CNAME, all DNS-only. Old github.io URL 301-redirects. Supabase redirect URLs and the
  Google OAuth origin were added additively, keeping the old URL valid through the transition.
- **Google sign-in shipped** (28cf37d, 2424f42, 5594fb7): Google Cloud project
  `indigo-cider-471318-p8`, OAuth client "PedEndoLit web (Supabase)", scopes exactly
  `openid email profile` (no verification review), published to production. Client secret
  lives only in the Supabase dashboard. `GOOGLE_ENABLED` flag gates the button. Old fake
  `molonychtest@gmail.com` account deleted first — with confirmation off it was "confirmed"
  without ownership proof and could have auto-linked to whoever owns that address.
- **Rendering performance** (b20ef6b, b94e2bb), measured with `performance.now()` on the live
  page: DOM nodes 36,133→14,091; cards built 1,274→512; abstract bodies in DOM 1,130→0 until
  opened; initial render 748→164 ms; filter interaction ~750→200 ms. `fillGroup()` builds a
  collapsed tier on first open; `absText()` inserts abstract text on demand.
- **Deploy gotcha recorded:** GitHub Pages' CDN caches by path and ignores query strings — a
  `?v=N` cache-buster does NOT fetch a fresh copy and made a working deploy look broken.
  Verify with a hard reload or `curl -H 'Cache-Control: no-cache'`.

### [2026-08-04] phase3b-features

- **Phase 3B shipped** (98bafc7, 7507410): `user_prefs` table (`last_seen_at` +
  `prev_seen_at`, so opening the page doesn't erase the "new since your last visit" marker),
  private notes on saves (debounced `update`, not the optimistic-insert/swallow-23505
  pattern used for saves — that pattern is wrong for free text), guidelines
  filter (two lines — the `.chip[data-flag]` handler binds any chip), and citation export
  (per-article copy, bulk copy, RIS download) as pure client-side string building.
- **Two long-standing bugs fixed:** open abstracts collapsed on every re-render (no backing
  state — added `openAbstracts` mirroring `openCards`); search re-rendered ~1,300 articles on
  every keystroke (added debounce).
- **Verified:** RLS isolation on `user_prefs` (owner 1 row / other user 0 / anon denied), note
  round-trip, guidelines filter (15 of 1,273), citation copy.
- Noted: Supabase leaked-password protection is Pro-only (advisor flags it; the free-tier
  toggle silently refuses to save). Password-reset limitation documented: the built-in
  sender refuses non-team addresses entirely ("Email address not authorized") on top of
  2/hour — and the owner's own address IS on the team, so self-testing passes while every
  colleague fails. This is why reset waited for custom SMTP.

### [2026-08-04] data-recovery-archive-fix

- **Defused the archive time bomb** (286366d): `ARCHIVE_AFTER_DAYS = None`. The 60-day rule
  keyed on `review_date` (date *added*); the historical backfill shares one date, so the site
  would have dropped 1,287→258 articles on 2026-08-30 and →35 by late September.
- **Recovered the data foundation** (f58cd82, a4e33e1, 9bbf888, 6ab0009): 74% of the store had
  no abstract and had been classified on title alone — the prior `comprehensive_raw.json` held
  1,053 records but only 93 abstracts while `_tmp_batches/` still had full text. Wrote
  `merge_raw_sources.py` (richest-value-wins merge, seeds from the store because 45 published
  articles exist in no raw file). Fixed `map_raw()` (dropped citation block, `identifiers.pmc`,
  truncated authors at 6). Fixed guideline detection (guidelines now tested before
  systematic-review, using `pub_types` + full title, with an about-guidelines guard).
  Re-fetched 427 abstracts from PubMed via MCP in batches of 20.
- **Cumulative result:** abstracts 336→1,214; clinical bottom lines 336→1,214; "Other" study
  type 853→400; guidelines 4→15; fully citable 308→1,266; board-relevant 69→186;
  volume/issue/pages 0→910; PMC ids 0→595. Store 1,287→1,273 (14 correct removals). Only 59
  articles still lack an abstract — all letters/editorials with none indexed.

### [2026-08-04] phase2-accounts-live

- **Phase 2 activated** (31ad9ce, 2a8a63b, 24131de): Supabase project `oiafndmmdplvitrttene`
  (ca-central-1, free tier), `saved_articles` table from `supabase_setup.sql`, publishable
  key, anon role grants explicitly revoked. Sign-in modal, per-card Save buttons, "My Saved
  Articles" tab.
- **This folder became the git repo / publish channel** (f87e612, 030336e): GitHub Pages
  first enabled on the repo — before this the handoff docs assumed a live site that had never
  actually been switched on.

### [2026-07-24] apem-and-legacy-backfill

- **APEM added as the 19th monitored journal** after confirming it active and PubMed-indexed;
  IJPE ruled out as dormant. Backfilled Jan 2026–present: 30 candidate PMIDs, 29 added,
  1 excluded (erratum). Runbook updated to 19 journals.
- Legacy metadata backfill for old records worked via `backfill_legacy_metadata.py`, then
  paused (`PedEndoLit Legacy Metadata Backfill Handoff.md`) — later superseded by the
  2026-08-04 data recovery.

### [2026-05-29 → -30] initial-build

- Ported the Perplexity classifier spec (v2.4.2 + Diabetes Framework) to `classifier.py`;
  pilot run caught two bugs (incidental "IGF"/"MEN1" mentions hijacking topic — fixed with
  subject-vs-mention guards; systematic reviews getting the generic "Authoritative review"
  rationale — now have their own) — both fixed.
- Added Gender Medicine topic and the Calcium/Parathyroid split; Turner/PWS placed under
  Growth.
- Built the three-stage pipeline and the self-contained dashboard; impact tier accordion +
  Analytics tab layout settled.
- **2026-05-30: month bucketing reversed** from entry-date to publication-date (0 mismatches
  verified) — see DECISIONS.md.
