import json
import re
import sys
from pathlib import Path

try:
    from py_common import log
    from py_common import graphql
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr
    )
    sys.exit()

MAX_TITLE_LENGTH = 25


def announce_result_to_stash(result):
    if result is None:
        result = [] if 'query' in sys.argv else {}
    if 'query' in sys.argv:
        if isinstance(result, list):
            print(json.dumps(result))
            sys.exit(0)
        else:
            print(json.dumps([result]))
            sys.exit(0)
    else:
        if isinstance(result, list):
            if len(result) > 0:
                print(json.dumps(result[0]))
                sys.exit(0)
            else:
                print("{}")
                sys.exit(0)
        else:
            print(json.dumps(result))
            sys.exit(0)


# Allows us to simply debug the script via CLI args
if len(sys.argv) > 2 and '-d' in sys.argv:
    stdin = sys.argv[sys.argv.index('-d') + 1]
else:
    stdin = sys.stdin.read()

frag = json.loads(stdin)
performer_name = frag.get("name")
if performer_name is None:
    announce_result_to_stash(None)
else:
    performer_name = str(performer_name)

regex_obj_parse_name_with_scene = re.compile(
    r"(.*?) - Scene (\d+)\. (.*)", re.IGNORECASE | re.MULTILINE)

parsed_name = regex_obj_parse_name_with_scene.search(performer_name)


if parsed_name:
    # scene id already available, get scene directly
    performer_name = parsed_name.group(1)
    scene_id = parsed_name.group(2)
    log.debug(f"Using scene {scene_id} to get performer image")
    performer_scene = graphql.getSceneScreenshot(scene_id)
    performer = {'Name': performer_name,
                 'Image': performer_scene['paths']['screenshot'],
                 'Images': [performer_scene['paths']['screenshot']]}
    announce_result_to_stash(performer)
else:
    # search for scenes with the performer

    # first find the id of the performer
    performers_data = graphql.getPerformersIdByName(performer_name)
    performer_data = None
    if performers_data is None or performers_data['count'] < 1:
        announce_result_to_stash(None)
    elif performers_data['count'] > 1:
        for performers_data_element in performers_data['performers']:
            if str(performers_data_element['name']).lower().strip() == performer_name.lower().strip():
                performer_data = performers_data_element
                break
        if performer_data is None:
            # No match found by looking into the names, let's loop again and match with the aliases
            for performers_data_element in performers_data['performers']:
                if performer_name.lower().strip() in str(performers_data_element['aliases']).lower().strip():
                    performer_data = performers_data_element
                    break
    else:
        performer_data = performers_data['performers'][0]

    if performer_data is None or 'id' not in performer_data or int(performer_data['id']) < 0:
        announce_result_to_stash(None)

    # get all scenes with the performer
    performer_scenes = graphql.getSceneIdByPerformerId(performer_data['id'])

    image_candidates = []
    for scene in performer_scenes['scenes']:
        if 'paths' in scene and 'screenshot' in scene['paths'] and len(scene['paths']['screenshot']) > 0:
            if 'query' in sys.argv:
                scene_title = scene.get("title")
                if scene_title is None:
                    scene_title = Path(scene["path"]).name
                image_candidates.append(
                    {
                        'Name': f'{performer_name} - Scene {scene["id"]}. {scene_title[0:MAX_TITLE_LENGTH]}',
                        'Image': scene['paths']['screenshot'],
                        'Images': [scene['paths']['screenshot']]
                    }
                )
    announce_result_to_stash(image_candidates)
