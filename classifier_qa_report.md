# Classifier QA report

Generated 2026-08-05. 0 correct, 3 wrong (this round), 0 pending fix (whole ledger).

## Confirmed-wrong groups (current → target)

| current → target | count | trigger location | example PMIDs (titles) |
|---|---|---|---|
| Diabetes → Growth | 1 | mixed | 39557026 (The Influence of X Chromosome Parent-of-Origin on Glycemia in Individu…) |
| Hyperinsulinism → Growth | 1 | mixed | 41482637 (Diazoxide Choline Extended-Release Tablets in Prader-Willi Syndrome: A…) |
| Puberty → General Endocrinology | 1 | mixed | 40987949 (Framework for the comprehensive screening for endocrine disorders in p…) |

### Matched literals per article

**Diabetes → Growth**
- 39557026 — matched `['turner syndrome']` in **mixed** — The Influence of X Chromosome Parent-of-Origin on Glycemia in Individuals with Turner Syndrome.

**Hyperinsulinism → Growth**
- 41482637 — matched `['prader-willi']` in **mixed** — Diazoxide Choline Extended-Release Tablets in Prader-Willi Syndrome: A Randomized, Double-Blind, Wit

**Puberty → General Endocrinology**
- 40987949 — matched `['thalassemia', 'endocrine complications', 'endocrinopathies', 'endocrine disorders']` in **mixed** — Framework for the comprehensive screening for endocrine disorders in patients with transfusion-depen

## Accepted residuals (whole ledger): 2
Known-wrong, deliberately NOT fixed — every code-level guard tried caused worse collateral damage than the bug itself. The sampler no longer force-includes these; see `residual_reason` for why.

- 38828931 — Diabetes → Calcium/Parathyroid — Vitamin D for the Prevention of Disease: An Endocrine Society Clinical Practice Guideline.. **Why not fixed:** Tested both a title-only guard and a bare-keyword pre-check for vitamin d before Diabetes: both misroute 8-9 genuinely diabetes-focused articles that discuss vitamin D as a risk factor/therapy (e.g. PMID 42039127 High-dose vitamin D therapy and prolonged partial remission of type 1 diabetes). No keyword-based fix found without worse collateral damage than this single article.
- 38869512 — Diabetes → Obesity/Metabolic — EASL-EASD-EASO Clinical Practice Guidelines on the management of metabolic dysfunction-associated steatotic liver disease (MASLD): Executive Summary.. **Why not fixed:** Tested a title-only guard for MASLD/NAFLD/steatotic-liver terms before Diabetes: misroutes 4 genuinely diabetes-focused articles (e.g. PMID 41861135 Rethinking Liver Transaminases to Predict Diabetes Risk in Children With MASLD; PMID 42250281 MASLD as Complication of Diabetes, which arguably belongs in Diabetes by its own framing). No keyword-based fix found without worse collateral damage.

## Next steps

This script never edits `classifier.py` or the store. After root-causing the groups above into a fix:
```
python3 merge_raw_sources.py
python3 build_dataset.py --run-date 2026-08-05 --raw comprehensive_raw.json --rebuild
python3 build_dashboard.py
```
Then snapshot {pmid: topic} before/after the rebuild and diff it — every changed PMID should match a `verdict: wrong` ledger entry with that exact `target_topic`; anything else is a regression.