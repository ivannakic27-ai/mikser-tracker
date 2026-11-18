"""Scheduled pipeline: scrape tracked models -> alerts -> store -> JSON snapshot.

  python -m scraper.pipeline --init                 load data/tracked_models.json into the store
  python -m scraper.pipeline --scheduled            used by the cron (only runs at 07:xx / 19:xx Europe/Zagreb)
  python -m scraper.pipeline --slot manual          run now
  python -m scraper.pipeline --dry                  local JSON store + print Telegram messages
Never bypasses blocks: 403/Cloudflare => adapter skipped, noted in scrape_runs, Telegram warning.
"""
import argparse, json, logging, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .common import Fetcher, Blocked
from .normalize import model_key, norm_shop
from .adapters.nabava import Nabava, ROOT
from .adapters.harveynorman import HarveyNorman
from .store import get_store, get_setting
from .telegram import Telegram
from . import alerts, commands

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)   # httpx logs full URLs (Telegram URL contains the bot token)
log = logging.getLogger("pipeline")
TRACKED = Path("data/tracked_models.json")


def init_store(store):
    for m in json.loads(TRACKED.read_text(encoding="utf-8")):
        target = m.pop("suggested_target", None)
        store.insert("models", [m], key=("model_id",))
        if not store.select("user_thresholds", model_id=m["model_id"]):
            store.insert("user_thresholds", [{"model_id": m["model_id"], "target_price": target,
                                              "alerts_enabled": True, "paused": False}], key=("model_id",))
    extra = Path("data/all_models.json")
    if extra.exists():       # all other stand mixers: visible in the app, tracked=false until you add them
        d = json.loads(extra.read_text(encoding="utf-8"))
        for i in range(0, len(d["models"]), 100):
            store.insert("models", d["models"][i:i + 100], key=("model_id",))
        for i in range(0, len(d["offers"]), 200):
            store.insert("offers", d["offers"][i:i + 200], key=("model_id", "shop", "source"))
    log.info("inicijalizirano %d modela", len(store.select("models")))


def health(store, tg, adapter, msg):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"health:{adapter}:{day}"
    if not store.select("alerts", dedupe_key=key):
        ok = tg.send(f"⚠️ <b>Scraper za {adapter} je pokvaren</b>\n{msg}\nNe zaobilazim blokade; nastavljam s ostalim izvorima.")
        store.insert("alerts", [{"rule": "health", "shop": adapter, "message": msg, "dedupe_key": key, "telegram_ok": ok}])


