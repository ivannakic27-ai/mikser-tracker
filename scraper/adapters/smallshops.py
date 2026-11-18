"""Adapters for small shops (Links, Elipso, Instar, Mikronis). Same interface, per-shop selectors.
Only category pages allowed by robots.txt are fetched. Elipso: first page only (?page= is disallowed)."""
from bs4 import BeautifulSoup
from ..common import Adapter, Offer, parse_price, extract_specs


def _txt(el):
    return el.get_text(" ", strip=True) if el else None


class Links(Adapter):
    shop = "Links"
    base = "https://www.links.hr"
    urls = ["https://www.links.hr/hr/mikseri-040103"]

    def scrape(self, f):
        out = []
        for u in self.urls:
            for c in BeautifulSoup(f.get(u), "lxml").select("div.card.mobile-card"):
                a = c.select_one("a.card-link")
                name = _txt(c.select_one("h3"))
                if not a or not name:
                    continue
                price = parse_price(_txt(c.select_one(".product-price .active")))
                old = parse_price(_txt(c.select_one(".product-price .inactive")))
                anchor = c.select_one(".anchor-price")
                o = Offer(shop=self.shop, url=self.base + a["href"], name=name, brand=name.split()[-1] if False else None,
                          price=price, old_price=old, anchor_text=_txt(anchor),
                          lowest_30d=parse_price(_txt(anchor.select("span")[-1])) if anchor else None)
                if old and price:
                    o.declared_discount_pct = round((old - price) / old * 100, 1)
                o.specs = extract_specs(name)
                out.append(o)
        return out


class Elipso(Adapter):
    shop = "Elipso"
    base = "https://www.elipso.hr"
    urls = ["https://www.elipso.hr/mali-kucanski/mikseri/"]   # no ?page= (robots.txt)

    def scrape(self, f):
        out = []
        for u in self.urls:
            for c in BeautifulSoup(f.get(u), "lxml").select("div.product-card-container"):
                a = c.select_one("a[href]")
                brand, model, title = (_txt(c.select_one(s)) for s in (".artikl-brand", ".fw-bolder", ".artikl-title"))
                price = parse_price(_txt(c.select_one(".fs-4")))
                old = parse_price(_txt(c.select_one(".text-decoration-line-through")))
                name = " ".join(x for x in (brand, model, title) if x)
                o = Offer(shop=self.shop, url=self.base + a["href"], name=name, brand=brand, price=price,
                          old_price=old, description=title)
                if old:
                    o.lowest_30d = old   # Elipso: struck price = lowest in 30 days before sale (Omnibus text)
                    o.anchor_text = "stara cijena = najniza u 30 dana (Omnibus, tekst shopa)"
                    if price:
                        o.declared_discount_pct = round((old - price) / old * 100, 1)
                o.specs = extract_specs(name)
                out.append(o)
        return out


class Instar(Adapter):
    shop = "Instar Informatika"
    base = "https://www.instar-informatika.hr"
    urls = ["https://www.instar-informatika.hr/blenderi-i-mikseri/2078/"]

    def scrape(self, f):
        out = []
        for u in self.urls:
            for c in BeautifulSoup(f.get(u), "lxml").select("div.product-item"):
                a = c.select_one("h2.title a")
                if not a:
                    continue
                price = parse_price(_txt(c.select_one(".standard-price")))
                old = parse_price(_txt(c.select_one(".pricelistpriceLow span")))
                av = _txt(c.select_one(".product-tehspec_footer"))
                o = Offer(shop=self.shop, url=self.base + a["href"], name=_txt(a), price=price, old_price=old,
                          availability=av, description=_txt(c.select_one(".tehspectag_opis")))
                if old:
                    o.lowest_30d = old   # tooltip: "Najniza cijena u zadnjih 30 dana"
                    o.anchor_text = "prekrizena cijena = najniza u 30 dana (tooltip shopa)"
                    if price:
                        o.declared_discount_pct = round((old - price) / old * 100, 1)
                o.specs = extract_specs(f"{o.name} {o.description or ''}")
                out.append(o)
        return out


class Mikronis(Adapter):
    shop = "Mikronis"
    base = "https://www.mikronis.hr"
    cat = "https://www.mikronis.hr/katalog/kucanski-aparati/mali-kucanski-aparati/mikseri/"

    def scrape(self, f):
        out, seen = [], set()
        for page in range(1, 8):
            soup = BeautifulSoup(f.get(self.cat if page == 1 else f"{self.cat}?page={page}"), "lxml")
            new = 0
            for c in soup.select("div.prod-item"):
                a = c.select_one(".item-title a")
                href = c.select_one(".item-pic a")
                if not a or not href or href["href"] in seen:
                    continue
                seen.add(href["href"]); new += 1
                price = parse_price(_txt(c.select_one(".price-now")))
                low = c.select_one(".lowest-price-catalogue span")
                o = Offer(shop=self.shop, url=self.base + href["href"], name=a.get("title", _txt(a)).strip(),
                          price=price, lowest_30d=parse_price(_txt(low)),
                          availability=(c.select_one(".ip-available") or {}).get("title") if c.select_one(".ip-available") else None)
                if o.lowest_30d:
                    o.old_price = o.lowest_30d
                    o.anchor_text = "najniza cijena u prethodnih 30 dana"
                    if price:
                        o.declared_discount_pct = round((o.lowest_30d - price) / o.lowest_30d * 100, 1)
                o.specs = extract_specs(o.name)
                out.append(o)
            if new == 0:
                break
        return out
