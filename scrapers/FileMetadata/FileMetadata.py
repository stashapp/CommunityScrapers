import json
import os
import sys
import subprocess as sp
from datetime import datetime
from urllib.parse import urlparse

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

def parse_url_from_comment(comment):
    if urlparse(comment).scheme:
        return comment
    
    return None

def metadata_from_primary_path(js):
    scene_id = js["id"]
    scene = graphql.getScene(scene_id)
    scraped_metadata = {}

    if scene is None:
        log.error(f"Could not scrape video: scene not found - {scene_id}")
        return
    
    path = scene["files"][0]["path"]
    if path is None:
        log.error("Could not scrape video: no file path")
        return
    
    video_data = sp.run(["ffprobe", "-loglevel", "error", "-show_entries", "format_tags", "-of", "json", f"{path}"], capture_output=True).stdout
    if video_data is None:
        log.error("Could not scrape video: ffprobe returned null")
        return
    
    metadata = json.loads(video_data)["format"]["tags"]
    metadata_insensitive = {}

    for key in metadata:
        metadata_insensitive[key.lower()] = metadata[key]

    if m_title := metadata_insensitive.get("title"):
        scraped_metadata["title"] = m_title

    if m_comment := metadata_insensitive.get("comment"):
        scraped_metadata["url"] = parse_url_from_comment(m_comment)
    
    if m_description := metadata_insensitive.get("description"):
        scraped_metadata["details"] = m_description

    if m_date := metadata_insensitive.get("date"):
        scraped_metadata["date"] = format_date(m_date)

    if m_artist := metadata_insensitive.get("artist"):
        scraped_metadata["performers"] = [{"name": m_artist}]
        scraped_metadata["studio"] = {"name": m_artist}

    return scraped_metadata

input = sys.stdin.read()
js = json.loads(input)

if sys.argv[1] == "metadata_from_primary":
    ret = metadata_from_primary_path(js)
    print(json.dumps(ret))