# Redesign brief (roadmap item B) — input for the brainstorm, not a design

**Written overnight 2026-08-05/06. Nothing here is decided.** The agreed process is that B
starts with brainstorming, and a brainstorm needs Christian in the room. What follows is
material to react to: three directions built as clickable prototypes, plus four constraints
found while building them that any direction has to answer.

Open the prototypes by double-click:

| File | Direction | One-line premise |
|---|---|---|
| `mockups/the-brief.html` | **The Brief** | An editorial weekly issue with a lead story. The page has an opinion. |
| `mockups/triage-queue.html` | **Triage queue** | An inbox you clear. Keyboard-driven, unread state, bottom line as headline. |
| `mockups/topic-catchup.html` | **Topic catch-up** | Topic grid first; "what's new in X since Y" with a stated coverage floor. |

All three use real articles and real counts. They share the current palette and tier colors,
which the live review already judged good. They are throwaway: no pipeline file was touched,
`build_dashboard.py` was not run, `index.html` is unchanged.

---

## Four constraints found while building these

These are the useful part of the night. Each one is a fact about the data that limits what
any redesign can honestly promise.

### 1. There is not enough important news for a weekly brief

Across **all of June and July 2026**, the store holds **1** Practice-Altering article and
**11** High. Not per week — total, across two months.

The whole premise of "a weekly keep-up brief" assumes a weekly supply of things worth
knowing. Pediatric endocrinology does not generate that. A weekly issue would be padding
itself with Moderate-tier material within a month, and the reader would learn to skim it,
which is exactly the failure the redesign is meant to fix.

Three honest ways out, and this is a real decision, not a detail:
- Make it **monthly**, where the volume genuinely supports a lead story.
- Keep it weekly but let it **say "quiet week"** and show three Moderate items without
  pretending they're landmark.
- Drop the editorial frame entirely and use the **queue** model, which doesn't promise
  importance — only completeness since you last looked.

### 2. A quarter of the publication dates are wrong

`audit_pub_dates.py` (new, read-only) checked all 1,406 articles against PubMed.
**344 (24.5%) have a broken `pub_date`:**

| Problem | Count | What it means |
|---|---|---|
| Fabricated date | 165 | Journal issue gives year-month only, so the **day was taken from a different field** and glued on. `2026-01-31` where PubMed says the article date is `2025-07-31` and the issue is `2026-01`. This date exists in neither source. |
| Not a sortable date | 110 | `2018-Oct`, `2018-Aug-01`, bare `2018`. String comparison mis-buckets all of these. |
| Issue-dated, not e-pub dated | 69 | Stored date matches the journal issue, but the paper went online a year or two earlier. A 2024 paper displays as 2026. |

Every direction above reads this field. The Brief dates its issues from it, the queue sorts
by it, and catch-up mode filters on it — so "what's new in thyroid since March 2025" is
currently answered with a field that is wrong a quarter of the time, and confidently so.

**This is arguably the real item to do before B, not after it.** It is also fixable, though
not as simply as "pick a field": `ArticleDate` is missing for 289 articles (20.6%), and
`JournalIssue/PubDate` exists for all 1,406 but is not a full date in 52.6% of them. So the
fix is a fallback order plus a rule for partial dates, then a re-fetch — still an afternoon,
not a research project. Full per-article list in `pub_date_audit.md`.

### 3. The bottom line is sometimes just the abstract's first sentence

All three directions promote `clinical_bottom_line` to the headline slot, because the live
review correctly identified it as the most valuable field and noted it's buried behind a
click. But **182 of 1,347 (14%)** are extractive — the opening words of the abstract, not a
synthesized takeaway — and some are the literal string `[Abstract not available]`.

At 15px in a card, buried under a title, that degrades quietly. At 18px as the headline, with
nothing above it, it reads as broken. Promoting the field means either accepting a visible
14% failure rate, generating real bottom lines for those articles, or falling back to the
title when the bottom line is extractive. The prototypes take the third option so you can see
the difference; `real_bottom_line()` in `build_mockups.py` is the test.

### 4. Topic labels are wrong 11.5% of the time, and unevenly

From classifier QA round 2 (see `HANDOFF.md`), weighting each topic's measured rate by its
share of the corpus: **11.5% of articles carry the wrong topic, roughly 161 of 1,406.**

The unevenness matters more than the average for a topic-first design:

| Topic | Wrong | Basis |
|---|---|---|
| Genetics | 36.8% | census |
| General Endocrinology | 34.5% | census — exact, every article judged |
| Calcium/Parathyroid | 25.0% | census |
| Gender Medicine | 22.2% | census |
| Puberty | 16.7% | sample |
| Diabetes | 11.1% | sample, n=18 — loosest figure here, and half the store |
| Growth · Hyperinsulinism · Lipids | 0% | — |

Direction 3 is built entirely on topic tiles and topic filtering is load-bearing in the other
two. A topic-first UI inherits this directly and makes it visible: a reader who opens
"Genetics" has better than a one-in-three chance of the first thing they see being misfiled.

Not a blocker for the brainstorm, but it argues strongly for landing the classifier fixes
before committing to a topic-first entry point.

---

## What I'd argue for, for you to disagree with

**The queue (direction 2), with catch-up (direction 3) as a second tab, and no editorial
brief.**

The reasoning is constraint 1. The Brief is the most attractive of the three and the one I'd
most like to be right, but it makes a promise the corpus can't keep — it needs a lead story
every week and there is roughly one every two months. The queue promises only "here is what
arrived since you last looked, in priority order," which is true every week including quiet
ones, and it degrades gracefully at 20,000 articles because a stream never shows you the
corpus. Catch-up covers the second job you named, filling gaps by topic.

The strongest argument against: the queue has no point of view, and "no point of view" is the
exact criticism of the current page. The difference is that the queue is *ordered* and
*finite* rather than filtered and infinite, but that's a real objection and worth arguing.

---

## What none of these prototypes do

Honest gaps, so the mockups aren't read as more finished than they are:

- **No async data boundary** (roadmap item A). They embed data the same way the live page
  does. A is still worth doing alongside B, exactly as agreed.
- **Not responsive.** Desktop widths only. Phone layout is where the current page's
  performance work landed and it would need real attention.
- **No accounts, saves, notes, or search.** Those exist and work today; leaving them out
  keeps the prototypes about layout.
- **The queue's unread state is fake** — it resets on reload. Real unread needs the per-user
  `last_seen_at` from Phase 3, which is a genuine dependency, not a detail.
- **The Brief's issue archive is invented.** There is no issue history; it exists to show
  what the shape would feel like.
