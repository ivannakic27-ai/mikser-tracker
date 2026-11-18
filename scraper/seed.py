"""Builds data/tracked_models.json (approved top 20) from research/top20.csv + scraped data.
Also writes supabase/seed.sql-free JSON; `pipeline --init` loads it into the store."""
import csv, json
from pathlib import Path
from .normalize import build
from .analyze import dough_score

top = list(csv.DictReader(open("research/top20.csv", encoding="utf-8-sig"), delimiter=";"))
ref_url = {p["ref"]: p["url"] for p in json.loads(Path("data/nabava_products.json").read_text(encoding="utf-8"))}
models = {m["model_id"]: m for m in build()}

out = []
for r in top:
    m = models[r["model_id"]]
    refs = sorted({o["product_ref"] for o in m["offers"] if o.get("product_ref")})
    score, comp = dough_score(m["specs"])
    out.append({
        "model_id": m["model_id"], "brand": m["brand"], "name": m["name"], "mpn_family": m["mpn_family"],
        "variants": m["variants"], "specs": m["specs"],
        "spec_sources": {k: "opis ponude (Nabava.net/shop)" for k in m["specs"]},
        "dough_score": score, "completeness": comp,
        "nabava_urls": [ref_url[x] for x in refs if x in ref_url],
        "tracked": True, "suggested_target": float(r["suggested_target"]),
        "best_buy_note": f"Rang {r['rank_pos']}, dough score {score}, najniža cijena u analizi {r['min_price']} EUR "
                         f"({r['cheapest_shop']}).",
    })
Path("data/tracked_models.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "praćenih modela;", sum(len(m["nabava_urls"]) for m in out), "Nabava stranica")
