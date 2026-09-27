import base64
import hashlib
import json
import os
import re
import sys
import time

from py_common import log
from py_common.cache import cache_to_disk
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGroup, ScrapedScene, ScrapedStudio
from py_common.util import dig, scraper_args

ensure_requirements("requests", "Crypto:pycryptodome")
import requests  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402
from Crypto.Util.Padding import pad  # noqa: E402

API = "https://ns-api.nakedsword.com/frontend"
NETWORK = "Falcon | NakedSword"
# The API and the sites reject non-browser user agents outright
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept": "application/json",
}
URL_PATTERN = re.compile(
    r"https?://(?:www\.)?([^/]+)/movies/(\d+)/([^/?#]+)(?:/scene/(\d+))?"
)


@cache_to_disk(ttl=24 * 60 * 60)
def site_config(host: str) -> dict | None:
    # Each white-label site ships its API passphrase and property id in its JS bundle
    page = requests.get(f"https://www.{host}/", headers=HEADERS, timeout=30).text
    if not (bundle := re.search(r"/static/js/main\.[0-9a-f]+\.chunk\.js", page)):
        log.error(f"Could not find the JS bundle for {host}")
        return None
    js = requests.get(
        f"https://www.{host}{bundle.group(0)}", headers=HEADERS, timeout=30
    ).text
    passphrase = re.search(r'REACT_APP_PASSPHRASE:"([^"]+)"', js)
    property_id = re.search(r'REACT_APP_PROPERTY_ID:"([^"]+)"', js)
    if not (passphrase and property_id):
        log.error(f"Could not find the API configuration for {host}")
        return None
    return {"passphrase": passphrase.group(1), "property_id": property_id.group(1)}


def ident(config: dict) -> str:
    # Mirrors the site's CryptoJS scheme: AES-CBC with a PBKDF2-SHA512 key over a timestamped payload
    payload = json.dumps(
        {"date": int(time.time() * 1000), "propertyId": config["property_id"]},
        separators=(",", ":"),
    )
    salt, iv = os.urandom(256), os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha512", config["passphrase"].encode(), salt, 999, dklen=32
    )
    ciphertext = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(payload.encode(), 16))
    token = json.dumps(
        {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "salt": salt.hex(),
            "iv": iv.hex(),
        },
        separators=(",", ":"),
    )
    return base64.b64encode(token.encode()).decode()


def fetch_movie(host: str, movie_id: str) -> dict | None:
    if not (config := site_config(host)):
        return None
    res = requests.get(
        f"{API}/movies/{movie_id}/details",
        headers={**HEADERS, "x-ident": ident(config)},
        timeout=30,
    )
    if not res.ok:
        log.error(
            f"API returned {res.status_code} for movie {movie_id} on {host}: {res.text[:200]}"
        )
        return None
    return dig(res.json(), "data")


def studio(movie: dict) -> ScrapedStudio | None:
    names = [name for s in movie.get("studios", []) if (name := s.get("name"))]
    if not (own := [name for name in names if name != NETWORK]):
        return None
    # A collaboration label ("NakedSword X Rhyheim") is listed after the base studio
    result: ScrapedStudio = {"name": own[-1]}
    if NETWORK in names:
        result["parent"] = {"name": NETWORK}
    return result


def image(images: list[dict], image_type: str | None = None) -> str | None:
    candidates = [
        i for i in images if image_type is None or i.get("type") == image_type
    ]
    if not candidates:
        return None
    if not (url := max(candidates, key=lambda i: i.get("width") or 0).get("url")):
        return None
    # AEBN serves a thumbnail for the ?s= size parameter and the original without it
    return url.split("?")[0] if "pic.aebn.net" in url else url


def seconds(runtime: str | None) -> int | None:
    if not re.fullmatch(r"\d+:\d{2}:\d{2}", runtime or ""):
        return None
    hours, minutes, secs = map(int, (runtime or "").split(":"))
    return hours * 3600 + minutes * 60 + secs


