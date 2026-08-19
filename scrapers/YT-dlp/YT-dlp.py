import json
import os
import sys
import datetime
from pathlib import Path

from py_common import graphql
from py_common import log

# This scraper assumes that the JSON files are stored in the same directory as the video files,
# with the same name, but with .info.json or .json extensions. You can add a second directory to check
# for JSON files here. JSON file names here must match the original media file name, but with a
# .info.json or .json extension. JSON files will be taken from the media's folder first, and if not
# present there a suitably named JSON file in the below directory will be used.
alternate_json_dir = ""


def scene_from_json(scene_id):

    #
    # Load the scene and the JSON.
    #
    log.debug(f"Loading for JSON file for scene {scene_id}")
    response = graphql.callGraphQL(
        """
    query FilenameBySceneId($id: ID){
      findScene(id: $id){
        files {
          path
        }
      }
    }""",
        {"id": scene_id},
    )
    assert response is not None
    file = next(iter(response["findScene"]["files"]), None)
    log.debug(f"Found file for scene {scene_id}: {file}")
    if not file:
        log.debug(f"No files found for scene {scene_id}")
        return None

    file_path = Path(file["path"])
    json_files = [file_path.with_suffix(suffix)
                  for suffix in (".info.json", ".json")]
    log.debug(
        f"Looking for JSON files for '{file_path}': {[str(p) for p in json_files]}")

    if alternate_json_dir:
        json_files += [Path(alternate_json_dir) / p.name for p in json_files]

    json_file = next((f for f in json_files if f.exists()), None)

    if not json_file:
        paths = "', '".join(str(p) for p in json_files)
        log.debug(f"No JSON file found for '{file_path}': tried '{paths}'")
        return None

    log.debug(f" JSON file: '{json_file}'")

    #
    # Extract the data from the JSON and insert into the scene dictionary.
    #

    # Get the existing scene data from the GraphQL API.
    scene = graphql.getScene(scene_id)

    # Read the JSON file.
    yt_json = json.loads(json_file.read_text(encoding="utf-8"))

    # Title
    if title := yt_json.get("title"):
        scene["title"] = title
        log.debug(f" title: {title}")

        # Thumbnail
    if thumbnail := yt_json.get("thumbnail"):
        scene["image"] = thumbnail
        log.debug(f" thumbnail: {thumbnail}")

        # URL
    if url := yt_json.get("webpage_url"):
        scene["url"] = url
        log.debug(f" webpage_url: {url}")

        # Performers
    scene["performers"] = [{"name": actor}
                           for actor in yt_json.get("cast", [])]
    log.debug(f" performers: ")

    # Tags and categories
    tags = yt_json.get("tags", []) + yt_json.get("categories", [])
    scene["tags"] = [{"name": tag} for tag in tags]
    log.debug(f" tags: {[tag['name'] for tag in scene['tags']]}")

    # Extractor
    # This is the extractor name, not the tubesite name. For example, "generic" is an extractor that was used to extract from a site "mysupervids.com".
    extractor = yt_json.get("extractor", "UNKNOWN")
    log.debug(f" extractor: {extractor}")

    # Tubesite
    # This is the tubesite name, extracted from the URL.
    tubesite = url.split(
        "/")[2].split(".")[-2] if url != "UNKNOWN" else "UNKNOWN"
    log.debug(f" tubesite: {tubesite}")

    # Upload date
    upload_on = yt_json.get("upload_date", "UNKNOWN")
    log.debug(f" upload date: {upload_on}")
    # Friendly date format
    if upload_on != "UNKNOWN":
        s = datetime.datetime.strptime(upload_on, "%Y%m%d")
        upload_on = s.strftime("%B %d, %Y")
        scene["date"] = s.strftime("%Y-%m-%d")

        # Uploader
    upload_by = yt_json.get("uploader", "UNKNOWN")
    log.debug(f" uploader: {upload_by}")

    # Description.
    description = yt_json.get("description", "")
    log.debug(f" description: {description}")
    # Append the tubesite, upload date, uploader, and extractor name to the description if they are not "UNKNOWN".
    description += f"\n\nUploaded to {tubesite} on {upload_on} by {upload_by} using {extractor}" if upload_on != "UNKNOWN" and upload_by != "UNKNOWN" and extractor != "UNKNOWN" else ""
    log.debug(f" description+additional: {description}")

    # Details
    # scene["details"] = f"Uploaded to {tubesite} on {upload_on} by {upload_by}" # "details" should be the "description" field, not a custom string. Built a description string that includes the tubesite, upload date, and uploader name, and append it to the description field.
    scene["details"] = description
    log.debug(f" details: details='{description}'")

    # Studio
    # Most extractors use the uploader for the "studio" name. Reference YT-dlp extractors: PornHub, XVideos, XHamster, etc.
    scene["studio"] = {"name": upload_by}
    log.debug(f" studio: studio='{scene['studio']}'")

    # Scene Markers
    chapters = yt_json.get("chapters", [])
    if chapters:
        log.debug(f" chapters: {chapters}")

        # Loop over the chapters from the JSON and create scene markers for each chapter.
        for chapter in chapters:
            title = chapter.get("title", "")
            seconds = chapter.get("start_time", 0)
            end_seconds = chapter.get("end_time", 0)
            primary_tag_name = title if title else "Chapter"
            log.debug(
                f"Creating marker for scene {scene_id}: title='{title}', seconds={seconds}, end_seconds={end_seconds}, primary_tag_name='{primary_tag_name}'")
            marker = graphql_createMarker(
                scene_id, title, primary_tag_name, seconds, end_seconds)
            log.debug(f"Created marker: {marker}")

    return scene


