import json
import sys
from typing import Any
from py_common import log
from py_common.util import replace_at, replace_all
from Reptyle.scrape import (
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)

SEARCH_URL = "https://ma-store.sayuncle.com/rs/"

studio_map = {
    "Black Godz": "BlackGodz",
    "BottomGames": "Bottom Games",
    "BoysDoPorn": "Boys Do Porn",
    "DadCreep": "Dad Creep",
    "DoctorTapes": "Doctor Tapes",
    "SayUncle AllStars": "SayUncle All-Stars",
    "StayHomeBro": "Stay Home Bro",
    "StickyRub": "Sticky Rub",
    "MilitaryDick": "Military Dick",
    "TroopSex": "Troop Sex",
    "YesFather": "Yes Father",
}


def sayuncle(obj: Any, _: Any) -> Any:
    fixed = replace_at(
        obj,
        "studio",
        replacement=lambda s: {
            "name": studio_map.get(s["name"], s["name"]),
            "parent": {
                "name": "SayUncle",
                "url": "https://www.sayuncle.com/",
            },
        },
    )
    fixed = replace_all(fixed, "urls", lambda url: url.replace("placeholder", "sayuncle", 1))
    return fixed


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=sayuncle)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_url=SEARCH_URL, postprocess=sayuncle)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_url=SEARCH_URL, postprocess=sayuncle)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
