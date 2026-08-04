# PedEndoLit Phase 2: Accounts and Saved Articles

Everything in the dashboard code is already written and tested. What is left is
about 20 minutes of point-and-click setup in Supabase, then pasting two values
into one file and re-running the build.

Nothing about the weekly refresh changes. `build_dataset.py`, `journals.json`,
and the Sunday scheduled task are untouched.

---

## 1. Supabase setup (point and click)

1. Go to [supabase.com](https://supabase.com) and sign up with your Google
   account or email. The free tier is enough for this.
2. Click **New project**.
   - **Name:** `pedendolit`
   - **Database Password:** click Generate, then save it in your password
     manager. You will not need it for the dashboard, but you cannot recover it
     later.
   - **Region:** East US (North Virginia) is closest to Pittsburgh.
   - Click **Create new project** and wait about two minutes for it to finish
     provisioning.
3. In the left sidebar click **SQL Editor**, then **New query**.
4. Open `supabase_setup.sql` (same folder as this guide), copy the whole file,
   paste it into the editor, and click **Run**. You should see "Success. No rows
   returned." That one step creates the table, switches on Row-Level Security,
   and creates all four policies.
5. In the left sidebar click **Authentication**, then **Sign In / Providers**.
   Confirm **Email** is enabled. It is on by default.
6. Still under Authentication, open the email provider settings and turn
   **Confirm email** OFF. See "Why confirmation is off" below before you decide.
7. Left sidebar, **Project Settings** (gear icon), then **API**. You need two
   values from this page:
   - **Project URL**, which looks like `https://abcd1234efgh.supabase.co`
   - the **anon public** key, a long token starting with `eyJ`

   Copy both somewhere you can paste from. Do not copy the `service_role` key.
   That one bypasses all the security rules and must never go in a web page.

### Why confirmation is off

Supabase's built-in email sender is rate limited to a small number of messages
per hour and their docs describe it as suitable for testing, not production. A
group of fellows signing up on the same afternoon would hit that ceiling and
people would sit waiting for confirmation emails that never arrive. With
confirmation off, signup and login work instantly and no email is ever sent.

The tradeoff is that someone can register with an email address they do not own.
For a private literature list that is a low-stakes tradeoff, and Row-Level
Security still keeps every account's list separate. You can see your project's
actual limits under **Authentication → Rate Limits**.

When you want to turn confirmation on later, connect a real email provider
(Resend and SendGrid both have free tiers) under **Project Settings → Auth →
SMTP Settings**, and set **Site URL** to your GitHub Pages address so the
confirmation links point back to the dashboard.

---

## 2. Paste your two values and rebuild

Open `build_dashboard.py` and find these two lines near the top, at lines 38 and 39:

```python
SUPABASE_URL = ""
SUPABASE_ANON_KEY = ""
```

Paste your values between the quotes:

```python
SUPABASE_URL = "https://abcd1234efgh.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.....the rest of the key....."
```

Then rebuild the dashboard:

```bash
python3 "01_Clinical_Research/Resources/PedEndoLit/build_dashboard.py"
```

That rewrites all three copies. Upload the regenerated
`01_Clinical_Research/index.html` to your GitHub repo the same way you did for
Phase 1, keeping the filename so the URL stays the same.

The anon key is meant to be public in the page, exactly like the Web3Forms key
already in that file. On its own it grants no access to anything. Row-Level
Security is what decides who can read and write which rows.

**If you leave both values empty,** the dashboard builds and behaves exactly as
it does today: no Sign in button, no Saved tab, no Save buttons. That is the
current state, so this Sunday's automatic refresh is safe either way.

---

## 3. What the code does

All of it lives inside `build_dashboard.py`, in the `HTML_TEMPLATE` string. That
matters: the generator overwrites all three HTML files every Sunday, so editing
the HTML by hand would be wiped. There is nothing for you to paste beyond the
two values above.

- **Sign in button** in the header, next to the Report button. It opens a small
  panel with email, password, Sign in, and Create account.
- **A Save button on every article card.** It is greyed out with a "Sign in to
  save articles" tooltip until someone logs in.
- **A "My Saved Articles" tab** between Feed and Analytics, showing only that
  person's saves, newest first.
- **Sessions persist.** Supabase stores the login in the browser, so a refresh
  or a return visit tomorrow keeps you signed in until you click Sign out.
- **Only PMIDs go to the database.** Titles and abstracts are read from the
  weekly dataset already embedded in the page, so the saved list can never drift
  out of sync with the article content.
- **Articles that drop out of the dataset degrade gracefully.** The Saved tab
  splits into the articles still present and a "Not in the current list" section
  underneath, where each one reads `[Article no longer in current list]` with its
  PMID and a working PubMed link. The count line says, for example,
  `12 saved articles · 2 no longer in the current list`. Nothing breaks and
  nothing is silently lost, which matters because the pipeline archives articles
  at 60 days.

---

## 4. Testing checklist

Do this in order. Step 6 is the one that actually matters.

1. Open the dashboard. The Sign in button and the My Saved Articles tab are
   visible. Save buttons are greyed out.
2. Click **My Saved Articles**. It reads "Sign in to start building your saved
   list."
3. Click **Sign in**, enter a real email and a password of at least six
   characters, and click **Create account**. The panel closes and the header now
   shows your email with a Sign out button.
4. Back on the Feed, click **☆ Save** on two or three articles. Each turns into
   a green **★ Saved**. Open **My Saved Articles** and confirm those articles are
   there, newest first.
5. Refresh the page. You are still signed in and the saved list is unchanged.
   Click **★ Saved** on one article to remove it and confirm it disappears from
   the tab.
6. **The two-account isolation test.** Click Sign out. Create a second account
   with a different email, ideally in a private or incognito window so the two
   sessions cannot interfere. Save one different article. Then confirm all three
   of these:
   - Account B's Saved tab shows only account B's article, not account A's.
   - Sign back in as account A and confirm the list is unchanged and does not
     include account B's article.
   - In the Supabase SQL Editor run the last query at the bottom of
     `supabase_setup.sql`. It shows every save with the owner's email. You should
     see both accounts' rows there, with different `user_id` values. The SQL
     Editor bypasses Row-Level Security by design, which is exactly why it is the
     right place to confirm the rows really are separate.

   If account B can see account A's saves in the dashboard, Row-Level Security
   is not switched on. Re-run `supabase_setup.sql` and check the two verification
   queries in its comments.
7. **The graceful degradation test.** In the SQL Editor, insert a PMID that is
   not in the current dataset, using your own account's ID:

   ```sql
   insert into public.saved_articles (user_id, pmid)
   values ((select id from auth.users where email = 'your@email.com'), 99999999);
   ```

   Reload the dashboard. The Saved tab shows a "Not in the current list" section
   with `[Article no longer in current list]`, PMID 99999999, and a PubMed link.
   Remove it afterwards by clicking its ★ Saved button.

---

## 5. Limitations and what to revisit at scale

**Works now:** accounts, login that survives refreshes, per-user saved lists,
account isolation, and articles that drop out of the weekly dataset handled
without breaking.

**Known limitations:**

- **No password reset in the UI.** Reset emails go through the same rate-limited
  built-in sender, so adding the button before connecting a real email provider
  would mostly produce emails that never arrive. For now a forgotten password
  means deleting the user under Authentication → Users and having them sign up
  again. Add the reset flow at the same time you add SMTP.
- **Email confirmation is off,** so addresses are unverified. See section 1.
- **The free tier pauses a project after about a week with no activity.** A
  paused project makes login fail until you resume it from the dashboard. Real
  weekly use prevents this, but a quiet month will not.
- **No sharing or annotation.** Saves are private, with no notes, tags, or
  folders. Those are natural Phase 3 features and all fit the same table.
- **Rebuild and re-upload is still manual.** Setting up the auto-publish task
  (already on the PedEndoLit TASKS.md list, needs the repo URL and a token) would
  remove the weekly upload step and matters more now that people depend on the
  site being current.

**One open item:** MEMORY.md still records the GitHub repo as "to be filled in
once Christian creates it," and no Pages URL is written down anywhere in the
workspace. Nothing above needs it, because with email confirmation off Supabase
never sends a link that has to point back at the site. You will need it the
moment you turn confirmation on or add password reset, so it is worth recording
the URL in MEMORY.md now.
