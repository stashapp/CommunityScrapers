import json
import os
import pathlib
import re
import sys
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

def findTagbyName(name):
    query = """
        query {
            allTags {
                id
                name
                aliases
            }
        }
    """
    result = graphql.callGraphQL(query)
    for tag in result["allTags"]:
        if tag["name"] == name:
            return tag["id"]
        if tag.get("aliases"):
            for alias in tag["aliases"]:
                if alias == name:
                    return tag["id"]
    return None

def createMarker(scene_id, title, main_tag, seconds, tags=[]):
    main_tag_id = findTagbyName(main_tag)
    if main_tag_id is None:
        log.debug(f"The 'Primary Tag' don't exist ({main_tag}), marker won't be created.")
        return None
    log.debug(f"Creating Marker: {title}")
    query = """
    mutation SceneMarkerCreate($title: String!, $seconds: Float!, $scene_id: ID!, $primary_tag_id: ID!, $tag_ids: [ID!] = []) {
        sceneMarkerCreate(
            input: {
            title: $title
            seconds: $seconds
            scene_id: $scene_id
            primary_tag_id: $primary_tag_id
            tag_ids: $tag_ids
            }
        ) {
            ...SceneMarkerData
        }
    }
    fragment SceneMarkerData on SceneMarker {
        id
        title
        seconds
        stream
        preview
        screenshot
        scene {
            id
        }
        primary_tag {
            id
            name
            aliases
        }
        tags {
            id
            name
            aliases
        }
    }
    """
    variables = {
        "primary_tag_id": main_tag_id,
        "scene_id":	scene_id,
        "seconds":	seconds,
        "title": title,
        "tag_ids": tags
    }
    result = graphql.callGraphQL(query, variables)
    return result

def getMarker(scene_id):
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            scene_markers {
                seconds
            }
        }
    }
    """
    variables = {
        "id": scene_id
    }
    result = graphql.callGraphQL(query, variables)
    if result:
        if result["findScene"].get("scene_markers"):
            return [x.get("seconds") for x in result["findScene"]["scene_markers"]]
    return None

def getScene(scene_id):
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            file {
                duration
            }
            scene_markers {
                seconds
            }
        }
    }
    """
    variables = {
        "id": scene_id
    }
    result = graphql.callGraphQL(query, variables)
    if result:
        return_dict = {}
        return_dict["duration"] = result["findScene"]["file"]["duration"]
        if result["findScene"].get("scene_markers"):
            return_dict["marker"] = [x.get("seconds") for x in result["findScene"]["scene_markers"]]
        else:
            return_dict["marker"] = None
        return return_dict
    return None