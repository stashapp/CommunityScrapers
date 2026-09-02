import base64
from datetime import datetime as dt
from html import unescape

import json
import sys
from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args, dig
from py_common.deps import ensure_requirements

ensure_requirements("cloudscraper", "lxml")

import cloudscraper  # noqa: E402
from lxml import html  # noqa: E402

scraper = cloudscraper.create_scraper()


def _as_keyword_list(keywords) -> list[str]:
    if not keywords:
        return []
    if isinstance(keywords, list):
        return [k.strip() for k in keywords if k and k.strip()]
    if isinstance(keywords, str):
        return [k.strip() for k in keywords.split(",") if k.strip()]
    return []


def scene_from_url(url: str) -> ScrapedScene | None:
    try:
        scraped = scraper.get(url)
        scraped.raise_for_status()
    except Exception as ex:
        log.error(f"Error scraping {url}: {ex}")
        return None

    tree = html.fromstring(scraped.text)

    video_data = None
    for d in tree.xpath("//script[@type='application/ld+json']"):
        if not d.text or "VideoObject" not in d.text:
            continue
        try:
            data = json.loads(d.text)
        except json.JSONDecodeError as ex:
            log.debug(f"Failed to parse JSON-LD block: {ex}")
            continue

        # Normalize to a flat list of candidate dicts, since sites may emit
        # a single object, a list of objects, or an object with an @graph
        candidates = data if isinstance(data, list) else [data]
        flattened = []
        for c in candidates:
            if isinstance(c, dict) and "@graph" in c:
                flattened.extend(c["@graph"])
            else:
                flattened.append(c)

        for c in flattened:
            if isinstance(c, dict) and c.get("@type") == "VideoObject":
                video_data = c
                break
        if video_data:
            break

    if not video_data:
        log.error(f"No VideoObject data found at {url}")
        return None

    log.debug(f"Video data: {json.dumps(video_data)}")
    scene: ScrapedScene = {
        "title": video_data["name"],
        "details": unescape(video_data["description"]).strip(),
        "date": dt.fromisoformat(video_data["datePublished"]).date().isoformat(),
        "tags": [{"name": t} for t in _as_keyword_list(video_data.get("keywords"))],
    }

    if studio := dig(video_data, "productionCompany", "en"):
        scene["studio"] = {"name": studio}

    if dig(video_data, "actor"):
        scene["performers"] = [{"name": a["name"]} for a in video_data["actor"]]
    # Performers are also listed in the data-zeder-actor-* attributes
    # but they do not have accented characters and are not capitalized
    elif actors := tree.xpath("/html/body/div/@*[contains(name(), 'zeder-actor-')]"):
        scene["performers"] = [{"name": a.replace("-", " ").title()} for a in actors]

    for image_url in tree.xpath("//meta[@property='og:image']/@content"):
        try:
            img = scraper.get(image_url)
            img.raise_for_status()
            scene["image"] = (
                "data:image/jpeg;base64," + base64.b64encode(img.content).decode()
            )
        except Exception as ex:
            log.error(f"Failed to get image from {image_url}: {ex}")

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(
                f"Not Implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

    print(json.dumps(result))
