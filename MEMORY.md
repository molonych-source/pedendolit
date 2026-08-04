# PedsEndoBrief — Memory

Project memory for PedsEndoBrief, the pediatric endocrinology literature dashboard
(named PedEndoLit until 2026-08-04; internal filenames still use the old name).
Durable facts, decisions, and architecture. For open ideas and to-dos see `TASKS.md`
in this same folder. For the weekly run procedure see `WEEKLY_REFRESH_RUNBOOK.md`.

## What this is
A self-contained literature-surveillance dashboard that replaces the paid Perplexity
Computer workflow. Pulls pediatric endocrinology articles from 19 monitored journals
via PubMed (free NCBI E-utilities, accessed through the PubMed MCP), classifies each
with a rules-based classifier ported from the Perplexity spec, and renders a single
self-contained `PedEndoLit-Dashboard.html` (data embedded; opens by double-click, no
server). Goal: drop the Perplexity subscription, run everything inside Cowork.

## Architecture (the pipeline)
- **`journals.json`** — 19 monitored journals + PEDS_TERMS + Template A/B (peds-filter) flags.
- **`classifier.py`** — the rules classifier (currently v2.5-equivalent: v2.4.2 spec + diabetes framework + Gender Medicine + Calcium/Parathyroid split). Pure functions, unit-tested.
- **`build_dataset.py`** — fetch→classify→dedup(by PMID)→60-day archive + is_new reset→writes `pedendolit-data.json`. `--rebuild` reclassifies all raw from scratch (use after classifier edits). Decodes HTML entities (`&#xa0;` etc.) at ingest.
- **`build_dashboard.py`** — reads the datastore, writes `index.html` (the published artifact, inside this folder = inside the git repo) plus two identical convenience copies: `PedEndoLit-Dashboard.html` here (gitignored) and one at the `01_Clinical_Research/` level. Holds the WEB3FORMS_KEY, the Supabase keys, and the entry-date override logic.
- **`pedendolit-data.json`** — the datastore (active + archived, keyed by PMID).
- **Weekly refresh** — scheduled task, Sundays ~9:01 AM ET, follows `WEEKLY_REFRESH_RUNBOOK.md`. Replaces the old Perplexity cron.

## Source-of-truth spec documents (in this folder)
- `PedEndoLit_Classifier_Spec_v2.4.2.docx` — full classification logic (exclusions, 25-branch topic waterfall, study types, 4-tier impact, board relevance, tags).
- `PedEndoLit_Retrieval_Config.docx` — the original 18 journals, exact PubMed queries, date window, dedup. Not yet updated for the 19th (APEM, added 2026-07-24 directly to `journals.json`) — see Key Decisions below.
- `PedEndoLit_Diabetes_Classification_Framework.docx` — diabetes subtype framework (v2.5.0).
- `all_articles_export.csv` — Perplexity's ground-truth article export (used as the entry-date source for the historical set).

