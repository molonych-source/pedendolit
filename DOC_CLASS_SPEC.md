# Document class, source-text honesty, and retractions — design spec

**Status:** Approved 2026-08-07 · **Branch:** `bottom-lines` · Supersedes the "source-text
cascade" idea, which did not survive testing (see `SOURCE_TEXT_RECOVERY_FINDINGS.md`).

Filed as `DOC_CLASS_SPEC.md` at repo root to match the existing `REDESIGN_SPEC.md` /
`REVIEW_PANEL_SPEC.md` convention rather than the skill's default `docs/` path.

## Problem

261 of 1,406 articles have a mechanically broken clinical bottom line, and 178 of those have no
usable source text at all. Investigation established that the text is **not recoverable** for
most of them: Europe PMC and Crossref return 0/178, publisher PDFs redirect to landing pages,
and green-OA copies are metadata stubs. Only 15 are recoverable, from PMC.

So the fix is not retrieval. It is to stop presenting articles as though they carry a clinical
takeaway when they do not, and to separate genuine research from commentary.

A live defect surfaced during the same work: **PMID `39834161`, a retracted paper, is on the
site right now** rated HIGH impact with a confident bottom line and no retraction marker.

## Goals

1. No card ever shows a fabricated, extractive, or placeholder bottom line.
2. Commentary and correspondence stop competing with research in the default view, without
   being silently deleted.
3. Retracted papers are visibly marked, never hidden.
4. Every omission from the default view is visible as a count the reader can toggle on.
5. Genuine research letters — e.g. the Lancet stem-cell islet therapy report — stay in the
   main queue.

## Non-goals

- Firecrawl retrieval, publisher scraping, and the credit budget. Dropped; see §4 of the
  findings doc. Elsevier asserts `tdm-reservation: 1` and must not be scraped.
- Recovering the ISPAD 2018 text. Those 23 chapters are two editions superseded; the real
  defect there is a **coverage gap** (ISPAD 2022 absent, 2024/2025 thin) and belongs to the
  guideline sweep, not here.
- Regenerating bottom lines. That is `PLAN_bottom_lines.md` Task 3, which this unblocks.

## Design

### 1. Data model

Three new article fields, computed in `classifier.py`, merged by `classify()`:

| Field | Values | Meaning |
|---|---|---|
| `doc_class` | `Research` \| `Correspondence` \| `Editorial` \| `RetractionNotice` | What kind of document this is |
| `source_text_state` | `abstract` \| `full_text_pmc` \| `none` | What the bottom line was derived from |
| `retracted` | bool | The article itself has been retracted |
| `retraction_notice_pmid` | str \| null | The notice announcing it, when PubMed gives one |

`doc_class` and `source_text_state` are **independent axes**. A Nat Rev research highlight is
`doc_class: Research` but `source_text_state: none`; a letter with an abstract is
`Correspondence` but `source_text_state: abstract`.

**Invariant:** `source_text_state == "none"` implies `clinical_bottom_line == ""`. Enforce this
in `classify()`, not in the template. This alone kills the `[Abstract not available]` string
currently rendering as a takeaway on PMID `28627221`.

### 2. Classification rules

New pure function `classify_doc_class(art) -> str` in `classifier.py`, evaluated in order.
First match wins.

1. `pub_types` intersects `{"Retraction Notice", "Retraction of Publication"}` → `RetractionNotice`
2. `pub_types` contains `"Editorial"` → `Editorial`
3. `pub_types` intersects `{"Letter", "Comment"}` **and** the title matches the reply pattern → `Correspondence`
4. Otherwise → `Research`

Reply pattern, matched case-insensitively against the **title only** (never the abstract):

```
^\s*(re|reply|response|comment|comments|correspondence)\b[\s:,-]
|\b(comment|comments)\s+on\b
|\b(response|reply)\s+to\b
|\bauthors?['’]?\s+reply\b
|^[^"“]*["“][^"”]{20,}["”]          # a quoted article title inside the title
```

Rule 4 is load-bearing: a `Letter` that does **not** announce itself as a reply stays
`Research`. That is what keeps *Autologous and allogeneic stem cell-derived islet therapy in
three recipients with type 1 diabetes* in the main queue.

`source_text_state` is set separately:

- `none` when the abstract is empty or the literal `[Abstract not available]`
- `full_text_pmc` when text came from the PMC fetch in §5
- `abstract` otherwise

The Nat Rev Endocrinol research highlights need no special rule. They are single-page items with
no abstract anywhere, so `source_text_state: none` catches all 24 on merit. (A single-page probe
was tested and matched 13/24 with zero false positives, but it is redundant given the above and
is **not** part of this design.)

### 3. Reader-facing behaviour

Two independent toggles in the filter bar of `HTML_TEMPLATE` in `build_dashboard.py`, both
**off by default**, both showing a live count so no omission is silent:

```
[ ] Include commentary & correspondence (69)
[ ] Include articles with no source text (109)
```

**The two buckets must not double-count.** 69 of the 178 no-source articles are also
commentary. Define them disjointly:

