import json
import sys
import subprocess as sp
from datetime import datetime
from urllib.parse import urlparse

from py_common import graphql
from py_common import log


def parse_url(comment):
    if urlparse(comment).scheme:
        return comment

    return None


def get_path(scene_id):
    scene = graphql.getScene(scene_id)
    if not scene:
        log.error(f"Scene with ID '{scene_id}' not found")
        return

    if not scene["files"]:
        log.error(f"Scene with ID '{scene_id}' has no files")
        return

    return scene["files"][0]["path"]


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
        scene["date"] = datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d")

    if date := metadata_insensitive.get("creation_time"):
        scene["date"] = date[:10]

    if artist := metadata_insensitive.get("artist"):
        scene["performers"] = [{"name": artist}]
        scene["studio"] = {"name": artist}

    return scene


if __name__ == "__main__":
    fragment = json.loads(sys.stdin.read())
    path = get_path(fragment["id"])
    if not path:
        print("null")
        sys.exit(1)

    scraped = scrape_file(path)
    print(json.dumps(scraped))
