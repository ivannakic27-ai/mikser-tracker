-- Black Friday mixer tracker: schema + RLS.
-- Scraper writes with the service_role key (bypasses RLS). The app signs in as the owner (Supabase Auth)
-- and only that user can read/write. Anyone else (including anon key holders) gets nothing.

create table if not exists models (
  model_id      text primary key,
  brand         text,
  name          text not null,
  mpn_family    text,
  variants      text[] default '{}',
  specs         jsonb  default '{}',
  spec_sources  jsonb  default '{}',      -- which source each spec came from
  dough_score   numeric,
  completeness  numeric,
  best_buy_note text,
  nabava_urls   text[] default '{}',
  tracked       boolean not null default false,
  created_at    timestamptz default now()
);

create table if not exists offers (
  id                    bigserial primary key,
  model_id              text not null references models(model_id) on delete cascade,
  shop                  text not null,
  url                   text,
  source                text not null default 'direct',   -- direct | nabava | jeftinije | newsletter
  verified_direct       boolean not null default true,
  price                 numeric,
  old_price             numeric,
  lowest_30d            numeric,
  declared_discount_pct numeric,
  availability          text,
  shipping              numeric,
  last_seen             timestamptz default now(),
  unique (model_id, shop, source)
);

create table if not exists scrape_runs (
  id          bigserial primary key,
  started_at  timestamptz default now(),
  finished_at timestamptz,
  slot        text,                     -- morning | evening | manual
  status      text,                     -- ok | partial | failed
  details     jsonb default '{}'        -- per adapter: status, count, error
);

create table if not exists price_snapshots (
  id          bigserial primary key,
  run_id      bigint references scrape_runs(id) on delete set null,
  model_id    text not null references models(model_id) on delete cascade,
  shop        text not null,
  source      text not null default 'direct',
  price       numeric not null,
  old_price   numeric,
  lowest_30d  numeric,
  availability text,
  fetched_at  timestamptz default now()
);
create index if not exists price_snapshots_model_time on price_snapshots (model_id, fetched_at desc);

create table if not exists user_thresholds (
  model_id         text primary key references models(model_id) on delete cascade,
  target_price     numeric,
  min_discount_pct numeric,
  alerts_enabled   boolean not null default true,
  paused           boolean not null default false
);

create table if not exists alerts (
  id          bigserial primary key,
  model_id    text references models(model_id) on delete cascade,
  shop        text,
  rule        text not null,            -- new_low | bigger_discount | below_threshold | fake_discount | daily_top
  price       numeric,
  message     text,
  dedupe_key  text unique,              -- same alert for same offer/price is never sent twice
  sent_at     timestamptz default now(),
  telegram_ok boolean
);

create table if not exists settings (
  key   text primary key,
  value jsonb
);

-- ---------- RLS: only the owner ----------
-- After creating your Supabase user, set its UUID here (Authentication > Users):
--   select set_config('app.owner', '<UUID>', false);  -- or just replace the placeholder below
create or replace function is_owner() returns boolean language sql stable as $$
  select auth.uid() = 'c832a665-53b4-4491-a06e-f65dbc607b06'::uuid
$$;

do $$
declare t text;
begin
  foreach t in array array['models','offers','scrape_runs','price_snapshots','user_thresholds','alerts','settings']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists owner_all on %I', t);
    execute format('create policy owner_all on %I for all to authenticated using (is_owner()) with check (is_owner())', t);
  end loop;
end $$;
-- No policy for role anon => anon key alone can neither read nor write.
