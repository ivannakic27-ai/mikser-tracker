"""Telegram bot commands, polled at the start of every run (so replies can take up to ~12 h; GitHub Actions has no
always-on process). Only the configured chat id is obeyed."""
from .store import get_setting, set_setting
from .telegram import esc


def _find(models, q):
    q = q.lower()
    hits = [m for m in models if q in m["name"].lower() or q in m["model_id"].lower()]
    return hits


def process(store, tg):
    offset = get_setting(store, "tg_offset")
    for u in tg.updates(offset):
        set_setting(store, "tg_offset", u["update_id"] + 1)
        msg = u.get("message") or {}
        if str((msg.get("chat") or {}).get("id")) != str(tg.chat_id):
            continue
        parts = (msg.get("text") or "").split()
        if not parts:
            continue
        cmd, args = parts[0].split("@")[0].lower(), parts[1:]
        models = [m for m in store.select("models") if m.get("tracked")]
        if cmd == "/pauza":
            set_setting(store, "paused", True); tg.send("⏸ Praćenje pauzirano. /nastavi za nastavak.")
        elif cmd == "/nastavi":
            set_setting(store, "paused", False); set_setting(store, "stopped", False); tg.send("▶️ Praćenje nastavljeno.")
        elif cmd == "/stop":
            set_setting(store, "stopped", True); tg.send("⏹ Praćenje zaustavljeno (scraper preskače runove). /nastavi za ponovno.")
        elif cmd == "/status":
            runs = sorted(store.select("scrape_runs"), key=lambda r: str(r.get("started_at")))[-1:]
            r = runs[0] if runs else None
            tg.send(f"Status: {'pauzirano' if get_setting(store, 'paused') or get_setting(store, 'stopped') else 'aktivno'}\n"
                    f"Praćenih modela: {len(models)}\nZadnji run: {r['started_at'] if r else 'nema'} ({r['status'] if r else '-'})")
        elif cmd == "/top":
            snap = store.select("offers")
            best = {}
            for o in snap:
                if o.get("price") and (o["model_id"] not in best or o["price"] < best[o["model_id"]]["price"]):
                    best[o["model_id"]] = o
            names = {m["model_id"]: m["name"] for m in models}
            lines = [f"{esc(names[k][:36])}: {v['price']:.2f} € ({esc(v['shop'])})"
                     for k, v in sorted(best.items(), key=lambda kv: kv[1]["price"]) if k in names][:10]
            tg.send("<b>Najjeftinije trenutno</b>\n" + ("\n".join(lines) or "nema podataka"))
        elif cmd == "/prag" and len(args) >= 2:
            try:
                price = float(args[-1].replace(",", "."))
            except ValueError:
                tg.send("Format: /prag <dio naziva modela> <cijena>"); continue
            hits = _find(models, " ".join(args[:-1]))
            if len(hits) != 1:
                tg.send("Našao " + str(len(hits)) + " modela, budi precizniji: " + ", ".join(esc(h["name"][:25]) for h in hits[:5]))
                continue
            store.insert("user_thresholds", [{"model_id": hits[0]["model_id"], "target_price": price}], key=("model_id",))
            tg.send(f"🎯 Prag za {esc(hits[0]['name'])}: {price:.2f} €")
        else:
            tg.send("Komande: /status /top /prag &lt;model&gt; &lt;cijena&gt; /pauza /nastavi /stop")
