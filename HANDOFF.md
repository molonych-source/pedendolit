# PedsEndoBrief — Session Handoff

**Rewritten 2026-08-04 (evening), superseding the earlier same-day handoff.** Paste this into
a new session and say "continue from this handoff."

**Read order for a fresh session:** `CLAUDE.md` (architecture + how to run things) →
`MEMORY.md` (current-state facts) → `DECISIONS.md` (why things are the way they are) →
`_log.md` (what happened when) → `TASKS.md` (what's open). The weekly run procedure is in
`WEEKLY_REFRESH_RUNBOOK.md`.

## Where the project lives

- **Working directory (the git repo):**
  `/Users/christianmolony/Documents/Claude Cowork OS 1.0/01_Clinical_Research/Resources/PedEndoLit/`
  There is a stale duplicate at `~/Documents/PedEndoLit copy/` — a setup-era safety net,
  **safe to delete**. Do not edit it.
- **Repo:** https://github.com/molonych-source/pedendolit (public; name deliberately unchanged)
- **Live site:** https://pedsendobrief.org (HTTPS enforced)
- **Supabase:** `oiafndmmdplvitrttene` · **Google Cloud:** `indigo-cider-471318-p8` ·
  **Resend:** account under molonych@gmail.com

## What this is

A weekly pediatric-endocrinology literature digest: 19 PubMed journals → rules-based
classifier → one self-contained `index.html` (1,273 articles), plus accounts. Built for a
clinician audience, meant to be shared at conferences.

## Current state: nothing is broken or half-finished

As of 2026-08-04 the entire auth/email stack is live and verified end-to-end:
HTTPS on the custom domain, Google sign-in, email/password with **six-digit-code password
reset**, **email confirmation ON** (six-digit code at signup), all sending through Resend
SMTP on the project's own domain. Details in `MEMORY.md`; the how-and-why in `DECISIONS.md`
and `_log.md`.

## What's next, in order (mirrors TASKS.md)

1. **Weekly email digest + Supabase keepalive ping** — highest-value item on the clinician
   wishlist. GitHub Actions as scheduler; the keepalive matters because free Supabase projects
   pause after ~7 days idle and silently break sign-in. **Blocker: Christian must run
   `gh auth refresh -s workflow`** — the current token can't push `.github/workflows/`.
2. **Public share links** — `shared_lists` + a `SECURITY DEFINER` function keyed on an
   unguessable slug, so the table never becomes enumerable.
3. **ISPAD 2024 guidelines backfill** — the ~25-chapter series (Horm Res Paediatr, late 2024)
   predates the dataset's coverage; targeted PubMed fetch + merge-only pipeline.
4. **Confirm the rendering-performance fix on a real phone.**
5. **Delete the old unused Google client secret** (two are enabled; only the newer is in use).
6. Backlog: expand the database to January 2025; "Recent" default view; the rest of TASKS.md.

## The traps most likely to bite next (full list in MEMORY.md → Operational traps)

- **`--rebuild` reads the `--raw` file, not the store** — always run `merge_raw_sources.py`
  first or the store shrinks to one week of articles.
- **Cloudflare proxy must stay OFF (grey cloud) on every DNS record** — it blocks GitHub's
  TLS renewal. Cloudflare nags; ignore it.
- **Pages CDN ignores query strings** — verify deploys with a hard reload or
  `curl -H 'Cache-Control: no-cache'`, never a `?v=N` cache-buster.
- **RLS is the only thing separating users** — re-run the two-account isolation test after
  any policy change.
- **Supabase dashboard forms can silently revert scripted edits** — type into fields for
  real and re-read the setting afterward.

## Working style that fits this project

Christian is a pediatric endocrinologist, not a developer. Do the code, git, SQL and CLI work
directly rather than handing over instructions. Reserve for him only what genuinely needs his
hands: vendor dashboard toggles with no API, account creation, payment, accepting terms, and
granting OAuth consent. Explain tradeoffs plainly and flag honest caveats — he asks good
architectural questions and wants to know what's actually true, not reassurance.
