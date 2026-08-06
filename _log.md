# PedsEndoBrief — Project Log

Reverse-chronological record of what happened and when. Rationale for standing choices lives
in `DECISIONS.md`; current-state facts live in `MEMORY.md`. Backfilled 2026-08-04 from the
git history (33 commits to that date) and the dated sections formerly in `MEMORY.md`.

---

### [2026-08-05] regression check, and NCBI is reachable after all

Started a website-redesign conversation; it turned up two things worth more than the
redesign, so those landed first.

**`CLAUDE.md` was wrong about NCBI.** It said E-utilities was "not reachable directly from
the shell," which is the entire reason every fetch is an agent-mediated MCP step. Tested it:
`esearch` and `efetch` both answer from the sandbox over plain HTTPS, HTTP 200 in ~0.2s,
full metadata including abstracts, pub_types and MeSH. Since `efetch` takes 200 PMIDs per
request, a job the MCP path makes prohibitive — a full 2015-onward backfill, ~20k articles —
is about 100 requests, i.e. minutes as a plain script rather than many agent sessions. The
claim is corrected in `CLAUDE.md`; nothing has been migrated yet.

**Built `check_classifier_regressions.py`** — the deterministic, zero-LLM layer of
classifier QA, and the thing that would have caught today's earlier near-miss
automatically (a thalassemia guard that looked right but quietly moved an
already-correct Puberty article). It diffs topics between the last published store
(`git HEAD`) and the working tree; a change is legitimate only if the ledger holds a
`target_topic` matching the new topic. Exits 1 on unexplained topic changes and on any
article that *disappeared* (a classifier edit can make exclusion rules newly fire and
silently drop content). `study_type`/`impact` drift is reported but never fails, since
no ledger records intent for those and failing would cry wolf on every real improvement.
`--bless PMID "reason"` records a correct-but-unpredicted change into the same ledger,
because hand-editing JSON was exactly the friction that would make a future session
ignore a red exit code.

Verified against real scenarios rather than only the happy path: passes on the current
state, correctly recognises all 9 of today's topic moves as predicted when run against
the pre-fix commit, and — with a deliberately mutated store — fails on an unexplained
topic change, fails on a removed article, treats a `study_type` flip as informational,
and passes the topic case after `--bless`. Store and ledger restored afterward; the
test used a throwaway ledger copy so the real one was never touched.

**Also fixed the Analytics impact chart.** It was sorted by count, rendering an ordinal
scale as LOW → MODERATE → PRACTICE-ALTERING → HIGH, which reads as a ranking and isn't
one. `distBar` gained a `keepOrder` flag; impact now renders PRACTICE-ALTERING → HIGH →
MODERATE → LOW, and topic/journal still count-sort (correct, they're nominal). Confirmed
in a browser, not just in the source.

Agreed roadmap for the redesign, decomposed because it was six things pretending to be
one: (A) async data-loading boundary, (B) UI redesign, (C) catch-up mode "what's new in
topic X since date Y", (D) backfill to 2015, (E) unattended scheduling, (F) automated
classification QA. Decided to plan for an eventual 20,000 articles now — the binding
constraint is not storage (~65MB, trivial) but the single-file embed model, which would
make `index.html` ~62MB and breaks GitHub Pages' 100MB file cap near 30k articles. Git
history is a second real constraint and already visible: `.git` is 53MB after 8 commits
because the store is rewritten wholesale each week. Likely answer is a recent window
embedded plus deep archive queried from Supabase, which also maps onto C exactly. This
entry's work is F's layer 1; B and C are next, then D.

`gh auth refresh -s workflow` completed (needs `--hostname github.com` and a real TTY,
not the `!` prefix), so the scope is now in place for E later.

### [2026-08-05] classifier QA sweep — built the pipeline, closed round 1

Christian noticed filtering the live dashboard to Guidelines + Diabetes surfaced guidelines
that weren't actually about diabetes. `classify_topic()` has no rejection path (always
returns some topic, ends in an unconditional `General Endocrinology` fallback), so this is a
structural, ongoing risk, not a one-off bug — built a repeatable QA tool rather than a
one-shot patch, mirroring the guideline sweep's shape but for topic *correctness* instead of
coverage.

