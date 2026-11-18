import json, sys, logging
from pathlib import Path
from .common import Fetcher, Blocked, looks_like_stand_mixer
from .adapters.harveynorman import HarveyNorman
from .adapters.smallshops import Links, Elipso, Instar, Mikronis

# Big Bang / Ronis (Cloudflare 403) and Mall.hr / Pevex / Jeftinije.hr are skipped on purpose: prices come via Nabava
ADAPTERS = [HarveyNorman(), Links(), Elipso(), Instar(), Mikronis()]
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main(out="data/raw_offers.json"):
    f = Fetcher()
    offers, runs = [], []
    for ad in ADAPTERS:
        try:
            res = ad.scrape(f)
            for o in res:
                o.specs["stand_mixer_guess"] = looks_like_stand_mixer(o)
            offers += res
            runs.append({"shop": ad.shop, "status": "ok", "count": len(res)})
            logging.info("%s: %d ponuda (%d stand mixer)", ad.shop, len(res),
                         sum(o.specs["stand_mixer_guess"] for o in res))
        except Blocked as e:
            runs.append({"shop": ad.shop, "status": "blocked", "error": str(e)})
            logging.warning("%s BLOCKED %s", ad.shop, e)
        except Exception as e:
            runs.append({"shop": ad.shop, "status": "error", "error": str(e)})
            logging.error("%s ERROR %s", ad.shop, e)
    Path(out).parent.mkdir(exist_ok=True)
    Path(out).write_text(json.dumps({"runs": runs, "offers": [o.to_dict() for o in offers]},
                                    ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
