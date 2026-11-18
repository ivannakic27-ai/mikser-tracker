from bs4 import BeautifulSoup
from ..common import Adapter, Offer, parse_price, extract_specs

BASE = "https://www.bigbang.hr/mali-kucanski-aparati/priprema-hrane/kuhinjski-roboti/"


class BigBang(Adapter):
    shop = "Big Bang"

    def scrape(self, f):
        out, seen = [], set()
        for page in range(1, 25):
            html = f.get(BASE if page == 1 else f"{BASE}?page={page}")
            cards = BeautifulSoup(html, "lxml").select("article.cp")
            new = 0
            for c in cards:
                a = c.select_one("a.cp-product-link-overlay")
                if not a or a["href"] in seen:
                    continue
                seen.add(a["href"]); new += 1
                name = c.select_one(".cp-title").get_text(" ", strip=True)
                cur = c.select_one(".current-price")
                old = c.select_one("del.old-price")
                anchor = c.select_one(".cp-anchor-price")
                avail = c.select_one(".cp-availability")
                seller = c.select_one(".seller-title")
                o = Offer(shop=self.shop, url="https://www.bigbang.hr" + a["href"], name=name,
                          price=parse_price(cur.get_text()) if cur else None,
                          old_price=parse_price(old.get_text()) if old else None,
                          anchor_text=anchor.get_text(" ", strip=True) if anchor else None,
                          availability=avail.get_text(" ", strip=True) if avail else None,
                          seller=seller.get_text(strip=True) if seller else None)
                # Big Bang anchor is "MPC na <datum>" (recommended price), NOT an Omnibus 30-day low
                if o.old_price and o.price:
                    o.declared_discount_pct = round((o.old_price - o.price) / o.old_price * 100, 1)
                o.brand = name.split()[0]
                o.specs = extract_specs(name)
                out.append(o)
            if new == 0:
                break
        return out
