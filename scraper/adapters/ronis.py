from bs4 import BeautifulSoup
from ..common import Adapter, Offer, parse_price, extract_specs

BASE = "https://www.ronis.hr/hr/mali-kucanski-aparati/kuhinjski-roboti-i-mutlipraktici"


class Ronis(Adapter):
    shop = "Ronis"

    def scrape(self, f):
        out, seen = [], set()
        for page in range(1, 20):
            html = f.get(BASE if page == 1 else f"{BASE}?page={page}")
            cards = BeautifulSoup(html, "lxml").select("div.product-display-grid.item")
            new = 0
            for c in cards:
                a = c.select_one(".product-description a")
                if not a:
                    continue
                url = "https://www.ronis.hr" + a["href"]
                if url in seen:
                    continue
                seen.add(url); new += 1
                name = a.get("title") or a.get_text(" ", strip=True)
                pv = c.select_one(".prices > .price .value")
                price = parse_price(pv.get_text()) if pv else None
                old_el = c.select_one(".prices .old-price .value, .prices del .value")
                anchor = c.select_one(".anchor-price")
                spec = c.select_one(".specification")
                avail = c.select_one(".available")
                o = Offer(shop=self.shop, url=url, name=name, price=price,
                          old_price=parse_price(old_el.get_text()) if old_el else None,
                          description=spec.get_text(" ", strip=True) if spec else None,
                          availability=avail.get_text(" ", strip=True) if avail else None)
                if anchor:
                    o.anchor_text = anchor.get_text(" ", strip=True)
                    if "lowest-price" in anchor.get("class", []):
                        v = anchor.select_one(".price .value")
                        o.lowest_30d = parse_price(v.get_text()) if v else None
                if o.old_price and price:
                    o.declared_discount_pct = round((o.old_price - price) / o.old_price * 100, 1)
                parts = name.split()
                o.brand = parts[2] if name.lower().startswith("kuhinjski robot") and len(parts) > 2 else parts[0]
                o.specs = extract_specs(f"{name} {o.description or ''}")
                out.append(o)
            if new == 0:
                break
        return out