def names(items: list[dict]) -> list[str]:
    return [name for i in items if (name := i.get("name"))]


def movie_url(host: str, movie_id: str, slug: str) -> str:
    return f"https://www.{host}/movies/{movie_id}/{slug}"


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (match := URL_PATTERN.match(url)):
        log.error(f"Not a movie or scene URL: {url}")
        return None
    host, movie_id, slug, index = match.groups()
    if not (movie := fetch_movie(host, movie_id)):
        return None
    scenes = movie.get("scenes") or []
    if index is None:
        return whole_movie_as_scene(host, movie_id, slug, movie)
    if not (scene := next((s for s in scenes if str(s.get("index")) == index), None)):
        log.error(f"Movie {movie_id} has no scene {index}")
        return None

    multi_scene = len(scenes) > 1
    result: ScrapedScene = {
        "title": f"{movie['title']} - Scene {index}" if multi_scene else movie["title"],
        "urls": [f"{movie_url(host, movie_id, slug)}/scene/{index}"],
    }
    if details := movie.get("description"):
        result["details"] = details
    if performers := names(scene.get("stars") or []):
        result["performers"] = [{"name": name} for name in performers]
    if tags := [
        name for c in movie.get("categories") or [] if (name := dig(c, "tag", "name"))
    ]:
        result["tags"] = [{"name": name} for name in tags]
    if directors := names(movie.get("directors") or []):
        result["director"] = ", ".join(directors)
    if studio_ := studio(movie):
        result["studio"] = studio_
    if cover := image(scene.get("cover_images") or []):
        result["image"] = cover
    if (start := scene.get("startTimeSeconds")) is not None and (
        end := scene.get("endTimeSeconds")
    ):
        result["duration"] = end - start
    # A single-scene release is the scene itself, not a group it belongs to
    if multi_scene:
        result["groups"] = [
            {"name": movie["title"], "urls": [movie_url(host, movie_id, slug)]}
        ]
    return result


def whole_movie_as_scene(
    host: str, movie_id: str, slug: str, movie: dict
) -> ScrapedScene:
    # The movie is the scene here, so it must not list itself as a group
    result: ScrapedScene = {
        "title": movie["title"],
        "urls": [movie_url(host, movie_id, slug)],
    }
    if details := movie.get("description"):
        result["details"] = details
    if performers := names(movie.get("stars") or []):
        result["performers"] = [{"name": name} for name in performers]
    if tags := [
        name for c in movie.get("categories") or [] if (name := dig(c, "tag", "name"))
    ]:
        result["tags"] = [{"name": name} for name in tags]
    if directors := names(movie.get("directors") or []):
        result["director"] = ", ".join(directors)
    if studio_ := studio(movie):
        result["studio"] = studio_
    if cover := image(dig(movie, "scenes", 0, "cover_images") or []):
        result["image"] = cover
    if (duration := seconds(movie.get("runTime"))) is not None:
        result["duration"] = duration
    return result


def group_from_url(url: str) -> ScrapedGroup | None:
    if not (match := URL_PATTERN.match(url)):
        log.error(f"Not a movie URL: {url}")
        return None
    host, movie_id, slug, _ = match.groups()
    if not (movie := fetch_movie(host, movie_id)):
        return None

    result: ScrapedGroup = {
        "name": movie["title"],
        "urls": [movie_url(host, movie_id, slug)],
    }
    if synopsis := movie.get("description"):
        result["synopsis"] = synopsis
    if directors := names(movie.get("directors") or []):
        result["director"] = ", ".join(directors)
    if studio_ := studio(movie):
        result["studio"] = studio_
    if (duration := seconds(movie.get("runTime"))) is not None:
        result["duration"] = str(duration)
    images = movie.get("images") or []
    if front := image(images, "Box Cover (Extra Large, Front)"):
        result["front_image"] = front
    if back := image(images, "Box Cover (Extra Large, Back)"):
        result["back_image"] = back
    return result


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "group-by-url", {"url": url} if url:
            result = group_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
