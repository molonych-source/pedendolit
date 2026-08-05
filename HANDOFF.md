# PedsEndoBrief — Session Handoff

**Rewritten 2026-08-04 (night), superseding the earlier same-day handoff.** Paste this into
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

A pediatric-endocrinology literature digest: 19 PubMed journals → rules-based classifier →
one self-contained `index.html` (**1,406 articles, including 149 guidelines**), plus accounts.
Built for a clinician audience, meant to be shared at conferences.

## Current state: nothing is broken or half-finished

The entire auth/email stack is live and verified end-to-end: HTTPS on the custom domain,
Google sign-in, email/password with **six-digit-code password reset**, **email confirmation
ON**, all sending through Resend SMTP on the project's own domain.

**Guideline coverage is also done, not just improved.** A same-day investigation found the
classifier had no way to reject an off-topic guideline (its topic waterfall ends in an
unconditional "General Endocrinology" fallback) and missed society house styles like
"Standards of Care" — both fixed. Because rules can't judge specialty relevance, a new
**agent-reviewed approval workflow** was built (`guideline_sweep.py` → a Sonnet subagent that
judges each candidate against the taxonomy → `build_review_page.py`'s checkbox HTML page →
`apply_approvals.py`, which never writes to the store itself). Run across five rounds —
journal-scoped and wide-all-journal sweeps, each for both 2024–2026 and 2018–2023 — closing
every coverage gap identified this session. 184 individual approve/reject decisions are
recorded in `guideline_decisions.json` so nothing gets re-asked. Details and the full agent
prompt: `DECISIONS.md`, `_log.md`, `WEEKLY_REFRESH_RUNBOOK.md` → "Monthly guideline sweep".

## What's next, in order (mirrors TASKS.md)

1. **Weekly email digest + Supabase keepalive ping** — highest-value item on the clinician
   wishlist. GitHub Actions as scheduler; the keepalive matters because free Supabase projects
   pause after ~7 days idle and silently break sign-in. **Blocker: Christian must run
   `gh auth refresh -s workflow`** — the current token can't push `.github/workflows/`.
2. **Public share links** — `shared_lists` + a `SECURITY DEFINER` function keyed on an
   unguessable slug, so the table never becomes enumerable.
3. **Run the monthly guideline sweep going forward** — no backlog left, just keeping pace.
   Procedure is fully documented in `WEEKLY_REFRESH_RUNBOOK.md`; should run on Sonnet or a
   subagent, not the main session (see the "Which model to run this on" note there).
4. **Fix the Gender Medicine misclassification of GnRH-analog guidelines** — low priority,
   single known occurrence (see TASKS.md).
5. **Confirm the rendering-performance fix on a real phone.**
6. **Delete the old unused Google client secret** (two are enabled; only the newer is in use).
7. Backlog: expand the full (non-guideline) corpus back to January 2025; "Recent" default
   view; the rest of TASKS.md.

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
