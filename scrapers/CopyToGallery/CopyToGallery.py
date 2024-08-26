import json
import sys
from pathlib import Path

import py_common.graphql as graphql
import py_common.log as log
from py_common.config import get_config
from py_common.util import dig


config = get_config(
    default="""
find_missing_galleries = False
"""
)


def get_gallery_id_by_path(abs_path):
    abs_path = str(abs_path.resolve())
    log.debug(f"Finding gallery associated with path '{abs_path}'")
    query = """
query FindGalleries($galleries_filter: GalleryFilterType) {
  findGalleries(gallery_filter: $galleries_filter filter: {per_page: -1}) {
    galleries {
      id
    }
  }
}
"""
    variables = {
        "galleries_filter": {"path": {"value": abs_path, "modifier": "EQUALS"}}
    }
    result = graphql.callGraphQL(query, variables)
    if (
        result is None
        or (gallery_id := dig(result, "findGalleries", "galleries", 0, "id")) is None
    ):
        log.error(
            f"Found gallery with path '{abs_path}' but it needs to be added into Stash with a scan first"
        )
        exit(1)

    log.debug(f"Found gallery {gallery_id} with path '{abs_path}'")
    return gallery_id


def update_gallery(input):
    log.debug(f"Updating gallery {input['id']}")
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
    if not result:
        log.error(f"Failed to update gallery {input['id']}")
        sys.exit(1)

    g_id = result["galleryUpdate"]["id"]
    g_title = result["galleryUpdate"]["title"]
    log.info(f"Updated gallery {g_id}: {g_title}")


def add_galleries_to_scene(scene_id, gallery_ids):
    data = {"id": scene_id, "gallery_ids": gallery_ids}
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
    if not result:
        log.error(f"Failed to update scene {scene_id}")
        sys.exit(1)


def find_galleries(scene_id, scene_path):
    directory_path = Path(scene_path).parent
    log.debug(f"Searching for galleries in {directory_path.resolve()}")
    return [
        get_gallery_id_by_path(f) for f in directory_path.glob("*.zip") if f.is_file()
    ]


FRAGMENT = json.loads(sys.stdin.read())
log.debug("FRAGMENT " + str(FRAGMENT))
SCENE_ID = FRAGMENT.get("id")

scene = graphql.getScene(SCENE_ID)
if not scene:
    log.error(f"Scene with id '{SCENE_ID}' not found")
    sys.exit(1)


gallery_ids = [g["id"] for g in scene["galleries"]]
if not gallery_ids and config.find_missing_galleries:
    log.debug(
        f"No galleries associated with scene {SCENE_ID}, searching for zips in folder..."
    )
    gallery_ids = find_galleries(SCENE_ID, scene["files"][0]["path"])

if not gallery_ids:
    log.debug("No galleries found, exiting")

word = "gallery" if len(gallery_ids) == 1 else "galleries"
log.debug(f"Scene has {len(gallery_ids)} {word}: {','.join(gallery_ids)}")

gallery_input = {
    "urls": scene["urls"],
    "title": scene["title"],
    "code": scene["code"],
    "date": scene["date"],
    "details": scene["details"],
    "tag_ids": [t["id"] for t in scene["tags"]],
    "performer_ids": [p["id"] for p in scene["performers"]],
    "studio_id": dig(scene, "studio", "id"),
}

for gallery_id in gallery_ids:
    update_gallery({"id": gallery_id, **gallery_input})

add_galleries_to_scene(SCENE_ID, gallery_ids)

print(json.dumps({}))