## Key decisions (and the why)
- **Stricter peds filter kept over matching Perplexity's count.** Perplexity's set is 960; ours is ~878. The gap is Perplexity letting non-pediatric noise through (erectile dysfunction, colorectal cancer, postmenopausal, personal essays). Our v2.4.2 classifier excludes those by design. Decision: keep the clean filter, accept the lower count. (Decided 2026-05-29.)
- **Month filter keyed on PUBLICATION date (pub_date).** REVERSED the earlier entry-date decision: entry-date bucketing put Jan–Mar articles under "June 2026" (when Perplexity indexed them), which confused the "Month" filter — a clinician expects "published in." Now month_key = pub_date month for every article; verified 0 mismatches between an article's month bucket and its displayed date. Trade-off accepted: the dropdown again lists older real publication months (back to 2023) for the handful of old-print articles, which is honest. The `all_articles_export.csv` entry-date override is no longer used for month bucketing. (Reversed 2026-05-30; original entry-date approach was 2026-05-29.)
- **Date scope restricted to 2026 (+ small 2025 tail) on the May-29 pass.** A NEXT step is in flight to expand back to Jan 2025 — see TASKS.md.
- **Impact segmented filter replaced by the tier-accordion grouping** — grouping by tier IS the impact filter; two controls for one dimension was redundant.
- **Analytics charts moved to their own tab** (Topic distribution, Evidence impact, Articles by journal); Feed is the default tab.
- **PubMed search MCP errors at max_results=500 — use 200.** No journal approaches 200 even over 5 months. (Noted in runbook.)
- **Turner & Prader-Willi intentionally live under Growth** (not a dedicated topic) — GH therapy is the dominant peds-endo touchpoint; the search box covers syndrome-level retrieval. (Decided 2026-05-29.)
- **Two classifier bugs found via pilot and fixed:** (1) incidental "IGF" / "MEN1" abstract mentions hijacking topic — fixed with subject-vs-mention guards; (2) Systematic Reviews showed the generic "Authoritative review" rationale — now have their own.
- **Added Annals of Pediatric Endocrinology & Metabolism (APEM) as the 19th monitored journal** (`Ann Pediatr Endocrinol Metab`, `peds_filter: false` — dedicated peds-endo journal like Horm Res Paediatr / J Clin Res Pediatr Endocrinol / J Pediatr Endocrinol Metab). Confirmed active and PubMed-indexed (89 articles since Jan 2025) before adding; ruled out International Journal of Pediatric Endocrinology (IJPE) as a candidate — PubMed shows no articles since ~2021, effectively dormant. Backfilled Jan 2026–present (matching the store's primary Jan–Jul 2026 coverage window for the other 18 journals) on 2026-07-24: 30 candidate PMIDs, 29 added, 1 excluded (erratum). `WEEKLY_REFRESH_RUNBOOK.md` updated to reflect 19 journals; `PedEndoLit_Retrieval_Config.docx` (the original spec doc) still says 18 and hasn't been regenerated. (Decided 2026-07-24.)

## Taxonomy state
17 topics: Diabetes, Growth, Puberty, Thyroid, Adrenal, Obesity/Metabolic, General
Endocrinology, Bone/Calcium, Pituitary, Hyperinsulinism, Genetics, Calcium/Parathyroid,
DSD, PCOS, Gender Medicine, Cancer Late Effects, Lipids.
Diabetes subtypes: T1D, T1D·Stage, T2D, Technology(subtopic), MODY/Monogenic, CFRD,
GDM, Steroid-induced, General.
Recently added: **Gender Medicine** (ABP Domain 16, pre-check before Puberty/DSD with a
DSD-context guard) and **Calcium/Parathyroid** split out of Bone/Calcium (both 2026-05-29).

## Publishing
- **Live at https://pedsendobrief.org** — GitHub Pages serving `main` branch root of https://github.com/molonych-source/pedendolit (public repo, name unchanged). The old `molonych-source.github.io/pedendolit/` URL 301-redirects here. Pages was first enabled 2026-08-04; before that the repo existed but Pages had never been switched on, so the site was never live despite handoff docs assuming it was.
- **This folder is the git repo.** Re-publishing = `git add`, `git commit`, `git push`; Pages redeploys automatically (~10 min CDN cache). No more manual file upload. Auto-publish on a schedule is still a TASKS.md item.
- **Bug/comment form**: Web3Forms (key `bb727558-...` is in `build_dashboard.py`; safe to expose — send-only). Reports email to Christian. First submission triggers a one-time Web3Forms verification email. Sandbox can't test the POST (proxy blocks api.web3forms.com) — test from a real browser.

## Phase 2: accounts + saved articles (live 2026-08-04)
- Supabase project **`oiafndmmdplvitrttene`** — `https://oiafndmmdplvitrttene.supabase.co`, region ca-central-1, free tier. One table, `public.saved_articles` (`user_id`, `pmid`, `saved_at`), created from `supabase_setup.sql`. Only PMIDs are stored, so the saved list can never drift out of sync with the weekly dataset.
- Uses the **publishable key** (`sb_publishable_…`) rather than the legacy `eyJ…` anon JWT; either works, the swap is one line in `build_dashboard.py` plus a rebuild.
- Emptying `SUPABASE_URL` / `SUPABASE_ANON_KEY` rebuilds a pure Phase 1 page — that's the feature's off switch.
- **Per-user scoping rests entirely on Row-Level Security**: `loadSaved()` issues a bare select with no `user_id` filter. Correct by design, but re-run the two-account isolation test after ANY policy change — a broken policy leaks every list while the UI looks normal.
- Email confirmation OFF (built-in sender is rate-limited), so addresses are unverified and signup is open. No password-reset UI — reset from Supabase → Authentication → Users.
- The `anon` role has zero table grants (explicitly revoked; Supabase's defaults would otherwise auto-grant).

## Data recovery + archive fix (2026-08-04)
- **The 60-day archive was a time bomb and is now OFF** (`ARCHIVE_AFTER_DAYS = None` in `build_dataset.py`). It keyed on `review_date` = when an article was ADDED, not published; the whole historical backfill shares `2026-06-28`, so all 1029 would have expired on one run. Simulated: 1287 → 258 articles on the 2026-08-30 run, → 35 by late September. The dashboard is a searchable corpus; "what's new" belongs per-user, not as a global purge.
- **74% of the store had no abstract** and had been classified on title alone. Cause: the previous `comprehensive_raw.json` (built by an unsaved ad-hoc script) held 1053 records but only 93 abstracts, while the original per-batch MCP fetches in `_tmp_batches/` still had full text. This — not the classifier — was why two-thirds of articles typed as "Other" with no bottom line.
- **`merge_raw_sources.py` fixes it with zero API calls.** Merges every local raw file, richest-value-wins per field. Seeds from the current store first because **45 published articles exist in no raw file at all** (including both Endocrine Society guidelines) and a rebuild without that seed would delete them.
- **`map_raw()` was silently dropping data**: never read the `citation` block (volume/issue/pages) or `identifiers.pmc`, and truncated authors at 6 — 174 records sat at exactly 6, so complete vs truncated was indistinguishable. All fixed.
- **Guideline detection was broken two ways**: `classify_study_type` tested meta-analysis and systematic review *before* guidelines (so the Endocrine Society precocious-puberty guideline typed as "Systematic Review"), and only looked at the first 120 chars against a narrow phrase list. Now guidelines are tested first, using `pub_types` + full title, with a guard excluding papers *about* guidelines (adherence/implementation/survey).
- **Then re-fetched the rest from PubMed** (2026-08-04): 427 articles had no abstract in any local file, pulled via the PubMed MCP in batches of 20 (the tool caps there and persists large results to files — read those from disk, don't pull into context). PubMed returns the literal string `[Abstract not available]` for letters/editorials that genuinely have none; `merge_raw_sources.py` treats that as empty rather than storing it as body text.
- **Cumulative result:** abstracts 336→1214, clinical bottom lines 336→1214, "Other" 853→400, guidelines 4→15, fully citable 308→1266, board-relevant 69→186, volume/issue/pages 0→910, PMC ids 0→595. Store 1287→1273; all 14 removals correct (errata/corrections and adult-only studies) and only detectable once abstracts existed.
- **Only 59 articles still lack an abstract**, and those are letters/editorials with none indexed in PubMed. This is effectively done — the backfill job in `PedEndoLit Legacy Metadata Backfill Handoff.md` is superseded.

## Phase 3B: since-last-visit, notes, guidelines filter, citation export (live 2026-08-04)
- **`user_prefs` table** — one row per user (`user_id` PK, `last_seen_at`, `prev_seen_at`). Not a clone of `saved_articles`; it's a different shape. `prev_seen_at` exists so opening the page doesn't erase the very "new since" marker the reader is looking at. On a first visit `prev_seen_at` is null and nothing is flagged new, which is the honest answer.
- **`saved_articles.note`** — free text. Uses `update` on a debounced timer plus blur, NOT the optimistic-insert/swallow-23505 pattern used for saves; that pattern is wrong for free text.
- **Guidelines filter** was two lines: `build_dashboard.py`'s `.chip[data-flag]` handler already binds any chip, so a new filter is one static span plus one line in `matches()`.
- **Citation export** (per-article copy, bulk copy, RIS download for Zotero) is pure client-side string building from the embedded dataset. Only worth having after the metadata recovery — 1266 articles are now fully citable and 910 have volume/issue/pages.
- **Two long-standing bugs fixed**: open abstracts collapsed on every re-render (inline `style.display` with no backing state Set — now `openAbstracts`, mirroring `openCards`), and search had no debounce so every keystroke re-filtered ~1300 articles and rebuilt the entire list.
- **Verified**: RLS isolation on `user_prefs` (real user 1 row, different user id 0, owner view 1, anon denied), note round-trip to the DB, guidelines filter (15 of 1273), citation copy.
- **Leaked-password protection is Pro-only.** The Supabase security advisor flags it as disabled, but the toggle is gated behind the paid plan — the UI lets you flip it and then silently refuses to save.
- **Do NOT add character-class password rules.** (An earlier version of this file recommended them; that was wrong.) NIST SP 800-63B: *"Verifiers and CSPs SHALL NOT impose other composition rules (e.g., requiring mixtures of different character types) for passwords."* They push people to `Password1!` — apparent strength, real usability cost. Length is the lever that works; the normative floor for password-only sign-in is 15 characters. If raising it, note `"at least 6 characters"` is hardcoded in **three** places (`build_dashboard.py` modal placeholder and client-side check, plus the Phase 2 setup guide) and they must move together or the page accepts a password Supabase then rejects.
- **Password reset is not merely rate-limited, it is blocked.** Supabase's built-in sender *"will refuse to deliver messages to addresses that are not part of the project's team"* — everyone else gets *"Email address not authorized"* — on top of a fixed 2 messages/hour. **Trap: the project owner's own address IS on the team**, so testing reset on yourself succeeds and then fails for every colleague. Requires custom SMTP, which requires a verified sending domain.
- **When reset is built, use the six-digit `{{ .Token }}` template, not a magic link.** Hospital mail security (Defender Safe Links etc.) pre-clicks links and consumes the one-time token before the human does; Supabase has a dedicated troubleshooting page for it and this audience is exactly the affected population.

## Name and domain (2026-08-04)
- **The product is PedsEndoBrief, at https://pedsendobrief.org** (Cloudflare Registrar, ~$10/yr, auto-renew on). Renamed from "PedEndoLit" before any colleague had been given the address — the cheapest possible moment.
- **Why "Peds" not "Ped":** the specialty says "peds endo" aloud; "Ped" is a written truncation nobody speaks. The name is meant to be passed along at conferences, so matching speech matters. "Brief" promises the filtering-down, which is the actual value, rather than just naming the contents.
- **Only user-facing strings were renamed** — page title, header, sign-in heading, footer, bug-report subject. Internal filenames (`pedendolit-data.json`, `PedEndoLit-Dashboard.html`, the scripts, the repo name `pedendolit`) are deliberately unchanged: invisible to users, and renaming them risks the pipeline for nothing.
- **DNS:** 4 A records at the apex to GitHub Pages (185.199.108-111.153) plus a `www` CNAME to `molonych-source.github.io`. **All must be "DNS only" (grey cloud), NOT proxied** — Cloudflare's proxy prevents GitHub from issuing the TLS certificate. Cloudflare nags you to enable proxying; ignore it.
- The old `molonych-source.github.io/pedendolit/` URL now 301-redirects to the custom domain, so nothing that was shared earlier breaks.
- **Supabase redirect URLs and the Google OAuth origin were added additively**, keeping the old URL valid through the transition rather than cutting it over.

## Google sign-in (live 2026-08-04)
- **Google Cloud project `indigo-cider-471318-p8`**, OAuth client "PedEndoLit web (Supabase)", client ID `774609386490-c3vucn75ttkggi9rsjvkufhdtr696tb5.apps.googleusercontent.com` (public by design). The **client secret lives only in the Supabase dashboard** — never in this repo. Google no longer lets you view a secret after creation; if lost, use **Add secret** on the client's "Additional information" panel rather than recreating the client (two secrets can coexist for rotation).
- **Scopes are exactly `openid`, `email`, `profile` — do not add more.** Google's Manage App Audience page carves out an exception for precisely this set: no verification review, no unverified-app warning, no 100-test-user cap, no 7-day expiry. Any additional scope forfeits all of it and triggers a review that takes weeks. Verified in practice: the consent URL showed `scope=email+profile` and went straight to the account chooser with no warning screen.
- **Published to "In production"** (Audience page). The push-to-production dialog confirmed verification is only needed for >10 domains, a logo, or sensitive scopes — none apply.
- Redirect URI given to Google: `https://oiafndmmdplvitrttene.supabase.co/auth/v1/callback`. JS origin: `https://molonych-source.github.io`. Supabase Redirect URLs allow-list now contains the Pages URL (wildcards split on `/`, so `…/pedendolit/*` would NOT match nested paths — use the exact URL).
- **`GOOGLE_ENABLED` in `build_dashboard.py`** gates the button, same pattern as the Supabase keys. Leave it False if the provider is ever disabled, or the button errors with "provider is not enabled".
- **Google accounts get a genuinely verified email**; email/password accounts do not while confirmation is off. Verified: `molonych@gmail.com`, provider `google`, `email_confirmed_at` set by Google.
- Cosmetic: the consent screen says `oiafndmmdplvitrttene.supabase.co`, not "PedEndoLit", because brand verification was skipped. Fix later with a Supabase custom domain; not worth doing for a pilot.
- The old fake `molonychtest@gmail.com` account was **deleted** before enabling Google — with confirmation off it was marked confirmed without ownership proof, so whoever owns that address could have been auto-linked into it.

## Rendering performance (2026-08-04)
Measured on the live page with `performance.now()`, not estimated:

| | before | after |
|---|---|---|
| DOM nodes | 36,133 | **14,091** |
| cards built | 1,274 | **512** |
| abstract bodies in DOM | 1,130 | **0** until opened |
| initial render | 748 ms | **164 ms** |
| a filter interaction | ~750 ms | **200 ms** |

- **`render()` used to build every tier's cards even when collapsed**, then let CSS hide them. LOW is collapsed by default and holds 762 of 1273 articles, so 60% of the DOM was built for content nobody had asked to see. `fillGroup()` now builds a tier on first open (~250 ms for LOW, paid only if you open it).
- **Abstract text is inserted on open** via `absText()`, not emitted inline on every card.
- `openCards` / `openAbstracts` still drive state, so a re-render preserves whatever the reader had open — verified after the change.
- **Deploy gotcha: GitHub Pages' CDN caches by path and ignores query strings.** A `?v=N` cache-buster does NOT force a fresh copy in the browser; it fooled me into thinking a deploy hadn't worked. Use a hard reload (cmd+shift+R) or `curl -H 'Cache-Control: no-cache'` when verifying a deploy.

## HTTPS on the custom domain (fixed 2026-08-04)
- GitHub's certificate provisioning never started because the Pages **DNS check was stuck
  "in progress"** — DNS itself was verified correct (four apex A records to GitHub, proxy off).
  Fix: remove and re-add the custom domain in Settings → Pages, which re-triggers the check.
  Cert issued within minutes (expires 2026-11-02, auto-renews); `https_enforced` is ON.
- The remove/re-add makes GitHub commit a `Delete CNAME` + `Create CNAME` pair to the repo —
  pull after doing it or the next push conflicts.
- Google sign-in verified end-to-end on https://pedsendobrief.org after enforcement.

## Password reset + email confirmation (live 2026-08-04)
- **Custom SMTP via Resend** (account under molonych@gmail.com, free tier: 100/day).
  Domain `pedsendobrief.org` verified in Resend via manual DNS at Cloudflare — deliberately
  NOT the "Auto configure" OAuth path, so Resend holds no standing access to DNS. Four records:
  DKIM TXT `resend._domainkey`, MX + SPF TXT on `send`, DMARC TXT `_dmarc` (`p=none`).
  "Enable Receiving" was skipped on purpose — no inbound mail wanted.
- Supabase SMTP: `smtp.resend.com:465`, user `resend`, password = Resend API key (Christian
  holds it), sender `no-reply@pedsendobrief.org`. Saving custom SMTP auto-raised the email
  rate limit to 30/hour and unlocked template editing (templates are NOT editable before that).
- **Both templates use six-digit `{{ .Token }}` codes, not links** — hospital mail scanners
  pre-click links and consume one-time tokens; codes are immune.
- **Trap: this project's "Email OTP length" was 8, not the documented default 6.** First two
  test emails carried 8-digit codes that the UI's 6-digit validation would reject. Set to 6 in
  Sign In / Providers → Email. Second trap: setting the field via scripted `.value` assignment
  showed "saved" but silently reverted (React state); real keystrokes committed it.
- **UI (all in `HTML_TEMPLATE`):** "Forgot password?" → email → code → new password, via
  `resetPasswordForEmail` → `verifyOtp(type:'recovery')` → `updateUser`. A consumed-OTP guard
  (`otpOK`) prevents re-verifying a spent code if `updateUser` fails. Signup confirmation is the
  same pattern with `verifyOtp(type:'signup')` + `resend()`. Watch for JS name collisions in the
  single inline script — `rstatus` was already taken by the bug-report form (renamed `pwstatus`).
  Verified end-to-end by Christian on the live site.
- **Email confirmation is ON** (Sign In / Providers → Confirm email) as of 2026-08-04. This
  closes the pre-account-takeover hole: unverified email/password signups can no longer squat
  on an address that later links to a Google sign-in. Supabase links same-email identities into
  one account (same user_id, same saved list) regardless of which method is used first.

## Known limitations / honest caveats
- `is_new` means "added in the most recent run" — a global flag, so it cannot answer "what's new for me". Per-user last-seen is the Phase 3 fix.
- "Other" is still the largest study-type bucket (590 of 1280), mostly articles that genuinely lack PubMed type tags.
- A few DSD enzyme-deficiency terms (e.g. 17β-HSD3) aren't in the DSD keyword list, so those occasionally land in General Endocrinology.
- 28 backfilled articles had abstracts condensed (not verbatim) by a subagent during fetch; classification verified unaffected.

## Contacts / accounts
- Web3Forms key: in `build_dashboard.py` (`WEB3FORMS_KEY`).
- GitHub repo: https://github.com/molonych-source/pedendolit (public, account `molonych-source`). Live site https://pedsendobrief.org (the old github.io URL 301-redirects).
- Resend account under molonych@gmail.com — sending domain `pedsendobrief.org` (us-east-1), dashboard at resend.com. API key lives only in Supabase's SMTP settings; if lost, create a new key and re-paste.
- Supabase project `oiafndmmdplvitrttene` (free tier). **Free-tier projects pause after ~1 week with no API activity, and a paused project makes sign-in fail** — the weekly refresh doesn't touch Supabase, only real user traffic does. Resume from the Supabase dashboard.
- Local caveat: `~/Documents` is iCloud-synced, so `.git` lives inside a syncing folder. GitHub is the durable backup — push at every checkpoint; re-clone if git ever reports corruption.
