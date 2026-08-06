# UI redesign — design spec (roadmap item B, with A)

**Status: spec reviewed and approved by Christian 2026-08-06. Not built.** Direction chosen by Christian after
reviewing the three prototypes in `mockups/`: **topic catch-up as the primary surface, the
triage queue as the secondary.** Supersedes the open questions in `REDESIGN_BRIEF.md`; that
document's four measured constraints still apply and are referenced below.

## The job this page does

The site's primary job is a **weekly keep-up brief**, with a secondary "catch me up on
*topic* since *date*" mode. Designing for an eventual 20,000 articles.

The current page has no point of view: it opens to all 1,406 articles behind four rows of
filter controls and makes the reader construct their own query. This design replaces that
with a single opinionated entry point.

## Navigation model: grid is the door, queue is the room

There is one path in. The reader always arrives through a topic; the queue is never the
first thing seen.

```
LANDING                              AFTER CLICKING "Thyroid"
┌────────────────────────────┐      ┌────────────────────────────┐
│ header: search · saved ·   │      │ header: search · saved ·   │
│         analytics · account│      │         analytics · account│
│────────────────────────────│      │────────────────────────────│
│ What's new in [Thyroid ▾]  │      │ ‹ All topics               │
│ since [2026-07-01]  (Go)   │      │ Thyroid · 8 since Jul 1    │
│                            │      │────────────────────────────│
│ ⚠ Dense coverage begins    │      │ ▌ bottom line (headline)   │
│   January 2026             │      │   title · journal · date   │
│────────────────────────────│      │                       ☆ ✓  │
│ ┌──────┐ ┌──────┐ ┌──────┐ │      │────────────────────────────│
│ │Diabet│ │Thyroid│ │Growth│ │      │ ▌ bottom line (headline)   │
│ │3 new │ │8 new │ │  —   │ │      │   title · journal · date   │
│ │lead… │ │lead… │ │      │ │      │                       ☆ ✓  │
│ └──────┘ └──────┘ └──────┘ │      │                            │
│  … 16 topic tiles …        │      │                            │
└────────────────────────────┘      └────────────────────────────┘
```

### Landing

- **Catch-up control.** One sentence: *what's new in `[topic ▾]` since `[date]`*. Submitting
  it opens the queue for that topic, scoped to that date range.
- **Coverage-floor notice.** Always present, and **it must adapt to what was asked.** Dense
  coverage begins January 2026; 2025 holds ~118 articles thinning to 1–9/month; 2018–2024 is
  essentially guidelines only. Asking "since March 2025" must produce a statement of what
  the answer can and cannot see, *before* the articles. A naive date filter would return
  three papers and look authoritative — that is the failure this notice exists to prevent,
  and it must keep working even after a 2025 backfill, because someone will always ask for a
  date earlier than the corpus goes.

  **Christian's call, 2026-08-06:** disclosing the gap is an acceptable answer for now.
  *Closing* the gap — backfilling so the notice has less to disclose — is future work
  (roadmap item D), not a blocker for this redesign.
- **16 topic tiles.** Each shows: topic name, count new since the reader's last visit, and a
  one-line preview of its highest-impact recent article. Topics with nothing new say so
  plainly rather than showing a zero.
- **No article list and no filter rows on the landing screen.** That is the point.

### Topic queue

- Scoped to one topic. Ranked by **impact tier first, then newest**.
- Each row: **bottom line as the headline** (largest text on the row), title beneath it in
  smaller type, then journal · date · tier. Save (☆) and mark-read (✓) per row.
  This inverts the current card, where the title dominates and the bottom line — the single
  most valuable field — is hidden behind a click.
- Tier is shown once per group, not repeated on every row inside its own tier group.
- Back link to the grid.

### Header destinations

Search, Saved, and Analytics are **destinations, not modes** — always one click away, never
occupying the reading surface.

- **Search** queries all 1,406 articles regardless of topic or date. It is the "I know the
  paper exists" path. A search *box* does not undercut the grid-first model; a
  browse-everything *view* would, so there isn't one.
- **Saved** — accounts, saved articles and private notes are live with real user data since
  2026-08-04. Unchanged by this redesign.
- **Analytics** — kept as-is.

## Card content changes

From the 2026-08-05 clinician review (full list in `MEMORY.md` → "Known UI problems"):

