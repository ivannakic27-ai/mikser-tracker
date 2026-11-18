"""Alert rules evaluated after every run. History is read BEFORE the current snapshots are stored."""
import statistics as st
from datetime import datetime, timezone, timedelta
from .telegram import esc

MIN_DROP_PCT, MIN_DROP_EUR = 2.0, 5.0
FALSE_MARGIN = 1.2


def _t(row):
    return datetime.fromisoformat(str(row["fetched_at"]).replace("Z", "+00:00"))


def _eur(x):
    return f"{x:.2f} €" if x is not None else "?"


def real_ref(offer, hist_shop, days=30):
    """Reference for 'real' discount: shop's Omnibus 30-day low if given, else own min price in our history."""
    if offer.get("lowest_30d"):
        return offer["lowest_30d"], "Omnibus 30 dana"
    cut = datetime.now(timezone.utc) - timedelta(days=days)
    prices = [h["price"] for h in hist_shop if _t(h) >= cut]
    return (min(prices), "naša povijest 30 dana") if prices else (None, None)


def fmt(rule_icon, title, model, o, hist_shop):
    ref, kind = real_ref(o, hist_shop)
    real = f"{(ref - o['price']) / ref * 100:.1f}% ispod ({kind}: {_eur(ref)})" if ref and ref > o["price"] else \
        ("nema stvarnog popusta vs " + kind if ref else "nema reference za stvarni popust")
    lines = [f"{rule_icon} <b>{esc(title)}</b>", f"<b>{esc(model['name'])}</b>",
             f"Shop: {esc(o['shop'])}", f"Cijena: <b>{_eur(o['price'])}</b>"
             + (f" (stara: {_eur(o['old_price'])})" if o.get("old_price") else ""),
             f"Stvarni popust: {real}", f"Dostupnost: {esc(o.get('availability') or 'nepoznato')}"]
    if not o.get("verified_direct", True):
        lines.append("<i>Cijena preko usporednika, provjeri na shopu prije kupnje.</i>")
    lines.append(f"Link: {esc(o.get('url') or '')}")
    return "\n".join(lines)


def evaluate(store, tg, models, offers_by_model, thresholds, slot, dry=False):
    """models: tracked model rows. offers_by_model: {model_id: [offer dict]} from THIS run."""
    sent = []

    def emit(rule, model, o, text, key):
        if store.select("alerts", dedupe_key=key):
            return
        ok = tg.send(text)
        store.insert("alerts", [{"model_id": model["model_id"], "shop": o["shop"] if o else None, "rule": rule,
                                 "price": o["price"] if o else None, "message": text, "dedupe_key": key,
                                 "telegram_ok": ok}])
        sent.append((rule, model["model_id"]))

    for m in models:
        th = thresholds.get(m["model_id"], {})
        if th.get("paused") or th.get("alerts_enabled") is False:
            continue
        cur = [o for o in offers_by_model.get(m["model_id"], []) if o.get("price")]
        if not cur:
            continue
        hist = store.select("price_snapshots", model_id=m["model_id"])
        by_shop = {}
        for h in hist:
            by_shop.setdefault((h["shop"], h.get("source", "direct")), []).append(h)
        best = min(cur, key=lambda o: o["price"])

        # 1. new all-time / 90-day low (needs a baseline)
        cut90 = datetime.now(timezone.utc) - timedelta(days=90)
        prev = [h["price"] for h in hist if _t(h) >= cut90]
        if prev and best["price"] < min(prev):
            emit("new_low", m, best, fmt("🔥", "Novi najniži iznos", m, best,
                 by_shop.get((best["shop"], best["source"]), [])), f"new_low:{m['model_id']}:{best['price']:.2f}")

        for o in cur:
            hs = by_shop.get((o["shop"], o["source"]), [])
            last = max(hs, key=_t) if hs else None
            # 2. bigger discount / price drop vs previous run (noise filter: >=2% or >=5 EUR)
            if last and last["price"] > o["price"]:
                drop = last["price"] - o["price"]
                if drop >= MIN_DROP_EUR or drop / last["price"] * 100 >= MIN_DROP_PCT:
                    emit("bigger_discount", m, o, fmt("📉", f"Veći popust (−{drop:.2f} € od prošlog runa)", m, o, hs),
                         f"bigger_discount:{m['model_id']}:{o['shop']}:{o['price']:.2f}")
            # 3. below my threshold
            ref, _ = real_ref(o, hs)
            real_pct = (ref - o["price"]) / ref * 100 if ref and ref > o["price"] else 0
            hit_price = th.get("target_price") and o["price"] <= th["target_price"]
            hit_pct = th.get("min_discount_pct") and real_pct >= th["min_discount_pct"]
            if hit_price or hit_pct:
                emit("below_threshold", m, o, fmt("🎯", "Ispod tvog praga", m, o, hs),
                     f"below_threshold:{m['model_id']}:{o['shop']}:{o['price']:.2f}")
            # 4. fake discount: struck price (not an Omnibus value) above what others charge / our own history
            if o.get("old_price") and not o.get("lowest_30d"):
                others = [x["price"] for x in cur if x is not o]
                own_max = max([h["price"] for h in hs], default=None)
                inflated_vs_market = len(others) >= 2 and o["old_price"] > FALSE_MARGIN * st.median(others)
                inflated_vs_own = own_max is not None and len(hs) >= 4 and o["old_price"] > FALSE_MARGIN * own_max
                if (inflated_vs_market or inflated_vs_own) and (o["old_price"] - o["price"]) / o["old_price"] >= 0.10:
                    emit("fake_discount", m, o, fmt("⚠️", "Sumnjiv popust (napuhana stara cijena)", m, o, hs),
                         f"fake_discount:{m['model_id']}:{o['shop']}:{o['price']:.2f}:{o['old_price']:.2f}")

    # 5. evening top offer + short rank of all tracked models
    if slot in ("evening", "manual-top"):
        rows = []
        for m in models:
            cur = [o for o in offers_by_model.get(m["model_id"], []) if o.get("price")]
            if cur and m.get("dough_score"):
                b = min(cur, key=lambda o: o["price"])
                rows.append((m["dough_score"] / b["price"] * 100, m, b))
        rows.sort(key=lambda r: -r[0])
        if rows:
            _, m0, b0 = rows[0]
            text = [f"🏆 <b>Top ponuda dana</b>: {esc(m0['name'])} za <b>{_eur(b0['price'])}</b> ({esc(b0['shop'])})", "",
                    "<b>Rang (dough score po cijeni):</b>"]
            text += [f"{i}. {esc(m['name'][:34])} — {_eur(b['price'])} ({esc(b['shop'])})"
                     for i, (_, m, b) in enumerate(rows, 1)]
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            emit("daily_top", m0, b0, "\n".join(text), f"daily_top:{day}")
    return sent
