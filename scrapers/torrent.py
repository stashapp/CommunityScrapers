import sys
import json
from os import walk
from os.path import join, dirname, realpath, basename

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

TORRENTS_PATH = join(dirname(dirname(realpath(__file__))), "torrents")


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

    if response:
        for f in response["findScene"]["files"]:
            scene_files.append({"filename": basename(f["path"]), "size": f["size"]})
        return {"id": scene_id, "title": scene_title, "files": scene_files}
    return {}


def get_torrent_metadata(scene_data, torrent_data):
    res = {"title": scene_data["title"], "url": decode_bytes(torrent_data[b"comment"])}
    if b"metadata" in torrent_data:
        if b"title" in torrent_data[b"metadata"]:
            res["title"] = decode_bytes(torrent_data[b"metadata"][b"title"])
        if b"cover url" in torrent_data[b"metadata"]:
            res["image"] = decode_bytes(torrent_data[b"metadata"][b"cover url"])
        if b"description" in torrent_data[b"metadata"]:
            res["details"] = decode_bytes(torrent_data[b"metadata"][b"description"])
        if b"taglist" in torrent_data[b"metadata"]:
            res["tags"] = [{"name": decode_bytes(t)} for t in torrent_data[b"metadata"][b"taglist"]]
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
    for root, dirs, files in walk(TORRENTS_PATH):
        for name in files:
            if name.endswith(".torrent"):
                with open(join(root, name), "rb") as f:
                    torrent_data = bdecode(f.read())
                    if scene_in_torrent(scene_data, torrent_data):
                        return get_torrent_metadata(scene_data, torrent_data)
    return {}


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(process_torrents(get_scene_data(fragment))))
# Last Updated December 12, 2022
