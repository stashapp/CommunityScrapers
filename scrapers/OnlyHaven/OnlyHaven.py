import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from py_common import log
from py_common.types import (
    Gender,
    ScrapedGallery,
    ScrapedImage,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, scraper_args

API = "https://cum.st/api/v1"
SITE = "https://cum.st"
MEDIA = "https://e1.cum.st"
IMG = "https://img.cum.st"

# Post/DM page URL
POST_URL_RE = re.compile(
    r"cum\.st/creators/(?P<service>onlyfans|fansly)/(?P<creator>\d+)/(?P<kind>post|dm)/(?P<id>[\w-]+)"
)
SHA256_RE = re.compile(r"(?<![0-9a-f])([0-9a-f]{64})(?![0-9a-f])", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.-]{3,})")

NETWORKS = {"onlyfans": ("OnlyFans", "https://onlyfans.com"), "fansly": ("Fansly", "https://fansly.com")}
GENDERS: dict[str, Gender] = {
    "woman": "FEMALE",
    "man": "MALE",
    "trans_woman": "TRANSGENDER_FEMALE",
    "trans_man": "TRANSGENDER_MALE",
    "nonbinary": "NON_BINARY",
}

session = requests.Session()
session.headers.update({"User-Agent": "stash-scraper/1.0", "Accept": "application/json"})


def api(path: str) -> Any:
    res = session.get(f"{API}/{path}", timeout=20)
    if res.status_code == 404:
        log.debug(f"Not found: {path}")
        return None
    if not res.ok:
        log.error(f"API error {res.status_code} for {path}")
        return None
    return res.json()


def creator_url(service: str, username: str) -> str:
    return f"{NETWORKS[service][1]}/{username}"


def post_urls(service: str, creator_id: str, kind: str, post_id: str, username: str) -> list[str]:
    urls = [f"{SITE}/creators/{service}/{creator_id}/{kind}/{post_id}"]
    if kind == "post":
        match service:
            case "onlyfans":
                urls.append(f"https://onlyfans.com/{post_id}/{username}")
            case "fansly":
                urls.append(f"https://fansly.com/post/{post_id}")
    return urls


def to_studio(service: str, username: str) -> ScrapedStudio:
    network, network_url = NETWORKS[service]
    return {
        "name": f"{username} ({network})",
        "urls": [creator_url(service, username)],
        "parent": {"name": f"{network} (network)", "urls": [network_url]},
    }


def to_performer(service: str, creator_id: str, profile: dict) -> ScrapedPerformer:
    username = profile["name"]
    performer: ScrapedPerformer = {
        "name": username,
        "urls": [creator_url(service, username), f"{SITE}/creators/{service}/{creator_id}"],
        "image": f"{IMG}/creator/{service}/{creator_id}/avatar.webp",
    }
    if gender := GENDERS.get(profile.get("gender") or ""):
        performer["gender"] = gender
    return performer


def mentioned_performers(service: str, text: str, exclude: str) -> list[ScrapedPerformer]:
    seen = {exclude.lower()}
    performers = []
    for handle in MENTION_RE.findall(text):
        handle = handle.rstrip(".")
        if handle.lower() not in seen:
            seen.add(handle.lower())
            performers.append(ScrapedPerformer(name=handle, urls=[creator_url(service, handle)]))
    return performers


def attachment_image(att: dict) -> str | None:
    if not (sha := att.get("sha256")):
        return None
    if att.get("kind") == "video":
        return f"{IMG}/thumbnail/{sha}/preview.webp"
    ext = dig(att, "variants", 0, "name", default="original.jpg").rpartition(".")[2]
    return f"{MEDIA}/media/{sha}/original.{ext}"


def title_from_caption(caption: str) -> str | None:
    if not (lines := [line.strip() for line in caption.splitlines() if line.strip()]):
        return None
    first = lines[0]
    if len(first) > 80:
        first = first[:80].rsplit(" ", 1)[0] + "…"
    return first


