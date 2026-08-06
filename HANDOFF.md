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

## Current state: two things are waiting on Christian, nothing is broken

Auth/email stack is live and verified. Guideline coverage is done (2018 onward). The live site
is unchanged and healthy.

**The working tree is dirty on purpose and nothing from the overnight session was committed** —
`check_classifier_regressions.py` diffs against `git HEAD`, so committing now would destroy the
baseline it needs. HEAD is `84b7c10`.

Three things want a human:
1. **`classifier_qa_review.html`** — round 2 is judged and ready to review (below).
2. **`CLASSIFIER_FIX_PROPOSAL.md`** — a measured, unapplied patch for what the review will
   confirm. Apply *after* the review, in the runbook's order.
3. **`REDESIGN_BRIEF.md`** — read before any redesign work starts.

## What happened overnight 2026-08-05/06 (uncommitted)

Full detail in `_log.md`. Three findings, in order of how much they change the plan.

**1. `pub_date` is wrong for 344 of 1,406 articles (24.5%).** Verified against PubMed for the
whole store (`audit_pub_dates.py`, read-only; list in `pub_date_audit.md`). 165 are
**fabricated** — the journal issue gives year-month only, so the day is taken from
`ArticleDate` and glued on, yielding a date in neither source. 110 aren't sortable
(`2018-Oct`, bare `2018`). 69 show 2024 papers as 2026. **Catch-up mode (C) filters on this
field and the redesign sorts by it, so this plausibly outranks both.** The fix is a decision
plus a re-fetch, not research.

**2. Classifier QA round 2 is judged and awaiting review.** 418 articles, 9 parallel Sonnet
judges, merged verdicts validated globally (418/418, no drift or dupes): **287 correct, 37
defensible, 94 wrong.** That 22.5% is an enriched sample, not the store. Weighting each
topic's rate by its share of the corpus gives **11.5% wrong store-wide, ≈161 of 1,406
articles** — worst in `Genetics` (36.8%) and `General Endocrinology` (34.5%, exact because
that topic was judged exhaustively). Seven of nine judges independently flagged the same root
cause: the Diabetes branch firing on incidental insulin/hyperglycemia mentions, round 1's bug
class still unfixed in general form. Open the review page, adjust, Submit, then
`python3 apply_classifier_qa.py`.

**3. F2 suspicion scoring works.** `suspicion_score.py` (read-only) hit **81.8% precision
against the 11.1% random-Diabetes baseline — a 7.4× lift**, measured rather than asserted,
because the sample kept seeded and random portions separable. The baseline rests on 18
articles, so treat the multiplier as approximate. Use it to seed future rounds.

**4. The Diabetes over-firing is root-caused, with a measured patch waiting.**
`CLASSIFIER_FIX_PROPOSAL.md` + `proposed_classifier_fix.patch` (applies cleanly; **not
applied**). Three bugs: `tandem` matching *tandem mass spectrometry* (10 articles mislabeled
Diabetes on their assay method alone); no subject guard on generic terms like `insulin` and
`vitamin d`; and **the classifier only reads American spellings**, so an inclisiran trial for
familial hypercholesterol**ae**mia missed the Lipids pre-check and fell 23 branches to
Genetics. Measured over the whole store: 40 articles move, **17 land exactly where the judges
said, zero regressions**.

Redesign prep also landed: `REDESIGN_BRIEF.md` and three prototypes in `mockups/`. **B still
starts with a brainstorm** — these are inputs to react to, not a design.

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

## What's next, in order (mirrors TASKS.md)

> **Order changed overnight.** Before B, two items now have evidence behind them: review the
> round 2 QA verdicts (and fix the Diabetes branch), and decide the `pub_date` question. The
> redesign rests on both — a topic-first UI inherits an 11.5% topic error rate, and every
> direction sorts or filters by a date field that's wrong a quarter of the time.

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
