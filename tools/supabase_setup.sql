-- Shadow Road online Arena: run this once in your Supabase project (SQL Editor -> New query -> Run).
-- Players may ADD ghosts/scores and READ them. Nobody can change or delete anything through the API.

create table if not exists public.ghosts (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player     text not null check (char_length(player) between 1 and 40),
  name       text not null check (char_length(name) between 1 and 16),
  cls        text not null check (cls in ('samurai', 'ninja', 'kunoichi', 'onmyoji', 'sohei')),
  round      int  not null check (round between 1 and 20),
  wins       int  not null check (wins between 0 and 10),
  losses     int  not null check (losses between 0 and 5),
  version    text not null check (char_length(version) <= 16),
  build      jsonb not null check (pg_column_size(build) < 12000)
);
create index if not exists ghosts_lookup on public.ghosts (version, round, created_at desc);

create table if not exists public.scores (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player     text not null check (char_length(player) between 1 and 40),
  name       text not null check (char_length(name) between 1 and 16),
  cls        text not null check (cls in ('samurai', 'ninja', 'kunoichi', 'onmyoji', 'sohei')),
  wins       int  not null check (wins between 0 and 10),
  hearts     int  not null check (hearts between 0 and 5),
  rounds     int  not null check (rounds between 1 and 20),
  version    text not null check (char_length(version) <= 16)
);
create index if not exists scores_board on public.scores (version, wins desc, hearts desc, created_at);

alter table public.ghosts enable row level security;
alter table public.scores enable row level security;

drop policy if exists "read ghosts" on public.ghosts;
drop policy if exists "add ghosts" on public.ghosts;
drop policy if exists "read scores" on public.scores;
drop policy if exists "add scores" on public.scores;
create policy "read ghosts" on public.ghosts for select to anon using (true);
create policy "add ghosts"  on public.ghosts for insert to anon with check (true);
create policy "read scores" on public.scores for select to anon using (true);
create policy "add scores"  on public.scores for insert to anon with check (true);

grant select, insert on public.ghosts, public.scores to anon;

-- Optional housekeeping (run by hand now and then): keep only the newest 30 days of ghosts.
-- delete from public.ghosts where created_at < now() - interval '30 days';