- Toggle 1 counts `doc_class != "Research"` → 69
- Toggle 2 counts `doc_class == "Research" AND source_text_state == "none"` → 109,
  falling to 94 once the PMC fetch in §5 lands

Hide logic is an OR of the two conditions, so an article that is both stays hidden until
toggle 1 is on:

```
hidden = (doc_class != "Research"       && !showCommentary)
      || (source_text_state == "none"   && !showNoSource)
```

Counts are computed from the rendered dataset at page load, not hardcoded, so they track the
PMC fetch automatically.

Card rendering:

- `doc_class != Research` → a type badge (`CORRESPONDENCE`, `EDITORIAL`, `RETRACTION NOTICE`)
- `source_text_state == none` → in place of the bottom line, the literal line
  `No source text available in PubMed or PMC.`
- `source_text_state == full_text_pmc` → a provenance line under the takeaway:
  `⤷ distilled from full text (PMC)`
- `retracted` → see §4

Everything lives in `HTML_TEMPLATE`. **Never edit the generated HTML**; it is overwritten on
every build.

### 4. Retractions

Distinct from `RetractionNotice`, which is the announcement. `retracted` marks the *paper that
was withdrawn*.

- Set `retracted = True` when `pub_types` contains `Retracted Publication`, or when PubMed's
  `CommentsCorrectionsList` carries a `RetractionIn` reference (which also yields
  `retraction_notice_pmid`).
- Render a red `RETRACTED` banner **replacing** the bottom line.
- Force `impact` to `LOW` and `board_relevant` to false.
- The card stays visible and is **not** covered by either toggle in §3. A reader who
  half-remembers the paper must be able to find out it was withdrawn.

`RetractionIn` must be parsed at ingest in `build_dataset.py` so this cannot silently recur;
today's store was built before the field was read.

Known target: `39834161`.

### 5. PMC full-text recovery (small, in scope)

New `fetch_pmc_fulltext.py`:

- Input: PMIDs where `source_text_state == none` and `doc_class == Research`.
- Resolve PMC ids via the **NCBI ID converter**, not the store's `pmc` field — the field holds
  32 where the converter finds 40, and using the field silently loses 8.
- `efetch db=pmc&retmode=xml`, batched, `tool=` + `email=` set, ≤3 req/sec.
- Extract `<body>` text; accept only if >200 words. Verified 15/15 on the current keep-set.
- Write `pmc_fulltext.json` as `{pmid: {"text": ..., "pmcid": ..., "fetched": "YYYY-MM-DD"}}`.
  **Never write the full text into `pedendolit-data.json`** — the store is embedded verbatim in
  `index.html` and the single-file embed is the project's binding scale constraint.
- The bottom-line generator (`PLAN_bottom_lines.md` Task 3) reads this file as its source for
  those PMIDs and sets `source_text_state = full_text_pmc`.

Idempotent: a PMID already present with a `fetched` date is skipped.

### 6. Verification

Extend `check_classifier_regressions.py` to diff `doc_class` and `retracted` between `git HEAD`
and the working tree, failing on unblessed changes exactly as it does for `topic`. A rule edit
that silently reclassifies 200 articles must fail loudly.

**Run it after the rebuild and before committing** — it compares against `git HEAD`, so
committing destroys the comparison.

Expected counts after the rebuild, to be asserted:

| Assertion | Expected |
|---|---|
| `doc_class != Research` | 69 |
| `source_text_state == none` (all) | 178, falling to 163 after the PMC fetch |
| `doc_class == Research AND source_text_state == none` (toggle 2) | 109, falling to 94 |
| `clinical_bottom_line` non-empty where `source_text_state == none` | **0** |
| `retracted == True` | ≥1, including `39834161` |
| Articles containing the literal `[Abstract not available]` in the bottom line | **0** |
| Lancet stem-cell islet therapy report still `doc_class == Research` | true |

Manual check: open the dashboard, confirm both toggles show counts and reveal their buckets,
and confirm the retraction banner renders on `39834161`.

## Execution order

1. `merge_raw_sources.py` — required before any `--rebuild`, or the store shrinks to one week.
2. Classifier changes (§2), `RetractionIn` parsing (§4).
3. `build_dataset.py --rebuild --raw comprehensive_raw.json`
4. `check_classifier_regressions.py` — **before** committing.
5. Template changes (§3), `build_dashboard.py`.
6. `fetch_pmc_fulltext.py` (§5) — can land after the above; it only adds.

## Risks

- **The reply regex will misfile some letters.** Failure mode is visible in the regression diff
  and correctable per-PMID. Accepted over the alternative of losing research letters wholesale.
- **Hiding 94 no-source articles removes 6.7% of the store from the default view.** Deliberate:
  a card with no takeaway does not belong in a weekly brief. 15 return after the PMC fetch, and
  the toggle count keeps the omission visible.
- **`doc_class` is derived from PubMed `pub_types`, which is imperfect.** Mitigated by rule 4
  defaulting to `Research`, so the failure mode is showing too much rather than hiding a paper.
