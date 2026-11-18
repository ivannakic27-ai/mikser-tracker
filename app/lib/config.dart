// Supabase URL and the PUBLISHABLE (anon) key are public by design: access is enforced by RLS,
// so only the signed-in owner can read/write. Never put the secret/service key in the app.
// Override at build time with --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_ANON_KEY=...
const supabaseUrl = String.fromEnvironment('SUPABASE_URL',
    defaultValue: 'https://kyvnlitfaenuuwrgeqzj.supabase.co');
const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY',
    defaultValue: 'sb_publishable_Sft-iNHEweqGyrD_VqxO7w_ZDgddVzd');
