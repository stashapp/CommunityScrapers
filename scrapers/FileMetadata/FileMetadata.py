import json
import os
import sys
import subprocess as sp
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

try:
    from py_common import graphql
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

def format_date(date):
    return datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')

def parse_performers(performers):
    performers_array = []
    query = graphql.getPerformersByName(performers)["performers"]

    for performer in query:
        performers_array.append({"name": performer["name"]})

    return performers_array

def metadata_from_primary_path(js):
    scene_id = js["id"]
    scene = graphql.getScene(scene_id)

    scraped_metadata = {}

    if scene is not None:
        path = scene["files"][0]["path"]

        if path is not None:
            video_data = sp.run(["ffprobe", "-loglevel", "error", "-show_entries", "format_tags", "-of", "json", f"{path}"], capture_output=True).stdout
            if video_data is not None:
                metadata = json.loads(video_data)["format"]["tags"]
                metadata_insensitive = {}

                for key in metadata:
                    metadata_insensitive[key.lower()] = metadata[key]

                if metadata_insensitive.__contains__("title"):
                    scraped_metadata["title"] = metadata_insensitive["title"]
                
                if metadata_insensitive.__contains__("description"):
                    scraped_metadata["details"] = metadata_insensitive["description"]
                
                if metadata_insensitive.__contains__("date"):
                    scraped_metadata["date"] = format_date(metadata_insensitive["date"])

                if metadata_insensitive.__contains__("artist"):
                    scraped_metadata["performers"] = parse_performers(metadata_insensitive["artist"])

                return scraped_metadata
            else:
                log.error("Could not scrape video: ffprobe returned null")
                return
        else:
            log.error("Could not scrape video: no file path")
            return
    else:
        log.error(f"Could not scrape video: scene not found - {scene_id}")
        return

input = sys.stdin.read()
js = json.loads(input)

if sys.argv[1] == "metadata_from_primary":
    ret = metadata_from_primary_path(js)
    print(json.dumps(ret))