######################################
# GraphQL helper functions
def graphql_createMarker(scene_id, title, primary_tag_name, seconds, end_seconds):
    '''
    Create a scene marker. If primary_tag_name does not exist, it will be created. If primary_tag_name exists, it will be used as the primary tag for the marker.

    Args:
        scene_id (str): The ID of the scene to create the marker for.
        title (str): The title of the marker.
        primary_tag_name (str): The name of the primary tag for the marker.
        seconds (int): The time in seconds for the marker.
        end_seconds (int): The end time in seconds for the marker.

    Returns:
        dict: The result of the GraphQL mutation.
    '''
    primary_tag_id = graphql_findTagbyName(primary_tag_name)
    if primary_tag_id is None:
        primary_tag_id = graphql_createTag(primary_tag_name)
    log.info("Creating Marker: {}".format(title))
    query = """
    mutation SceneMarkerCreate($scene_id: ID!, $title: String!, $primary_tag_id: ID!, $seconds: Float!, $end_seconds: Float!) {
        sceneMarkerCreate(
            input: {
				scene_id: $scene_id
				title: $title
				primary_tag_id: $primary_tag_id
				seconds: $seconds
				end_seconds: $end_seconds
            }
        ) {
    		id
			title
			seconds
			stream
			preview
			screenshot
        }
    }
    
    """
    variables = {
        "title": title,
        "primary_tag_id": primary_tag_id,
        "scene_id": scene_id,
        "seconds": seconds,
        "end_seconds": end_seconds,

    }
    result = graphql.callGraphQL(query, variables)
    if result and "sceneMarkerCreate" in result:
        log.debug(
            f"Created marker '{title}' for scene {scene_id} with ID: {result['sceneMarkerCreate']['id']}")
    else:
        log.error(f"Failed to create marker '{title}' for scene {scene_id}")
    
    return result


def graphql_findTagbyName(tag_name):
    '''
    Find a tag by name. 

    Args:
        tag_name (str): The name of the tag to find.

    Returns:
        str: The ID of the tag if found, None otherwise.

    '''

    query = """
        query FindTagByName($name: String!) {
        findTags(tag_filter: {name: { value: $name, modifier: EQUALS }}) {
				count
				tags {
					id
				}
			}
        }
        """
    variables = {"name": tag_name}
    log.debug(f"Searching for tag '{tag_name}'")
    result = graphql.callGraphQL(query, variables)
    if result and "findTags" in result and result["findTags"]["count"] == 1:
        tag_id = result["findTags"]["tags"][0]["id"]
        log.debug(f"Found tag '{tag_name}' with ID: {tag_id}")
        return tag_id
    return None


def graphql_createTag(tag_name):
    '''
    Create a new tag

    Args:
        tag_name (str): The name of the tag to create.

    Returns:
        str: The ID of the newly created tag if successful, None otherwise.
    '''

    query = """
        mutation TagCreate($name: String!) {
			tagCreate(input: {name: $name}) {
				id
			}
        }
        """
    variables = {"name": tag_name}
    log.debug(f"Creating new tag '{tag_name}'")
    result = graphql.callGraphQL(query, variables)
    if result and "tagCreate" in result:
        log.debug(
            f"Created new tag '{tag_name}' with ID: {result['tagCreate']['id']}")
        return result["tagCreate"]["id"]
    return None


if __name__ == "__main__":
    input = sys.stdin.read()
    js = json.loads(input)
    scene_id = js["id"]
    ret = scene_from_json(scene_id)
    log.debug(json.dumps(ret))
    print(json.dumps(ret))
