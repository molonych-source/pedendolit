# PedsEndoBrief — Project Log

Reverse-chronological record of what happened and when. Rationale for standing choices lives
in `DECISIONS.md`; current-state facts live in `MEMORY.md`. Backfilled 2026-08-04 from the
git history (33 commits to that date) and the dated sections formerly in `MEMORY.md`.

---

### [2026-08-07] Source-text recovery tested and mostly disproved; doc-class spec approved

Started from Christian's hypothesis that weak bottom lines came from non-English sources.
**They do not.** Non-English articles are 9 of 1,406 (0.6%), only 2 are flagged, and off-list
journals from the guideline sweep are *cleaner* than the 19 monitored ones (15.3% vs 18.7%
flagged). The real driver is missing abstract text concentrated in the highest-profile
journals: Pediatr Diabetes 62% flagged, Lancet D&E 58%, Nat Rev Endocrinol 55%.

**Then tested whether the missing text is recoverable. Mostly it is not.** Findings and every
verification are in `SOURCE_TEXT_RECOVERY_FINDINGS.md`.

- Europe PMC **0/178**, Crossref **0/178** — both verified working against positive controls,
  so the zeros are real. These articles have no abstract deposited anywhere.
- PubMed re-fetch recovers 2 (both Chinese guidelines).
- **PMC full text is the only working path: 15/15 verified** >200 words of real JATS body.
- **A mid-session claim that Firecrawl retrieves the Wiley/ISPAD full text was WRONG and is
  corrected in the findings doc.** Wiley redirects every PDF URL to the abstract landing page;
  the 222k characters were navigation chrome (`Recommendation` 0 occurrences). Firecrawl's
  `summary` format then produced a fluent, plausible ISPAD summary *from that empty page* —
  precisely the fabrication mode this work exists to remove. **Never feed Firecrawl `summary`
  into a bottom line.**
- Green-OA repository copies are 1.6 KB metadata stubs.
- Christian's Zotero (1,507 PDFs) matches **2 of the 109** — because his library holds ISPAD
  **2022** and the store holds **2018**.
- Springer previews genuinely work via Firecrawl, but cover Nat Rev research highlights that
  should be demoted rather than retrieved. Elsevier asserts `tdm-reservation: 1` — do not
  scrape it.

**LIVE DEFECT FOUND: PMID `39834161` is a retracted paper on the site right now** — *Effects of
Maternal Vitamin D Supplementation on Childhood Health* (Endocr Rev), rated HIGH impact, with a
confident bottom line and no retraction marker. Present in the deployed `index.html`.
Also PMID `28627221` renders the literal string `[Abstract not available]` as its takeaway.

**ISPAD reframe:** the store holds 23 ISPAD **2018** chapters (all no-source) against only 4
from 2024. That edition is two generations superseded, so recovering its text would mean
writing confident takeaways for stale guidance. The real defect is a **coverage gap** — ISPAD
2022 is absent entirely — and it belongs to the guideline sweep.

**Design brainstormed and approved: `DOC_CLASS_SPEC.md`.** The cascade collapsed to a PMC fetch,
so the spec covers what is certain instead: `doc_class` / `source_text_state` / `retracted`
fields, two disjoint filter toggles that always show their counts (69 commentary, 109
research-with-no-source), a RETRACTED banner, and the 15-article PMC fetch. Load-bearing rule:
a `Letter` that does not announce itself as a reply stays `Research`, which keeps the Lancet
stem-cell islet therapy report in the main queue.

Commits on `bottom-lines`: `eecf940`, `1857134` (the correction), `b51b404` (spec).
Nothing written to the store or `index.html`. Implementation plan not yet written.

### [2026-08-06] UI redesign direction chosen; design spec written

Christian reviewed the three prototypes and picked **topic catch-up as primary, triage queue
as secondary**. Design worked through and agreed; written up as `REDESIGN_SPEC.md`. Not built.

Composition is **"grid is the door, queue is the room"** — there is one path in, and the
reader always arrives through a topic. Landing is a 16-topic grid (count new since last
visit + a one-line preview of the top article per tile) plus the catch-up sentence
("what's new in X since Y") and a coverage notice that **adapts to what was asked**, so
"since March 2025" says what it cannot see before showing three papers as if they were the
whole story. Clicking a topic opens the queue scoped to it, ranked impact-then-date, with
the **bottom line as the headline** and the title demoted beneath it — inverting today's
card, where the most valuable field is hidden behind a click.

