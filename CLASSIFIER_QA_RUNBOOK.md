# Classifier QA Sweep — Runbook

This is a companion to the monthly guideline sweep in `WEEKLY_REFRESH_RUNBOOK.md`, but
solves a different problem. The guideline sweep decides whether a PMID should be **added**
to the store. This sweep re-checks whether a PMID **already in the store** has the **right
topic** — the bug class that surfaced when filtering the live dashboard to
Guidelines + Diabetes and finding guidelines that weren't actually about diabetes (Turner
syndrome, Vitamin D, thalassemia, two Hyperinsulinism guidelines — see `_log.md`).

`classify_topic()` in `classifier.py` has no rejection path: it's a 25-branch waterfall
that always returns some topic, ending in an unconditional `General Endocrinology`
fallback. It can mislabel an article; it can never flag itself as uncertain. So
misclassification is a structural, ongoing risk, not a one-time bug — this sweep is a
repeatable tool, run whenever a topic-boundary problem is suspected or as periodic QA.

## Which model to run this on
Same rule as the guideline sweep's model note: this loop **changes how articles are
judged** (`classifier.py` edits, taxonomy boundary calls) — reserve the stronger model for
it, same as any other classifier/taxonomy change. The sampling script itself is mechanical
and fine on Sonnet; the judge subagent and the root-cause-to-code-fix step are not.

## Files
- `classifier_qa_sample.py` — stratified sampler over `pedendolit-data.json`. Filters by
  `--topic` / `--study-type`, exhaustive below `--exhaustive-below` (default 30) articles
  per topic, `--n-per-topic` (default 20) otherwise. Writes `classifier_qa_sample.json`.
- **Judge subagent** (Sonnet, not a script) — writes `classifier_qa_verdicts.json`. Prompt
  spec below.
- `build_classifier_qa_review.py` — self-contained review page (same shape as
  `build_review_page.py`). Writes `classifier_qa_review.html`.
- `apply_classifier_qa.py` — reads the downloaded decisions, updates
  `classifier_qa_decisions.json` (the ledger) and writes `classifier_qa_report.md` (the
  root-cause artifact, grouped by `current_topic → target_topic` with a title-vs-abstract
  trigger-location column). Never touches `classifier.py` and never runs the rebuild —
  prints the commands instead.

## Procedure

