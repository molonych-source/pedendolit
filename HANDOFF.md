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

## Current state: nothing is broken or half-finished

Auth/email stack is live and verified. Guideline coverage is done (2018 onward). Classifier QA
now has both a review pipeline and an automatic regression gate. Working tree clean, pushed
through `218d23f`.

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