Everything currently live survives: accounts, saved articles, notes, global search, impact
tiers, Analytics. Search / Saved / Analytics become header *destinations* rather than modes.
A search box does not undercut a grid-first landing; a browse-everything view would, so
there isn't one. Item **A** (async data boundary) is built at the same time — invisible, but
it makes the eventual move off the single-file embed plumbing instead of a rewrite.

**Blocking dependency Christian decided on: generate real bottom lines**, rather than
falling back to the title. 182 of 1,347 are extractive. Two conditions recorded: audit the
other 1,165 first, since the 182 were found by pattern-matching and the true number is
probably higher; and Christian spot-checks a sample before it ships, because these become
the most prominent clinical text on the page.

Risk carried into the spec: a topic-first UI **inherits the 11.5% topic error rate**, and
unevenly — `Genetics` 36.8%, `General Endocrinology` 34.5% against 0% for `Growth` and
`Hyperinsulinism`. This design makes misclassification more visible than the current page
does, so classifier QA runs alongside the rebuild rather than after it.

Also regenerated the three prototypes against current data — they had been built before the
Bone/Mineral merge and the pub_date repair, so they were showing retired topic names and
pre-repair dates. The brief now leads with genuinely recent work (the Endocrine Society CPP
guideline, a navepegritide/lonapegsomatropin trial) instead of a 2017 vitamin D guideline,
which is the date repair doing its job.

---

### [2026-08-06] the review panel was built, measured, and failed its gate

Ran the validation from `REVIEW_PANEL_SPEC.md`: 15 Sonnet agents (3 lenses × 5 batches),
1,254 verdicts, replayed over round 2's 418 articles where Christian's decisions are ground
truth. **It failed. Auto-apply is not enabled and should not be.** Full numbers in the
spec's RESULTS section.

| Metric | Gate | Measured |
|---|---|---|
| Escalation volume | lower is better | 27 of 418 (6.5%) |
| Auto-apply precision | ≥ 98% | **94.1%** |
| Silent failures on his 8 overrides | 0 | **3** |

**Why, and it is the whole finding: the lenses are not independent.** They agree with each
other 95–96% of the time while each is only ~91% accurate against Christian. They are far
more similar to one another than they are correct, so their agreement carries almost no
information — they converge confidently on the same mistakes. Different framings of the
same model do not make independent judges. No escalation rule rescued it: the strictest
tested (escalate anything not unanimously high-confidence) still leaked one silent failure
*and* sent 174 cards, more than the 131 that actually mattered in round 2.

Two confounds recorded for anyone retrying: **blinding made it worse, not more
independent** (the round-2 judge saw the existing label and scored 98.1% on an easier,
anchored task), and **a prompt bias explains most of the error** — 14 of 23 auto-apply
errors are cases where Christian chose `General Endocrinology` and the panel committed to
something specific, after the taxonomy text warned them off the catch-all.

What survives: the panel is a good **sorter**, not a decider — a 6.5% split rate is a
high-value queue and three opinions on a card beat one. And the persistent-split signal
works: the boundaries that split are exactly the contested ones (`General Endocrinology vs
PCOS`, `DSD vs Puberty`, `Adrenal vs Growth`), which is the same diagnostic that pointed at
the Bone/Mineral merge. Harness kept at `scratchpad/panel/score_panel.py`; the ground truth
does not expire.

Cost: ~2.1M subagent tokens for a definitive negative result — cheap against shipping a
system that silently mislabels 6% of the corpus while appearing to work.

**Also today: `fix_pub_dates.py` written, dry-run only, NOT applied** (awaiting Christian's
call). Root cause of the date bug is upstream: the raw feed supplies one merged
`publication_date` dict, so when the journal issue has only year+month the day is taken
from the e-publication date and glued on. The fix prefers `ArticleDate` (when a reader
could first see the paper — the right semantics for a keep-up brief), falls back to the
issue date, and **never invents a day**: partial dates pin to the start of the period and
record `pub_date_precision` of `month` or `year` so the UI can render "March 2018" rather
than a false "1 March 2018". Dry run over 1,406: **496 dates change, 469 move month
bucket**, and they move earlier (72 of 80 sampled, mostly by two years). Resulting
precision: 1,335 day / 61 month / 10 year. Re-runnable with `--only-missing` for the ~35
new articles each week, which is what stops the bug returning through the raw feed.

### [2026-08-06] Bone/Mineral merge; review-panel spec written

**Bone/Calcium + Calcium/Parathyroid merged into `Bone/Mineral`** with four subdomains.
Rationale, evidence and rejected alternatives in `DECISIONS.md`; the 2026-05-29 split entry is
now marked Superseded. Taxonomy is **16 topics**.

