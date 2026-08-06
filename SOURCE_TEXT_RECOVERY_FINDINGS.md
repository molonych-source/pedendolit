# Source-text recovery for the 178 no-source articles — feasibility findings

**Date:** 2026-08-06 · **Branch:** `bottom-lines` · Read-only investigation, nothing written to the store.

> **Revised after testing.** An earlier version of this file led with "Firecrawl retrieves the
> full Wiley/ISPAD text." **That claim was wrong** and is corrected in §4. Everything below has
> been probed for actual content, not just for a 200 status.

Question asked: for articles with no abstract in PubMed, can the real text be recovered from
PMC or the journal website, systematically and automatically?

**Answer: mostly no, and the cascade isn't worth building.** One retrieval path works. Two
looked like they worked and don't. The bulk of the value turns out to be in *not* showing
these articles rather than in recovering them.

---

## 1. Final counts

| Bucket | n | Disposition |
|---|---|---|
| Letters, editorials, comments, retraction notices | **69** | Demote — no retrieval needed |
| Recoverable from PMC full text | **15** | Verified: 15/15 returned >200 words of real JATS body text |
| Everything else | **94** | No legitimate automated route. Needs an honest `no_source_text` state. |

The 69 demote and the 15 PMC fetches are the entire win. There is no third tier.

## 2. Sources that return nothing (all verified against positive controls)

| Source | Yield | Control proving the test worked |
|---|---|---|
| PubMed `efetch` re-fetch | 2 / 178 | n/a — 176 genuinely have no abstract element |
| Europe PMC `resultType=core` | **0 / 178** | PMID `39377175` returned 1,808 chars |
| Crossref `works/{doi}` | **0 / 178** | 5/12 hit rate on store articles that do have abstracts |

These articles have no abstract deposited anywhere because they were published without one.

## 3. PMC full text — the one path that works

`efetch db=pmc` returns structured JATS. On the 15 articles in the keep-set that have a PMC id,
**15/15** returned real body text. Free, no scraping, no credits, no ToS question.

**Load-bearing detail:** the store's `pmc` field is populated for 32 articles, but the NCBI ID
converter finds PMC ids for **40**. Drive the cascade from the ID converter, not the stored
field, or you silently lose 8.

## 4. Correction: Firecrawl does NOT retrieve the Wiley/ISPAD text

The earlier claim rested on a 222,413-character response to
`onlinelibrary.wiley.com/doi/pdfdirect/10.1111/pedi.12702`. On inspection that response's
`url` is `/doi/abs/…` and its `contentType` is `text/html` — **Wiley redirected the PDF request
to the abstract landing page.** The 222k characters are navigation chrome and related-article
listings. Probes confirm it: `Recommendation` 0 occurrences, `Conflict of interest` 0,
`Click on the article title` 3. Retried against the canonical `/doi/pdf/…` URL: same redirect,
same landing page.

**Worse, Firecrawl's `summary` format then produced a fluent, accurate-sounding ISPAD guideline
summary from that empty page.** It reads like a real takeaway and is not grounded in the
chapter. **Never feed Firecrawl's `summary` into a bottom line.** If Firecrawl is used at all,
take `markdown` and gate it on a content probe (length plus expected section markers) before
anything downstream consumes it.

Green open-access copies are a dead end too: the Unpaywall-listed repository PDFs for two ISPAD
2018 chapters (`repositorio.uchile.cl`) are **1.6 KB metadata stubs** — 239 characters of title
and author names, not the chapter.

**Springer Nature is the one publisher where Firecrawl genuinely works** — the paywall preview
returns two real paragraphs plus rich article metadata (`dc.type: BriefCommunication`,
`citation_article_type: Journal Club`). A plain fetch is bot-blocked (3 KB stub), so this path
does require Firecrawl, at 1 credit per article. It covers ~24 Nat Rev Endocrinol items — but
see §6, because those items should probably be demoted rather than retrieved.

**Do not scrape Elsevier.** Lancet D&E pages set `tdm-reservation: 1` with a policy URL, and
Firecrawl had to escalate to a `stealth` proxy (5 credits) to load one at all. That is a stated
opt-out being evaded, on a site shown publicly at conferences.

## 5. Zotero covers almost none of it

Christian's local library holds 1,507 PDFs across 4,048 items. Matched by DOI against the
109 articles that still need text: **2 hits.** Against the whole 1,406-article store: 46.

The reason is instructive — his library has the ISPAD **2022** chapters. The store's are **2018**.

## 6. The ISPAD finding that matters more than retrieval

The store holds **23 ISPAD 2018 chapters, all with no source text**, and only 4 chapters from
2024. The 2018 edition has been superseded twice.

So the right move is not to recover the 2018 text. Writing confident takeaways for guidance
two editions stale is the same class of error as the retracted paper in §7 — it makes
out-of-date guidance look current and authoritative. The real defect is a **coverage gap**: the
ISPAD 2022 set is absent from the store entirely and 2024/2025 is thin. That is a job for the
guideline sweep, and Christian's Zotero can seed it.

The same question applies to the ~24 Nat Rev Endocrinol items: they are `Journal Club` /
`BriefCommunication` research highlights — commentary on other people's papers. They are tagged
`Journal Article`, so the pub_type demote rule misses them, but they belong in the demote
bucket on merit, not the retrieval bucket.

## 7. Live defect found during this work — fix independently

**PMID `39834161` is a retracted paper currently live on the site.** *Effects of Maternal
Vitamin D Supplementation on Childhood Health* (Endocr Rev) carries PubMed's
`Retracted Publication` type, is rated **HIGH impact**, and renders a confident bottom line
about vitamin D sufficiency and infection risk. Nothing marks it as retracted. It is present in
the deployed `index.html`.

Agreed treatment: a `RETRACTED` banner replacing the bottom line, impact dropped to LOW, article
kept visible so a reader who half-remembers it learns it was withdrawn. Pull retraction status
from PubMed `CommentsCorrections` on every run so it cannot silently recur.

Separately, PMID `28627221`'s bottom line is the literal string `[Abstract not available]`,
rendering as a takeaway.

## 8. Two ingest defects found in passing

1. **Non-Latin abstracts are truncated at ingest.** `efetch` returns several hundred characters
   of Chinese abstract for `39844487` and `42527127`; the store holds 24. Recurs on every future
   CJK guideline.
2. **The `pmc` field is undercounted** — 32 stored vs 40 found by the ID converter (see §3).

## 9. What this means for the budget question

The 1,000-credit/month Firecrawl free tier was a real constraint against a Firecrawl-heavy
design. With PMC as the only retrieval tier and Springer previews likely demoted instead of
fetched, projected spend is **near zero**. The cap-and-throttle machinery is solving a problem
that no longer exists. A ledger is still worth having for idempotency.

## 10. Sequencing

Retrieval must land before the regenerate-everything run or the 178 get regenerated twice. This
does not change the regenerate-everything recommendation — the 23% weak rate among unflagged
articles is independent of source text.
