# PedsEndoBrief — Project Log

Reverse-chronological record of what happened and when. Rationale for standing choices lives
in `DECISIONS.md`; current-state facts live in `MEMORY.md`. Backfilled 2026-08-04 from the
git history (33 commits to that date) and the dated sections formerly in `MEMORY.md`.

---

### [2026-08-04] https-resend-auth (evening session)

- **HTTPS finished on pedsendobrief.org.** The certificate was never provisioned because the
  GitHub Pages DNS check was stuck "in progress" despite DNS being verifiably correct. Fix:
  removed and re-added the custom domain in Settings → Pages (via browser). Cert issued within
  minutes (expires 2026-11-02, auto-renews); HTTPS enforcement enabled; http→https 301 and
  www→apex redirects verified. The remove/re-add made GitHub commit `Delete CNAME` +
  `Create CNAME` (53bf59c, cbd3cba) — pulled into local.
- **Google sign-in verified end-to-end on the new HTTPS domain** by Christian.
- **Resend set up for transactional email.** Account created by Christian (molonych@gmail.com,
  free tier 100/day); domain `pedsendobrief.org` added (us-east-1) with manual DNS: DKIM TXT
  `resend._domainkey`, MX + SPF TXT on `send`, DMARC TXT `_dmarc` (`v=DMARC1; p=none;`).
  Records added at Cloudflare (all DNS-only), verified live with dig, domain **Verified** in
  Resend ~18 min after creation. "Enable Receiving" skipped.
- **Supabase custom SMTP configured** (Christian pasted the API key): `smtp.resend.com:465`,
  user `resend`, sender `no-reply@pedsendobrief.org` / "PedsEndoBrief". Saving custom SMTP
  auto-raised the email rate limit 2→30/hour and unlocked template editing (templates are not
  editable before custom SMTP exists).
- **Both email templates rewritten to six-digit `{{ .Token }}` codes** (reset password +
  confirm signup), replacing the default `{{ .ConfirmationURL }}` links.
- **OTP length trap found and fixed:** first two test emails carried 8-digit codes — this
  project's "Email OTP length" was 8, not the documented default 6. Set to 6 in Sign In /
  Providers → Email. Second trap: setting the field by scripted value assignment appeared to
  save but silently reverted (React state); real keystrokes committed it. Third test email
  delivered a 6-digit code in seconds.
- **Password reset + signup confirmation UI shipped** (eb8ec91): "Forgot password?" →
  email → code → new password via `resetPasswordForEmail` → `verifyOtp(type:'recovery')` →
  `updateUser`, with a consumed-OTP guard so a spent code isn't re-verified if `updateUser`
  fails; signup confirmation mirrors it with `verifyOtp(type:'signup')` + `resend()`. Built in
  `HTML_TEMPLATE`, caught a name collision locally (`rstatus` already used by the bug-report
  form → renamed `pwstatus`; whole inline script now node --check'd), tested all view states
  locally, deployed, and **verified end-to-end by Christian on the live site**.
- **Email confirmation switched ON** (Sign In / Providers → Confirm email), closing the
  pre-account-takeover hole (see DECISIONS.md).
- **ISPAD gap diagnosed:** the ISPAD 2024 Clinical Practice Consensus Guidelines (~25 chapters,
  Horm Res Paediatr, late 2024) predate the dataset's coverage — the store has zero Horm Res
  Paediatr 2024–2025 articles (by pub year: 2024×21, 2025×91, 2026×1160). Targeted backfill
  added to TASKS.md.
- Docs updated (82e2af5); HANDOFF.md restructure into _log.md/DECISIONS.md agreed.

### [2026-08-04] rename-domain-google-perf (afternoon sessions)

- **Rebranded to PedsEndoBrief** on https://pedsendobrief.org (0caf02e, a914e2b; domain via
  Cloudflare Registrar ~$10/yr, auto-renew). Only user-facing strings renamed; internal
  filenames and the repo name deliberately unchanged. DNS: four apex A records to GitHub Pages
  + `www` CNAME, all DNS-only. Old github.io URL 301-redirects. Supabase redirect URLs and the
  Google OAuth origin were added additively, keeping the old URL valid through the transition.
- **Google sign-in shipped** (28cf37d, 2424f42, 5594fb7): Google Cloud project
  `indigo-cider-471318-p8`, OAuth client "PedEndoLit web (Supabase)", scopes exactly
  `openid email profile` (no verification review), published to production. Client secret
  lives only in the Supabase dashboard. `GOOGLE_ENABLED` flag gates the button. Old fake
  `molonychtest@gmail.com` account deleted first — with confirmation off it was "confirmed"
  without ownership proof and could have auto-linked to whoever owns that address.
- **Rendering performance** (b20ef6b, b94e2bb), measured with `performance.now()` on the live
  page: DOM nodes 36,133→14,091; cards built 1,274→512; abstract bodies in DOM 1,130→0 until
  opened; initial render 748→164 ms; filter interaction ~750→200 ms. `fillGroup()` builds a
  collapsed tier on first open; `absText()` inserts abstract text on demand.
