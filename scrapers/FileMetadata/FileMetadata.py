import json
import sys
import subprocess as sp
from datetime import datetime
from urllib.parse import urlparse

from py_common import log


def parse_url(comment):
    if urlparse(comment).scheme:
        return comment

    return None


def scrape_file(path):
    video_data = sp.check_output(
        [
            "ffprobe",
            "-loglevel",
            "error",
            "-show_entries",
            "format_tags",
            "-of",
            "json",
            f"{path}",
        ],
        text=True,
    )
    if not video_data:
        log.error("Could not scrape video: ffprobe returned null")
        return

    metadata = json.loads(video_data)["format"]["tags"]
    metadata_insensitive = {key.lower(): metadata[key] for key in metadata}

    scene = {}
    if title := metadata_insensitive.get("title"):
        scene["title"] = title

    if (comment := metadata_insensitive.get("comment")) and (url := parse_url(comment)):
        scene["url"] = url

    if description := metadata_insensitive.get("description"):
        scene["details"] = description

    if date := metadata_insensitive.get("date"):
        scene["date"] = datetime.fromisoformat(date).strftime("%Y-%m-%d")

    if date := metadata_insensitive.get("creation_time"):
        scene["date"] = date[:10]

    if artist := metadata_insensitive.get("artist"):
        scene["performers"] = [{"name": artist}]
        scene["studio"] = {"name": artist}

    return scene


if __name__ == "__main__":
    fragment = json.loads(sys.stdin.read())
    scene_id = fragment["id"]

    if "files" not in fragment:
        log.error(f"Cannot scrape scene {scene_id} because it contains no files")
        print("null")
        sys.exit(0)

    paths = [f["path"] for f in fragment["files"]]
    path = paths.pop(0)
    if paths:
        log.debug(
            f"Scene {scene_id} has multiple files, only scraping the first one: {path}"
        )

    scraped = scrape_file(path)
    print(json.dumps(scraped))
