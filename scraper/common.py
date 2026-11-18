"""Shared types and helpers for all shop adapters."""
from __future__ import annotations
import re, time, random, urllib.robotparser
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


@dataclass
class Offer:
    shop: str
    url: str
    name: str
    brand: str | None = None
    mpn: str | None = None
    ean: str | None = None
    price: float | None = None
    old_price: float | None = None
    declared_discount_pct: float | None = None
    lowest_30d: float | None = None       # only if shop states Omnibus 30-day lowest
    anchor_text: str | None = None        # raw reference-price text shown by shop
    availability: str | None = None
    shipping: float | None = None
    description: str | None = None
    specs: dict = field(default_factory=dict)
    rating: float | None = None
    reviews: int | None = None
    seller: str | None = None
    source: str = "direct"                # direct | nabava | jeftinije | newsletter
    verified_direct: bool = True          # False = price via comparison site, verify on shop
    product_ref: str | None = None        # comparison-site product id/url (for grouping)
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self):
        return asdict(self)


def parse_price(text: str | None) -> float | None:
    """'1.299,00 EUR' / '229,90' / '299 EUR' -> float. Returns None if no number."""
    if not text:
        return None
    m = re.search(r"\d[\d.\s]*(?:,\d{1,2})?", text.replace("\xa0", " "))
    if not m:
        return None
    s = m.group(0).strip().replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


class Blocked(Exception):
    pass


class Fetcher:
    """Polite HTTP client: robots.txt check, delay, retry with backoff, timeouts.
    Never tries to bypass blocks: 403/429/challenge pages raise Blocked."""

    def __init__(self, delay=(1.5, 3.0), retries=3, timeout=25):
        self.client = httpx.Client(headers={"User-Agent": UA, "Accept-Language": "hr-HR,hr;q=0.9"},
                                   timeout=timeout, follow_redirects=True)
        self.delay, self.retries = delay, retries
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        u = urlparse(url)
        base = f"{u.scheme}://{u.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.client.get(base + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[base] = rp
        return self._robots[base].can_fetch(UA, url)

    def get(self, url: str) -> str:
        if not self.allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        last = None
        for attempt in range(self.retries):
            time.sleep(random.uniform(*self.delay))
            try:
                r = self.client.get(url)
            except httpx.HTTPError as e:
                last = e
            else:
                if r.status_code in (403, 429, 503) or "Just a moment" in r.text[:2000]:
                    raise Blocked(f"{r.status_code} bot protection at {url}")
                if r.status_code == 200:
                    return r.text
                last = RuntimeError(f"HTTP {r.status_code}")
            time.sleep(2 ** attempt * 2)
        raise RuntimeError(f"failed {url}: {last}")


class Adapter:
    shop = "base"

    def scrape(self, f: Fetcher) -> list[Offer]:
        raise NotImplementedError


# --- spec extraction from free text (names/descriptions) ---
def extract_specs(text: str) -> dict:
    t = text.lower()
    s: dict = {}
    if (m := re.search(r"(\d{3,4})\s*w\b", t)):
        s["power_w"] = int(m.group(1))
    if (m := re.search(r"(\d(?:[.,]\d)?)\s*(?:l|litr)\b", t)):
        s["bowl_l"] = float(m.group(1).replace(",", "."))
    if (m := re.search(r"(\d{1,2})\s*(?:brzin|stupnjeva brzine|razina)", t)):
        s["speeds"] = int(m.group(1))
    if "planetar" in t:
        s["planetary"] = True
    if re.search(r"lijevan|metalno kućište|metalno kuciste|kućište od metala|metalno tijelo", t):
        s["body"] = "metal"
    if re.search(r"metalni (prijenos|zupčan)|metalni zupčanici|metal gear", t):
        s["metal_gears"] = True
    if (m := re.search(r"do\s*(\d[.,]?\d?)\s*kg\s*(?:kvasn|tijest|brašn)", t)):
        s["dough_kg"] = float(m.group(1).replace(",", "."))
    return s


NEG = re.compile(r"štapn|stapn|ručni mikser|rucni mikser|blender|sjeckalic|sokovnik|multipraktik|"
                 r"nastavak|dodatak|pribor|mlin za meso|posuda za|zdjela za|"
                 r"rezervni|adapter|set za|nož|raspakirano", re.I)
POS_MODEL = re.compile(r"5k(sm|45)|kmix|kmx\d|kvc\d|kvl\d|kmc\d|kmm\d|chef (xl|titanium|elite)|"
                       r"mum\d|mumx|smf0|planetar", re.I)
POS_WORD = re.compile(r"stand mixer|samostoje|stolni mikser|mikser s posudom|kuhinjski (stroj|asistent|robot)|"
                      r"robot za tijesto|mikser za tijesto", re.I)


def looks_like_stand_mixer(o: Offer) -> bool:
    text = f"{o.name} {o.description or ''}"
    if NEG.search(o.name):
        return False
    if POS_MODEL.search(text):
        return True
    if POS_WORD.search(text) and re.search(r"tijest|kuk[ae]", text, re.I):
        return True
    return False
