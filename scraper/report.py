"""Writes research/top10.md from data/analysis.json. All text is derived from scraped data; missing = stated as missing."""
import json
from collections import Counter
from pathlib import Path

a = json.loads(Path("data/analysis.json").read_text(encoding="utf-8"))
stats, cand = a["stats"], a["top"]

top, per_brand = [], Counter()
for m in cand:                       # max 3 per brand so the list is not one brand
    if per_brand[m["brand"]] < 3:
        top.append(m); per_brand[m["brand"]] += 1
    if len(top) == 10:
        break

raw = json.loads(Path("data/raw_offers.json").read_text(encoding="utf-8"))
L = []
L += ["# Top 10 best buy: samostojeći mikseri (predloženo 18. 11. 2026.)", "",
      "**Ovo je prijedlog za tvoj pregled.** Dodaj, makni ili zamijeni modele prije Faze 4.", ""]
L += ["## Mid range (izračunato iz podataka)", "",
      f"- Uzorak: {stats['n_models']} različitih stand mixer modela (varijante boja grupirane), najniža cijena po modelu.",
      f"- Min {stats['min']:.0f} EUR, 25. percentil {stats['p25']:.0f}, medijan {stats['median']:.0f}, "
      f"75. percentil {stats['p75']:.0f}, 90. percentil {stats['p90']:.0f}, max {stats['max']:.0f} EUR.",
      f"- **Mid range = 35. do 75. percentil = {stats['p35']:.0f} do {stats['p75']:.0f} EUR.**",
      "- Obrazloženje: ispod 35. percentila su uglavnom jeftini azijski/privatni brendovi s nejasnim motorom; "
      "iznad 75. percentila je premium (KitchenAid Heavy Duty, Smeg, Bosch MUM9), gdje se cijena ne opravdava "
      "dodatnom snagom za tijesto.", ""]
L += ["## Kako je izračunat dough score (0 do 100)", "",
      "Težine: snaga motora 35 %, kapacitet 30 %, metalno kućište ili zupčanici 20 %, planetarno miješanje 15 %.", "",
      "- Snaga: `min(W / 1500, 1)`. Kapacitet: `dough_kg / 2,5` ako je naveden, inače `litre posude / 6`.",
      "- Metal: 1 ako opis navodi metalno kućište ili metalne zupčanike. Planetarno: 1 ako opis navodi.",
      "- **Podatak koji nedostaje se ne računa kao nula**, nego se score računa samo iz poznatih dijelova. "
      "Stupac *potpunost* (0 do 1) pokazuje koliko težina je pokriveno. Odabrani modeli imaju potpunost ≥ 0,65.",
      "- **Ograničenje:** specifikacije dolaze iz opisa ponuda na Nabavi i shopovima, ne od proizvođača. "
      "Nedostaje težina i vrsta prijenosa za većinu modela. Specifikacije proizvođača još nisu dopunjene.",
      "- **Upozorenje o KitchenAidu:** navedena snaga (300 W) nije usporediva s indukcijskim/AC motorima drugih brendova, "
      "ali taj ugrađeni DC motor ovdje nisam mogao korigirati iz podataka, pa KitchenAid dobiva nizak score. "
      "Nije nužno loš za tijesto. Ako želiš, dodaj ga ručno.", ""]
L += ["## Stvarni popust i lažni popusti", "",
      "- **Povijest cijena nemamo:** Jeftinije.hr je blokiran, a Nabavina putanja povijesti zabranjena je robots.txt-om. "
      "Povijest gradimo sami od ovog runa.",
      "- Zato stvarni popust računam na dva načina: (1) prema Omnibus cijeni (najniža u 30 dana) ondje gdje je shop "
      "objavljuje, (2) najniža cijena u odnosu na medijan svih shopova (samo kad ima ≥ 3 ponuda).",
      "- Lažni popust: označavam ako je precrtana cijena (bez Omnibus oznake) više od 20 % iznad medijana ostalih shopova.", ""]
L += ["## Pokrivenost izvora", "",
      "- **Izravno provjereno:** Harvey Norman (adapter). Links, Elipso, Instar, Mikronis: adapteri rade, ali njihove kategorije "
      "miksera sadrže gotovo samo ručne miksere (praktički nula stand mixera).",
      "- **Preko usporednika (Nabava.net, `verified_direct = false`):** gotovo sve ostalo, uključujući Big Bang, Ronis, Mall.hr, "
      "eKupi, Euronics. **Cijenu provjeri na shopu prije kupnje.**",
      "- **Nikako (blokirano, ne zaobilazimo):** Jeftinije.hr, Pevex, Bauhaus, Lesnina. Big Bang i Ronis samo preko Nabave.", ""]

L += ["## Top 10", ""]
L += ["| # | Model | Min cijena | Shop | Dough | Potpunost | Vrijednost (bod/100 EUR) | Shopova |", "|---|---|---|---|---|---|---|---|"]
for i, m in enumerate(top, 1):
    L.append(f"| {i} | {m['name'][:50]} | {m['min_price']:.2f} € | {m['best']['shop']} | {m['dough_score']} | "
             f"{m['completeness']} | {m['value']} | {m['n_shops']} |")
L.append("")
for i, m in enumerate(top, 1):
    sp = m["specs"]
    pros, cons = [], []
    if sp.get("power_w"):
        (pros if sp["power_w"] >= 1000 else cons).append(f"motor {sp['power_w']} W")
    if sp.get("bowl_l"):
        (pros if sp["bowl_l"] >= 4.5 else cons).append(f"posuda {sp['bowl_l']} l")
    if sp.get("planetary"):
        pros.append("planetarno miješanje")
    else:
        cons.append("planetarno miješanje nije navedeno u izvoru")
    if sp.get("body") == "metal" or sp.get("metal_gears"):
        pros.append("metalno kućište/zupčanici (iz opisa)")
    else:
        cons.append("materijal kućišta/prijenosa nije potvrđen")
    d = m["disc"]
    disc = []
    if d["vs_omnibus_pct"] is not None:
        disc.append(f"{d['vs_omnibus_pct']} % ispod Omnibus cijene (30 dana)")
    if d["vs_market_median_pct"] is not None:
        disc.append(f"{d['vs_market_median_pct']} % ispod medijana {m['n_shops']} shopova")
    if d["fake_discount"]:
        disc.append("⚠️ moguć lažni popust: " + d["fake_note"])
    offers = ", ".join(f"{o['shop']} {o['price']:.2f} €" for o in m["offers"][:3])
    L += [f"### {i}. {m['name']}", "",
          f"- **Zašto:** dough score {m['dough_score']} uz najnižu cijenu {m['min_price']:.2f} € "
          f"({m['value']} bodova na 100 €). Varijante: {', '.join(m['variants'][:6]) or 'nepoznato'}.",
          f"- **Prednosti:** {'; '.join(pros) or 'nema podatka'}.",
          f"- **Nedostaci / nepoznato:** {'; '.join(cons) or '-'}.",
          f"- **Najjeftinije:** {offers}. "
          + ("Izravno provjereno." if m["direct_shops"] else "Cijena preko Nabave, provjeri na shopu."),
          f"- **Popust:** {'; '.join(disc) or 'nema pouzdane reference za stvarni popust'}.", ""]
Path("research/top10.md").write_text("\n".join(L), encoding="utf-8")
print(len(top), "u top 10")
for m in top:
    print(m["name"][:50], m["min_price"])
