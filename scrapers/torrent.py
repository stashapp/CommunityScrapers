import sys
import json
from os.path import basename
from pathlib import Path
import re
from datetime import datetime
import difflib

try:
    from bencoder import bdecode
except ModuleNotFoundError:
    print("You need to install the 'bencoder.pyx' module. (https://pypi.org/project/bencoder.pyx/)", file=sys.stderr)
    sys.exit()

try:
    from py_common import graphql
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

def process_tags_performers(tagList):
    return map(lambda tag: decode_bytes(tag).replace('.', ' '), tagList)

def process_description_bbcode(description):
    res = re.sub(r'\[(?:b|i|u|s|url|quote)?\](.*)?\[\/(?:b|i|u|s|url|quote)\]',r"\1", description )
    res = re.sub(r'\[.*?\].*?\[\/.*?\]',r'',res)
    res = re.sub(r'\[.*?\]',r'',res)
    return res.strip()

def get_torrent_metadata(torrent_data):
    res = {}

    if b"metadata" in torrent_data:
        if b"title" in torrent_data[b"metadata"]:
            res["title"] = decode_bytes(torrent_data[b"metadata"][b"title"])
        if b"cover url" in torrent_data[b"metadata"]:
            res["image"] = decode_bytes(torrent_data[b"metadata"][b"cover url"])
        if b"description" in torrent_data[b"metadata"]:
            res["details"] = process_description_bbcode(decode_bytes(torrent_data[b"metadata"][b"description"]))
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
                    return get_torrent_metadata(torrent_data)
    return {}

def similarity_file_name(search, fileName):
    result = difflib.SequenceMatcher(a=search.lower(), b=fileName.lower())
    return result.ratio()

def cleanup_name(name):
    ret = str(name)
    ret = ret.removeprefix("torrents\\").removesuffix(".torrent")
    return ret


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(process_torrents(get_scene_data(fragment))))
elif sys.argv[1] == "fragment":
    filename = json.loads(sys.stdin.read()).get('url')
    with open(filename, 'rb') as f:
        torrent_data = bdecode(f.read())
        print(json.dumps(get_torrent_metadata(torrent_data)))
elif sys.argv[1] == "search":
    search = json.loads(sys.stdin.read()).get('name')
    torrents = list(TORRENTS_PATH.rglob('*.torrent'))
    ratios = {}
    for t in torrents:
        clean_t = cleanup_name(t)
        ratios[round(10000*(1-similarity_file_name(search, clean_t)))] = {'url': str(t.absolute()), 'title': clean_t}

    # Order ratios and return the top 5 results
    if len(ratios) > 0:
        ratios_sorted = list(ratios.keys())
        ratios_sorted.sort()
        ratios_filtered = (ratios[i] for i in ratios_sorted[:5])
        print(json.dumps(list(ratios_filtered)))

# Last Updated December 16, 2022
