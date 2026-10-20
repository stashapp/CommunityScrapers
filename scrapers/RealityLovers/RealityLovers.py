"Scraper for RealityLovers network"

import concurrent.futures
import json
import re
import sys
from time import strftime, strptime
from typing import Any
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import is_valid_url, scraper_args

ensure_requirements("bs4:beautifulsoup4", "requests")

import requests
import requests.cookies
from bs4 import BeautifulSoup

session = requests.session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
    }
)
session.cookies.set_cookie(requests.cookies.create_cookie("agreedToDisclaimer", "true"))

DOMAIN_STUDIO_MAP = {
    "playgirlstories.com": "Play Girl Stories",
    "realitylovers.com": "Reality Lovers",
    "tsvirtuallovers.com": "TS Virtual Lovers",
    "wearecrazy.com": "We Are Crazy",
}

filename_transforms = [
    lambda s: re.sub(r"[^/]+$", "00_Main_photo_Large.jpg", s),
    lambda s: re.sub(r"[^/]+$", "00-Main-photo-Large.jpg", s),
    lambda s: re.sub(r"\w+_main_", "", s).replace("small.jpg", "large@2x.jpg"),
]


def api_get(domain: str, endpoint: str, **params: Any) -> Any:
    # Some content IDs 404 without a Referer from the site itself
    try:
        response = session.get(
            f"https://engine.{domain}/content/{endpoint}",
            params=params,
            headers={"Referer": f"https://{domain}/"},
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"{domain} {endpoint}: {e}")
        return None
    return response.json()


def split_url(url: str) -> tuple[str, str] | None:
    domain = urlparse(url).netloc.removeprefix("www.")
    if domain in DOMAIN_STUDIO_MAP and (match := re.search(r"/(\d+)(?:/|$)", url)):
        return domain, match.group(1)
    log.error(f"Unsupported URL: {url}")
    return None


def srcset_by_width(srcset: str) -> list[str]:
    "URLs from an img srcset, widest first"
    entries = [entry.split() for entry in srcset.split(",")]
    return [url for url, _ in sorted(entries, key=lambda e: -int(e[1][:-1]))]


def parse_date(date_str: str) -> str:
    "Oct 15th 2026 -> 2026-10-15"
    plain = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_str)
    return strftime("%Y-%m-%d", strptime(plain, "%b %d %Y"))


