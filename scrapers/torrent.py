import sys
import json
from os import walk
from os.path import join, dirname, realpath, basename
from pathlib import Path
import re
from datetime import datetime

try:
    from bencoder import bdecode
except ModuleNotFoundError:
    print("You need to install the 'bencoder.pyx' module. (https://pypi.org/project/bencoder.pyx/)", file=sys.stderr)
    sys.exit()

try:
    from py_common import graphql, log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! "
          "(CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

TORRENTS_PATH = Path("torrents")


def get_scene_data(fragment_data):
    scene_id = fragment_data["id"]
    scene_title = fragment_data["title"]
    scene_files = []

    response = graphql.callGraphQL("""
    query FileInfoBySceneId($id: ID) {
      findScene(id: $id) {
        files {
          path
          size
        }
      }
    }""", {"id": scene_id})

    if response and response["findScene"]:
        for f in response["findScene"]["files"]:
            scene_files.append({"filename": basename(f["path"]), "size": f["size"]})
        return {"id": scene_id, "title": scene_title, "files": scene_files}
    return {}

def readJSONInput():
    input = sys.stdin.read()
    log.debug(input)
    return json.loads(input)

def process_tags_performers(tagList):
    return map(lambda tag: decode_bytes(tag).replace('.', ' '), tagList)

def procress_description_bbcode(description):
    res = re.sub('\[.*?\].*?\[\/.*?\]','',description)
    res = re.sub('\[.*?\]','',res)
    return res.rstrip()



def get_torrent_metadata(scene_data, torrent_data):
    res = {"title": scene_data["title"], "url": decode_bytes(torrent_data[b"comment"])}
    if b"metadata" in torrent_data:
        if b"title" in torrent_data[b"metadata"]:
            res["title"] = decode_bytes(torrent_data[b"metadata"][b"title"])
        if b"cover url" in torrent_data[b"metadata"]:
            res["image"] = decode_bytes(torrent_data[b"metadata"][b"cover url"])
        if b"description" in torrent_data[b"metadata"]:
            res["details"] = procress_description_bbcode(decode_bytes(torrent_data[b"metadata"][b"description"]))
        if b"taglist" in torrent_data[b"metadata"]:
            res["tags"] = [{"name": decode_bytes(t)} for t in torrent_data[b"metadata"][b"taglist"]]
        if b"taglist" in torrent_data[b"metadata"]:
            res["performers"]=[{"name":x} for x in process_tags_performers(torrent_data[b"metadata"][b"taglist"])]
        if b"comment" in torrent_data:
            res["url"] = decode_bytes(torrent_data[b"comment"])
        if b"creation date" in torrent_data:
            res["date"] = datetime.fromtimestamp(torrent_data[b"creation date"]).strftime("%Y-%m-%d")
    return res


def decode_bytes(s, encodings=("utf-8", "latin-1")):
    for enc in encodings:
        try:
            return s.decode(enc)
        except UnicodeDecodeError:
            pass
    return s.decode("utf-8", "ignore")


def scene_in_torrent(scene_data, torrent_data):
    for scene in scene_data["files"]:
        if b"length" in torrent_data[b"info"]:
            if scene["filename"] in decode_bytes(torrent_data[b"info"][b"name"]) and torrent_data[b"info"][b"length"] == scene["size"]:
                return True
        elif b"files" in torrent_data[b"info"]:
            for file in torrent_data[b"info"][b"files"]:
                if scene["filename"] in decode_bytes(file[b"path"][-1]) and file[b"length"] == scene["size"]:
                    return True


def process_torrents(scene_data):
    if scene_data:
        for name in TORRENTS_PATH.glob("*.torrent"):
            with open(name, "rb") as f:
                torrent_data = bdecode(f.read())
                if scene_in_torrent(scene_data, torrent_data):
                    return get_torrent_metadata(scene_data, torrent_data)
    return {}


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(process_torrents(get_scene_data(fragment))))


# Last Updated December 16, 2022
