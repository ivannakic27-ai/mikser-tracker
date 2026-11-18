import json
from scraper.common import Fetcher
from scraper.adapters.nabava import Nabava
n=Nabava(); f=Fetcher(delay=(1.0,2.0))
prods=n.scrape_products(f)
json.dump([{**p,"offers":[o.to_dict() for o in p["offers"]]} for p in prods],open("data/nabava_products.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("DONE",len(prods),sum(len(p["offers"]) for p in prods))
