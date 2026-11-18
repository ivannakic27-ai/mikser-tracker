# Faza 1: HR webshopovi sa samostojećim mikserima

Provjera od 18. 11. 2026. (curl s običnim browser UA, bez zaobilaženja zaštita). "Provjereno" = stvarno dohvaćeno; "Nije provjereno" = ne tvrdim ništa.

## Sažetak odluka

| Shop | Status | Težina | Adapter |
|---|---|---|---|
| Harvey Norman | OK, statički HTML, Omnibus tekst na stranici | Laka | DA |
| Big Bang (=Sancta Domenica, preusmjerava) | OK, statički HTML | Laka | DA |
| Ronis | OK, statički HTML + JSON-LD | Laka | DA |
| Links | OK, HTML (cijene se u listingu nisu našle regexom, treba provjera) | Srednja | DA |
| Elipso | OK, HTML, Omnibus tekst prisutan | Laka | DA |
| Instar Informatika | OK, HTML, Omnibus tekst; kategorija je "Blenderi i mikseri" (nije potvrđeno ima li stand mixere) | Srednja | Vjerojatno |
| Mikronis | OK, HTML, Omnibus tekst; nema KitchenAid/Kenwood | Laka | Vjerojatno (niski prioritet) |
| Nabava.net | Dostupan (200), robots dopušta kategorije | Srednja | DA (širok pregled) |
| Bosch Home HR | Dostupan (200), samo službeni katalog | Srednja | Za specifikacije |
| Kenwood World HR | Dostupan, robots blokira samo neke botove | Srednja | Za specifikacije |
| KitchenAid HR | Dostupan (200) | Nije ispitano | Za specifikacije |
| Mall.hr | **403 na automatski zahtjev** | Blokiran | NE (vidi dolje) |
| Pevex | **403 na automatski zahtjev** | Blokiran | NE |
| Jeftinije.hr | **Cloudflare izazov ("Just a moment")** | Blokiran | NE |
| eKupi | **WAF "Request Rejected"** | Blokiran | NE |
| Bauhaus | 403 | Blokiran | NE |
| Lesnina (XXXLesnina) | 403 | Blokiran | NE |
| Kaufland HR | Dostupan (200), ali moja pretraga vratila 404; URL treba naći | Nepoznato | Kasnije |
| Spar/Interspar | Dostupan, URL pretrage 404; nije nađen | Nepoznato | Kasnije |
| Emmezeta | Dostupan, kategorija miksera nije nađena | Nepoznato | Kasnije |
| Klarstein HR | Dostupan (200) | Nije ispitano | Opcionalno |

## Važni problemi koje trebaš znati

1. **Jeftinije.hr je iza Cloudflare izazova.** Prema pravilima koje sam si postavio ne zaobilazim bot zaštite, pa ga ne mogu scrapati. Povijest cijena s njega nije dostupna.
2. **Nabava.net:** `robots.txt` dopušta kategorije i stranice proizvoda, ali **zabranjuje `/product/priceHistory`**. Dakle ne mogu dohvaćati njihov graf povijesti. Kategorije i trenutne ponude po shopu su dopuštene.
3. **Mall.hr i Pevex** (dva najveća izvora u rezultatima pretrage) vraćaju 403 običnom HTTP klijentu. To je najvjerojatnije zaštita od botova. Ne zaobilazim je. Mogući izlazi: (a) preskočiti, (b) provjeriti postoji li službeni partnerski feed/XML, (c) ti ručno dodaš ponude u aplikaciji. Mall.hr ipak ima javno vidljive cijene u pretrazi, pa je gubitak velik; reci kako želiš.
4. **Povijest cijena:** bez Jeftinije.hr i Nabava priceHistory, jedina povijest je ona koju gradimo sami (2× dnevno od sada) + Omnibus "najniža cijena u 30 dana" gdje je shop prikazuje. Do Black Fridaya (9 dana) imamo oko 18 snimaka, što je malo za pouzdano otkrivanje lažnih popusta. Omnibus podatak je tu ključan.

## Detalji po shopu

### Harvey Norman — https://www.harveynorman.hr
- Kategorija: `/mali-kucanski-aparati/aparati-za-pripremu-hrane/kuhinjski-roboti-multipraktici/kuhinjski-roboti`
- Dohvat: statički HTML (Magento), 1 JSON-LD blok. Našao KitchenAid (22 pojavljivanja) i Kenwood (28).
- Omnibus: DA, tekst "30 dana prije provođenja posebnog oblika prodaje: ..." uz proizvode.
- robots.txt: zabranjuje parametre sortiranja/filtera (`product_list_order`, `cat=` ...) i `/catalogsearch/`. Kategorije bez tih parametara su dopuštene. Paginaciju treba provjeriti (`?p=2` nije zabranjen, ali potvrdi pri izradi adaptera).
- Težina: laka.