def tag_name(tag: Any) -> str | None:
    match tag:
        case str():
            return tag
        case {"name": str() as name} | {"label": str() as name} | {"slug": str() as name}:
            return name
    return None


def to_scraped_scene(service: str, creator_id: str, kind: str, post_id: str, target_sha: str | None = None) -> ScrapedScene | None:
    if not (post := api(f"{service}/user/{creator_id}/{kind}/{post_id}")):
        return None
    profile = api(f"{service}/user/{creator_id}/profile") or {}
    username = profile.get("name") or post.get("creatorName") or creator_id

    caption = post.get("caption", "")
    date = (
        datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if (ts := dig(post, ("published", "added")))
        else None
    )
    title = (post.get("title", "")).strip() or title_from_caption(caption) or f"{username} - {date or post_id}"

    unlocked = [a for a in post.get("attachments") or [] if not a.get("locked")]
    target = next((a for a in unlocked if a.get("sha256") == target_sha), None) if target_sha else None
    if target and len(unlocked) > 1:
        title += f" ({unlocked.index(target) + 1}/{len(unlocked)})"

    scene: ScrapedScene = {
        "title": title,
        "details": caption,
        "urls": post_urls(service, creator_id, kind, post_id, username),
        "studio": to_studio(service, username),
        "performers": [to_performer(service, creator_id, profile), *mentioned_performers(service, caption, username)],
    }
    if date:
        scene["date"] = date
    if kind == "post":  # DM ids are cum.st-internal UUIDs, not platform post ids
        scene["code"] = post_id
    if tags := [ScrapedTag(name=n) for t in post.get("tags") or [] if (n := tag_name(t))]:
        scene["tags"] = tags
    if image := attachment_image(target or (unlocked[0] if unlocked else {})):
        scene["image"] = image
    return scene


def from_url(url: str) -> ScrapedScene | None:
    if not (m := POST_URL_RE.search(url)):
        log.error(f"Not a cum.st post/DM URL: {url}")
        return None
    return to_scraped_scene(m["service"], m["creator"], m["kind"], m["id"])


def from_hash(sha: str) -> ScrapedScene | None:
    if not (matches := api(f"media/lookup?sha256={sha}")):
        log.info(f"No cum.st match for sha256 {sha}")
        return None
    hit = matches[0]
    return to_scraped_scene(hit["service"], hit["creatorId"], hit.get("kind", "post"), hit["ownerId"], target_sha=sha)


def sha256_of(path: str) -> str:
    log.info(f"Hashing {path} (this can take a while for large files)")
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def from_fragment(fragment: dict) -> ScrapedScene | None:
    # A cum.st URL already on the object is the cheapest and most reliable route
    for url in fragment.get("urls") or []:
        if POST_URL_RE.search(url):
            return from_url(url)

    paths = [p for f in fragment.get("files") or [] if (p := f.get("path"))]
    # Files downloaded from cum.st are named by their sha256, so try that before hashing
    for candidate in [*paths, fragment.get("title") or ""]:
        if m := SHA256_RE.search(candidate):
            return from_hash(m[1].lower())
    for path in paths:
        if os.path.isfile(path):
            return from_hash(sha256_of(path))
    log.warning("No cum.st URL, hash-named file or readable file on this object")
    return None


def without_image(scene: ScrapedScene | None) -> ScrapedGallery | ScrapedImage | None:
    if not scene:
        return None
    return {k: v for k, v in scene.items() if k != "image"}  # type: ignore


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = from_url(url)
        case "scene-by-fragment", fragment:
            result = from_fragment(fragment)
        case "gallery-by-url", {"url": url} if url:
            result = without_image(from_url(url))
        case "gallery-by-fragment", fragment:
            result = without_image(from_fragment(fragment))
        case "image-by-url", {"url": url} if url:
            result = without_image(from_url(url))
        case "image-by-fragment", fragment:
            result = without_image(from_fragment(fragment))
        case _:
            log.error(f"Operation not implemented: {op}")
            sys.exit(1)
    print(json.dumps(result))