Subtopics: **Skeletal Fragility 18 · Phosphate/FGF23 16 · PTH/Calcium 14 · Vitamin D/Rickets
6** (54 articles). `Bone/Mineral` is the second topic after Diabetes to use `subtopic`, and the
dashboard already renders that field generically, so no dashboard change was needed. Subtopic
is scored, not first-match — a term in the title counts 2, anywhere counts 1 — because XLH
mentions fractures and hypoparathyroidism is treated with calcitriol, so a waterfall would
misfile both.

Touched: `classifier.py` (branches 5a/5b → one pre-check, 22a/22b → one branch, new
`bone_mineral_subtopic()`, merged tag maps), `build_dataset.py` (`apply_topic_overrides` now
recomputes subtopic instead of blanking it — otherwise every overridden Bone/Mineral article
would lose its subdomain), `suspicion_score.py` and `build_classifier_qa_review.py` (topic
lists, MeSH map), the ledger (110 topic fields migrated old → new), and the taxonomy statements
in `CLAUDE.md`, `MEMORY.md`, `CLASSIFIER_QA_RUNBOOK.md`, `WEEKLY_REFRESH_RUNBOOK.md`.

**`check_classifier_regressions.py` gained a `TOPIC_RENAMES` map.** Without it the merge read
as 50 unexplained regressions, and worse, six articles with *still-pending* fixes inside the
merged topic looked like fresh breakage. A rename is not a reclassification; renames are now
reported informationally. Add a row there in the same commit as any future topic rename.

Final state: 50 renamed, 36 changed as predicted, **1 unexplained** (41513899, unchanged from
before the merge).

**Review-panel design spec written** (`REVIEW_PANEL_SPEC.md`, approved, not built). Three
agents but **not** a 2/3 majority — majority voting discards the split, and the split is the
signal worth having. Measured from round 2: Christian's concordance with the single judge was
**98.1%**, and he overrode **0 of 287** `correct` calls versus **6 of 37** `defensible` ones.
So the panel's job is detecting disagreement, not resolving it: three different clinical lenses
(primary clinical question / indexer / reader), unanimity auto-applies, any split escalates.
Spec includes a hard validation gate — replay over round 2's 418 labelled articles and require
100% recall on his 8 overrides before auto-apply is enabled — plus override retirement and a 5%
cap, since auto-applied decisions are data patches that mask classifier bugs if left to
accumulate.

### [2026-08-06] round 2 reviewed and applied; classifier patched; a 4th collision found

Christian reviewed all 418 cards, agreeing with the judge on 410 and overriding 8. Applied,
patched, rebuilt, regression-checked. **Not committed** — one item still needs his call, and
committing would destroy the `git HEAD` baseline the check compares against.

**Review outcome:** 292 correct, 126 topic changes. Worth noting for future rounds: **32 of
the 126 came from cards the judge marked `defensible`, not `wrong`** — the dropdown is pre-set
to the judge's alternative, so leaving a defensible card untouched *accepts* the change. He
reverted 6 explicitly, so he did work the group, but the affordance is a trap.

