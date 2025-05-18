import json
import sys
from typing import Literal
import requests
from datetime import datetime
from urllib.parse import urlparse

import py_common.log as log
from py_common.util import dig, scraper_args
from py_common.types import ScrapedScene, ScrapedPerformer, ScrapedStudio, ScrapedTag

studio_hierarchy = {
    "Fuck You Cash": {
        "anal-4k": "Anal 4K",
        "bbc-pie": "BBC Pie",
        "casting-couch-x": "Casting Couch X",
        "cum4k": "Cum4K",
        "exotic-4k": "Exotic4K",
        "facials-4k": "Facials4K",
        "fantasy-hd": "Fantasy HD",
        "girlcum": "GirlCum",
        "holed": "Holed",
        "lubed": "Lubed",
        "mom-4k": "Mom4K",
        "my-very-first-time": "My Very First Time",
        "nannyspy": "NannySpy",
        "passion-hd": "Passion HD",
        "povd": "POVD",
        "pure-mature": "Pure Mature",
        "spyfam": "SpyFam",
        "strippers4k": "Strippers4K",
        "tiny4k": "Tiny4K",
        "wetvr": "WetVR",
    },
    "Gay Room": {
        "bathhousebait": "Bath House Bait",
        "boysdestroyed": "Boys Destroyed",
        "damnthatsbig": "Damn That's Big",
        "gaycastings": "Gay Castings",
        "gaycreeps": "Gay Creeps",
        "gayviolations": "Gay Violations",
        "manroyale": "Man Royale",
        "massagebait": "Massage Bait",
        "menpov": "Men POV",
        "officecock": "Office Cock",
        "outhim": "Out Him",
        "showerbait": "Shower Bait",
        "thickandbig": "Thick and Big",
    },
    "PORN+": {
        "asians-exploited": "Asians Exploited",
        "bbc-povd": "BBC POVD",
        "bikini-splash": "Bikini Smash",
        "boobs4k": "Boobs 4K",
        "caged-sex": "Caged Sex",
        "creepy-pa": "Creepy PA",
        "double-trouble": "Double Trouble",
        "facials-galore": "Facials Galore",
        "game-on": "Game On",
        "glory-hole-4k": "Glory Hole 4K",
        "kinky-sluts-4k": "Kinky Sluts 4K",
        "momcum": "Mom Cum",
        "passion-fuck": "Passion Fuck",
        "pornstars-in-cars": "Pornstars in Cars",
        "property-exploits": "Property Exploits",
        "rv-adventures": "RV Adventures",
        "school-of-cock": "School of Cock",
        "sexercise": "Sexercise",
        "shower-4k": "Shower 4K",
        "squirt-bomb": "Squirt Bomb",
        "strip-club-tryouts": "Strip Club Tryouts",
        "throat-creampies": "Throat Creampies",
        "waxxxed": "WaXXXed",
        "zoom-pov": "Zoom POV",
    },
    "Porn Pros": {
        "18yearsold": "18 Years Old",
        "40ozbounce": "40oz Bounce",
        "cockcompetition": "Cock Competition",
        "crueltyparty": "Cruelty Party",
        "cumshotsurprise": "Cumshot Surprise",
        "deepthroatlove": "Deep Throat Love",
        "disgraced18": "Disgraced 18",
        "eurohumpers": "Euro Humpers",
        "flexiblepositions": "Flexible Positions",
        "freaksofboobs": "Freaks of Boobs",
        "freaksofcock": "Freaks of Cock",
        "jurassiccock": "Jurassic Cock",
        "massagecreep": "Massage Creep",
        "pimpparade": "Pimp Parade",
        "publicviolations": "Public Violations",
        "realexgirlfriends": "Real Ex Girlfriends",
        "shadypi": "Shady PI",
        "squirtdisgrace": "Squirt Disgrace",
        "teenbff": "Teen BFF",
    },
}

# PornPros appears to only feature cis performers
gender_map: dict[str, Literal["MALE", "FEMALE"]] = {
    "girl": "FEMALE",
    "guy": "MALE",
}

tag_map = {
    "Milf": "MILF",
    "Bdsm": "BDSM",
    "Hd": "HD",
}

# Some scenes are available on multiple sites and some have different domains
# than their API metadata indicate so we map some of them manually
site_map = {
    **{
        studio: [studio.replace("-", "")]
        for studio in studio_hierarchy["Fuck You Cash"].keys()
    },
    **{studio: ["pornpros"] for studio in studio_hierarchy["Porn Pros"].keys()},
    **{studio: ["pornplus"] for studio in studio_hierarchy["PORN+"].keys()},
    **{studio: ["gayroom", studio] for studio in studio_hierarchy["Gay Room"].keys()},
    "casting-couch-x": ["castingcouch-x"],
    "passion-hd": ["passion-hd"],
    "creepy-pa": ["pornplus", "creepypa"],
    "momcum": ["pornplus", "momcum"],
}


def to_scraped_studio(raw_scene: dict) -> ScrapedStudio:
    site = dig(raw_scene, "sponsor", "cachedSlug")
    for parent, children in studio_hierarchy.items():
        if site in children:
            return {"name": children[site], "parent": {"name": parent}}

    return {"name": dig(raw_scene, "sponsor", "name")}


def to_scraped_performer(dict: dict) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": dict["name"]}
    if gender := dig(dict, "gender"):
        performer["gender"] = gender_map.get(gender, gender)  # type: ignore
    return performer


def to_scraped_tag(tag: str) -> ScrapedTag:
    name = " ".join(tag.split("_")).title()
    return {"name": tag_map.get(name, name)}


def get_urls(raw_scene: dict) -> list[str]:
    slug = dig(raw_scene, "cachedSlug")
    site_slug = dig(raw_scene, "sponsor", "cachedSlug")
    return [
        f"https://{site}.com/video/{slug}"
        for site in site_map.get(site_slug, [site_slug])
    ]


def to_scraped_scene(raw_scene: dict) -> ScrapedScene | None:
    scene: ScrapedScene = {
        "title": raw_scene["title"],
        "date": datetime.fromisoformat(raw_scene["releasedAt"]).date().isoformat(),
        "details": raw_scene["description"].strip(),
        "urls": get_urls(raw_scene),
        "studio": to_scraped_studio(raw_scene),
    }

    if (image := dig(raw_scene, ("posterUrl", "thumbUrl"))) or (
        image := dig(raw_scene, "thumbUrls", 0)
    ):
        full_size_image = image.split("?")[0]
        scene["image"] = full_size_image
    if tags := dig(raw_scene, "tags"):
        scene["tags"] = [to_scraped_tag(t) for t in tags]
    if performers := dig(raw_scene, "actors"):
        scene["performers"] = [to_scraped_performer(p) for p in performers]

    return scene


def scene_from_url(url) -> ScrapedScene | None:
    parsed = urlparse(url)
    slug = parsed.path.split("/")[-1].lower()
    domain = parsed.hostname

    api_url = parsed._replace(path=f"api/releases/{slug}").geturl()

    if not (res := requests.get(api_url, headers={"x-site": domain})):
        log.error(f"Unable to scrape from {api_url}")
        return None

    res.raise_for_status()
    raw_scene = res.json()
    log.debug(json.dumps(raw_scene, indent=2))
    return to_scraped_scene(raw_scene)


def find_scene(query: str) -> ScrapedScene | None:
    log.error(f"No scenes found for '{query}'")
    return None


def scene_search(query: str) -> list[ScrapedScene]:
    if not query:
        log.error("No query provided")
        return []

    return []


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": query} if query:
            result = scene_search(query)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
