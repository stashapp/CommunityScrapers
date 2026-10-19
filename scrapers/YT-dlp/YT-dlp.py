import json
import re
import sys
from pathlib import Path
from typing import Any

from py_common import log
from py_common.config import get_config
from py_common.types import ScrapedScene, ScrapedTag
from py_common.util import scraper_args

config = get_config(
    default="""
# yt-dlp's --write-info-json files are looked for next to the video first
# (<video name>.info.json or <video name>.json), then in this folder, if set
alternate_json_dir =
"""
)


def find_json(video: Path) -> Path | None:
    candidates = [video.with_suffix(suffix) for suffix in (".info.json", ".json")]
    if alternate := str(config.alternate_json_dir).strip():
        candidates += [Path(alternate) / candidate.name for candidate in candidates]
    if found := next((path for path in candidates if path.exists()), None):
        return found
    log.debug(f"No JSON file for '{video}', tried: {', '.join(map(str, candidates))}")
    return None


def to_date(yyyymmdd: str | None) -> str | None:
    if yyyymmdd and re.fullmatch(r"\d{8}", yyyymmdd):
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return None


def to_scraped_scene(info: dict[str, Any]) -> ScrapedScene:
    scene: ScrapedScene = {}
    if title := info.get("title"):
        scene["title"] = title
    if description := (info.get("description") or "").strip():
        scene["details"] = description
    if url := info.get("webpage_url"):
        scene["urls"] = [url]
    if thumbnail := info.get("thumbnail"):
        scene["image"] = thumbnail
    # release_date is the original release when the site states one, upload_date the posting
    if date := to_date(info.get("release_date")) or to_date(info.get("upload_date")):
        scene["date"] = date
    if (duration := info.get("duration")) and duration >= 10:
        scene["duration"] = int(duration)
    if cast := info.get("cast"):
        scene["performers"] = [{"name": name} for name in cast if name]
    # Categories first: where both exist they're the site's curated spelling of the tags
    tags: dict[str, str] = {}
    for tag in (info.get("categories") or []) + (info.get("tags") or []):
        if tag:
            tags.setdefault(tag.casefold(), tag)
    if tags:
        scene["tags"] = [ScrapedTag(name=tag) for tag in tags.values()]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-fragment", {"files": list() as files} if files:
            if json_file := next(
                (
                    found
                    for file in files
                    if (path := file.get("path")) and (found := find_json(Path(path)))
                ),
                None,
            ):
                log.debug(f"Reading '{json_file}'")
                info = json.loads(json_file.read_text(encoding="utf-8"))
                print(json.dumps(to_scraped_scene(info)))
            else:
                print("null")
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
