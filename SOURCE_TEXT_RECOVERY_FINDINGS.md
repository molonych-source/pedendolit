# Source-text recovery for the 178 no-source articles — feasibility findings

**Date:** 2026-08-06 · **Branch:** `bottom-lines` · Read-only investigation, nothing written to the store.

Question asked: for the articles with no abstract in PubMed, can the real text be recovered
from PMC or the journal website, systematically and automatically?

Short answer: **partly, and only via a tiered cascade.** No single source covers it. Two free
JSON APIs that looked promising return literally nothing. Firecrawl is the only thing that
reaches the highest-value set. And ~68 of the 178 should not be regenerated at all.

---

## 1. The 178 are four different problems

| Type | n | PMC id | What it needs |
|---|---|---|---|
| Journal Article | 74 | 8 | Cascade retrieval |
| Letter | 50 | 16 | Triage first — see §5 |
| Practice Guideline | 35 | 7 | Targeted job; 25 are ISPAD 2018 |
| Editorial | 17 | 7 | **Label, don't generate** |
| Retraction / Comment | 2 | 2 | **Label, don't generate** |

A single generic pipeline underserves all four.

## 2. What each source actually returns (all tested, not assumed)

| Source | Yield on the 178 | Notes |
|---|---|---|
| PubMed `efetch` (re-fetch) | **2 / 178 (1.1%)** | Both Chinese guidelines. PubMed genuinely has no abstract for the other 176 — this is not an ingest gap. |
| Europe PMC `resultType=core` | **0 / 178** | Verified working: positive control `39377175` returned 1,808 chars. EuropePMC mirrors PubMed here. |
| Crossref `api.crossref.org/works/{doi}` | **0 / 178** | Verified working: 5/12 hit rate on a control set of articles that *do* have abstracts. These 178 have no deposited abstract because they have no abstract. |
| PMC full text (`efetch db=pmc`) | **~28 / 178** | 40 have a PMC id; 14/20 sampled returned >200 words of body text. Structured JATS XML, free, legal, no scraping. |
| Unpaywall → direct fetch | uncertain | 24/39 sampled flagged OA, but see §3 — OA status ≠ fetchable. |
| **Firecrawl (`firecrawl_scrape`)** | **high on Wiley** | See §4. The decisive tool. |

## 3. OA status is not fetchability

Plain `urllib` GET against the five host types Unpaywall returned:

| Host | Result |
|---|---|
| Sage publisher PDF | 200, real `%PDF-` bytes |
| Wiley `pdfdirect` | **403 Forbidden** on one, HTML bot-challenge on another |
| `repositorio.uchile.cl` | 200 but a **landing page** — needs a second hop to find the PDF |
| `hdl.handle.net` | 200, landing page |
| `publications.rwth-aachen.de` | 200, 248 bytes — a redirect stub |
| figshare | 202, empty body |

So the honest headline is not "62% are open access." It is "62% have a copy somewhere, and
roughly one host type in five hands it over to a plain HTTP GET."

## 4. Firecrawl changes the picture — unevenly

- **Wiley (Pediatric Diabetes, the ISPAD 2018 set): works.** The same
  `onlinelibrary.wiley.com/doi/pdfdirect/10.1111/pedi.12702` that returned **403** to `urllib`
  returned **222,413 characters** of correctly parsed full text through Firecrawl with
  `parsers: ["pdf"]`. This is the single most valuable result — 25 of the 35 guidelines are
  this exact set, on this exact publisher.
- **Springer Nature (Nat Rev Endocrinol): works, and is enough.** The paywall preview carries
  two full paragraphs of real substance before the cut. For these items that is sufficient —
  they are `citation_article_type: Journal Club` / `BriefCommunication` research highlights, so
  the preview *is* the article's argument.
- **Elsevier (Lancet Diabetes Endocrinol): body blocked, and do not push it.** The rendered
  markdown returned only ad-console scaffolding. Article metadata (`og:description`) does carry
  the opening paragraph, but that is the background sentence — the same "extractive" failure
  mode the audit already flags. More importantly the page sets **`tdm-reservation: 1`** with a
  `tdm-policy` pointing at Elsevier's opt-out. That is a machine-readable "no text mining"
  declaration. Firecrawl also silently escalated to its `stealth` proxy to load the page at all.

**Recommendation: do not scrape Elsevier or any publisher asserting `tdm-reservation`.** This
site is public and gets shown at conferences under Christian's name. Unpaywall→repository and
publisher-OA retrieval is legitimate; evading a stated TDM opt-out is not, and the yield there
is poor anyway.

## 5. Triage the 50 letters before spending retrieval on them

`Diabetes Technol Ther` and `J Diabetes Sci Technol` research letters carry real data and
deserve a bottom line. Lancet/Nature correspondence does not. One query on journal + title
decides whether ~50 items are worth any retrieval at all.

## 6. Realistic ceiling

- **Recoverable and worth recovering:** ~25 ISPAD guidelines (Firecrawl/Wiley) + ~10 other
  guidelines + ~28 PMC full texts + some share of the 74 journal articles.
- **Should be labelled, not generated:** 17 editorials + 1 retraction + 1 comment, plus
  whichever of the 50 letters are pure correspondence. Call it ~40–70 articles.
- The remainder is genuinely unavailable without a paid publisher agreement or manual work.

A tiered cascade — PMC XML → Unpaywall direct fetch → Firecrawl on non-reserving publishers →
honest label — is the right shape. It is automatable. It will not reach 100%, and the residue
needs an explicit "no source text available" state on the card rather than a manufactured
takeaway.

## 7. Two unrelated defects found in passing

Both generalise beyond the 178 and are worth fixing regardless of what happens here.

1. **Non-Latin abstracts are mangled at ingest.** `efetch` returns several hundred characters
   of Chinese abstract for `39844487` and `42527127`; the store holds 24 characters. This will
   recur on every future CJK guideline the monthly sweep picks up.
2. **The `pmc` field is undercounted.** The NCBI ID converter finds PMC ids for 40 of the 178;
   the store's `pmc` field is populated for 32.

## 8. Sequencing constraint

If source-text recovery is going to happen, it must land **before** the regenerate-everything
run, or the 178 get regenerated twice. This does not change the regenerate-everything
recommendation — the 23% weak rate among unflagged articles is independent of source text —
but it reorders the work.