def clean_text(html: str) -> str:
    text = BeautifulSoup(re.sub(r"</?p>", "\n", html), "html.parser").get_text()
    lines = "\n".join(" ".join(line.split()) for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", lines).strip()


def to_tags(names: list[str]) -> list[ScrapedTag]:
    return [{"name": name} for name in dict.fromkeys(n.strip() for n in names)]


def scene_image(srcset: str) -> str | None:
    first_url = srcset.split()[0]
    for transform in filename_transforms:
        if is_valid_url(candidate := transform(first_url)):
            return candidate
        log.debug(f"No image at {candidate}")
    return None


def performer_by_url(url: str) -> ScrapedPerformer | None:
    if not (parts := split_url(url)):
        return None
    domain, actor_id = parts
    if not (data := api_get(domain, "actor", actorId=actor_id)):
        return None

    performer: ScrapedPerformer = {
        "name": data["name"],
        "gender": "TRANSGENDER_FEMALE" if domain == "tsvirtuallovers.com" else "FEMALE",
    }
    if birthdate := data.get("birthDay"):
        performer["birthdate"] = strftime("%Y-%m-%d", strptime(birthdate, "%Y-%m-%d"))
    if country := data.get("country"):
        performer["country"] = country
    if measurements := data.get("cupSize"):
        performer["measurements"] = measurements
    if height := data.get("height"):
        performer["height"] = height
    if weight := data.get("weight"):
        performer["weight"] = weight
    if (biography := data.get("biography")) and (details := clean_text(biography)):
        performer["details"] = details
    if tags := to_tags([c["name"] for c in data.get("categories", [])]):
        performer["tags"] = tags
    if urls := [
        link
        for key in ("twitterLink", "instagramLink", "facebookLink")
        if (link := data.get(key))
    ]:
        performer["urls"] = urls
    # The widest srcset tier is missing for some performers
    if (screenshots := data.get("screenshots")) and (
        image := next(
            (
                u
                for u in srcset_by_width(screenshots[0]["galleryImgSrcSet"])
                if is_valid_url(u)
            ),
            None,
        )
    ):
        performer["images"] = [image]

    return performer


def scene_by_url(url: str) -> ScrapedScene | None:
    if not (parts := split_url(url)):
        return None
    domain, scene_id = parts
    if not (data := api_get(domain, "videoDetail", contentId=scene_id)):
        return None

    title = re.sub(r"\s+VR( Porn( Video)?)?$", "", data["title"])
    studio = DOMAIN_STUDIO_MAP[domain]
    urls = [url]
    if "play girl stories" in title.lower():
        studio = "Play Girl Stories"
        urls = [
            urlparse(url)._replace(netloc="playgirlstories.com").geturl(),
            urlparse(url)._replace(netloc="realitylovers.com").geturl(),
        ]

    tag_names = [c["name"] for c in data["categories"]] + ["Virtual Reality"]
    main_image = data["mainImages"][0]
    if main_image["perspective"] == "VOYEUR":
        tag_names += ["Non-POV", "Voyeur"]

    scene: ScrapedScene = {
        "title": title,
        "code": str(data["contentId"]),
        "date": data["releaseDate"],
        "urls": urls,
        "studio": {"name": studio},
        "tags": to_tags(tag_names),
        "performers": [
            {"name": actor["name"], "urls": [f"https://{domain}/{actor['uri']}"]}
            for actor in data["starring"]
        ],
    }
    if details := clean_text(data.get("description") or ""):
        scene["details"] = details
    if image := scene_image(main_image["imgSrcSet"]):
        scene["image"] = image
    return scene


def search_domain(domain: str, query: str) -> list[ScrapedScene]:
    results = api_get(
        domain,
        "search",
        max=100000,
        page=0,
        pornstar=0,
        category=0,
        perspective="",
        sort="",
        s=query,
    )
    scenes: list[ScrapedScene] = []
    for result in (results or {}).get("contents", []):
        scene: ScrapedScene = {
            "title": result["title"],
            "urls": [f"https://{domain}/{result['videoUri']}"],
            "date": parse_date(result["released"]),
            "studio": {"name": DOMAIN_STUDIO_MAP[domain]},
            "performers": [
                {"name": actor["name"], "urls": [f"https://{domain}/{actor['uri']}"]}
                for actor in result.get("actors", [])
            ],
        }
        if srcset := result.get("mainImageSrcset"):
            scene["image"] = srcset_by_width(srcset)[0]
        if details := clean_text(result.get("description") or ""):
            scene["details"] = details
        scenes.append(scene)
    return scenes


def scene_by_name(query: str) -> list[ScrapedScene]:
    # Search every site, since a title doesn't tell us which one it's from
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(DOMAIN_STUDIO_MAP)
    ) as executor:
        per_domain = executor.map(lambda d: search_domain(d, query), DOMAIN_STUDIO_MAP)
        return [scene for scenes in per_domain for scene in scenes]


def scene_by_fragment(fragment: dict[str, Any]) -> ScrapedScene | None:
    for url in fragment.get("urls") or []:
        if urlparse(url).netloc.removeprefix("www.") in DOMAIN_STUDIO_MAP and (
            scene := scene_by_url(url)
        ):
            return scene

    if not (title := fragment.get("title")):
        log.error("Fragment has neither a supported URL nor a title")
        return None
    if not (scenes := scene_by_name(title)):
        log.info(f"No results for '{title}'")
        return None
    best = next((s for s in scenes if s.get("title") == title), scenes[0])
    return scene_by_url(best.get("urls", [""])[0]) or best


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_by_name(name)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_by_fragment(args)
        case "performer-by-url", {"url": url} if url:
            result = performer_by_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
