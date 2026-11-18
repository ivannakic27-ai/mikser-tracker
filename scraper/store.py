"""Storage layer. SupabaseStore (PostgREST over httpx, service_role key) and LocalStore (JSON file, for dry runs/tests)."""
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx

TABLES = ["models", "offers", "scrape_runs", "price_snapshots", "user_thresholds", "alerts", "settings"]
now = lambda: datetime.now(timezone.utc)


class LocalStore:
    """Same interface as SupabaseStore, backed by data/local_db.json."""

    def __init__(self, path="data/local_db.json"):
        self.path = Path(path)
        self.db = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {t: [] for t in TABLES}
        self._id = 1 + max([r.get("id", 0) for t in TABLES for r in self.db.get(t, [])] or [0])

    def _save(self):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.db, ensure_ascii=False, default=str), encoding="utf-8")

    def select(self, table, **eq):
        return [r for r in self.db[table] if all(r.get(k) == v for k, v in eq.items())]

    def insert(self, table, rows, key=None):
        """Insert rows; if key (tuple of columns) is given, upsert on it. Returns inserted/updated rows."""
        out = []
        for r in rows:
            r = dict(r)
            ts = {"price_snapshots": "fetched_at", "scrape_runs": "started_at", "alerts": "sent_at"}.get(table)
            if ts:
                r.setdefault(ts, now().isoformat())   # DB default in Supabase
            if key:
                ex = next((x for x in self.db[table] if all(x.get(k) == r.get(k) for k in key)), None)
                if ex:
                    ex.update(r); out.append(ex); continue
            if table != "settings" and table != "models" and table != "user_thresholds":
                r.setdefault("id", self._id); self._id += 1
            self.db[table].append(r); out.append(r)
        self._save()
        return out

    def since(self, table, field, delta):
        cut = (now() - delta).isoformat()
        return [r for r in self.db[table] if str(r.get(field, "")) >= cut]


def _check(r):
    """raise_for_status, but with the response body (Supabase error text) and no secrets."""
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase {r.request.method} {r.request.url.path} -> HTTP {r.status_code}: {r.text[:300]}")


class SupabaseStore:
    def __init__(self, url=None, key=None):
        self.url = (url or os.environ["SUPABASE_URL"]).rstrip("/") + "/rest/v1"
        key = key or os.environ["SUPABASE_SERVICE_KEY"]
        headers = {"apikey": key, "Content-Type": "application/json"}
        if not key.startswith("sb_"):          # legacy JWT service_role key; new sb_secret_ keys are not JWTs
            headers["Authorization"] = f"Bearer {key}"
        self.c = httpx.Client(headers=headers, timeout=30)

    def select(self, table, **eq):
        params = {"select": "*", **{k: f"eq.{str(v).lower() if isinstance(v, bool) else v}" for k, v in eq.items()}}
        r = self.c.get(f"{self.url}/{table}", params=params)
        _check(r)
        return r.json()

    def insert(self, table, rows, key=None):
        if not rows:
            return []
        headers = {"Prefer": "return=representation" + (",resolution=merge-duplicates" if key else "")}
        params = {"on_conflict": ",".join(key)} if key else {}
        r = self.c.post(f"{self.url}/{table}", params=params, headers=headers, content=json.dumps(rows, default=str))
        _check(r)
        return r.json()

    def since(self, table, field, delta):
        cut = (now() - delta).isoformat()
        r = self.c.get(f"{self.url}/{table}", params={"select": "*", field: f"gte.{cut}", "limit": "100000"})
        _check(r)
        return r.json()


def get_store(dry=False):
    return LocalStore() if dry or not os.environ.get("SUPABASE_URL") else SupabaseStore()


def get_setting(store, key, default=None):
    r = store.select("settings", key=key)
    return r[0]["value"] if r else default


def set_setting(store, key, value):
    store.insert("settings", [{"key": key, "value": value}], key=("key",))
