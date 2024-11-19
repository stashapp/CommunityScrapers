import base64
from datetime import datetime as dt
import json
import sys
from py_common import log
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import scraper_args
from py_common.deps import ensure_requirements

ensure_requirements("cloudscraper", "lxml")

import cloudscraper
from lxml import html


def scene_from_url(url: str) -> ScrapedScene:
    scene = ScrapedScene()

    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url)
        scraped.raise_for_status()
    except Exception as ex:
        log.error(f"Error getting URL: {ex}")
        sys.exit(1)

    tree = html.fromstring(scraped.text)

    video_data = None
    video_data_elems = tree.xpath("//script[@type='application/ld+json']")
    for d in video_data_elems:
        if '"@type": "VideoObject"' in d.text:
            video_data = json.loads(d.text)[0]
            break
    if not video_data:
        log.error("No VideoObject data found.")
        sys.exit(1)

    scene = ScrapedScene({
        "title": video_data["name"],
        "details": video_data["description"],
        "studio": ScrapedStudio(name=video_data["productionCompany"]),
        "tags": [ScrapedTag(name=t) for t in video_data["keywords"].split(",")],
        "performers": [ScrapedPerformer(name=a["name"]) for a in video_data["actor"]]
    })

    # If no performers look in zeder elem
    if not scene["performers"]:
        try:
            zeder_elem = tree.xpath("//div[contains(@class, '-zeder-detail-')]")[0]
            zeder_attrs = zeder_elem.attrib
            for k, v in zeder_attrs.items():
                if "data-zeder-actor-" in k:
                    scene["performers"].append(ScrapedPerformer(name=v.replace("-", " ").title()))
        except IndexError:
            pass

    scene["date"] = dt.fromisoformat(video_data["datePublished"]).strftime("%Y-%m-%d")

    image_url = tree.xpath("//meta[@property='og:image']/@content")[0]
    try:
        img = scraper.get(image_url).content
        scraped.raise_for_status()
        scene["image"] = "data:image/jpeg;base64," + base64.b64encode(img).decode()
    except Exception as ex:
        log.error(f"Failed to get image: {ex}")

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Not Implemented: Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
