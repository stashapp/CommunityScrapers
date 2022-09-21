import json
import os
import sys

from py_common import graphql
from py_common import log


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
    if scene_title != filename:
        log.info(f"Scene {scene_id}: Title differs from filename: '{scene_title}' => '{filename}'")
        return {"title": filename}
    return {}


input = sys.stdin.read()
js = json.loads(input)

if sys.argv[1] == "title_from_filename":
    ret = title_from_filename(js)
    print(json.dumps(ret))
