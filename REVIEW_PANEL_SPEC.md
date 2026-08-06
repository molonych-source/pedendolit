# Review panel — design spec

**Status: built, validated, and FAILED its own gate on 2026-08-06. Auto-apply is NOT
enabled and should not be.** The design below is kept as written, with the measured
results appended at the end — the gate worked exactly as intended, which is the point of
having had one.

Supersedes the "F2/F3 LLM layers" line in `TASKS.md`. Kept in the repo root alongside the
other project docs rather than under `docs/specs/`, matching existing convention.

> **Read the results section at the bottom before building on any of this.** The core
> assumption — that three lenses would disagree in useful places — is false as specified.

## Problem

Round 2 measured the actual cost of classifier QA: Christian read **418 cards to make 8
decisions**. Concordance with the single Sonnet judge was **98.1%**, and the disagreements were
not evenly spread:

| Judge verdict | Cards | Overridden | Rate |
|---|---|---|---|
| correct | 287 | **0** | 0.0% |
| wrong | 94 | 2 | 2.1% |
| defensible | 37 | **6** | 16.2% |

Zero of 287 "correct" calls were overturned. The judge is not the bottleneck — the bottleneck
is that every card is reviewed at the same depth regardless of how contested it is.

This also means **a 2/3 majority vote is the wrong mechanism.** Majority voting collapses three
opinions into one and discards the split, but the split is the most valuable output: Christian's
override rate was 16% on genuinely contested cards versus 0% on confident ones. The panel's job
is to detect disagreement, not to resolve it.

## Design

### Three lenses, not three votes

Each article goes to three independent agents. Same model, same taxonomy, **different
question** — so their failure modes differ and agreement carries information:

| Lens | Question it answers | Failure mode it catches |
|---|---|---|
| **Clinical** | What is the primary clinical question this paper asks? | Incidental mentions — the cause of most round-2 errors (an "insulin" in the abstract of an obesity paper) |
| **Indexer** | Where would a journal section editor or MeSH indexer file it? | Prose-driven misreads; leans on MeSH, which is external to both the classifier and the model |
| **Reader** | A clinician searching for this subject expects it under which topic? | Technically-defensible-but-unfindable placements |

Each returns `{topic, confidence, reason}`. No lens sees the others' output, and **no lens is
told the classifier's current label** — otherwise all three anchor on it and unanimity becomes
a rubber stamp.

### Decision rule

- **All three agree** → auto-apply. Write a ledger entry recording all three rationales.
- **Any split** → escalate to Christian. The article **stays at its current topic** until he
  rules. A contested call must never change data silently.

Christian approved auto-apply on unanimity (2026-08-06). The escalation queue is therefore
"three ways of reading this paper disagreed," not "the model felt unsure."

### Where it runs

1. **Weekly ingest** (~35 new articles) — first build. Errors are cheapest to fix before they
   reach the site.
2. **Rotating archive audit** — same panel, different sample. Prioritised by
   `suspicion_score.py`, which measured **81.8% precision against an 11.1% baseline**, so the
   archive pass concentrates spend rather than sweeping 1,406 articles blind.

## Validation gate — build this before trusting it

We hold 418 articles with Christian's ground truth. **Replay the panel over round 2 before it
decides anything live** and measure:

1. **Recall on the 8 overrides.** Do the panel's splits contain every card Christian corrected?
   A card he overruled that the panel would have auto-applied is a silent failure, and the
   design changes rather than ships.
2. **Escalation volume.** How many of 418 split? That is the real review load, measured
   instead of projected.
3. **Auto-apply precision.** Of unanimous decisions, how many match Christian's call?

**Ship gate: 100% recall on the 8 overrides, and auto-apply precision ≥ 98%** (no worse than
the single judge it replaces). Miss either and the panel escalates more aggressively — for
example, escalating any card where confidence is below high, not only outright splits.

## Two risks the design must carry

### Auto-applied decisions are data patches, not fixes

Every auto-applied change becomes a per-PMID override via `apply_topic_overrides()`. Accumulate
a few hundred and the store quietly diverges from what `classifier.py` produces: real bugs get
masked by exceptions instead of repaired, and each override is invisible to anyone reading the
classifier.

**Required mitigation — override retirement.** After any `classifier.py` change and rebuild,
drop every override whose target now equals what the classifier produces unaided. An override
that no longer changes anything is noise. Report the count retired each run; a number that
never falls means fixes are not landing.

**Required cap.** If overrides exceed ~5% of the store, stop auto-applying and escalate
everything. That threshold is a smoke alarm for "the classifier is being papered over."

### The panel cannot fix an ambiguous taxonomy

Where the taxonomy itself is contested, the panel splits forever and escalates the same
boundary every week. That is not a defect to tune away — it is evidence, and the report should
surface it: **boundaries that split persistently are a signal the taxonomy needs changing, not
the classifier.** The Bone/Calcium ↔ Calcium/Parathyroid pair was exactly this case and is
being merged for that reason (2026-08-06).

## Interfaces

Reuses existing machinery rather than inventing a parallel path:

- **Input:** the article dicts already assembled at ingest, or `classifier_qa_sample.py` output
  for the archive pass.
- **Output:** `classifier_qa_decisions.json` — the same ledger, with new fields `decided_by:
  "panel"`, `lens_votes`, and `split: true|false`.
