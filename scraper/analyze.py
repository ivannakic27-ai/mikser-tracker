"""Phase 3: stand-mixer filter, mid range, dough score, value, real discount, top 10."""
import csv, json, re, statistics as st
from pathlib import Path
from .normalize import build, norm_shop
from .common import POS_MODEL

ACCESSORY = re.compile(r"zdjela|posuda|nastavak|dodatak|pribor|mlin za|adapter|rezervn|kuka za|metlica|set za|"
                       r"štapn|stapn|ručni|rucni|blender|sjeckalic|sokovnik|toster|friteza|\bMCM?\d|\bKH[CH]\d|multitalent|food processor", re.I)
BAD_BRAND = {"Planetarni", "Zdjela", "Kuhinjski", "Mikser", "Robot"}

# --- dough score: weights over components that are actually known (missing = excluded, completeness reported)
W = {"power": 0.35, "capacity": 0.30, "metal": 0.20, "planetary": 0.15}


def dough_score(sp):
    comp = {}
    if sp.get("power_w"):
        comp["power"] = min(sp["power_w"] / 1500, 1.0)
    if sp.get("dough_kg"):
        comp["capacity"] = min(sp["dough_kg"] / 2.5, 1.0)
    elif sp.get("bowl_l"):
        comp["capacity"] = min(sp["bowl_l"] / 6.0, 1.0)
    if sp.get("body") == "metal" or sp.get("metal_gears"):
        comp["metal"] = 1.0
    if sp.get("planetary"):
        comp["planetary"] = 1.0
    if "power" not in comp and "capacity" not in comp:
        return None, 0.0
    wsum = sum(W[k] for k in comp)
    score = sum(W[k] * v for k, v in comp.items()) / wsum * 100
    # unknown components are NOT counted as zero, but low completeness is shown and used as a filter
    return round(score, 1), round(wsum, 2)


def is_stand_mixer(m):
    if ACCESSORY.search(m["name"]) or m["brand"] in BAD_BRAND:
        return False
    text = " ".join(f"{o['name']} {o.get('description') or ''}" for o in m["offers"])
    sp = m["specs"]
    if sp.get("planetary") or POS_MODEL.search(m["name"]):
        return (sp.get("bowl_l") or 0) >= 3 or bool(POS_MODEL.search(m["name"]))
    return bool(re.search(r"stand mixer|za tijesto", text, re.I)) and (sp.get("bowl_l") or 0) >= 3


def real_discount(m):
    """Return (best offer, real_discount_pct vs reference, reference kind, fake flag)."""
    offers = m["offers"]
    best = offers[0]
    others = [o["price"] for o in offers[1:]]
    out = {"vs_market_median_pct": None, "vs_omnibus_pct": None, "fake_discount": False, "fake_note": ""}
    if len(offers) >= 3:
        med = st.median(o["price"] for o in offers)
        out["vs_market_median_pct"] = round((med - best["price"]) / med * 100, 1)
    om = [o for o in offers if o.get("lowest_30d")]
    if om:
        o = min(om, key=lambda x: x["price"])
        out["vs_omnibus_pct"] = round((o["lowest_30d"] - o["price"]) / o["lowest_30d"] * 100, 1)
    # inflated "old" price: struck price that no shop currently charges anything near
    for o in offers:
        if o.get("old_price") and not o.get("lowest_30d") and len(offers) >= 3:
            med = st.median(x["price"] for x in offers if x is not o)
            if o["old_price"] > 1.2 * med and o.get("declared_discount_pct", 0) >= 10:
                out["fake_discount"] = True
                out["fake_note"] = f"{o['shop']}: stara {o['old_price']:.0f} EUR vs medijan ostalih {med:.0f} EUR"
    return best, out


def main():
    models = [m for m in build() if is_stand_mixer(m)]
    for m in models:
        m["dough_score"], m["completeness"] = dough_score(m["specs"])
        m["best"], m["disc"] = real_discount(m)
    models = [m for m in models if m["dough_score"] is not None]
    prices = sorted(m["min_price"] for m in models)
    q = lambda p: prices[int(p * (len(prices) - 1))]
    lo, hi = q(0.35), q(0.75)
    for m in models:
        m["value"] = round(m["dough_score"] / m["min_price"] * 100, 2)   # points per 100 EUR
        m["mid_range"] = lo <= m["min_price"] <= hi
        m["direct_shops"] = sorted({o["shop"] for o in m["offers"] if o["verified_direct"]})
    cand = [m for m in models if m["mid_range"] and m["completeness"] >= 0.65 and m["n_shops"] >= 2
            and m["dough_score"] >= 55]
    cand.sort(key=lambda m: -m["value"])
    stats = {"n_models": len(models), "p35": lo, "p75": hi, "median": st.median(prices),
             "min": prices[0], "max": prices[-1], "p25": q(.25), "p90": q(.90), "n_candidates": len(cand)}
    Path("data/analysis.json").write_text(json.dumps({"stats": stats, "top": cand[:25]}, ensure_ascii=False, indent=1,
                                                      default=list), encoding="utf-8")
    Path("research").mkdir(exist_ok=True)
    with open("research/all_models_scores.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["model_id", "brand", "name", "min_price_eur", "n_shops", "cheapest_shop", "power_w", "bowl_l",
                    "planetary", "metal", "dough_score", "completeness", "value_per_100eur", "mid_range",
                    "vs_market_median_pct", "vs_omnibus_pct", "fake_discount", "direct_shops"])
        for m in sorted(models, key=lambda m: m["min_price"]):
            sp = m["specs"]
            w.writerow([m["model_id"], m["brand"], m["name"], m["min_price"], m["n_shops"], m["best"]["shop"],
                        sp.get("power_w"), sp.get("bowl_l"), sp.get("planetary"),
                        bool(sp.get("body") == "metal" or sp.get("metal_gears")), m["dough_score"],
                        m["completeness"], m["value"], m["mid_range"], m["disc"]["vs_market_median_pct"],
                        m["disc"]["vs_omnibus_pct"], m["disc"]["fake_discount"], "|".join(m["direct_shops"])])
    print(json.dumps(stats))
    for i, m in enumerate(cand[:15], 1):
        print(i, m["name"][:45], m["min_price"], m["best"]["shop"], m["dough_score"], m["completeness"], m["value"],
              m["n_shops"], m["disc"])


if __name__ == "__main__":
    main()
