# PedsEndoBrief — Decisions

Standing decisions for this project: what was decided, when, why, and what was rejected.
Entries are never deleted — a reversed decision is marked **Superseded** with a pointer.
Chronology lives in `_log.md`; current-state facts live in `MEMORY.md`.

---

## Classification & taxonomy

### Stricter peds filter kept over matching Perplexity's count — 2026-05-29 — **Active**
**Why:** Perplexity's set is 960 articles; ours is ~878. The gap is Perplexity letting
non-pediatric noise through (erectile dysfunction, colorectal cancer, postmenopausal,
personal essays). The v2.4.2 classifier excludes those by design.
**Rejected:** tuning the filter to match Perplexity's count for continuity — parity with a
noisier corpus is not a goal.

### Month filter keyed on publication date (`pub_date`) — 2026-05-30 — **Active** (supersedes entry-date bucketing, 2026-05-29)
**Why:** entry-date bucketing put Jan–Mar articles under "June 2026" (when Perplexity indexed
them). A clinician reading a "Month" filter expects "published in". Verified 0 mismatches
between bucket and displayed date after the switch.
**Trade-off accepted:** the dropdown lists older real publication months (back to 2023) for a
handful of old-print articles — which is honest. The `all_articles_export.csv` entry-date
override is no longer used for month bucketing.
**Note:** `WEEKLY_REFRESH_RUNBOOK.md` still describes the superseded entry-date behavior;
this file is the authority.

### Turner & Prader-Willi live under Growth, no dedicated topic — 2026-05-29 — **Active**
**Why:** GH therapy is the dominant peds-endo touchpoint for both; the search box covers
syndrome-level retrieval.

### Gender Medicine topic added; Calcium/Parathyroid split from Bone/Calcium — 2026-05-29 — **Active**
**Why:** Gender Medicine is ABP Domain 16 (implemented as a pre-check before Puberty/DSD with
a DSD-context guard). Parathyroid/calcium-homeostasis papers were drowning in metabolic bone
disease under a single Bone/Calcium bucket.

### APEM added as the 19th monitored journal; IJPE ruled out — 2026-07-24 — **Active**
**Why:** Annals of Pediatric Endocrinology & Metabolism is active and PubMed-indexed
(89 articles since Jan 2025); added as `peds_filter: false` (dedicated peds-endo journal).
International Journal of Pediatric Endocrinology rejected — no PubMed articles since ~2021,
effectively dormant.
**Note:** `PedEndoLit_Retrieval_Config.docx` still says 18 journals; `journals.json` is the
authority.

## Pipeline & data

### 60-day archiving switched OFF (`ARCHIVE_AFTER_DAYS = None`) — 2026-08-04 — **Active**
**Why:** the archive keyed on `review_date` = when an article was *added*, not published, and
the whole historical backfill shares one date — so 1,029 articles would all have expired on
the same weekly run (simulated: 1,287 → 258 on 2026-08-30, → 35 by late September). The
dashboard is a searchable corpus; "what's new" belongs per-user (`user_prefs.prev_seen_at`),
not as a global purge.
**Rejected:** fixing `review_date` semantics and keeping the archive — no user-facing benefit
justified the risk.

### Guideline detection must not rely on PubMed `pub_types` alone — 2026-08-04 — **Active**
**Why:** PubMed does not tag every guideline. The ADA "Standards of Care in Diabetes"
chapters carry only `Journal Article, Review`, so detection falls to the title — and the
title patterns missed the phrasings societies actually use: "Standards of Care",
"Consensus Report", and ISPAD's "Clinical Practice **Consensus** Guidelines 2024" (a word
between "practice" and "guidelines", a year where a preposition would be). Such articles
silently lost the PRACTICE-ALTERING tier, the `#Guidelines` tag, and the Guidelines filter.
**Guard kept:** papers *about* guidelines (adherence, implementation, awareness) are still
excluded, now both leading and mid-title.

### Guideline coverage is journal-scoped by design, with a publication-type sweep as the safety net — 2026-08-04 — **Active**
**Why:** the weekly refresh only sees the 19 journals in `journals.json`. An audit confirmed
that design works — every guideline published in a monitored journal inside the coverage
window was captured — but it is structurally blind to guidelines published elsewhere, and
societies do publish elsewhere (DSD guidelines in Endocrine Journal, the Female Athlete Triad
consensus in Sports Medicine, national CAH guidelines in Problems of Endocrinology).
`guideline_sweep.py` runs monthly across all journals to catch those.
**Rejected:** simply adding more journals — it trades one fixed blind spot for a slightly
larger fixed blind spot, and inflates the weekly fetch for a handful of articles a year.

### Sweep results are reviewed, never auto-merged — 2026-08-04 — **Active**
**Why:** the wide publication-type query runs **~35% precision**. The first real queue
contained guidelines for hemophilia A, endometriosis, atopic dermatitis, Axenfeld-Rieger
syndrome and infection-related glomerulonephritis — all of which classify cleanly as
`Guideline/Consensus` because they *are* guidelines; they just aren't pediatric endocrinology.
The classifier cannot filter on "is this my specialty", so a human gate is the honest design.
`guideline_sweep.py` therefore never writes to the store; it writes a review queue plus a
candidates file that feeds the normal `build_dataset.py --raw` merge.

