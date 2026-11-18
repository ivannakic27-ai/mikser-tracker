"""Top 20 with a wider price range (35th to 90th percentile) -> research/top20.md + research/top20.csv"""
import csv, statistics as st
from collections import Counter
from pathlib import Path
from .normalize import build
from .analyze import is_stand_mixer, dough_score, real_discount

models = [m for m in build() if is_stand_mixer(m)]
for m in models:
    m["dough_score"], m["completeness"] = dough_score(m["specs"])
    m["best"], m["disc"] = real_discount(m)
models = [m for m in models if m["dough_score"] is not None]
prices = sorted(m["min_price"] for m in models)
q = lambda p: prices[int(p * (len(prices) - 1))]
LO, OLD_HI, HI = q(0.35), q(0.75), q(0.90)
for m in models:
    m["value"] = round(m["dough_score"] / m["min_price"] * 100, 2)
    m["direct_shops"] = sorted({o["shop"] for o in m["offers"] if o["verified_direct"]})

cand = [m for m in models if LO <= m["min_price"] <= HI and m["completeness"] >= 0.65
        and m["n_shops"] >= 2 and m["dough_score"] >= 55]


def pct_rank(vals, v):
    return sum(x <= v for x in vals) / len(vals)


vs, ss = [m["value"] for m in cand], [m["dough_score"] for m in cand]
for m in cand:   # composite: half value-for-money, half raw dough score (so stronger, pricier models can enter)
    m["rank"] = round(0.5 * pct_rank(vs, m["value"]) + 0.5 * pct_rank(ss, m["dough_score"]), 3)
cand.sort(key=lambda m: -m["rank"])

top, per_brand = [], Counter()
for m in cand:
    if per_brand[m["brand"]] < 4:
        top.append(m); per_brand[m["brand"]] += 1
    if len(top) == 20:
        break


def target(m):
    """Suggested target price: the lower of (current min - 5 %) and (market median - 15 %), never below 70 % of min."""
    t = min(m["min_price"] * 0.95, m["median_price"] * 0.85)
    return round(max(t, m["min_price"] * 0.70), 0)


L = ["# Top 20 best buy (proširen cjenovni raspon), prijedlog za pregled", "",
     "## Predloženi raspon cijena", "",
     f"- Raniji mid range: {LO:.0f} do {OLD_HI:.0f} EUR (35. do 75. percentil).",
     f"- **Predlažem proširenje na {LO:.0f} do {HI:.0f} EUR** (35. do 90. percentil, {len(cand)} modela prolazi filtere).",
     f"- Razlog: iznad {OLD_HI:.0f} EUR tržište još ima modele sa stvarno jačim motorom i većom posudom; "
     f"90. percentil ({HI:.0f} EUR) odsijeca premium segment (KitchenAid Heavy Duty, Smeg, Bosch MUM9 i skuplje).",
     "- Rang više nije samo \"bodova po euru\" (to favorizira jeftine): **rang = 50 % vrijednost za novac + 50 % sirovi dough score**, "
     "pa skuplji jači modeli mogu ući. Najviše 4 modela po brendu.",
     "- **Ciljna cijena (prijedlog)** = niža od (trenutna najniža − 5 %) i (medijan shopova − 15 %), ali ne ispod 70 % trenutne. "
     "Ti je kasnije mijenjaš po modelu.",
     "- Popust: Omnibus (najniža u 30 dana) gdje shop objavljuje, inače usporedba s medijanom shopova. "
     "Povijesti cijena nema (vidi top10.md).", ""]
L += ["| # | Model | Min cijena | Shop | Dough | Rang | Popust | Ciljna cijena | Shopova |", "|---|---|---|---|---|---|---|---|---|"]
rows = []
for i, m in enumerate(top, 1):
    d = m["disc"]
    disc = []
    if d["vs_omnibus_pct"] is not None:
        disc.append(f"{d['vs_omnibus_pct']}% vs Omnibus")
    if d["vs_market_median_pct"] is not None:
        disc.append(f"{d['vs_market_median_pct']}% vs medijan")
    if d["fake_discount"]:
        disc.append("⚠️ moguć lažni")
    m["target"] = target(m)
    L.append(f"| {i} | {m['name'][:48]} | {m['min_price']:.2f} € | {m['best']['shop']} | {m['dough_score']} | {m['rank']} | "
             f"{', '.join(disc) or 'nema reference'} | {m['target']:.0f} € | {m['n_shops']} |")
    sp = m["specs"]
    rows.append([i, m["model_id"], m["name"], m["min_price"], m["best"]["shop"], sp.get("power_w"), sp.get("bowl_l"),
                 m["dough_score"], m["completeness"], m["value"], m["rank"], d["vs_omnibus_pct"],
                 d["vs_market_median_pct"], d["fake_discount"], m["target"], m["n_shops"],
                 "da" if m["direct_shops"] else "ne (preko usporednika)"])
L += ["", "## Modeli s najzanimljivijim popustom", ""]
good = sorted([m for m in top if (m["disc"]["vs_omnibus_pct"] or 0) >= 10 or (m["disc"]["vs_market_median_pct"] or 0) >= 12],
              key=lambda m: -max(m["disc"]["vs_omnibus_pct"] or 0, m["disc"]["vs_market_median_pct"] or 0))
for m in good:
    d = m["disc"]
    L.append(f"- **{m['name']}**: {m['min_price']:.2f} € ({m['best']['shop']}); "
             f"{d['vs_omnibus_pct'] if d['vs_omnibus_pct'] is not None else '-'}% ispod Omnibus, "
             f"{d['vs_market_median_pct'] if d['vs_market_median_pct'] is not None else '-'}% ispod medijana.")
L += ["", "## Detalji", ""]
for i, m in enumerate(top, 1):
    sp = m["specs"]
    offers = ", ".join(f"{o['shop']} {o['price']:.0f} €" for o in m["offers"][:3])
    L.append(f"{i}. **{m['name']}**, snaga {sp.get('power_w', '?')} W, posuda {sp.get('bowl_l', '?')} l, "
             f"planetarno {'da' if sp.get('planetary') else 'nije navedeno'}, "
             f"metal {'da' if (sp.get('body') == 'metal' or sp.get('metal_gears')) else 'nije potvrđeno'}. Najjeftinije: {offers}. "
             + ("" if m["direct_shops"] else "Cijene preko Nabave: provjeri na shopu."))
Path("research/top20.md").write_text("\n".join(L), encoding="utf-8")
with open("research/top20.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["rank_pos", "model_id", "name", "min_price", "cheapest_shop", "power_w", "bowl_l", "dough_score",
                "completeness", "value_per_100eur", "rank_score", "vs_omnibus_pct", "vs_market_median_pct",
                "fake_discount", "suggested_target", "n_shops", "verified_direct"])
    w.writerows(rows)
print(f"range {LO}-{HI}, cand {len(cand)}")
for i, m in enumerate(top, 1):
    print(i, m["name"][:42], m["min_price"], m["dough_score"], m["rank"], m["disc"]["vs_omnibus_pct"], m["disc"]["vs_market_median_pct"], m["target"])