def scrape_tracked(models, f, store, tg):
    """Returns ({model_id: [offer dict]}, details)."""
    by_model = {m["model_id"]: [] for m in models}
    details = {}
    # --- Nabava: only the product pages of tracked models
    nab, ok, failed = Nabava(), 0, []
    urls = [(m["model_id"], u) for m in models for u in (m.get("nabava_urls") or [])]
    for mid, url in urls:
        try:
            href = url.replace(ROOT, "")
            p = nab.parse_product(f.get(url), href, url)
            by_model[mid] += [o.to_dict() for o in p["offers"]]
            ok += 1
        except Blocked as e:
            failed.append(str(e)[:80]); break          # blocked: stop hitting the site
        except Exception as e:
            failed.append(str(e)[:80])
    n_off = sum(len(v) for v in by_model.values())
    status = "ok" if ok and n_off and len(failed) <= len(urls) * 0.3 else ("blocked" if any("bot protection" in x or "robots" in x for x in failed) else "broken")
    details["Nabava.net"] = {"status": status, "pages_ok": ok, "pages_failed": len(failed), "offers": n_off, "errors": failed[:3]}
    if status != "ok":
        health(store, tg, "Nabava.net", f"status={status}, stranica ok={ok}/{len(urls)}, ponuda={n_off}")
    # --- Harvey Norman direct (listing pages), matched to tracked models by normalised model key
    try:
        hv = HarveyNorman().scrape(f)
        matched = 0
        for o in hv:
            key = model_key(o.name)[0]
            if key in by_model:
                by_model[key].append(o.to_dict()); matched += 1
        details["Harvey Norman"] = {"status": "ok" if hv else "broken", "listed": len(hv), "matched": matched}
        if not hv:
            health(store, tg, "Harvey Norman", "0 rezultata (promijenjena struktura stranice?)")
    except Blocked as e:
        details["Harvey Norman"] = {"status": "blocked", "error": str(e)[:100]}
        health(store, tg, "Harvey Norman", str(e)[:100])
    except Exception as e:
        details["Harvey Norman"] = {"status": "error", "error": str(e)[:100]}
        health(store, tg, "Harvey Norman", str(e)[:100])
    # direct offer replaces the comparison-site offer of the same shop
    for mid, offs in by_model.items():
        direct = {norm_shop(o["shop"]) for o in offs if o["verified_direct"]}
        by_model[mid] = [o for o in offs if o["verified_direct"] or norm_shop(o["shop"]) not in direct]
    return by_model, details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--scheduled", action="store_true")
    ap.add_argument("--slot", default="manual")
    ap.add_argument("--no-commands", action="store_true")
    a = ap.parse_args()
    store, tg = get_store(a.dry), Telegram(a.dry)
    if a.init:
        return init_store(store)

    slot = a.slot
    if a.scheduled:
        zg = datetime.now(ZoneInfo("Europe/Zagreb"))
        slot = "morning" if zg.hour in (7, 8) else "evening" if zg.hour in (19, 20) else None
        recent = [r for r in store.select("scrape_runs")
                  if r.get("status") in ("ok", "partial")
                  and datetime.fromisoformat(str(r["started_at"]).replace("Z", "+00:00")) > datetime.now(timezone.utc) - timedelta(hours=5)]
        if slot is None or recent:
            log.info("izvan termina (Zagreb %02d:xx) ili je run već odrađen; preskačem", zg.hour); return

    if not a.no_commands:
        commands.process(store, tg)
    if get_setting(store, "paused") or get_setting(store, "stopped"):
        log.info("praćenje pauzirano/zaustavljeno; preskačem scrape"); return

    models = [m for m in store.select("models") if m.get("tracked")]
    thresholds = {t["model_id"]: t for t in store.select("user_thresholds")}
    run = store.insert("scrape_runs", [{"slot": slot, "status": "running"}])[0]
    f = Fetcher(delay=(1.5, 3.0))
    by_model, details = scrape_tracked(models, f, store, tg)

    alerts.evaluate(store, tg, models, by_model, thresholds, slot)     # uses history from BEFORE this run

    snaps, offers = [], []
    for mid, offs in by_model.items():
        for o in offs:
            snaps.append({"run_id": run["id"], "model_id": mid, "shop": o["shop"], "source": o["source"], "price": o["price"],
                          "old_price": o.get("old_price"), "lowest_30d": o.get("lowest_30d"), "availability": o.get("availability")})
            offers.append({"model_id": mid, "shop": o["shop"], "source": o["source"], "url": o["url"],
                           "verified_direct": o["verified_direct"], "price": o["price"], "old_price": o.get("old_price"),
                           "lowest_30d": o.get("lowest_30d"), "declared_discount_pct": o.get("declared_discount_pct"),
                           "availability": o.get("availability"), "last_seen": datetime.now(timezone.utc).isoformat()})
    # de-duplicate (model, shop, source): keep the cheapest
    uniq = {}
    for o in offers:
        k = (o["model_id"], o["shop"], o["source"])
        if k not in uniq or o["price"] < uniq[k]["price"]:
            uniq[k] = o
    store.insert("offers", list(uniq.values()), key=("model_id", "shop", "source"))
    for i in range(0, len(snaps), 500):
        store.insert("price_snapshots", snaps[i:i + 500])
    bad = [k for k, v in details.items() if v["status"] != "ok"]
    status = "failed" if len(bad) == len(details) else "partial" if bad else "ok"
    run.update({"status": status, "details": details, "finished_at": datetime.now(timezone.utc).isoformat()})
    store.insert("scrape_runs", [run], key=("id",))

    out = Path("data/snapshots"); out.mkdir(parents=True, exist_ok=True)
    (out / f"{datetime.now(timezone.utc):%Y-%m-%d_%H%M}.json").write_text(
        json.dumps({"run": run, "offers": list(uniq.values())}, ensure_ascii=False, default=str), encoding="utf-8")
    log.info("run %s: %s, %d ponuda, %d modela", run["id"], status, len(uniq), len(models))
    if status == "failed":
        sys.exit(1)      # make the GitHub job red when every source failed


if __name__ == "__main__":
    main()
