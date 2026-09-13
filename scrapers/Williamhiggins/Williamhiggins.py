import json
import re
import sys
from html import unescape

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import dig, scraper_args

ensure_requirements("requests")
import requests  # noqa: E402

NETWORK = "William Higgins"
STUDIOS = {
    "ambushmassage.com": "Ambush Massage",
    "cfnmeu.com": "CFNM EU",
    "malefeet4u.com": "MaleFeet4U",
    "str8hell.com": "Str8 Hell",
    "swnude.com": "SWNude",
    "williamhiggins.com": NETWORK,
}
HEADERS = {"User-Agent": "stash-scraper/1.0"}


def fetch(host: str, path: str) -> requests.Response:
    res = requests.get(f"https://www.{host}{path}", headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res


def studio_for(host: str) -> ScrapedStudio:
    name = STUDIOS[host]
    if name == NETWORK:
        return {"name": name}
    return {"name": name, "parent": {"name": NETWORK}}


def performers_for(host: str, internal_id: int) -> list[ScrapedPerformer]:
    # Models are only exposed through this HTML popup,
    # keyed by the set's internal id rather than its public set id
    html = fetch(host, f"/api/set/more-info?id={internal_id}").text
    seen: dict[str, str] = {}
    for path, name in re.findall(
        r"Model Name:</span>\s*<a href='(/model/[^']+)'[^>]*>([^<]+)</a>", html
    ):
        seen.setdefault(unescape(name).strip(), f"https://www.{host}{path}")
    return [{"name": name, "urls": [url]} for name, url in seen.items()]


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (match := re.search(r"https?://(?:www\.)?([^/]+)/(?:set/)?detail/(\d+)", url)):
        log.error(f"Unrecognised URL: {url}")
        return None
    host, set_id = match.groups()
    if host not in STUDIOS:
        log.error(f"Unknown site: {host}")
        return None
    if not (data := dig(fetch(host, f"/api/set/data?setid={set_id}").json(), "data")):
        log.error(f"No set data for {set_id} on {host}")
        return None

    category = data.get("category_name", "")
    scene: ScrapedScene = {
        "title": f"{category.upper()}: {data['name']}" if category else data["name"],
        "code": data.get("setid") or set_id,
        "urls": [f"https://www.{host}/set/detail/{set_id}"],
        "studio": studio_for(host),
    }
    if date := data.get("public_date"):
        # dates are DD/MM/YYYY
        scene["date"] = "-".join(reversed(date.split("/")))
    if details := unescape(data.get("info") or "").strip():
        scene["details"] = details
    if image := data.get("main_image"):
        scene["image"] = image if image.startswith("http") else f"https://www.{host}{image}"
    if category:
        scene["tags"] = [ScrapedTag(name=category)]
    if (minutes := data.get("videoduration_min")) is not None:
        scene["duration"] = int(minutes) * 60 + int(data.get("videoduration_sec") or 0)
    if performers := performers_for(host, data["id"]):
        scene["performers"] = performers
    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
