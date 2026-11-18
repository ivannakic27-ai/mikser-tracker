from bs4 import BeautifulSoup
from ..common import Adapter, Offer, extract_specs

BASE = "https://www.harveynorman.hr/mali-kucanski-aparati/aparati-za-pripremu-hrane/kuhinjski-roboti-multipraktici/kuhinjski-roboti"


class HarveyNorman(Adapter):
    shop = "Harvey Norman"

    def scrape(self, f):
        out, seen = [], set()
        for page in range(1, 15):
            html = f.get(BASE if page == 1 else f"{BASE}?p={page}")
            cards = BeautifulSoup(html, "lxml").select("div.product-item-info")
            new = 0
            for c in cards:
                a = c.select_one("a.product-item-link")
                if not a or a["href"] in seen:
                    continue
                seen.add(a["href"]); new += 1
                price_el = c.select_one("[data-price-type=finalPrice]")
                old_el = c.select_one("[data-price-type=oldPrice]")
                price = float(price_el["data-price-amount"]) if price_el else None
                old = float(old_el["data-price-amount"]) if old_el else None
                usp = " ".join(li.get_text(" ", strip=True) for li in c.select("li.usp-item"))
                brand = c.select_one(".product-item-brand-name")
                o = Offer(shop=self.shop, url=a["href"], name=a.get_text(" ", strip=True),
                          brand=brand.get_text(strip=True) if brand else None,
                          price=price, old_price=old, description=usp)
                # Harvey states the struck-through price IS the lowest price in the 30 days before the sale
                if old and "30 d" in c.get_text(" ", strip=True):
                    o.lowest_30d = old
                    o.anchor_text = "stara cijena = najniza u 30 dana (Omnibus, tekst shopa)"
                if old and price:
                    o.declared_discount_pct = round((old - price) / old * 100, 1)
                o.specs = extract_specs(f"{o.name} {usp}")
                out.append(o)
            if new == 0:
                break
        return out