- **Deploy gotcha recorded:** GitHub Pages' CDN caches by path and ignores query strings — a
  `?v=N` cache-buster does NOT fetch a fresh copy and made a working deploy look broken.
  Verify with a hard reload or `curl -H 'Cache-Control: no-cache'`.

### [2026-08-04] phase3b-features

- **Phase 3B shipped** (98bafc7, 7507410): `user_prefs` table (`last_seen_at` +
  `prev_seen_at`, so opening the page doesn't erase the "new since your last visit" marker),
  private notes on saves (debounced `update`, not the optimistic-insert/swallow-23505
  pattern used for saves — that pattern is wrong for free text), guidelines
  filter (two lines — the `.chip[data-flag]` handler binds any chip), and citation export
  (per-article copy, bulk copy, RIS download) as pure client-side string building.
- **Two long-standing bugs fixed:** open abstracts collapsed on every re-render (no backing
  state — added `openAbstracts` mirroring `openCards`); search re-rendered ~1,300 articles on
  every keystroke (added debounce).
- **Verified:** RLS isolation on `user_prefs` (owner 1 row / other user 0 / anon denied), note
  round-trip, guidelines filter (15 of 1,273), citation copy.
- Noted: Supabase leaked-password protection is Pro-only (advisor flags it; the free-tier
  toggle silently refuses to save). Password-reset limitation documented: the built-in
  sender refuses non-team addresses entirely ("Email address not authorized") on top of
  2/hour — and the owner's own address IS on the team, so self-testing passes while every
  colleague fails. This is why reset waited for custom SMTP.

### [2026-08-04] data-recovery-archive-fix

- **Defused the archive time bomb** (286366d): `ARCHIVE_AFTER_DAYS = None`. The 60-day rule
  keyed on `review_date` (date *added*); the historical backfill shares one date, so the site
  would have dropped 1,287→258 articles on 2026-08-30 and →35 by late September.
- **Recovered the data foundation** (f58cd82, a4e33e1, 9bbf888, 6ab0009): 74% of the store had
  no abstract and had been classified on title alone — the prior `comprehensive_raw.json` held
  1,053 records but only 93 abstracts while `_tmp_batches/` still had full text. Wrote
  `merge_raw_sources.py` (richest-value-wins merge, seeds from the store because 45 published
  articles exist in no raw file). Fixed `map_raw()` (dropped citation block, `identifiers.pmc`,
  truncated authors at 6). Fixed guideline detection (guidelines now tested before
  systematic-review, using `pub_types` + full title, with an about-guidelines guard).
  Re-fetched 427 abstracts from PubMed via MCP in batches of 20.
- **Cumulative result:** abstracts 336→1,214; clinical bottom lines 336→1,214; "Other" study
  type 853→400; guidelines 4→15; fully citable 308→1,266; board-relevant 69→186;
  volume/issue/pages 0→910; PMC ids 0→595. Store 1,287→1,273 (14 correct removals). Only 59
  articles still lack an abstract — all letters/editorials with none indexed.

### [2026-08-04] phase2-accounts-live

- **Phase 2 activated** (31ad9ce, 2a8a63b, 24131de): Supabase project `oiafndmmdplvitrttene`
  (ca-central-1, free tier), `saved_articles` table from `supabase_setup.sql`, publishable
  key, anon role grants explicitly revoked. Sign-in modal, per-card Save buttons, "My Saved
  Articles" tab.
- **This folder became the git repo / publish channel** (f87e612, 030336e): GitHub Pages
  first enabled on the repo — before this the handoff docs assumed a live site that had never
  actually been switched on.

### [2026-07-24] apem-and-legacy-backfill

- **APEM added as the 19th monitored journal** after confirming it active and PubMed-indexed;
  IJPE ruled out as dormant. Backfilled Jan 2026–present: 30 candidate PMIDs, 29 added,
  1 excluded (erratum). Runbook updated to 19 journals.
- Legacy metadata backfill for old records worked via `backfill_legacy_metadata.py`, then
  paused (`PedEndoLit Legacy Metadata Backfill Handoff.md`) — later superseded by the
  2026-08-04 data recovery.

### [2026-05-29 → -30] initial-build

- Ported the Perplexity classifier spec (v2.4.2 + Diabetes Framework) to `classifier.py`;
  pilot run caught two bugs (incidental "IGF"/"MEN1" mentions hijacking topic — fixed with
  subject-vs-mention guards; systematic reviews getting the generic "Authoritative review"
  rationale — now have their own) — both fixed.
- Added Gender Medicine topic and the Calcium/Parathyroid split; Turner/PWS placed under
  Growth.
- Built the three-stage pipeline and the self-contained dashboard; impact tier accordion +
  Analytics tab layout settled.
- **2026-05-30: month bucketing reversed** from entry-date to publication-date (0 mismatches
  verified) — see DECISIONS.md.
