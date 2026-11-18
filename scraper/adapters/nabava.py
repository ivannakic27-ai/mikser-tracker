"""Nabava.net: category listing -> product pages -> all shop offers.

robots.txt forbids /out.php and /product/priceHistory: we never fetch them.
Offer links point to nabava's /out.php redirect; stored for the user to open, never requested.
"""
import re, json
from pathlib import Path
from bs4 import BeautifulSoup
from ..common import Adapter, Offer, parse_price, extract_specs, POS_MODEL

ROOT = "https://www.nabava.net"
CATEGORIES = ["/kuhinjski-roboti-i-multipraktici", "/mikseri"]
CACHE = Path("data/cache/nabava")

# listing names that are clearly not stand mixers (hand/stick mixers, blenders, accessories)
LISTING_SKIP = re.compile(r"štapn|stapn|ručni|rucni|blender|sjeckalic|sokovnik|nastavak|dodatak|"
                          r"mlin za|posuda|zdjela|set |pribor|vakuum|friteza|parni|toster|kuhalo|"
                          r"multipraktik", re.I)


class Nabava(Adapter):
    shop = "Nabava.net"

    def _get(self, f, url):
        CACHE.mkdir(parents=True, exist_ok=True)
        p = CACHE / (re.sub(r"[^a-z0-9]+", "_", url.lower())[-120:] + ".html")
        if p.exists():
            return p.read_text(encoding="utf-8")
        html = f.get(url)
        p.write_text(html, encoding="utf-8")
        return html

    def list_products(self, f, max_pages=12):
        found = {}
        for cat in CATEGORIES:
            for page in range(1, max_pages + 1):
                url = ROOT + cat + ("" if page == 1 else f"?s={page}")
                soup = BeautifulSoup(self._get(f, url), "lxml")
                new = 0
                for a in soup.select("h3.product__name a.product__link"):
                    href = a["href"].split("#")[0]
                    name = a.get_text(" ", strip=True)
                    if href not in found:
                        found[href] = (name, cat); new += 1
                if new == 0:
                    break
        return found

    def parse_product(self, html, href, list_name):
        soup = BeautifulSoup(html, "lxml")
        pid = re.search(r"cijena-(\d+)", href)
        pid = pid.group(1) if pid else href
        title = (soup.select_one("h1") or soup).get_text(" ", strip=True)[:150] if soup.select_one("h1") else list_name
        offers = []
        for o in soup.select("div.offer"):
            lab = next((e["data-event-label"] for e in o.select("[data-event-label]")
                        if (e.get("data-event-label") or "").startswith("StoreLink")), None)
            shop = lab.split(" - ", 1)[1].strip() if lab and " - " in lab else None
            pe = o.select_one(".offer__price")
            link = o.select_one(".offer__buttons-to-store")
            desc = o.select_one(".offer__name span")
            nm = o.select_one(".offer__name h2")
            av = o.select_one(".offer__availability img")
            avm = re.search(r"availability-(\d+)", av.get("src", "")) if av else None
            if not (shop and pe):
                continue
            text = f"{nm.get_text(' ', strip=True) if nm else ''} {desc.get_text(' ', strip=True) if desc else ''}"
            of = Offer(shop=shop, url=ROOT + link["href"] if link else f"{ROOT}{href}#ponude",
                       name=nm.get_text(" ", strip=True) if nm else list_name,
                       price=parse_price(pe.get_text()),
                       availability=f"nabava_icon_{avm.group(1)}" if avm else None,
                       description=desc.get_text(" ", strip=True) if desc else None,
                       source="nabava", verified_direct=False, product_ref=f"nabava:{pid}")
            of.specs = extract_specs(text)
            offers.append(of)
        return {"ref": f"nabava:{pid}", "name": title or list_name, "url": ROOT + href, "offers": offers}

    def scrape_products(self, f, limit=None):
        items = []
        for h, (n, cat) in self.list_products(f).items():
            if LISTING_SKIP.search(n):
                continue
            # /mikseri is mostly hand/stick mixers: only follow recognisable stand-mixer models there
            if cat == "/mikseri" and not POS_MODEL.search(n):
                continue
            items.append((h, n))
        if limit:
            items = items[:limit]
        out, self.failed = [], []
        for h, n in items:
            try:
                out.append(self.parse_product(self._get(f, ROOT + h), h, n))
            except Exception as e:   # one broken product page must not kill the run
                self.failed.append((h, str(e)[:80]))
        return out

    def scrape(self, f):
        return [o for p in self.scrape_products(f) for o in p["offers"]]
