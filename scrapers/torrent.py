import sys
import json
from os import walk
from os.path import join, dirname, realpath, basename

try:
    from py_common import graphql
    from torrent_parser import parse_torrent_file
except ModuleNotFoundError:
    print("You need to download the file 'torrent_parser.py' from the community repo! "
          "(CommunityScrapers/tree/master/scrapers/torrent_parser.py)", file=sys.stderr)
    sys.exit()
'''  This script parses all torrent files in the specified directory for embedded metadata.
     The title can either be a filename or the filename of the .torrent file
     
     This requires python3.
     This uses the torrent_parser library to parse torrent files from: https://github.com/7sDream/torrent_parser
     This library is under the MIT Licence.
'''

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
    res = {"title": scene_data["title"], "url": torrent_data["comment"]}
    if "metadata" in torrent_data:
        if "title" in torrent_data["metadata"]:
            res["title"] = torrent_data["metadata"]["title"]
        if "cover url" in torrent_data["metadata"]:
            res["image"] = torrent_data["metadata"]["cover url"]
        if "description" in torrent_data["metadata"]:
            res["details"] = torrent_data["metadata"]["description"]
        if "taglist" in torrent_data["metadata"]:
            res["tags"] = [{"name": t} for t in torrent_data["metadata"]["taglist"]]
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
        if "length" in torrent_data["info"]:
            if scene["filename"] in torrent_data["info"]["name"] and torrent_data["info"]["length"] == scene["size"]:
                return True
        elif "files" in torrent_data["info"]:
            for file in torrent_data["info"]["files"]:
                file_name = file["path"][-1]
                if type(file_name) is bytes:
                    file_name = decode_bytes(file_name)
                if scene["filename"] in file_name and file["length"] == scene["size"]:
                    return True


def process_torrents(scene_data):
    for root, dirs, files in walk(TORRENTS_PATH):
        for name in files:
            if name.endswith(".torrent"):
                torrent_data = parse_torrent_file(join(root, name))
                if scene_in_torrent(scene_data, torrent_data):
                    return get_torrent_metadata(scene_data, torrent_data)
    return {}


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(process_torrents(get_scene_data(fragment))))
# Last Updated December 07, 2022
