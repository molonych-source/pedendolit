-- PedEndoLit Phase 2: personal saved-article lists
--
-- Paste this entire file into the Supabase SQL Editor and press Run.
-- It is safe to run more than once: it drops and recreates the policies
-- rather than erroring on a second run.
--
-- Only PMIDs are stored here. Article titles, abstracts, and everything else
-- stay in the weekly pedendolit-data.json, so nothing has to be kept in sync.

-- 1. The table -------------------------------------------------------------
create table if not exists public.saved_articles (
  id       uuid        primary key default gen_random_uuid(),
  user_id  uuid        not null default auth.uid()
                       references auth.users (id) on delete cascade,
  pmid     bigint      not null,
  saved_at timestamptz not null default now(),
  -- one row per article per person, so a double click cannot create duplicates
  unique (user_id, pmid)
);

-- Makes "show me my list, newest first" a single index lookup.
create index if not exists saved_articles_user_saved_at_idx
  on public.saved_articles (user_id, saved_at desc);

-- 2. Row-Level Security ----------------------------------------------------
-- Without this line every signed-in user could read every other user's list.
alter table public.saved_articles enable row level security;

-- auth.uid() is the ID of whoever is making the request. Each policy below
-- says: this row is only visible or writable if it belongs to that person.
drop policy if exists saved_articles_select_own on public.saved_articles;
create policy saved_articles_select_own
  on public.saved_articles for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists saved_articles_insert_own on public.saved_articles;
create policy saved_articles_insert_own
  on public.saved_articles for insert
  to authenticated
  with check (auth.uid() = user_id);

drop policy if exists saved_articles_update_own on public.saved_articles;
create policy saved_articles_update_own
  on public.saved_articles for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists saved_articles_delete_own on public.saved_articles;
create policy saved_articles_delete_own
  on public.saved_articles for delete
  to authenticated
  using (auth.uid() = user_id);

-- 3. Permissions -----------------------------------------------------------
-- Signed-in users get table access, still filtered by the policies above.
-- Signed-out visitors (the "anon" role) are never granted anything, so a
-- logged-out browser cannot read the table at all.
grant select, insert, update, delete on public.saved_articles to authenticated;


-- ==========================================================================
-- Checks you can run afterwards (paste and Run in the SQL Editor)
-- ==========================================================================

-- Is RLS actually switched on? rowsecurity must be true.
--   select relname, relrowsecurity as rowsecurity
--   from pg_class where relname = 'saved_articles';

-- Which policies exist? Expect four rows.
--   select policyname, cmd from pg_policies
--   where tablename = 'saved_articles' order by cmd;

-- Who has signed up?
--   select id, email, created_at from auth.users order by created_at desc;

-- Everyone's saves at once. Only the SQL Editor can see this, because it runs
-- as the database owner and bypasses RLS. This is the view you use to confirm
-- the two test accounts really did save to separate rows.
--   select u.email, s.pmid, s.saved_at
--   from public.saved_articles s join auth.users u on u.id = s.user_id
--   order by s.saved_at desc;
