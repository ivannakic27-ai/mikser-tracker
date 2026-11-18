# Black Friday praćenje cijena samostojećih miksera

Sustav prati 20 odabranih samostojećih miksera na hrvatskim shopovima, 2× dnevno (oko 07:00 i 19:00, Europe/Zagreb),
sprema cijene u Supabase i šalje Telegram alarme. Flutter Android aplikacija (`app/`) čita i piše u Supabase.

## Arhitektura

```
GitHub Actions (cron 2×/dan)
   └─ python -m scraper.pipeline
        ├─ Nabava.net: stranice modela (sve ponude svih shopova)       -> source=nabava, verified_direct=false
        ├─ Harvey Norman: izravno                                      -> source=direct, verified_direct=true
        ├─ pravila alarma (alerts.py) -> Telegram (dedupe u tablici alerts)
        ├─ upis u Supabase (offers, price_snapshots, scrape_runs, alerts)
        └─ JSON snapshot u data/snapshots/ (commit u repo kao sigurnosna kopija)
Supabase (Postgres + RLS)  <── Flutter app (čita/piše pragove, popis praćenih modela)
```

Poštovanje shopova: robots.txt se provjerava, pauze 1,5 do 3 s, retry s backoffom. **Ne zaobilazimo CAPTCHA ni zaštite od botova.**
Ako shop vrati 403/Cloudflare, adapter se preskače, run se označi u `scrape_runs` i stiže Telegram upozorenje.
Preskočeni izvori: Jeftinije.hr, Big Bang, Ronis, Mall.hr, Pevex (cijene Big Banga/Ronisa/Malla dolaze preko Nabave i označene su
„preko usporednika, provjeri na shopu prije kupnje").

## Postavljanje (jednom)

### 1. GitHub repozitorij
1. Napravi **privatni** repozitorij (npr. `mikser-tracker`) i učitaj sadržaj ove mape u njega.
2. Settings → Actions → General → Workflow permissions → **Read and write permissions** (treba za snapshot commit).

### 2. Supabase
1. Napravi projekt na supabase.com (besplatni plan).
2. Authentication → Users → **Add user** (tvoj e-mail + lozinka). Kopiraj **UUID** tog korisnika.
3. U `supabase/migrations/001_init.sql` UUID vlasnika je već upisan u SQL (provjeri da odgovara korisniku u Authentication → Users).
4. SQL Editor → zalijepi cijeli `001_init.sql` → Run.
5. Project Settings → API: zapiši **Project URL**, **service_role key** (tajni, samo za GitHub Secrets) i **anon key** (za aplikaciju).
   RLS je uključen: samo prijavljeni vlasnik može čitati i pisati, anon ključ sam ne može ništa.

### 3. Telegram bot
1. U Telegramu otvori **@BotFather** → `/newbot` → zadaj ime i korisničko ime (mora završavati na `bot`) → dobiješ **token**.
2. Otvori svog novog bota i pošalji mu `/start` (bez toga ti ne može pisati).
3. chat_id: u pregledniku otvori `https://api.telegram.org/bot<TOKEN>/getUpdates` i u JSON-u nađi `"chat":{"id": 123456789`.
   Taj broj je tvoj **chat_id**. (Ne dijeli token ni na jednom javnom mjestu.)

### 4. GitHub Secrets
Settings → Secrets and variables → Actions → New repository secret:

| Naziv | Vrijednost |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | service_role key |
| `TELEGRAM_BOT_TOKEN` | token iz BotFathera |
| `TELEGRAM_CHAT_ID` | tvoj chat_id |

Token i ključevi ne idu u kod ni u Supabase tablice. (Bot token namjerno nije u bazi, samo u GitHub Secrets.)

### 5. Pokretanje
1. Actions → **scrape** → Run workflow → `action = init` (učitava 20 modela i prijedloge ciljnih cijena u Supabase).
2. Actions → **scrape** → Run workflow → `action = run`, `slot = evening` (prvi run + poruka „Top ponuda dana").
3. Dalje radi sam: cron u 05:00/06:00 i 17:00/18:00 UTC, a Python propušta samo run kad je u Zagrebu 07:xx ili 19:xx
   (zbog ljetnog/zimskog računanja vremena).

Prvi run samo postavlja bazu cijena: alarmi „novi najniži" i „veći popust" počinju od drugog runa.

## Alarmi

| Ikona | Pravilo |
|---|---|
| 🔥 | model je na najnižoj cijeni u zadnjih 90 dana (od našeg praćenja) |
| 📉 | cijena u shopu pala ≥ 2 % ili ≥ 5 € od prošlog runa |
| 🎯 | cijena ≤ ciljna cijena ili stvarni popust ≥ tvoj prag (`user_thresholds`) |
| ⚠️ | „stara" cijena (bez Omnibus oznake) > 120 % medijana ostalih shopova ili vlastite povijesti |
| 🏆 | večernja poruka s najboljom ponudom i rangom svih 20 modela |

Isti alarm za istu ponudu i cijenu ne šalje se dvaput (`alerts.dedupe_key`).
Stvarni popust se računa prema Omnibus „najnižoj cijeni u 30 dana" ako je shop prikazuje, inače prema našoj povijesti.

Bot komande (provjeravaju se na početku svakog runa, pa odgovor može kasniti do ~12 h): `/status`, `/top`, `/prag <model> <cijena>`,
`/pauza`, `/nastavi`, `/stop`.

## Dodavanje novog shopa
1. Napravi `scraper/adapters/<shop>.py` s klasom koja nasljeđuje `Adapter` (`scrape(fetcher) -> list[Offer]`).
2. Provjeri robots.txt i uvjete korištenja; koristi `Fetcher` (robots, pauze, retry). Ako vrati `Blocked`, ne zaobilazi.
3. U `scraper/pipeline.py` (`scrape_tracked`) pozovi adapter i spoji ponude na `model_id` preko `normalize.model_key`.

## Lokalno testiranje (bez Supabasea i Telegrama)
```bash
pip install -r scraper/requirements.txt
python -m scraper.pipeline --init --dry
python -m scraper.pipeline --dry --slot evening
```
`--dry` koristi `data/local_db.json` i ispisuje Telegram poruke u konzolu.

## Istraživanje
`research/shops.md`, `research/search_terms.md`, `research/top10.md`, `research/top20.md`, `research/top20.csv`,
`research/all_models_scores.csv`.

## Poznata ograničenja
- Nema povijesti cijena prije početka praćenja (Jeftinije.hr blokiran, Nabavin `/product/priceHistory` zabranjen robots.txt-om).
- Specifikacije dolaze iz opisa ponuda, ne od proizvođača; dough score je izračunat samo iz poznatih podataka.
- Dostupnost s Nabave je samo ikona (šifra), ne tekst.

## Android aplikacija (APK)

Ekrani: Pregled (kartice praćenih modela), Detalj (graf povijesti po shopu, ponude, specifikacije, link na shop), Usporedba (2 do 3 modela),
Svi mikseri (filteri + "dodaj u praćenje"), Pragovi i postavke, Povijest alarma. Material 3, tamna tema, hrvatski, pull-to-refresh,
offline prikaz zadnjih podataka. Prijava e-mailom i lozinkom korisnika iz Supabasea (RLS: samo vlasnik).

**Build i preuzimanje:** Actions → **build-apk** → Run workflow. Nakon ~10 min: repo → **Releases** → zadnji "Mikser tracker APK" → `app-release.apk`.

**Instalacija na mobitel:**
1. Otvori Releases na mobitelu i preuzmi `app-release.apk`.
2. Android će pitati za dopuštenje: Postavke → dopusti instalaciju iz nepoznatih izvora za preglednik (ili aplikaciju Datoteke).
3. Otvori preuzetu datoteku → Instaliraj. Ako Play Protect upozori (aplikacija nije potpisana za Play Store), odaberi "Instaliraj svejedno".
4. Prijavi se e-mailom i lozinkom iz Supabase → Authentication → Users.

Konfiguracija: `app/lib/config.dart` (Supabase URL i **publishable** ključ; javni po dizajnu, zaštitu daje RLS). Secret/service ključ nikad ne ide u aplikaciju.
Android projekt se generira u workflowu (`flutter create`), pa nije u repozitoriju.
Nakon prvog `init` u bazi je i ~110 ostalih modela (`tracked=false`) za ekran "Svi mikseri"; kad ih dodaš u praćenje,
scraper ih uzima pri sljedećem runu.
