import json
import os
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

find_gallery = True


def get_gallery_id_by_path(gallery_path):
    log.debug("get_gallery_by_path gallery_path " + str(gallery_path))
    query = """
query FindGalleries($galleries_filter: GalleryFilterType) {
  findGalleries(gallery_filter: $galleries_filter filter: {per_page: -1}) {
  count
    galleries {
      id
    }
  }
}
"""
    variables = {
        "galleries_filter": {"path": {"value": gallery_path, "modifier": "EQUALS"}}
    }
    result = graphql.callGraphQL(query, variables)
    log.debug("get_gallery_by_path callGraphQL result " + str(result))
    return result["findGalleries"]["galleries"][0]["id"]


def update_gallery(input):
    log.debug("gallery input " + str(input))
    query = """
mutation GalleryUpdate($input : GalleryUpdateInput!) {
  galleryUpdate(input: $input) {
    id
    title
  }
}
"""
    variables = {"input": input}
    result = graphql.callGraphQL(query, variables)
    if result:
        g_id = result["galleryUpdate"].get("id")
        g_title = result["galleryUpdate"].get("title")
        log.info(f"updated Gallery ({g_id}): {g_title}")
    return result


def updateScene_with_gallery(scene_id, gallery_id):
    data = {"id": scene_id, "gallery_ids": [gallery_id]}
    log.debug("data " + str(data))
    query = """
mutation SceneUpdate($input : SceneUpdateInput!) {
  sceneUpdate(input: $input) {
    id
    title
  }
}
"""
    variables = {"input": data}
    result = graphql.callGraphQL(query, variables)
    log.debug("graphql_updateGallery callGraphQL result " + str(result))


def find_galleries(scene_id, scene_path):
    ids = []
    directory_path = os.path.dirname(scene_path)
    for cur, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".zip"):
                gallery_path = os.path.join(cur, file)
                id = get_gallery_id_by_path(gallery_path)
                updateScene_with_gallery(scene_id, id)
                ids.append(id)
        break
    log.debug("find_galleries ids' found " + str(ids))
    return ids


FRAGMENT = json.loads(sys.stdin.read())
log.debug("FRAGMENT " + str(FRAGMENT))
SCENE_ID = FRAGMENT.get("id")

scene = graphql.getScene(SCENE_ID)
if not scene:
    log.error("scene not found")
    sys.exit(1)

scene_galleries = scene["galleries"]
log.debug("scene_galleries " + str(scene_galleries))
gallery_ids = [g["id"] for g in scene_galleries]
if not gallery_ids and find_galleries:
    # if no galleries are associated see if any gallery zips exist in directory
    gallery_ids = find_galleries(SCENE_ID, scene["files"][0]["path"])
log.debug("gallery_ids " + str(gallery_ids))

for gallery_id in gallery_ids:
    gallery_input = {
        "id": gallery_id,
        "urls": scene["urls"],
        "title": scene["title"],
        "code": scene["code"],
        "date": scene["date"],
        "details": scene["details"],
        "tag_ids": [t["id"] for t in scene["tags"]],
        "performer_ids": [p["id"] for p in scene["performers"]],
    }
    if scene["studio"]:
        gallery_input["scene_ids"] = scene["studio"]["id"]
    update_gallery(gallery_input)

print(json.dumps({}))
