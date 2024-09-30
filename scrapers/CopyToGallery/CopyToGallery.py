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

# Fields to copy from Gallery to Images
title = False
studiocode = False
details = False
photographer = True
date = True
tags = False
performers = True
studio = True
urls = False

# ADD to existing values or SET
tagsmode = ADD
performersmode = ADD
urlsmode = ADD

# Filters
filtergender = False
# Values can be MALE, FEMALE, TRANSGENDER_MALE, TRANSGENDER_FEMALE, INTERSEX, NON_BINARY
gendervalue = MALE
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
    sys.exit(0)

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

def update_images(input):
    log.debug("Updating images")
    query = """
        mutation bulkImageUpdate($input : BulkImageUpdateInput!) {
            bulkImageUpdate(input: $input) {
                id
            }
        }
        """
    variables = {"input": input}
    result = graphql.callGraphQL(query, variables)
    if not result:
        log.error("Failed to update images")
        sys.exit(1)


def find_images(input):
    query = """
        query FindImages($image_filter: ImageFilterType, $filter:FindFilterType) {
            findImages(image_filter: $image_filter, filter: $filter) {
                images {
                    id
                }
            }
        }
        """
    variables = {
        "image_filter": {"galleries": {"value": input, "modifier": "INCLUDES_ALL"}},
        "filter": {"per_page": -1},
    }

    result = graphql.callGraphQL(query, variables)
    if not result:
        log.error(f"Failed to find images {input['id']}")
        sys.exit(1)

    return result

GALLERY_ID = gallery_ids[0]

gallery = graphql.getGallery(GALLERY_ID)
log.debug(gallery)
if not gallery:
    log.error(f"Gallery with id '{GALLERY_ID}' not found")
    sys.exit(1)

image_ids = find_images(GALLERY_ID)["findImages"]["images"]
if not image_ids:
    log.error("No images found, exiting")
    sys.exit(1)

images_input: dict[str, str | list | dict[str, list]] = {
    "ids": [i["id"] for i in image_ids]
}

if config.title is True:
    images_input["title"] = gallery["title"]

if config.studiocode is True:
    images_input["code"] = gallery["code"]

if config.details is True:
    images_input["details"] = gallery["details"]

if config.photographer is True:
    images_input["photographer"] = gallery["photographer"]

if config.date is True:
    images_input["date"] = gallery["date"]

if config.studio is True:
    images_input["studio_id"] = dig(gallery, "studio", "id")

if config.title is True:
    images_input["title"] = gallery["title"]

if config.tags is True:
    images_input["tag_ids"] = {
        "mode": config.tagsmode,
        "ids": [t["id"] for t in gallery["tags"]],
    }

if config.performers is True:
    if config.filtergender is True:
        images_input["performer_ids"] = {
            "mode": config.performersmode,
            "ids": [p["id"] for p in gallery["performers"] if p["gender"] != config.gendervalue],
        }
    else:
        images_input["performer_ids"] = {
            "mode": config.performersmode,
            "ids": [p["id"] for p in gallery["performers"]],
        }

if config.urls is True:
    images_input["urls"] = {
        "mode": config.urlsmode,
        "values": gallery["urls"],
    }

log.debug(images_input)

update_images(images_input)

print(json.dumps({}))