- **New pipeline**: `classifier_qa_sample.py` (stratified sampler, re-eligibility ledger
  instead of a flat skip-list — a PMID becomes eligible again once its store topic actually
  changes) → a Sonnet judge subagent (tri-state correct/defensible/wrong, not boolean, so a
  genuine taxonomy-boundary call isn't forced into "error") → `build_classifier_qa_review.py`
  (topic dropdown per card, not a checkbox) → `apply_classifier_qa.py` (ledger + a
  root-cause report grouped by current→target topic with a title/abstract trigger-location
  signal, via a new `classify_topic(art, trace=True)` — traced against the real waterfall,
  not a parallel reimplementation). Full procedure: `CLASSIFIER_QA_RUNBOOK.md`.
- **Round 1**: sampled all 64 articles tagged Diabetes + Guideline/Consensus. The judge
  flagged 6 wrong — the 5 suspected (Turner syndrome, Vitamin D, thalassemia, 2×
  Hyperinsulinism) plus a 6th it found independently (an EASL-EASD-EASO MASLD guideline).
  Root-caused into two `classifier.py` fixes:
  - **Hyperinsulinism substring/ordering bug**: bare `"insulin"` is a literal substring of
    `"hyperinsulinism"`, and a hyperinsulinism guideline's abstract almost always also says
    `"hypoglycemia"` — both are Diabetes-General (branch 10) triggers that fired before the
    Hyperinsulinism catch (branch 11) ever got a chance, because the earlier Hyperinsulinism
    pre-check (branch 8) only recognized phrase forms like "congenital hyperinsulinism," not
    the bare word. Fixed by adding bare `"hyperinsulinism"` to branch 8.
  - **Incidental multi-system mention**: Turner syndrome, thalassemia (and, transitively,
    Prader-Willi) guidelines discuss diabetes/glucose screening as one comorbidity among
    several; branch 10 had no "is this the subject" guard. Added a new pre-check (8b) before
    Diabetes for `"turner syndrome"`/`"prader-willi"` (→ Growth, the taxonomy's existing
    convention) and for `"thalassemia"` gated on an explicit broad-scope phrase (→ General
    Endocrinology) — the broad-scope gate was added after a bare `"thalassemia"` check
    over-fired on a single-organ ovarian-insufficiency article that was already correctly
    `Puberty`.
  - **2 residuals explicitly NOT fixed**: the Vitamin D and MASLD guidelines. Tested both a
    bare-keyword pre-check and a title-only guard for each — every version misrouted more
    genuinely-diabetes articles than it fixed (e.g. "High-dose vitamin D therapy and ...
    remission of type 1 diabetes"; "MASLD as Complication of Diabetes," which arguably
    belongs in Diabetes by its own framing). Recorded as accepted residuals
    (`residual_accepted: true` in `classifier_qa_decisions.json`, which the sampler now
    respects instead of force-including them every round).
  - **Verified via a full-store topic-diff** (snapshot before/after `--rebuild`): 7 total
    moves, all reviewed and confirmed correct — the 4 target fixes plus 2 beneficial side
    effects the sample never targeted (a Prader-Willi/diazoxide-choline article previously
    miscaught as Hyperinsulinism; a Turner-population glycemia study moved to Growth,
    consistent with the taxonomy convention) and one further genuinely multi-system
    thalassemia screening-framework article. `merge_raw_sources.py` also picked up its usual
    unrelated housekeeping (comprehensive_raw.json refresh); total store count unchanged at
    1406.
- **Not yet done**: the Gender Medicine/GnRH-analog item (PMID 31319416) and the DSD
  17β-HSD3 keyword gap weren't part of this sample — left for a round 2, per
  `CLASSIFIER_QA_RUNBOOK.md`.

**Follow-up after advisor review, same session**: caught a real bug before anything got
committed — `apply_classifier_qa.py` was writing a fresh dict per PMID instead of merging,
which would have silently dropped `residual_accepted`/`residual_reason` the next time either
residual got re-decided, putting it back into force-included `pending_fix` forever. Fixed to
merge; verified with a simulated round-2 re-decision that the flag survives. Also added the
missing documented path to actually set a residual (`apply_classifier_qa.py
--accept-residual PMID "reason"` — previously only settable by hand-editing the ledger, with
no CLI and no runbook mention of the field names) and fixed 3 hand-added regression-check
ledger entries that had put their reasoning in the `title` field (which the pending-list
printer reads as the article's actual title) rather than a dedicated field. Rebuilt the whole
ledger cleanly through the real tool afterward rather than patching the ad-hoc edits further.

Also asked Christian directly rather than deciding unilaterally: the Vitamin D and MASLD
guidelines were originally left as accepted residuals (rule-based fix rejected for collateral
damage) still showing under the Diabetes filter — his actual complaint, not fully resolved.
He chose a third option, a per-PMID topic override: `apply_classifier_qa.py
--accept-residual` now doubles as the trigger for a new `apply_topic_overrides()` in
`build_dataset.py`, which corrects just that one article (recomputing tags/subtype/rationale
via the real classifier functions) on every build. Verified in `index.html` — the actual
published artifact, not just the datastore, per the advisor's flag that the datastore check
alone wasn't sufficient. Final state: **9 total topic changes vs. the pre-session git
baseline** (7 from the classifier.py fix, 2 from the override), zero collateral, abstract/DOI
counts unchanged (1406 articles, 1347 abstracts).
- Not yet committed/pushed — pending Christian's review of the diff.

### [2026-08-04] wide all-journals pre-2024 sweep (2018–2023)

Ran the remaining priced-out option: the wide publication-type search, 2018–2023, across all
journals (139 hits; 29 already handled by earlier rounds; 109 fetched, 5 classifier-excluded,
104 for review — the largest single batch of the project).

- **Split across two parallel Sonnet subagents** (52 candidates each) to keep each context
  manageable; verdicts merged and validated (104/104, no gaps) before building the page.
- **41 accept / 21 borderline / 42 reject** — close to the ~35% precision estimate. Notable
  accepts: the 2023 international PCOS evidence-based guideline, AAP's 2023 pediatric obesity
  CPG, ETA congenital hypothyroidism and pediatric Graves' guidelines, a 5-part Mexican
  precocious-puberty guideline series, ADA Standards of Care ch.13, BSPED pediatric DKA, a
  French pediatric bone fragility guideline, USPSTF youth prediabetes/T2D screening, an
  international SGA consensus, and India's transgender youth care statement.
- **Christian approved 45**, including 7 deliberate overrides of `borderline` verdicts he
  judged in-scope (global vitamin D dosing, PWS management in adults/transition, pediatric
  parenteral-nutrition calcium/phosphorus, APA's pediatric-obesity behavioral-treatment
  guideline, post-HCT bone health, hospital CGM/automated-insulin-dosing consensus, Klinefelter
  syndrome). He declined 3 of the agent's `accept` calls: a duplicate ACOG summary (having
  already kept the full opinion), the Korean dyslipidemia guideline (consistent with his
  earlier call on a companion PMID), and one Russian congenital hypothyroidism guideline.
- Store 1361 → **1406**; guidelines 104 → **149**. Guideline-decision ledger now holds
  **184 rulings** (100 approved / 84 rejected) across five sweep rounds.
- **This closes every guideline-hunting angle identified this session**: journal-scoped
  weekly refresh, the 2024–25 backfill, the 2024–2026 wide sweep (both halves), the pre-2024
  dedicated-journal backfill, and the pre-2024 wide sweep. Ongoing coverage is now just the
  monthly sweep keeping pace with new publications.

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