- **Escalation:** `build_classifier_qa_review.py`, which already renders cards, a topic
  dropdown, and (as of 2026-08-06) a free-text note field. Splits become a review page showing
  all three lens opinions side by side.
- **Application:** `build_dataset.py`'s `apply_topic_overrides()`. Unchanged.
- **Safety net:** `check_classifier_regressions.py` still runs and still fails on any topic
  change without a matching ledger entry — so a panel that writes bad entries is caught by the
  existing deterministic gate rather than by a human noticing.

## Explicitly out of scope

- Panel deciding `study_type`, `impact`, or exclusions. Topic only.
- Panel editing `classifier.py`. Fixes stay human — the standing decision is unchanged.
- Any auto-publish. Publishing remains commit + push by a person.

## Build order

1. Panel runner + the three lens prompts; output to the ledger schema. No auto-apply.
2. Replay over round 2; report the three validation metrics.
3. **Gate: review the numbers with Christian.** Only past this point does auto-apply turn on.
4. Wire into the weekly ingest.
5. Override retirement + the 5% cap.
6. Archive audit mode, seeded by `suspicion_score.py`.
7. Persistent-split reporting for taxonomy boundaries.

Steps 1–3 are the whole experiment. If the gate fails, the honest outcome is a better-sorted
review page and no auto-apply, which is still a real improvement over reading 418 cards flat.

---

# RESULTS — the gate failed (2026-08-06)

Built the panel and replayed it over the 418 articles from QA round 2, where Christian's
decisions are the ground truth. 15 agents (3 lenses × 5 batches), all self-validated,
1,254 verdicts, no missing rows. **The panel does not pass and auto-apply stays off.**

## The three metrics

| Metric | Gate | Measured | |
|---|---|---|---|
| Escalation volume | (no gate — lower is better) | **27 of 418 (6.5%)** | good |
| Auto-apply precision | ≥ 98% | **94.1%** | **FAIL** |
| Silent failures on his 8 overrides | 0 | **3** | **FAIL** |

23 of the 391 unanimous decisions would have been auto-applied to a topic Christian
disagreed with. Three of those were cards he had already personally overruled.

## Why it failed: the lenses are not independent

This is the whole finding.

| Pair | Agreement |
|---|---|
| clinical vs indexer | 95.2% |
| clinical vs reader | 96.2% |
| indexer vs reader | 95.2% |

Each lens individually matches Christian ~91% of the time (clinical 90.9%, indexer 90.4%,
reader 91.1%), yet they agree *with each other* 95–96% of the time. **They are far more
similar to each other than they are correct.** Their agreement therefore carries almost no
information about correctness — they converge confidently on the same mistakes, which is
precisely the rubber-stamp failure the design was supposed to avoid.

Different framings of the same model do not produce independent judges. The lens idea is
not enough; independence would have to come from somewhere structural, such as genuinely
different models.

## No escalation rule rescues it

Tightening the trigger trades workload for safety and never reaches the gate:

| Escalation rule | Sent to Christian | Precision | Silent failures |
|---|---|---|---|
| Split only (as specified) | 27 (6.5%) | 94.1% | 3 |
| Split or any lens low-confidence | 73 (17.5%) | 96.5% | 3 |
| Split or any lens not-high-confidence | 174 (41.6%) | 99.2% | 1 |

The strictest rule still leaks one silent failure *and* sends him 174 cards — more than
the 131 that actually mattered in round 2. There is no setting where this is both safe and
less work.

## Two confounds worth naming before anyone retries this

1. **Blinding made it worse, not more independent.** The single judge in round 2 saw the
   existing label and answered "is this right?", scoring 98.1%. This panel was deliberately
   blinded and asked to classify from scratch, scoring ~91%. Some of the judge's advantage
   is anchoring on an already-mostly-correct label — real accuracy, but not the same task.
   A fair rematch would compare anchored-panel against anchored-judge.
2. **A prompt bias accounts for most of the error.** 14 of the 23 auto-apply errors are
   cases where Christian chose `General Endocrinology` and the panel committed to something
   specific. The taxonomy text warns against over-using the catch-all, and several agents
   explicitly reported forcing genuinely off-topic content (menopause, fish physiology,
   endometriosis, a code-sharing editorial) into organ topics rather than the catch-all.
   Telling panelists plainly that no-good-fit content *belongs* in `General Endocrinology`
   would likely close much of the gap — untested.

## What to do instead

- **Do not enable auto-apply.** Nothing here justifies letting the pipeline change topics
  unsupervised.
- **The panel is still useful as a sorter, not a decider.** A 6.5% split rate is a
  high-value queue, and showing three lens opinions on a review card is strictly more
  informative than one judge's verdict. That needs no gate because a human still decides.
- **The persistent-split signal works.** The boundaries that split are exactly the
  contested ones: `General Endocrinology vs PCOS` (3), `DSD vs Puberty` (2), `Adrenal vs
  Growth` (2), `General Endocrinology vs Genetics` (2). That is a taxonomy diagnostic worth
  keeping, and it is what pointed at the Bone/Mineral merge in the first place.
- **If retried:** fix the catch-all instruction, run anchored rather than blinded, and use
  different *models* for genuine independence. Re-run this same harness
  (`scratchpad/panel/score_panel.py`) — the ground truth does not expire.

## Cost

~2.1M subagent tokens for a definitive negative result, which is cheap next to shipping a
system that silently mislabels 6% of the corpus while looking like it is working.
