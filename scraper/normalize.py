"""Merge direct + comparison-site offers into models (model_id) with offers; compute stats and dough score.

Matching: EAN > MPN > brand + normalised model. Colour variants of KitchenAid (5KSM175PSE<colour>) are
grouped into one model family with several variants.
"""
import json, re, statistics as st
from collections import Counter, defaultdict
from pathlib import Path

MPN_RE = re.compile(r"\b(\d?[A-Z]{1,5}\d[A-Z0-9./-]{3,})\b")
KA_RE = re.compile(r"^(5KSM\d{2,3}(?:PS|CX|CP)?)E[A-Z]{2,3}$")
SM_RE = re.compile(r"^(SMF\d{2})[A-Z]{2,3}EU$")
KW_RE = re.compile(r"^(KMX\d{3})A?[A-Z]{2,3}$")
BRANDS = ["KitchenAid", "Kenwood", "Bosch", "Smeg", "Tefal", "Philips", "Gorenje", "Sencor", "Electrolux",
          "Severin", "Klarstein", "Ravanson", "Westinghouse", "Cecotec", "Russell Hobbs", "Morphy Richards",
          "Siemens", "Eldom", "Ruhhy", "Bergner", "Elit", "Esperanza", "Vertenz", "Hisense", "Candy", "Beko",
          "Teesa", "Mesko", "Adler", "Zelmer", "Vox", "Concept", "Rohnson", "Lauben", "ProfiCook", "Quigg"]


def find_brand(name):
    low = name.lower()
    for b in BRANDS:
        if b.lower() in low:
            return b
    return name.split()[0].title()


def find_mpn(name):
    cands = [m for m in MPN_RE.findall(name.upper()) if re.search(r"[A-Z]", m) and re.search(r"\d", m)]
    cands = [c for c in cands if c not in ("220-240V",)]
    return max(cands, key=len) if cands else None


def model_key(name, ean=None):
    brand = find_brand(name)
    mpn = find_mpn(name)
    if ean:
        return f"ean:{ean}", brand, mpn, mpn
    if not mpn:
        norm = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return f"name:{norm}", brand, None, None
    fam = mpn
    if brand == 'KitchenAid' and mpn.startswith('KA5'):
        mpn = fam = mpn[2:]
    if (m := KA_RE.match(mpn)):
        fam = m.group(1)
    if (m := SM_RE.match(mpn)):
        fam = m.group(1)
    if (m := KW_RE.match(mpn)):
        fam = m.group(1)
    return f"{brand.lower()}-{re.sub(r'[^a-z0-9]', '', fam.lower())}", brand, fam, mpn


def norm_shop(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace(".hr", ""))


def mode(vals):
    vals = [v for v in vals if v is not None]
    return Counter(vals).most_common(1)[0][0] if vals else None


def build(nabava_json="data/nabava_products.json", direct_json="data/raw_offers.json"):
    models = {}

    def add(offer, name):
        key, brand, fam, mpn = model_key(name)
        m = models.setdefault(key, {"model_id": key, "brand": brand, "mpn_family": fam, "name": name,
                                    "variants": set(), "offers": [], "spec_votes": defaultdict(list)})
        if mpn:
            m["variants"].add(mpn)
        # prefer the shortest descriptive name seen
        if len(name) < len(m["name"]) and brand.lower() in name.lower():
            m["name"] = name
        m["offers"].append(offer)
        for k, v in (offer.get("specs") or {}).items():
            if k != "stand_mixer_guess":
                m["spec_votes"][k].append(v)

    if Path(nabava_json).exists():
        for p in json.loads(Path(nabava_json).read_text(encoding="utf-8")):
            for o in p["offers"]:
                add(o, p["name"])
    if Path(direct_json).exists():
        d = json.loads(Path(direct_json).read_text(encoding="utf-8"))
        for o in d["offers"]:
            if not o["specs"].get("stand_mixer_guess"):
                continue
            add(o, o["name"])

    out = []
    for m in models.values():
        # direct offer replaces the comparison-site offer of the same shop
        direct_shops = {norm_shop(o["shop"]) for o in m["offers"] if o["verified_direct"]}
        offers = [o for o in m["offers"] if o["verified_direct"] or norm_shop(o["shop"]) not in direct_shops]
        offers = [o for o in offers if o.get("price")]
        if not offers:
            continue
        offers.sort(key=lambda o: o["price"])
        specs = {k: mode(v) for k, v in m["spec_votes"].items()}
        out.append({"model_id": m["model_id"], "brand": m["brand"], "mpn_family": m["mpn_family"],
                    "name": m["name"], "variants": sorted(m["variants"]), "specs": specs,
                    "offers": offers, "min_price": offers[0]["price"],
                    "n_shops": len({norm_shop(o["shop"]) for o in offers}),
                    "median_price": st.median(o["price"] for o in offers)})
    return out


if __name__ == "__main__":
    ms = build()
    Path("data/models.json").write_text(json.dumps(ms, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(ms), "modela")
