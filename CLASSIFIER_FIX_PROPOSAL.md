# Proposed `classifier.py` fix — measured, not applied

**Written 2026-08-06 from the round 2 QA verdicts.** Nothing has been applied.
`classifier.py` is untouched; the candidate lives only as `proposed_classifier_fix.patch`
(verified to apply cleanly with `patch --dry-run`).

Per the standing decision that classifier fixes are reviewed and never auto-merged, and per
`CLASSIFIER_QA_RUNBOOK.md` step 6, this is the root-cause step that follows your review of
`classifier_qa_review.html` — it does not replace it. If your review changes verdicts, the
measurement below shifts and should be re-run.

## Bottom line

Three distinct bugs, one patch. Measured against all 1,406 articles and scored against the
judges:

| | |
|---|---|
| Articles whose topic changes | **40** |
| Fixed — judge said wrong, moves to the judge's target | **17** |
| **Regressions — judge said correct, moved anyway** | **0** |
| Partial — moves off a wrong label, but not to the judge's target | 3 |
| Unjudged movers (not in the sample) | 20 |
| Landing in the `General Endocrinology` catch-all | **0** |

It resolves 17 of the 94 `wrong` verdicts (18%). It is not a complete fix and isn't meant to
be — the remaining errors sit in other branches, chiefly the 28 that fell through to the
catch-all, which need *new keywords* rather than *tighter guards* and are a separate job.

---

## Bug 1 — `tandem` matches tandem mass spectrometry

Branch 9 (Diabetes — Technology) matched the bare substring `"tandem"`, intending the Tandem
Control-IQ and t:slim insulin pumps. But **liquid chromatography–tandem mass spectrometry** is
a routine assay across adrenal, thyroid and vitamin D work.

15 store articles contain "tandem mass spectrometry"; **10 were labeled Diabetes purely
because of it** — including newborn screening for 21-hydroxylase deficiency, maternal vitamin D
metabolite profiling, and thyroid hormones in autism.

**Fix:** require product context (`tandem control-iq`, `tandem t:slim`, `tandem diabetes`,
`t:slim`) instead of the bare word. I checked the other brand literals in the same branch for
the same collision: `libre` and `aid system` are clean — every occurrence in the store is
genuinely FreeStyle Libre or automated insulin delivery.

## Bug 2 — no subject guard on generic Diabetes and Calcium terms

This is round 1's bug class, unfixed in general form, and the one **7 of 9 round-2 judges
independently flagged**. Branch 10 fired if any of `insulin`, `type 1`, `type 2`,
`hypoglycemia`, `hyperglycemia`, `glycemic` appeared *anywhere*, including a single passing
mention in an abstract. Of the 31 wrong-Diabetes articles, **26 were triggered by
abstract-only text**, and `insulin` alone accounted for 11.

**Fix:** split each branch's keywords by strength of evidence.
- **Strong** terms name the condition itself (`diabetes`, `dka`, `hba1c`, `neonatal diabetes`,
  `glucokinase`…) — one mention anywhere is enough, unchanged behavior.
- **Weak** terms are ordinary words in non-diabetes endocrine writing — they now carry the
  same guard branches 5c and 6 already use: **present in the title, or repeated at least
  twice**.

Applied to branch 10 (Diabetes — General) and branch 22a (Calcium/Parathyroid), where
`vitamin d` and `hypocalcemia` were over-firing the same way. The 22a guard matters twice
over: without it, fixing bug 3 caused a regression (a bisphosphonate guideline sliding from
Bone/Calcium to Calcium/Parathyroid on a newly-visible "hypocalcaemia"). With it, that
regression disappears and three more articles land correctly.

## Bug 3 — the classifier only reads American spellings

Every keyword is spelled American, so British and international spellings are invisible to the
entire waterfall. `hypercholesterolaemia` never matches `hypercholesterolemia`.

Concretely: PMID 41616799, the ORION-16 inclisiran trial in adolescents with heterozygous
familial hypercholesterolaemia, **missed the Lipids pre-check entirely** and fell 23 branches
to Genetics on the word "genetic".

**113 store articles carry at least one term the classifier cannot see** — 57 use `paediatric`,
29 `glycaemic`, 18 `hypoglycaemia`, 12 `tumour`. Most are still labeled correctly because some
other keyword caught them, so this is a latent fault rather than 113 visible errors. It will
get materially worse with the 2015 backfill: the monitored list includes *Lancet*, *Lancet
Diabetes & Endocrinology*, *Archives of Disease in Childhood* and several European journals.

**Fix:** a `_norm()` pass folding 28 British spellings onto their American forms before
matching. Deliberately a fixed substitution list, not a morphological rule — a general
`our → or` would maul "four" and "flour".

---

## What I recommend

Apply it, but **after** your review of `classifier_qa_review.html`, in the runbook's order:

```
# 1. review classifier_qa_review.html, Submit
python3 apply_classifier_qa.py
# 2. then this patch
patch classifier.py proposed_classifier_fix.patch
# 3. rebuild — note the --raw flag, or the store shrinks to one week
python3 merge_raw_sources.py
python3 build_dataset.py --run-date 2026-08-06 --raw comprehensive_raw.json --rebuild
python3 build_dashboard.py
# 4. BEFORE committing, while git HEAD still holds the pre-rebuild state
python3 check_classifier_regressions.py
```

Expect `check_classifier_regressions.py` to flag the 20 unjudged movers as unpredicted. That's
the normal case the runbook describes — a good fix helps articles the sample never targeted.
Spot-checking them, they read as clear improvements: a once-weekly lonapegsomatropin growth
trial, a Noonan syndrome report and an ectopic ACTH case were all labeled Diabetes and now go
to Growth, Growth and Adrenal. Bless them individually with `--bless <PMID> "<reason>"` rather
than in bulk, so each one is actually looked at.

## Honest caveats

- **18% of the wrong verdicts, not 100%.** The 28 catch-all errors and 7 Genetics errors need
  different work. The Genetics ones share bug 2's shape — 6 of 7 fired on a single abstract-only
  "genetic" — so the same guard would likely fix them, but I have not measured that and did not
  want to stack an unmeasured change onto a measured one.
- **The 3 partial movers** end up somewhere other than the judge's target: a MIRAGE syndrome
  case goes to Growth where the judge wanted General Endocrinology; a neuroblastoma thyroid-
  toxicity study goes to Thyroid where the judge wanted Cancer Late Effects; a fibrous dysplasia
  denosumab study goes to Calcium/Parathyroid where the judge wanted Bone/Calcium. All three
  leave a definitely-wrong Diabetes label, so each is an improvement, but none is finished.
- **The measurement is only as good as the verdicts.** It scores against one Sonnet judge's
  calls. If your review overturns some, re-run
  `scratchpad/fixcand/measure.py` before trusting these numbers.
