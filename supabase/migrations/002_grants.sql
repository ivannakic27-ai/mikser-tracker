-- Table privileges for the Data API roles. Newer Supabase projects do not auto-grant these on tables created via SQL.
-- RLS (001_init.sql) still decides WHICH rows each role can see:
--   service_role  = scraper (bypasses RLS)
--   authenticated = the app after sign-in (RLS allows only the owner UUID)
--   anon          = gets NO privileges at all
grant usage on schema public to service_role, authenticated;

grant all on all tables in schema public to service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to service_role, authenticated;

revoke all on all tables in schema public from anon;

-- Same for tables created later
alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public grant usage, select on sequences to service_role, authenticated;
