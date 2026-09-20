import json
import re
import sys

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGroup, ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import scraper_args

ensure_requirements("requests")
import requests  # noqa: E402

# The three sibling sites share one API, each under its own path prefix
SITES = {"avmoo.shop": "jav", "avsox.click": "javu", "avheat.shop": "wav"}

# URL language segment -> the suffix the API uses for that locale
LOCALES = {"en": "en", "ja": "ja", "zh": "cn", "cn": "cn", "tw": "tw"}

URL = re.compile(
    r"https?://(?:www\.)?(?P<host>[^/]+)/(?P<lang>[a-z]{2})/(?P<kind>\w+)/(?P<id>\w+)"
)


def _parse(url: str, kind: str) -> tuple[str, str, str] | None:
    if not (m := URL.match(url)) or m["kind"] != kind:
        log.error(f"Not a {kind} URL: {url}")
        return None
    return m["host"], LOCALES.get(m["lang"], "en"), m["id"]


def _api(host: str, method: str, **params) -> dict | None:
    if not (prefix := SITES.get(host)):
        log.error(f"No API prefix known for {host}")
        return None
    res = requests.post(
        f"https://{host}/{prefix}/data/api/{method}", json=params, timeout=30
    )
    if (body := res.json()).get("code") != 200:
        log.error(f"{method} failed: {body.get('message')}")
        return None
    return body.get("data")


def _text(obj: dict, field: str, lang: str) -> str:
    """Every locale is a separate key and most of them are present but empty."""
    keys = (f"{field}_{lang}", field, f"{field}_en", f"{field}_ja")
    return next((v for k in keys if (v := obj.get(k))), "")


def _aliases(obj: dict, field: str, lang: str) -> str:
    chosen = _text(obj, field, lang)
    others = {v for k in obj if k.startswith(f"{field}_") and (v := obj[k])}
    return ", ".join(sorted(others - {chosen}))


def _image(url: str) -> str:
    if not url or "nowprinting" in url:
        return ""
    return url.replace("https://jp.netcdn.space/", "https://pics.dmm.co.jp/")


def _link(host: str, lang: str, kind: str, id_: str) -> str:
    return f"https://{host}/{lang}/{kind}/{id_}"


def to_scraped_group(movie: dict, host: str, lang: str) -> ScrapedGroup:
    group: ScrapedGroup = {
        "name": _text(movie, "title", lang),
        "urls": [_link(host, lang, "movies", movie["movieId"])],
    }
    if date := movie.get("releaseDate"):
        group["date"] = date
    # 0 and 1 are "unknown" sentinels; real runtimes form a continuum from 2 up
    if (minutes := movie.get("length", 0)) > 1:
        group["duration"] = str(minutes * 60)
    if synopsis := _text(movie, "description", lang):
        group["synopsis"] = synopsis
    if director := movie.get("director"):
        group["director"] = _text(director, "directorName", lang)
    if studio := movie.get("studio"):
        group["studio"] = to_scraped_studio(studio, host, lang)
    if front_image := _image(movie.get("posterLarge", "")):
        group["front_image"] = front_image
    return group


def to_scraped_studio(studio: dict, host: str, lang: str) -> ScrapedStudio:
    return {
        "name": _text(studio, "studioName", lang),
        "urls": [_link(host, lang, "studios", studio["studioId"])],
    }


def to_scraped_performer(star: dict, host: str, lang: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": _text(star, "starName", lang),
        "urls": [_link(host, lang, "actresses", star["starId"])],
    }
    if aliases := _aliases(star, "starName", lang):
        performer["aliases"] = aliases
    if birthdate := star.get("birthday"):
        performer["birthdate"] = birthdate
    if star.get("hasAvatar") and (avatar := _image(star.get("avatarUrl", ""))):
        performer["images"] = [avatar]
    size = star.get("size") or {}
    if height := size.get("T"):
        performer["height"] = height
    bust, waist, hips = (size.get(k) for k in ("B", "W", "H"))
    if bust and waist and hips:
        performer["measurements"] = f"{bust}{size.get('C', '')}-{waist}-{hips}"
    return performer


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (parsed := _parse(url, "movies")):
        return None
    host, lang, id_ = parsed
    if not (movie := _api(host, "getMovie", movieId=id_)):
        return None

    scene: ScrapedScene = {
        "title": _text(movie, "title", lang),
        "urls": [_link(host, lang, "movies", movie["movieId"])],
    }
    if code := movie.get("movieFanHao"):
        scene["code"] = code
    if date := movie.get("releaseDate"):
        scene["date"] = date
    if (minutes := movie.get("length", 0)) > 1:
        scene["duration"] = minutes * 60
    if details := _text(movie, "description", lang):
        scene["details"] = details
    if director := movie.get("director"):
        scene["director"] = _text(director, "directorName", lang)
    if studio := movie.get("studio"):
        scene["studio"] = to_scraped_studio(studio, host, lang)
    if image := _image(movie.get("posterLarge", "")):
        scene["image"] = image
    if genres := movie.get("genre"):
        scene["tags"] = [{"name": _text(g, "genreName", lang)} for g in genres]
    if stars := movie.get("star"):
        scene["performers"] = [to_scraped_performer(s, host, lang) for s in stars]
    return scene


def group_from_url(url: str) -> ScrapedGroup | None:
    if not (parsed := _parse(url, "movies")):
        return None
    host, lang, id_ = parsed
    if not (movie := _api(host, "getMovie", movieId=id_)):
        return None
    return to_scraped_group(movie, host, lang)


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if not (parsed := _parse(url, "actresses")):
        return None
    host, lang, id_ = parsed
    if not (star := _api(host, "getStar", starId=id_)):
        return None
    return to_scraped_performer(star, host, lang)


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "group-by-url" | "movie-by-url", {"url": url} if url:
            result = group_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