1. **Sample.** `--n-per-topic` must be at least the filtered pool's actual size to get it
   exhaustively — it does NOT auto-detect that for you, so check the pool size first
   (`--n-per-topic` too low silently subsamples instead of erroring). Round 1's exact
   command targeted the known-bad 64-article batch and used `--n-per-topic 64` for that
   reason — 64 is not a default, it's specific to that one batch's size:
   ```
   python3 classifier_qa_sample.py --topic Diabetes --study-type "Guideline/Consensus" --n-per-topic 200
   ```
   (`--n-per-topic 200` here is a safe "definitely bigger than any filtered pool" value,
   not the pool's real size — the sampler caps at whatever the pool actually contains.)
   For a broad taxonomy-wide sweep, omit both filters — it stratifies across all 16 topics
   automatically, exhaustive for the small ones, `--n-per-topic`-sampled for the rest.
2. **Judge — dispatch a Sonnet subagent** with the prompt spec below, pointed at
   `classifier_qa_sample.json`. It writes `classifier_qa_verdicts.json`.
3. **Build the review page.** `python3 build_classifier_qa_review.py` → open
   `classifier_qa_review.html` by double-click.
4. **Review.** Adjust the topic dropdown on any card as needed, Submit → downloads
   `classifier_qa_review.json` to `~/Downloads/`.
5. **Apply.** `python3 apply_classifier_qa.py` → updates the ledger, writes
   `classifier_qa_report.md`.
6. **Root-cause into a `classifier.py` fix**, using the report's
   `(current_topic → target_topic)` groups and the title/abstract trigger-location column
   to tell apart the two real bug classes seen so far:
   - **Substring collision / branch ordering** (e.g. bare `"insulin"` inside
     `"hyperinsulinism"` firing branch 10 before branch 11's Hyperinsulinism catch) — fix by
     word-boundarying the trigger or hoisting it earlier in the waterfall.
   - **Incidental comorbidity mention, abstract-only** (Turner/Vitamin D/thalassemia
     guidelines discussing diabetes/glucose screening as one comorbidity among several) —
     fix by adding the same "title, or ≥2 abstract mentions" subject-guard branches 5c/6
     already use, to whichever branch over-fired.
7. **Rebuild** (verbatim, per the REBUILD PITFALL below):
   ```
   python3 merge_raw_sources.py
   python3 build_dataset.py --run-date <YYYY-MM-DD> --raw comprehensive_raw.json --rebuild
   python3 build_dashboard.py
   ```
8. **Regression check** — one command, no snapshotting to remember:
   ```
   python3 check_classifier_regressions.py
   ```
   It compares the last published store (`git HEAD`) against the just-rebuilt working-tree
   store. Every article whose topic changed must match a ledger entry whose `target_topic`
   equals its new topic; anything else exits 1. It also fails if an article *disappeared*
   (a classifier change can make exclusion rules newly fire and silently drop content), and
   reports `study_type`/`impact` drift without failing on it.

   A change that's correct but that nobody predicted is blessed in place — this is expected
   after most classifier edits, since a good fix usually helps articles the sample never
   targeted:
   ```
   python3 check_classifier_regressions.py --bless <PMID> "<why it's right>"
   ```
   Run this **before** committing, while `git HEAD` still holds the pre-rebuild state. Once
   you commit, HEAD becomes the new state and the comparison is gone.
9. **Re-sample** for the next round: every regression from step 8 (`--force-pmid`), every
   unresolved `pending_fix` PMID (the sampler surfaces these automatically), plus a fresh
   broad sweep across all 16 topics to catch collateral damage a PMID-level diff can't see.
10. Repeat from step 2 until **done** (below).

> **REBUILD PITFALL** (same warning as the weekly runbook): `--rebuild` reads from the
> `--raw` file, NOT the existing store. Always run `merge_raw_sources.py` first, or pass
> `--raw comprehensive_raw.json` explicitly — otherwise the store shrinks to whatever is in
> `raw_articles.json` at that moment.

## Definition of done
- A full stratified sweep (exhaustive for every topic ≤30 articles, `--n-per-topic ≥ 20` for
  the rest) returns **zero `wrong` verdicts**, or every remaining `wrong`/`defensible`
  verdict has an explicit, dated, reasoned ledger entry accepting it as a residual (a
  genuine taxonomy-boundary judgment call, not a code bug).
- The most recent rebuild's topic-diff shows **zero unexpected movers**.
- No PMID remains `pending_fix` in the ledger, other than accepted residuals (below).

### Accepting a residual
Some `wrong` verdicts have no code fix without worse collateral damage than the bug itself
— e.g. round 1's Vitamin D and MASLD guidelines: every general keyword or title guard
tested misrouted more genuinely-correct articles than it fixed. Mark one as an accepted
residual with:
```
python3 apply_classifier_qa.py --accept-residual <PMID> "<reason — what was tried, what it broke>"
```
This only annotates a PMID that already has a ledger entry (reviewed at least once through
the normal sample → judge → review → apply flow). `apply_classifier_qa.py` MERGES this onto
the existing entry rather than replacing it — the flag must survive a later round
re-flagging the same PMID, or it silently goes back to force-included `pending_fix`.

This does two things, not just one: it stops the sampler from force-including the PMID
every round (`pending_fix`), AND `build_dataset.py`'s `apply_topic_overrides()` reads every
`residual_accepted` entry's `target_topic` and applies it directly to that one article at
build time — no general rule, so zero effect on any other article. It recomputes every
field that depends on topic (subtopic/diabetes_subtype, tags, impact_rationale) via the
real classifier functions, so a corrected article doesn't keep a stale primary tag. Runs on
every build (merge or `--rebuild`), so it survives a full reclassification.

## The judge subagent prompt (step 2)

Point it at `classifier_qa_sample.json` and require this output shape in
`classifier_qa_verdicts.json`:

```json
{"reviewed_by":"agent",
 "verdicts":{"<pmid>":{"verdict":"correct|defensible|wrong",
                       "current_topic":"Diabetes",
                       "target_topic":"Hyperinsulinism",
                       "confidence":"high|medium|low",
                       "reason":"one sentence for a clinician"}}}
```
- `target_topic` must equal `current_topic` when `verdict=="correct"`.
- `target_topic` must be one of the 17 canonical topic strings and `!= current_topic` when
  `verdict=="wrong"`.
- `target_topic` names the topic weighed against when `verdict=="defensible"` — a genuine
  taxonomy-boundary judgment call between two reasonable topics is NOT the same as an
  error, and the pipeline needs to tell those apart (only `wrong` drives a code fix).

The prompt must contain:

- **The 16-topic taxonomy with each topic's defining criteria** (not just names — what the
  topic is actually *about*, so the judge reasons about subject matter independently rather
  than re-running the classifier's own keyword logic):

  | Topic | Defining criteria |
  |---|---|
  | Diabetes | T1D/T2D/MODY/neonatal diabetes, DKA, glycemic control, insulin therapy & technology, diabetes screening — diabetes must be the *primary subject*, not a comorbidity mentioned in passing |
  | Growth | GH deficiency, short stature, SGA, GH therapy, skeletal dysplasia/achondroplasia. **Turner syndrome and Prader-Willi syndrome are a deliberate taxonomy convention here**, not an error, despite being multi-system |
  | Puberty | Precocious/delayed puberty, GnRH-agonist therapy for CPP, Tanner staging, menarche/thelarche/adrenarche, hypogonadotropic hypogonadism, Kallmann syndrome |
  | Thyroid | Hypo/hyperthyroidism, Graves, Hashimoto, congenital hypothyroidism, thyroid nodules/cancer, goiter |
  | Adrenal | CAH, adrenal insufficiency/Addison, Cushing syndrome, pheochromocytoma, primary aldosteronism, adrenal crisis |
  | Obesity/Metabolic | Pediatric obesity, metabolic syndrome, NAFLD/NASH/MASLD, GLP-1/anti-obesity pharmacotherapy, insulin resistance outside a diabetes context, bariatric surgery |
  | General Endocrinology | Genuinely multi-system endocrine syndromes (APECED/APS-1, MEN1/2) or content that doesn't fit one organ-system topic — the deliberate catch-all; correct when the article really is multi-axis, not itself an error |
  | Bone/Mineral | The whole calcium-phosphate-bone domain: PTH axis, hypo/hyperparathyroidism, hypo/hypercalcemia, vitamin D and rickets, XLH/FGF23/burosumab, bone density, osteoporosis, osteogenesis imperfecta, bisphosphonates. Merged 2026-08-06 from Bone/Calcium + Calcium/Parathyroid; carries a `subtopic` (Phosphate/FGF23, Skeletal Fragility, PTH/Calcium, Vitamin D/Rickets) |
  | Pituitary | Craniopharyngioma, pituitary adenoma/hypopituitarism, acromegaly, central DI, SIADH, septo-optic dysplasia |
  | Hyperinsulinism | Congenital hyperinsulinism, hyperinsulinemic hypoglycemia, nesidioblastosis, insulinoma, diazoxide/octreotide for persistent hypoglycemia. Distinct from Diabetes: this is insulin *excess* causing hypoglycemia, Diabetes is insulin deficiency/resistance causing hyperglycemia |
  | Genetics | Variant/exome/genetic-testing-focused articles not better captured by a specific endocrine topic |
  | DSD | Disorders/differences of sex development, ambiguous genitalia, 46,XY/XX DSD, gonadal dysgenesis |
  | PCOS | PCOS/PMOS, hyperandrogenism and oligomenorrhea in the adolescent, ovarian-driven |
  | Gender Medicine | Gender-affirming care, gender dysphoria, transgender youth care — distinct from Puberty (CPP treatment) and DSD (intersex conditions) even though vocabulary overlaps (puberty blockers, GnRH analogs) |
  | Cancer Late Effects | Endocrine sequelae of childhood cancer treatment (radiation, chemo, HSCT), survivorship-focused |
  | Lipids | Familial hypercholesterolemia, pediatric dyslipidemia, statin therapy in children |

- **A named table of known-confusable pairs** to double-check explicitly rather than guess:

  | Pair | How to tell them apart |
  |---|---|
  | Diabetes ↔ Hyperinsulinism | Insulin deficiency/resistance + hyperglycemia (Diabetes) vs. insulin excess + hypoglycemia (Hyperinsulinism) — bare "insulin" appears in both, don't let the word alone decide it |
  | Puberty ↔ Gender Medicine | CPP treatment with GnRH agonists is Puberty; gender-affirming puberty suppression is Gender Medicine — same drug class, different clinical question |
  | PCOS ↔ Adrenal/CAH | CAH-driven hyperandrogenism is Adrenal; ovarian-driven hyperandrogenism is PCOS |
  | Growth ↔ Pituitary | If the pathology itself (craniopharyngioma, adenoma, hypopituitarism) is the subject, Pituitary; if isolated/idiopathic GH deficiency or a short-stature syndrome is the subject, Growth |

- **The multi-system rule**: an article whose actual subject is a syndrome/condition
  spanning several endocrine axes with no single dominant organ focus (the thalassemia
  endocrine-complications guideline is the concrete example already in hand) should be
  verdicted `correct` if labeled `General Endocrinology` — that catch-all is its intended
  home, not an error to flag just because the article isn't pinned to one organ system.
- Instruction to judge the article's **primary subject**, the same "is it the subject, not
  an incidental mention" framing `classify_topic`'s own branches 5c/6 already use — this is
  precisely the guard branch 10 (Diabetes — General) is missing, which is why comorbidity
  mentions leak into Diabetes.
- A **self-validation step**: reload the written `classifier_qa_verdicts.json`; assert
  exactly one verdict per PMID in the sample file (none missing, none extra, none
  duplicated); assert `verdict` is one of the three allowed strings; assert `current_topic`
  in the verdict matches `current_topic` in the sample file for that PMID (catches row
  drift on a large batch); assert `target_topic` is present, valid, and follows the rules
  above for each verdict value.

## Known items round 1 should close
Two known-but-unfixed misclassifications, both `MEMORY.md`/`TASKS.md` items, are the same
failure mode this tool exists to catch — round 1 should fold them in rather than leaving
them as separate stale backlog entries:
- PMID 31319416 — 2018 international GnRH-analog consensus for precocious puberty landed
  under Gender Medicine instead of Puberty (Gender Medicine pre-check over-firing on
  GnRH-analog phrasing shared with Puberty).
- A handful of DSD enzyme-deficiency terms (e.g. 17β-HSD3, 5-alpha reductase) aren't in the
  DSD keyword list, so those occasionally land in General Endocrinology instead of DSD.
