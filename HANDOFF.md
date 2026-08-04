# PedsEndoBrief — Session Handoff

**Written 2026-08-04.** Paste this into a new session and say "continue from this handoff."

Read `CLAUDE.md` for architecture and `MEMORY.md` for the full decision log with reasoning.
This file is the short version: where things stand, what's next, and the traps.

---

## Where the project lives

- **Working directory (the real one):**
  `/Users/christianmolony/Documents/Claude Cowork OS 1.0/01_Clinical_Research/Resources/PedEndoLit/`
  This folder **is** the git repo. There is a stale duplicate at
  `~/Documents/PedEndoLit copy/` — it was the safety net during setup and is now
  **safe to delete**. Do not edit it.
- **Repo:** https://github.com/molonych-source/pedendolit (public, name deliberately unchanged)
- **Live site:** https://pedsendobrief.org
- **Supabase project:** `oiafndmmdplvitrttene`
- **Google Cloud project:** `indigo-cider-471318-p8`

## What this is

A weekly pediatric-endocrinology literature digest. 19 PubMed journals → rules-based
classifier → a single self-contained `index.html` with 1,273 classified articles, plus
accounts so readers can save articles privately. Built for a clinician audience, intended
to be shared at conferences.

---

## Status: everything from this session is finished and verified

**https://pedsendobrief.org is fully live over HTTPS**, with enforcement on. Google
sign-in was tested on the new domain and works. Nothing is left half-done.

The TLS certificate initially stalled — it sat at `null` for 40+ minutes. DNS, CAA and
routing were all verified correct, so the fix was to clear and re-set the custom domain
via the API, which re-triggers provisioning:

```bash
gh api --method PUT repos/molonych-source/pedendolit/pages -f cname=''
gh api --method PUT repos/molonych-source/pedendolit/pages -f cname='pedsendobrief.org'
```

It then moved `null → authorized → approved` within a couple of minutes. A transient
"errored" build state during the swap was harmless. **Remember this if a certificate ever
stalls again** — waiting longer does not help; re-triggering does.

Verified working: HTTPS with enforcement (http and www both 301), the old github.io URL
still redirecting, Google sign-in, and saved articles intact across the domain change.

## Done this session

- **Defused a time bomb.** The 60-day archive keyed off "date added", and the whole
  historical backfill shared one date — the site was set to drop from 1,287 articles to 258
  on the 2026-08-30 run and to 35 by late September. Archiving is now off.
- **Recovered the data foundation.** 74% of articles had no abstract; the classifier had
  only ever seen their titles. Merged local raw files, then re-fetched 427 from PubMed.
  Abstracts 336→1,214. Fully citable 308→1,266. "Other" study type 853→400. Guidelines
  detected 4→15.
- **Phase 3B features:** since-your-last-visit, private notes on saves, guidelines filter,
  citation/Zotero export.
- **Google sign-in**, alongside email/password.
- **Performance:** 36,133→14,091 DOM nodes, 748→164 ms render, ~750→200 ms per filter.
- **Rebranded to PedsEndoBrief** on `pedsendobrief.org`.

## What's next, in order

1. **Finish HTTPS** (above). Blocks everything else that touches auth.
2. **Password reset.** Needs custom SMTP via Resend on the new domain. **Use the six-digit
   `{{ .Token }}` template, not a magic link** — hospital mail scanners pre-click links and
   consume the one-time token before the human gets there.
3. **Turn email confirmation back on** at the same time. Until then addresses are unverified,
   which is what makes the pre-account-takeover risk real (see traps).
4. **Weekly email digest** — the highest-value item on the clinician wishlist, since it stops
   this depending on anyone remembering to visit. GitHub Actions as scheduler, plus a **daily
   keepalive ping** because free Supabase projects pause after ~7 days idle and that silently
   breaks sign-in. Blocker: run `gh auth refresh -s workflow` — the current token cannot push
   `.github/workflows/`.
5. **Public share links** (`shared_lists` + a `SECURITY DEFINER` function keyed on an
   unguessable slug, so the table never becomes enumerable).
6. Confirm the performance fix on a real phone.
7. Delete the old Google client secret (two are enabled; only the newer one is in use).

---

## Traps that cost time this session

- **Cloudflare's proxy must stay OFF** (grey cloud) on all five DNS records. Its proxy
  prevents GitHub from issuing a TLS certificate. Cloudflare actively nags you to enable it.
- **GitHub Pages' CDN caches by path and ignores query strings.** A `?v=2` cache-buster does
  *not* force a fresh copy into the browser. This made a working deploy look broken. Verify
  with a hard reload or `curl -H 'Cache-Control: no-cache'`.
- **Supabase's built-in mailer only delivers to project team addresses** — everyone else gets
  "Email address not authorized", on top of a fixed 2 emails/hour. The owner's own address
  *is* on the team, so testing password reset on yourself passes and then fails for every
  colleague.
- **Never add OAuth scopes beyond `openid`, `email`, `profile`.** That exact set is what
  exempts the app from Google verification review. Any addition triggers a multi-week process.
- **Google client secrets cannot be viewed after creation.** If lost, use "Add secret" on the
  client's panel — do not delete and recreate the client.
- **`--rebuild` reads from the `--raw` file, not the store.** Always run
  `merge_raw_sources.py` first, or you will wipe the store down to one week of articles.
- **RLS is the only thing separating users.** `loadSaved()` issues a bare select with no
  `user_id` filter. Re-run the JWT-impersonation isolation test after *any* policy change —
  a broken policy leaks every list while the UI looks completely normal.
- **Don't add character-class password rules.** NIST 800-63B says verifiers SHALL NOT impose
  them. Length is the lever. Note `"at least 6 characters"` is hardcoded in three places.

## Working style that fits this project

Christian is a pediatric endocrinologist, not a developer. Do the code, git, SQL and CLI work
directly rather than handing over instructions. Reserve for him only what genuinely needs his
hands: vendor dashboard toggles with no API, account creation, payment, accepting terms, and
granting OAuth consent. Explain tradeoffs plainly and flag honest caveats — he asks good
architectural questions and wants to know what's actually true, not reassurance.