### Recurring PubMed work runs on the cheaper model — 2026-08-04 — **Active**
**Why:** the weekly refresh and monthly sweep are search-fetch-merge-rebuild, with no design
judgment, and nearly all their cost is article metadata. They should run on Sonnet or in a
subagent whose context absorbs the metadata. The stronger model is for work that changes how
articles are *judged* — classifier edits, taxonomy changes, diagnosing a coverage gap.
**Corollary:** never read article text into context; the MCP spills large results to files,
and the raw-file format is the MCP record verbatim, so assembling a raw file is a JSON
concatenation rather than a transformation.

## Product & identity

### Renamed to PedsEndoBrief; internal filenames and repo name deliberately unchanged — 2026-08-04 — **Active**
**Why "Peds" not "Ped":** the specialty says "peds endo" aloud; "Ped" is a written truncation
nobody speaks, and the name is meant to be passed along at conferences. "Brief" promises the
filtering-down, which is the actual value.
**Why filenames stayed:** `pedendolit-data.json`, the scripts, and the repo name `pedendolit`
are invisible to users; renaming them risks the pipeline for nothing.

### Impact filter replaced by the tier accordion; Analytics moved to its own tab — 2026-05-29 — **Active**
**Why:** grouping by tier IS the impact filter; two controls for one dimension was redundant.
Feed is the default tab.

### Lazy rendering: collapsed tiers and abstract bodies built on demand — 2026-08-04 — **Active**
**Why:** `render()` used to build every tier's cards even when collapsed; LOW alone holds 762
of 1,273 articles, so 60% of the DOM was built for content nobody asked to see. Measured
result: DOM nodes 36,133→14,091, initial render 748→164 ms, filter interaction ~750→200 ms.
`openCards`/`openAbstracts` state survives re-renders.

## Accounts & auth

### Phase 2 stores only PMIDs server-side — 2026-08-04 — **Active**
**Why:** article text is always read from the weekly dataset embedded in the page, so a saved
list can never drift out of sync with the corpus. One table (`saved_articles`), trivial schema.

### Per-user isolation rests entirely on RLS; `loadSaved()` intentionally unfiltered — 2026-08-04 — **Active**
**Why:** a bare select with Row-Level Security is the correct design (the server enforces
scoping, not the client). **Consequence:** any policy change must be re-verified with the
two-account isolation test — a broken policy leaks every list while the UI looks normal.

### Publishable key (`sb_publishable_…`) over the legacy anon JWT — 2026-08-04 — **Active**
**Why:** independent rotation and better defaults; the legacy `eyJ…` key remains a one-line
drop-in substitute in `build_dashboard.py` if ever needed.

### Google OAuth scopes exactly `openid email profile`, never more — 2026-08-04 — **Active**
**Why:** Google exempts exactly this set from verification review — no unverified-app warning,
no 100-test-user cap, no 7-day expiry. Any additional scope forfeits all of it and triggers a
multi-week review.

### No character-class password rules — 2026-08-04 — **Active** (supersedes earlier in-repo advice recommending them)
**Why:** NIST SP 800-63B: verifiers *SHALL NOT* impose composition rules. They push people to
`Password1!` — apparent strength, real usability cost. Length is the lever (normative floor
for password-only sign-in is 15 characters). If raising the minimum, `"at least 6 characters"` is
hardcoded in several places (modal placeholders, client-side checks) that must move together.

### Password reset and signup confirmation use six-digit `{{ .Token }}` codes, not magic links — 2026-08-04 — **Active**
**Why:** hospital mail security (Defender Safe Links etc.) pre-clicks links and consumes
one-time tokens before the human ever sees the email — and clinicians are exactly the affected
population. Codes are immune. Supabase has a dedicated troubleshooting page for this failure.

### Email OTP length set to 6 — 2026-08-04 — **Active**
**Why:** this project's Supabase setting was 8 (not the documented default 6), which mismatched
the six-digit UI validation and every "six-digit" string in the templates. 6 digits is standard,
and Supabase rate-limits verification attempts, so the entropy difference is immaterial.

### Resend domain verified via manual DNS, not the "Auto configure" OAuth grant — 2026-08-04 — **Active**
**Why:** auto-configure gives Resend standing write access to the Cloudflare zone. Manual DNS
is four records once, keeps DNS access with Christian only, and made it possible to verify
every record stayed un-proxied.

### Resend "Enable Receiving" skipped — 2026-08-04 — **Active**
**Why:** it would route inbound mail for pedsendobrief.org to Resend; the project only sends.
`no-reply@pedsendobrief.org` needs no mailbox.

### Email confirmation ON — 2026-08-04 — **Active**
**Why:** with confirmation off, addresses were unverified and signup was open — anyone could
register a colleague's Gmail address with their own password before the real owner ever
visited; when the owner later signed in with Google, Supabase's same-email identity linking
would merge the identities into an account the attacker holds a password for
(pre-account-takeover). Confirmation requires proving inbox control before the account
activates, closing the hole. (Same-email linking itself is desired behavior: whichever door a
user enters by, they get one account, one saved list.)

## Infrastructure

### Cloudflare DNS records all "DNS only" (grey cloud); proxy never enabled — 2026-08-04 — **Active**
**Why:** Cloudflare's proxy prevents GitHub Pages from issuing/renewing the TLS certificate.
Cloudflare's UI actively nags to enable proxying; ignore it. Applies to every record in the
zone, including any added later.
