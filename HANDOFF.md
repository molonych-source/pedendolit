# PedsEndoBrief — Session Handoff

**Rewritten 2026-08-05 (evening), superseding the 2026-08-04 handoff.** Paste this into a new
session and say "continue from this handoff."

**Read order for a fresh session:** `CLAUDE.md` (architecture + how to run things) →
`MEMORY.md` (current-state facts) → `DECISIONS.md` (why things are the way they are) →
`_log.md` (what happened when) → `TASKS.md` (what's open). Weekly procedure lives in
`WEEKLY_REFRESH_RUNBOOK.md`; classifier QA in `CLASSIFIER_QA_RUNBOOK.md`.

## Where the project lives

- **Working directory (the git repo):**
  `/Users/christianmolony/Documents/Claude Cowork OS 1.0/01_Clinical_Research/Resources/PedEndoLit/`
  Stale duplicate at `~/Documents/PedEndoLit copy/` — safe to delete, do not edit.
- **Repo:** https://github.com/molonych-source/pedendolit (public; name deliberately unchanged)
- **Live site:** https://pedsendobrief.org (HTTPS enforced)
- **Supabase:** `oiafndmmdplvitrttene` · **Google Cloud:** `indigo-cider-471318-p8` ·
  **Resend:** account under molonych@gmail.com

## What this is

A pediatric-endocrinology literature digest: 19 PubMed journals → rules-based classifier →
one self-contained `index.html` (**1,406 articles, 149 guidelines**), plus accounts with saved
articles and private notes. Built for a clinician audience, meant to be shared at conferences.

## Current state: one live defect, one approved spec, one decision still open

> **Rewritten 2026-08-07.** Read this section before anything else.

**🚨 A retracted paper is live on the site.** PMID `39834161`, *Effects of Maternal Vitamin D
Supplementation on Childhood Health* (Endocr Rev), carries PubMed's `Retracted Publication`
type, is rated **HIGH impact**, and renders a confident bottom line with no retraction marker.
It is in the deployed `index.html`. The fix is specced (`DOC_CLASS_SPEC.md` §4) but **not built**.
This is the highest-priority item in the project.

**`main` is at `d55b310` and that is what is live.** Nothing on the `bottom-lines` branch has
touched the store or `index.html`.

**A design was brainstormed and approved 2026-08-07: `DOC_CLASS_SPEC.md`.** It replaces the
"source-text recovery cascade" idea, which did not survive testing. The implementation plan has
**not** been written yet — that is the next step (`writing-plans`).

**What testing established** (full evidence in `SOURCE_TEXT_RECOVERY_FINDINGS.md`):
the 178 no-source articles are mostly *not* recoverable. Europe PMC and Crossref return 0/178
(both verified against positive controls). Only 15 are recoverable, from PMC. An intermediate
claim that Firecrawl retrieves the Wiley/ISPAD full text **was wrong** — Wiley redirects PDF
URLs to the abstract landing page, and Firecrawl's `summary` then fabricated a plausible ISPAD
summary from that empty page. So the work shifted from retrieval to honesty: demote 69
commentary items, mark 109 as having no source text, banner the retraction.

**A feature branch `bottom-lines` is paused mid-plan, waiting on one decision from
Christian.** 5 commits, pushed to origin. It has not touched `pedendolit-data.json` or
`index.html` — the work so far is read-only analysis, so merging or abandoning it are both
cheap.

### To resume the paused branch

```
git checkout bottom-lines
cat .superpowers/sdd/PLAN_bottom_lines/progress.md    # the ledger: what is done, what is parked
```

`PLAN_bottom_lines.md` is the plan; the ledger names every commit and every adjudication.
Tasks 1 and 2 are complete and reviewed. **Task 3 has not started** because the plan has a
hard human gate there.

**The decision waiting for Christian:** regenerate bottom lines for the 261 mechanically
flagged articles only, or for all 1,406?

- 261 of 1,406 are mechanically broken. **178 of those have no usable source text at all**
  (no abstract, or an abstract that is literally `[Abstract not available]`) — those carry
  the fabrication risk and get reviewed closely. The other 83 have a real abstract.
- Of the 1,145 that pass the mechanical rules, a judge called **23% weak** — not wrong, just
  uninformative ("The aim of this review is to describe…", "More research is needed").
  95% CI 14.8–31.2%; even the lower bound clears the plan's 10% regenerate-everything
  threshold, so the conclusion is robust to sampling noise.
- Estimated true total: **~524 of 1,406 (37%)**.
- Recommendation on record: regenerate everything, but have Christian review only the 178
  no-source articles closely plus a random sample of the rest, rather than 1,406 cards.

## What shipped 2026-08-06 (all live on main)

Full detail in `_log.md`. Everything below is DONE and published — an earlier version of this
handoff listed these as pending; they are not.

1. **Classifier QA round 2 applied.** Christian reviewed all 418 cards (410/418 concordance
   with the judge), 126 topic changes recorded, 6 accepted residuals.
2. **Four classifier bugs fixed.** `tandem` matching *tandem mass spectrometry* (10 articles
   filed as Diabetes on their assay method); `ghd` matching inside `tyGHDl`; no subject guard
   on generic terms; and **the classifier only read American spellings**, so an inclisiran
   trial for familial hypercholesterol**ae**mia missed the Lipids pre-check entirely.
3. **Bone/Calcium + Calcium/Parathyroid merged into `Bone/Mineral`** with four subdomains.
   **Taxonomy is now 16 topics.** Rationale in `DECISIONS.md`.
4. **`pub_date` repaired.** 496 of 1,406 dates corrected against PubMed, 469 moving month.
   Zero articles are now future-dated (was 30). `pub_dates.json` + `apply_pub_dates()` make it
   survive a `--rebuild`; `pub_date_precision` stops the page printing a fabricated day.
5. **Redesign direction chosen and specced** — `REDESIGN_SPEC.md`, approved. Topic grid
   landing, topic-scoped queue.

## Two things that are built but deliberately NOT enabled

- **The review panel failed its validation gate** (`REVIEW_PANEL_SPEC.md` → RESULTS).
  Auto-apply is off and should stay off: the three lenses agree with each other 95–96% while
  each is only ~91% accurate, so their agreement carries almost no information. Useful as a
  sorter, not a decider.
- **`suspicion_score.py`** works (81.8% precision against an 11.1% baseline) and is ready to
  seed future QA rounds.

## What happened 2026-08-05 (two sessions' worth, both committed)

1. **Classifier QA pipeline built, round 1 closed** (`82c19ce`). A clinician-visible bug —
   Guidelines + Diabetes surfacing non-diabetes guidelines — turned out to be two real
   classifier defects. Built `classifier_qa_sample.py` → Sonnet judge subagent →
   `build_classifier_qa_review.py` → `apply_classifier_qa.py`, procedure in
   `CLASSIFIER_QA_RUNBOOK.md`. Judge found 6 misclassifications (5 suspected + 1 it caught
   independently). Fixed 4 in `classifier.py`; the other 2 had no safe general rule, so they
   go through a new per-PMID override (`--accept-residual` → `apply_topic_overrides()`).
2. **Deterministic regression check built** (`218d23f`) —
   `check_classifier_regressions.py`. Plus: corrected a false claim in `CLAUDE.md`, and fixed
   the Analytics impact chart, which sorted an ordinal scale by count.

## Two findings that change future plans

- **NCBI E-utilities is reachable directly from the sandbox.** `CLAUDE.md` said otherwise for
  months, which is the only reason every fetch is an agent-mediated MCP step. `efetch` takes
  200 PMIDs/request, so the 2015 backfill (~20k articles) is ~100 requests — minutes as a
  script, not many agent sessions. Nothing migrated yet; the MCP still works.
- **The binding scale constraint is the single-file embed, not storage.** 20k articles is only
  ~65 MB of JSON, but `index.html` embeds all of it → ~62 MB page, and GitHub Pages caps files
  at 100 MB. `.git` is already 53 MB after 8 commits for the same reason. See `DECISIONS.md`.

## What's next, in order

> **Updated 2026-08-07.** Items 0a/0b below now sit ahead of everything.

0a. **Build `DOC_CLASS_SPEC.md`.** Ships the RETRACTED banner (clearing the live defect above),
    the commentary demote, the honest no-source state, and the 15-article PMC fetch.
    Next action: `writing-plans`.
0b. **Then close the paused bottom-line decision** below and run Task 3. It must come *after*
    0a or the 178 no-source articles get regenerated twice.

## What's next after that (mirrors TASKS.md)

> **Updated 2026-08-06.** The two items that used to sit ahead of B are DONE — QA round 2 is
> applied and the dates are fixed. B's design is now agreed (`REDESIGN_SPEC.md`) and its
> gating dependency is the bottom-line work on the paused `bottom-lines` branch. Classifier QA
> continues *alongside* the rebuild, not before it: ~90 known-wrong topics remain, the largest
> group being the 28 that fell through to the catch-all, which need new keywords rather than
> tighter guards.

Agreed roadmap: the site's primary job is a **weekly keep-up brief**, plus a "catch me up on
*topic* since *date*" mode. Designing for an eventual 20,000 articles.

1. **B — UI redesign. No agreed design exists yet; start with brainstorming, not code.** The
   problem list from a live review is in `MEMORY.md` → "Known UI problems". Headline issue:
   the page has no point of view — it opens to all 1,406 articles behind four rows of filter
   controls and makes the reader construct their own query.
2. **A — async data boundary**, done alongside B. Cheap now, a rewrite later.
3. **C — catch-up mode**, which **must state its own coverage floor**. Dense coverage begins
   Jan 2026; 2025 is ~118 articles and 2018–2024 is guidelines only. A naive date picker would
   answer "3 thyroid papers since March 2025" and look authoritative.
4. **D — backfill to 2015** (now a script job; needs an NCBI API key and a resumable manifest).
5. **E — unattended scheduling.** `workflow` scope was granted 2026-08-05, so that blocker is
   cleared. Split deterministic work (GitHub Actions) from judgment work (needs a model).
6. **F2/F3 — LLM layers of automated QA** (suspicion scoring + ingest/audit judge loops).
7. Leftovers: public share links; delete the old unused Google client secret; confirm the
   rendering-perf fix on a real phone.

## The traps most likely to bite next (full list in MEMORY.md → Operational traps)

- **Run `check_classifier_regressions.py` after a rebuild and BEFORE committing** — it diffs
  against `git HEAD`, so committing destroys the comparison it needs.
- **`--rebuild` reads the `--raw` file, not the store** — run `merge_raw_sources.py` first or
  the store shrinks to one week.
- **Cloudflare proxy must stay OFF (grey cloud) on every DNS record** — it blocks GitHub's TLS
  renewal. Cloudflare nags; ignore it.
- **Pages CDN ignores query strings** — verify deploys with a hard reload, not a `?v=N` buster.
- **RLS is the only thing separating users** — re-run the two-account isolation test after any
  policy change.
- **Supabase dashboard forms can silently revert scripted edits** — type into fields for real
  and re-read the setting afterward.
- **`gh auth refresh` needs `--hostname github.com` and a real TTY** — the `!` prefix in Claude
  Code isn't interactive enough for the device-code flow.

## Working style that fits this project

Christian is a pediatric endocrinologist, not a developer. Do the code, git, SQL and CLI work
directly rather than handing over instructions. Reserve for him only what genuinely needs his
hands: vendor dashboard toggles with no API, account creation, payment, accepting terms, and
granting OAuth consent. Explain tradeoffs plainly and flag honest caveats — he asks good
architectural questions and wants to know what's actually true, not reassurance. He responds
well to being told when a feature he asked for can't yet be delivered honestly.