### Big Bang — https://www.bigbang.hr (sancta-domenica.hr preusmjerava ovamo)
- Kategorija: `/mali-kucanski-aparati/priprema-hrane/kuhinjski-roboti/`
- Dohvat: statički HTML, velika stranica (1,4 MB), 1 JSON-LD. Puno Kenwooda (96) i KitchenAida (16).
- Omnibus: nije jasno vidljiv na listingu (1 pojavljivanje); provjeri na stranici proizvoda.
- robots.txt: ima `User-agent: *` pravila; nisam pročitao sva (treba još pregledati prije produkcije).
- Težina: laka.

### Ronis — https://www.ronis.hr
- Kategorija: `/hr/mali-kucanski-aparati/kuhinjski-roboti-i-mutlipraktici` (pravopisna greška u URL-u je njihova)
- Dohvat: statički HTML + JSON-LD. KitchenAid (41), Kenwood (11).
- Omnibus: nejasno (2 pojavljivanja).
- robots.txt: samo sitemap, bez zabrana.
- Težina: laka.

### Links — https://www.links.hr
- Kategorija: `/hr/mikseri-040103`
- Dohvat: HTML, mala stranica (155 KB), cijene regexom nisu pronađene u listingu, moguće se učitavaju JS-om ili u drugom formatu. **Treba pregledati ručno.**
- KitchenAid (27), Kenwood 0 na ovoj stranici.
- Težina: srednja.

### Elipso — https://www.elipso.hr
- Kategorija: `/mali-kucanski/mikseri/`
- Dohvat: HTML, 44 cijene u HTML-u, Omnibus tekst prisutan. Nema KitchenAida na toj stranici (možda drugdje).
- robots.txt: zabranjuje `?sort=`, `?filter=`, `?page=`. **Paginacija preko `?page=` je zabranjena**, pa treba drugi način (npr. veći broj po stranici ako postoji ili pojedinačne kategorije).
- Težina: laka do srednja.

### Instar Informatika — https://www.instar-informatika.hr
- Kategorija: `/blenderi-i-mikseri/2078/`
- Dohvat: HTML, 3 JSON-LD bloka, Omnibus tekst prisutan. Cijene regexom nisu pronađene (drugačiji format). Nema KitchenAida/Kenwooda na toj stranici, pa možda nema stand mixera ili su u drugoj kategoriji. **Nije potvrđeno.**
- Težina: srednja.

### Mikronis — https://www.mikronis.hr
- Kategorija: `/katalog/kucanski-aparati/mali-kucanski-aparati/mikseri/`
- Dohvat: HTML, 28 cijena, Omnibus tekst. Bez KitchenAida/Kenwooda; vjerojatno jeftiniji brendovi.
- Težina: laka, niski prioritet.

### Nabava.net — https://www.nabava.net/mikseri
- Dohvat: statički HTML, 3 JSON-LD bloka. Filteri po snazi (`/mikseri/1200-w?se=...`) pa se snaga može dobiti iz URL-a filtera.
- robots.txt: zabranjeno `/out.php`, `/out-proxy`, `/product/priceHistory`, `/product/priceAlarm`. Dozvoljene kategorije i stranice proizvoda.
- Uloga: pregled tržišta i otkrivanje shopova (nabava lista Harvey Norman, Techmall, Elipso itd.). Cijenu za odluku uzimamo izravno iz shopa.
- Težina: srednja. Bez povijesti cijena (zabranjena putanja).

### Službeni brendovi
- **Bosch Home:** `https://www.bosch-home.hr/hr/mkt-category-page/kuhinjski-roboti`, 200, robots dopušta. Za specifikacije (snaga, kapacitet).
- **Kenwood World:** `https://www.kenwoodworld.com/hr-hr/...`, robots blokira samo pojedine botove (trendictionbot, 360Spider...). Podaci o modelima (npr. KMX750AAR, KAT71 Chef XL) postoje. Točan URL kategorije treba još naći (moj prvi pogodak je 404).
- **KitchenAid HR:** `https://www.kitchenaid.hr/` dostupan; `kitchenaid.eu/hr-hr` vraća 403.

### Ostali pronađeni u pretrazi (nisu još ispitani)
- Tia mobiteli (`tia-mobiteli.hr`, KitchenAid Artisan), Favi (`favi.hr`, Tefal), Klarstein HR, Mimovrste (slovenski, ne HR), Techmall (preko Nabave).

## Nisam potvrdio / ostaje otvoreno
- Kaufland, Spar/Interspar, Emmezeta: dostupni, ali nisam našao URL kategorije/pretrage.
- Paginacija ni za jedan shop još nije testirana.
- Pune robots.txt datoteke za Big Bang, Links, Instar, Ronis nisam pročitao do kraja.
- Uvjeti korištenja (ToS) shopova nisu pregledani. To treba napraviti prije produkcije.

## Preporuka za Fazu 2
Krenuti s adapterima: **Harvey Norman, Big Bang, Ronis, Elipso, Links** (+ Nabava.net za otkrivanje), zatim Instar i Mikronis. Mall.hr/Pevex samo ako nađemo dozvoljen način (feed).