| Problem | Resolution |
|---|---|
| Bottom line buried behind a click | Promoted to headline |
| Uniform 13–15px type, nothing to scan by | Real hierarchy: bottom line > title > metadata |
| Tier badge repeated inside its own tier group | Shown once per group |
| `Why PRACTICE-ALTERING` byte-identical on all 150 guidelines | Removed — it carries no information |
| Tag noise (a precocious-puberty guideline tagged `#HealthEquity`, `#Genetics`) | Primary topic tag plus genuinely earned tags only |
| "New this period: 0" tile with equal weight to real metrics | Removed |
| No time dimension anywhere | The whole design is time-scoped |

**Keep:** the palette, the tier colours, and the general restraint. The clinician review
judged these good and they are not in scope to change.

## Blocking dependency: real bottom lines

Promoting the bottom line to headline position exposes a data problem. **261 of 1,406
(19%) are not usable takeaways** — measured 2026-08-06 across five rules: 119 placeholder,
63 that repeat the abstract's opening, 59 with no abstract at all, 19 truncated
mid-sentence, 1 too short. (An earlier figure of 182 counted only the extractive pattern;
261 is the real number.) Tolerable at 13px behind a click; visibly broken at headline size.

Agreed 2026-08-06: **generate real bottom lines** rather than fall back to the title.

Two requirements on that work:

1. **Audit before fixing.** Done — see `PLAN_bottom_lines.md` Task 1, which found 261 by
   five mechanical rules rather than one. Task 2 additionally judges a random sample of the
   1,145 that pass those rules, because a well-formed sentence can still be a poor takeaway
   and no mechanical rule catches that.
2. **Christian spot-checks a sample before it goes live.** These become the most prominent
   clinical text on the page. Same review posture as the classifier verdicts.

This is separable work and can run in parallel, but the redesign should not ship ahead of it.

## Roadmap item A, built at the same time

Every data access in the page becomes **asynchronous**, while the data is still embedded in
the file. Nothing changes on screen. It is cheap now and expensive later: at 20,000 articles
the single-file embed is not viable (~65 MB of JSON → a ~62 MB page, against GitHub Pages'
100 MB file cap — see `DECISIONS.md`), so moving to a database-backed archive is inevitable,
and this makes that move plumbing rather than a rewrite.

## Risks

- **A topic-first UI inherits the topic error rate.** Measured at **11.5% store-wide**, and
  uneven: `Genetics` 36.8%, `General Endocrinology` 34.5%, against 0% for `Growth` and
  `Hyperinsulinism`. A reader who opens Genetics has better than a one-in-three chance the
  first thing they see is misfiled. This design makes classification errors *more* visible
  than the current page does, which argues for continuing classifier QA alongside, not after.
- **"New since your last visit" needs the per-user timestamp** from Phase 3. `is_new` is a
  global flag meaning "added in the most recent run" and structurally cannot answer "new to
  me". Without the per-user value the tile counts are wrong for everyone but the first
  visitor of the week.
- **Not responsive yet.** The prototypes are desktop-width only. The phone layout is where
  the earlier performance work landed and needs real attention, not a media query.
- **The editorial-volume constraint does not apply here.** June–July 2026 held 1
  Practice-Altering and 11 High articles total, which is why the editorial "Brief" direction
  was rejected. A topic grid degrades gracefully in a quiet week — tiles simply say nothing
  new — so this design does not make a promise the corpus cannot keep.

## Explicitly out of scope

- Changing the taxonomy, the classifier, or any pipeline script.
- Auto-publishing. Publishing stays commit + push by a person.
- Any change to accounts, saves, notes, or the Supabase schema.
- Backfilling to 2015 (roadmap item D) — independent, and the coverage notice is designed to
  keep telling the truth whether or not it happens.

## Build order

1. **Bottom-line audit** — measure the real extent, beyond the 182 already found.
2. **Generate and review bottom lines** — Christian spot-checks before they land.
3. **Async data boundary (item A)** — invisible, do it first so the new UI is written against
   it rather than retrofitted.
4. **Landing: topic grid + catch-up control + adaptive coverage notice.**
5. **Topic queue** with the new card layout.
6. **Header destinations** — search, saved, analytics wired to the new shell.
7. **Phone layout.**
8. **Per-user "new since last visit"** — or, until it exists, tiles show "new this week"
   and say so, rather than silently meaning something else.

Steps 1–2 gate the visible work. Steps 3–6 are the redesign proper. Steps 7–8 can follow.

## Where the prototypes sit

`mockups/the-brief.html`, `mockups/triage-queue.html`, `mockups/topic-catchup.html`,
regenerated 2026-08-06 against current data. They are **throwaway inputs, not a starting
codebase** — the real work edits the `HTML_TEMPLATE` string in `build_dashboard.py`, and the
generated `index.html` is overwritten on every build. `mockups/build_mockups.py` can be
deleted once the redesign lands.