**Comment box added** (his request, same session). `build_classifier_qa_review.py` now renders
a per-card note field; `apply_classifier_qa.py` stores it on the ledger entry (merge-only, so
clearing the box never erases an earlier round's reasoning) and prints a "Reviewer notes"
section in `classifier_qa_report.md`. Tested end to end; the test note was removed from the
ledger afterwards. This exists precisely for the `defensible` case above, where a dropdown
cannot distinguish "arguable, leave it" from "yes, move it."

**Patch applied and verified.** Re-measured against Christian's actual decisions before
applying: 17 fixed, **0 regressions** — unchanged from the judge-scored run. Net effect vs. the
published site: **40 topic changes, 1406 articles in and 1406 out, none lost.**

**A fourth substring collision, found mid-flight.** The regression check's unexplained list
included a carotid-atherosclerosis study that had become Growth. Cause: bare `"ghd"` matches
inside **`tyGHDl`** (the triglyceride-glucose–HDL index). Same class as `tandem`. The fix is
*not* a plain word boundary — `ighd`/`iighd` (isolated GH deficiency) are legitimate and would
stop matching — so `ghd` is bounded on the right only: `ghd(?![a-z])`. Verified both ways.
An audit of every other bare abbreviation also caught `"pth "` matching inside `in-dePTH `
(latent — earlier branches happened to claim those two articles first); now word-bounded.

**A branch-13 guard was measured and rejected.** Extending the title-or-≥2× guard to
`growth hormone`/`igf-1` moved 7 more articles for 1 fix and 1 regression, and pushed a
stress-and-bone-health paper to Adrenal. Not applied.

**Open:** PMID 41513899 ("Endocrine regulation of the hepatic fasting response") is classified
Growth on a single abstract mention of "growth hormone". It is a hepatic fuel-metabolism
review; Growth is wrong. Deliberately **not blessed** — blessing would record it as correct and
stop the sampler re-examining it. The general fix is the rejected branch-13 guard above, so it
needs a human call: accept as a residual with a stated target, or leave failing. 19 other
unexplained movers were blessed individually with reasons; 3 partials were recorded as accepted
residuals so they land on Christian's chosen topics via `apply_topic_overrides()`.

### [2026-08-06] root-caused the Diabetes over-firing; found two more classifier bugs

Follow-on to the round 2 sweep below. Traced all 94 `wrong` verdicts back through
`classify_topic(trace=True)` to the branch and literal that produced each one. Result is a
measured patch, **`proposed_classifier_fix.patch`, written up in `CLASSIFIER_FIX_PROPOSAL.md`
and deliberately not applied** — `classifier.py` is untouched, per the standing "reviewed,
never auto-merged" decision and the runbook's order (review → apply → root-cause → rebuild).

Three distinct bugs, one patch:

1. **`tandem` matched tandem mass spectrometry.** Branch 9 matched the bare substring, meaning
   the Tandem Control-IQ pump. **10 articles were labeled Diabetes purely because their methods
   said "liquid chromatography–tandem mass spectrometry"** — newborn screening for 21OHD,
   maternal vitamin D profiling, thyroid hormones in autism. Checked `libre` and `aid system`
   for the same collision; both clean.
2. **No subject guard on generic terms** — round 1's bug class, unfixed in general form, and
   what 7 of 9 judges flagged. Branch 10 fired on `insulin` / `type 1` / `type 2` /
   `hypoglycemia` anywhere in the text; 26 of the 31 wrong-Diabetes articles were triggered by
   abstract-only mentions, 11 by `insulin` alone. Fixed by splitting each branch's keywords
   into strong (fire on one mention) and weak (need the title-or-≥2× guard branches 5c/6
   already use). Applied to branch 10 and branch 22a (Calcium/Parathyroid, same over-firing on
   `vitamin d` / `hypocalcemia`).
3. **The classifier only reads American spellings.** Every keyword is spelled American, so
   `hypercholesterolaemia` never matches `hypercholesterolemia`. Found because the ORION-16
   inclisiran trial in *familial hypercholesterolaemia* missed the Lipids pre-check entirely
   and fell 23 branches to Genetics on the word "genetic". **113 store articles carry a term
   the classifier cannot see** (57 `paediatric`, 29 `glycaemic`, 18 `hypoglycaemia`, 12
   `tumour`). Mostly latent today, but the monitored list includes *Lancet*, *Lancet Diabetes
   & Endocrinology* and *Archives of Disease in Childhood*, so the 2015 backfill would make it
   bite hard. Fixed with a 28-entry British→American fold before matching — a fixed list, not
   a morphological rule, since `our → or` would maul "four" and "flour".

Measured against all 1,406 articles and scored against the judges: **40 articles move, 17 land
exactly where the judge said, 0 regressions, 0 landing in the catch-all.** Resolves 18% of the
94 wrong verdicts. Fixing bug 3 alone caused one regression (a bisphosphonate guideline sliding
Bone/Calcium → Calcium/Parathyroid on a newly-visible "hypocalcaemia"); adding the 22a guard
removed it and fixed three more. Harness kept at `scratchpad/fixcand/measure.py` so the numbers
can be re-derived if the review changes verdicts.

### [2026-08-06] classifier QA round 2, suspicion scoring, a date audit, and redesign prep

Overnight unattended session. Christian asked for work that wouldn't need his input for a
while; everything below stops at the point where a human decision is required. **Nothing was
committed** (`check_classifier_regressions.py` needs `git HEAD` as its baseline) and nothing
was published.

**Classifier QA round 2 — 418 articles judged, awaiting review.** Sampled with `--seed 2026`,
stratified across all 17 topics, plus 150 forced PMIDs: the whole `General Endocrinology`
catch-all (84, exhaustive), 33 DSD enzyme/keyword candidates found by grep, 33 F2
suspicion-scored Diabetes articles, and the known GnRH item. Nine Sonnet judges ran in
parallel; verdicts were merged and validated **globally** rather than per-batch (a dead agent
would otherwise have produced a review page silently covering fewer articles than it claimed).
All assertions passed: 418 sampled, 418 judged, no drift, no dupes.

Verdicts: **287 correct, 37 defensible, 94 wrong.** The 22.5% raw rate is not the store's error
rate — the sample was deliberately enriched, and the stratified draw over-weights small topics
(Diabetes is 51% of the store but ~7% of the random slice). Corrected by computing a per-topic
rate and weighting by each topic's share of the 1,406 — using a **census** for the ten topics
sampled exhaustively and the random slice for the seven that were subsampled:

**Topic-weighted store estimate: 11.5% wrong, ≈161 of 1,406 articles.** Full store coverage.

Worst topics: `Genetics` 36.8%, `General Endocrinology` 34.5% (census, so this is exact),
`Calcium/Parathyroid` 25.0%, `Gender Medicine` 22.2%. Clean: `Growth`, `Hyperinsulinism`,
`Lipids` at 0%. Diabetes, at half the store, sits at 11.1% — but on n=18, so it's the loosest
number in the table and the one most worth tightening next round.

Seeding-strategy precision, each against the right baseline:

| Strategy | n | wrong | baseline | lift |
|---|---|---|---|---|
| F2 suspicion score (Diabetes) | 33 | **81.8%** | 11.1% random Diabetes (n=18) | **7.4×** |
| DSD keyword grep (non-DSD targets only) | 18 | **44.4%** | 11.5% store | 3.9× |
| General Endocrinology (census, not a strategy) | 84 | 34.5% | — | — |

The DSD grep returned 33 hits, but 15 were already correctly labeled DSD and were never
targets; it left 14 of those 15 alone, so 44.4% over the 18 real targets is its hit rate.

Dominant flows: `Diabetes → Obesity/Metabolic` (9), `General Endocrinology → Diabetes` (7),
`General Endocrinology → Obesity/Metabolic` (7), `General Endocrinology → Pituitary` (5).
Seven of nine judges independently flagged the same pattern: the Diabetes branch fires on
incidental insulin/hyperglycemia mentions. That is round 1's bug class, unfixed in general
form. The known GnRH consensus (31319416) was confirmed `wrong → Puberty`.
`classifier_qa_review.html` is built and ready; round 1's artifacts preserved as `*.round1.*`.

**F2 suspicion scoring built and measured** (`suspicion_score.py`, read-only). Scores every
article on signals `classify_topic(trace=True)` already exposes plus NLM MeSH disagreement.
Round 2 doubled as its first evaluation because the sample kept seeded and random portions
separable: **81.8% precision against the 11.1% random-Diabetes baseline, a 7.4× lift.** The
baseline rests on only 18 randomly-sampled Diabetes articles, so treat the multiplier as
approximate; the direction is not in doubt. It also behaves correctly on history — round 1's
seven code-fixed PMIDs now score low (~rank 600/1406) while the two that could only be patched
per-PMID still rank 65 and 113.

**`pub_date` is wrong for 24.5% of the store** (`audit_pub_dates.py`, new; full list in
`pub_date_audit.md`). Found while building the redesign mockups, verified against PubMed for
all 1,406 articles. 165 dates are **fabricated** — the journal issue supplies year-month only,
so the day is taken from `ArticleDate` and glued on, producing a date in neither source
(`2026-01-31` where PubMed has article date `2025-07-31`, issue `2026-01`). 110 aren't
sortable (`2018-Oct`, bare `2018`). 69 are issue-dated, showing 2024 papers as 2026. This
field is what catch-up mode (item C) filters on, so it plausibly outranks B in the roadmap.
For whoever fixes it: `ArticleDate` is missing for **289 of 1,406 (20.6%)**, and
`JournalIssue/PubDate` is present for all 1,406 but is **not a full date in 52.6%** of them.
So the fix needs a stated fallback order and a rule for partial dates, not just a choice
between two fields.

**Redesign prep** (`REDESIGN_BRIEF.md` + three prototypes in `mockups/`). Per the agreed
process, B starts with brainstorming, so these are inputs to react to, not a design: The
Brief (editorial issue), Triage queue (inbox), Topic catch-up (topic grid + coverage floor).
Building them surfaced two more constraints beyond the date bug: **June–July 2026 held 1
Practice-Altering and 11 High articles total**, so a weekly editorial brief has no weekly lead
story to run; and **14% of `clinical_bottom_line` values are extractive**, the abstract's
opening words rather than a takeaway, which matters because all three directions promote that
field to the headline slot.

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
