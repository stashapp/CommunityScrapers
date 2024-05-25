import json
import sys
import os

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.graphql as graphql
    import py_common.log as log
    from py_common.config import get_config
    from py_common.util import dig
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! "
        "(CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

config = get_config(
    default="""
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
"""
)

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
        log.error(f"Failed to update images")
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
        "image_filter": {
            "galleries":{
                "value": input,
                "modifier": "INCLUDES_ALL"
            }
        },
        "filter": {
            "per_page": -1
        }
    }

    result = graphql.callGraphQL(query, variables)
    if not result:
        log.error(f"Failed to find images {input['id']}")
        sys.exit(1)

    return result

FRAGMENT = json.loads(sys.stdin.read())
log.debug("FRAGMENT " + str(FRAGMENT))
GALLERY_ID = FRAGMENT.get("id")

gallery = graphql.getGallery(GALLERY_ID)
log.debug(gallery)
if not gallery:
    log.error(f"Gallery with id '{GALLERY_ID}' not found")
    sys.exit(1)

image_ids = find_images(GALLERY_ID)["findImages"]["images"]
if not image_ids:
    log.error("No images found, exiting")
    sys.exit(1)

images_input : dict[str, str | list | dict[str, list]] = {
    "ids": [i["id"] for i in image_ids]
}

if config.title == True:
    images_input["title"] = gallery["title"]

if config.studiocode == True:
    images_input["code"] = gallery["code"]

if config.details == True:
    images_input["details"] = gallery["details"]

if config.photographer == True:
    images_input["photographer"] = gallery["photographer"]

if config.date == True:
    images_input["date"] = gallery["date"]
    
if config.studio == True:   
    images_input["studio_id"] = dig(gallery, "studio", "id")

if config.title == True:
    images_input["title"] = gallery["title"]

if config.tags == True:
    images_input["tag_ids"] = {
        "mode": config.tagsmode,
        "ids":  [t["id"] for t in gallery["tags"]],
    }

if config.performers == True:
    images_input["performer_ids"] = {
        "mode": config.performersmode,
        "ids": [p["id"] for p in gallery["performers"]],
    }

if config.urls == True:
    images_input["urls"] = {
        "mode": config.urlsmode,
        "values":  gallery["urls"],
    }

log.debug(images_input)
    
update_images(images_input)

print(json.dumps({}))