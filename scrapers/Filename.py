import json
import os
import sys

try:
    from py_common import graphql
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

REMOVE_EXT = False  # remove file extension from title


def title_from_filename(js):
    scene_id = js['id']
    scene_title = js['title']
    response = graphql.callGraphQL("""
    query FilenameBySceneId($id: ID){
      findScene(id: $id){
        path
      }
    }""", {"id": scene_id})
    path = response["findScene"]["path"]
    filename = os.path.basename(path)
    if REMOVE_EXT:
        filename = os.path.splitext(filename)[0]
    if scene_title != filename:
        log.info(f"Scene {scene_id}: Title differs from filename: '{scene_title}' => '{filename}'")
        return {"title": filename}
    return {}


input = sys.stdin.read()
js = json.loads(input)

if sys.argv[1] == "title_from_filename":
    ret = title_from_filename(js)
    print(json.dumps(ret))
