# PedEndoLit Web App — Plan & Conversation Handoff

**Purpose of this doc:** A self-contained summary so this discussion can continue in a fresh thread. The original thread is reserved for changes to the existing dashboard itself. Paste or reference this file to pick the conversation back up.

---

## The goal

Turn the existing PedEndoLit dashboard (currently a single self-contained HTML file generated weekly from PubMed) into a **public website open to the wider pediatric endocrinology community**, where individuals can **create their own accounts and save individual articles** to a personal list.

**Key constraint:** Christian has no coding experience. The build path must not require hand-writing code, and explanations should stay in plain language.

**Helpful fact:** This is published-literature surveillance with no patient data, so there are **no HIPAA constraints** on where it's hosted.

---

## What exists today

- A weekly pipeline in `01_Clinical_Research/Resources/PedEndoLit/` that searches 16 journals on PubMed, classifies results, and builds `PedEndoLit-Dashboard.html`.
- The dashboard is a static HTML file with the article data embedded inside it. This format works for viewing, but it cannot store per-user information like saved articles. That's the core reason a true web app is needed.
- One technical note that helps the rebuild: the weekly PubMed pull currently routes through Claude because this workspace's sandbox can't reach PubMed directly. A normal web server **can** call PubMed (the E-utilities API) directly. So in the new version, the weekly refresh becomes an ordinary automatic timer with no Claude in the loop, and the existing classification logic carries over.

---

## Plain-English glossary (so the terms stop being a barrier)

Think of a web app like a clinic:

- **Frontend** = the waiting room and exam room. The part people see and click.
- **Database** = the chart room. Stores every article, every user, and every saved bookmark.
- **Backend / API** = the staff who fetch the right chart for the right person.
- **Authentication** = the front desk checking your ID when you sign in.
- **Row-Level Security** = a chart-room rule that guarantees each person can only ever pull their own saved list.
- **Hosting / deploy** = the building the clinic lives in, open 24/7 on the internet.
- **Cron / scheduled job** = an automatic timer that runs the weekly PubMed pull without anyone pressing a button.

Christian will not write any of this. The chosen tool builds it from plain-English descriptions.

---

## The agreed plan: ship it in two phases (pilot before scale)

**Phase 1 — Public, read-only dashboard, no accounts.** Put the existing dashboard online for anyone to browse. This delivers most of the value, costs almost nothing, has nothing to break, and proves people want it before investing in accounts.

**Phase 2 — Add accounts and "save this article."** Only after Phase 1 shows real use. This is where login and the per-user saved list come in.

This phased order matches the "pilot before you scale" instinct and keeps risk and cost low while Christian learns the tools.

---

## Recommended tools

Build it with an **AI app builder** (you describe what you want in plain English and it produces a real, live website):

- **Lovable — the recommended starting point.** Built for non-developers, produces clean web apps, and automatically sets up the accounts-and-database piece (a service called Supabase) so you don't have to.
- **Replit — backup option.** An all-in-one workshop with strong hand-holding, but its AI assistant bills by usage and can run up cost if it churns, so watch spending.

**Under the hood, the accounts/database engine is Supabase** (managed Postgres database + built-in authentication + Row-Level Security). The builder configures it for you. Free tier is fine for dozens of users; the paid tier is about $25/month if it grows.

---

## Realistic responsibilities of going public (named, not to discourage, just to plan for)

- You become responsible for users' login info and for keeping the site online. A simple privacy policy is worth having once accounts exist.
- Cost is free or near-free at small scale and grows with traffic. The AI builders bill by usage, so monitor it.
- Ongoing care: the weekly ingestion, occasional bugs, the rare "it's down" message.

---

## Open questions to resolve in the new thread

1. **A name for the site** (it becomes the web address).
2. Confirm starting with **Phase 1** (public read-only dashboard) first.
3. Whether to use **Lovable** (recommended) or **Replit**.

---

## Suggested next step

Start Phase 1: have Claude draft the step-by-step plan plus the first plain-English build prompt to paste into Lovable, using the existing dashboard's look as the visual starting point.

**How Claude can help in the new thread:**

- Write the exact plain-English prompts to paste into the builder for each screen.
- Design the database layout (what fields each article and saved bookmark needs) so it's right the first time.
- Adapt the current dashboard's design as the visual starting point.

---

*Reference files for the new thread:* the live pipeline and dashboard live in `01_Clinical_Research/Resources/PedEndoLit/`. The dashboard's existing look (`PedEndoLit-Dashboard.html`) is the design starting point for Phase 1.
