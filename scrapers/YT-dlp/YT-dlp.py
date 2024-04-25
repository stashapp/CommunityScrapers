import json
import os
import sys
import datetime
from pathlib import Path

from py_common import graphql
from py_common import log

## This scraper assumes that the JSON files are stored in the same directory as the video files,
## with the same name, but with .info.json or .json extensions. You can add a second directory to check
## for JSON files here. JSON file names here must match the original media file name, but with a
## .info.json or .json extension. JSON files will be taken from the media's folder first, and if not
## present there a suitably named JSON file in the below directory will be used.
alternate_json_dir = ""


def scene_from_json(scene_id):
    response = graphql.callGraphQL(
        """
    query FilenameBySceneId($id: ID){
      findScene(id: $id){
        files {
          path
        }
      }
    }""",
        {"id": scene_id},
    )
    assert response is not None
    file = next(iter(response["findScene"]["files"]), None)
    if not file:
        log.debug(f"No files found for scene {scene_id}")
        return None

    file_path = Path(file["path"])
    json_files = [file_path.with_suffix(suffix) for suffix in (".info.json", ".json")]

    if alternate_json_dir:
        json_files += [Path(alternate_json_dir) / p.name for p in json_files]

    json_file = next((f for f in json_files if f.exists()), None)

    if not json_file:
        paths = "', '".join(str(p) for p in json_files)
        log.debug(f"No JSON file found for '{file_path}': tried '{paths}'")
        return None

    scene = {}

    log.debug(f"Found JSON file: '{json_file}'")

    yt_json = json.loads(json_file.read_text(encoding="utf-8"))

    if title := yt_json.get("title"):
        scene["title"] = title
    if thumbnail := yt_json.get("thumbnail"):
        scene["image"] = thumbnail
    if url := yt_json.get("webpage_url"):
        scene["url"] = url
    scene["performers"] = [{"name": actor} for actor in yt_json.get("cast", [])]

    tags = yt_json.get("tags", []) + yt_json.get("categories", [])
    scene["tags"] = [{"name": tag} for tag in tags]

    tubesite = yt_json.get("extractor", "UNKNOWN")
    upload_on = yt_json.get("upload_date", "UNKNOWN")
    upload_by = yt_json.get("uploader", "UNKNOWN")

    if upload_on != "UNKNOWN":
        s = datetime.datetime.strptime(upload_on, "%Y%m%d")
        upload_on = s.strftime("%B %d, %Y")
        scene["date"] = s.strftime("%Y-%m-%d")

    scene["details"] = f"Uploaded to {tubesite} on {upload_on} by {upload_by}"

    return scene


if __name__ == "__main__":
    input = sys.stdin.read()
    js = json.loads(input)
    scene_id = js["id"]
    ret = scene_from_json(scene_id)
    log.debug(json.dumps(ret))
    print(json.dumps(ret))
