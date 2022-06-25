import json
import os
import re
import sys
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
        file=sys.stderr
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
        file=sys.stderr
    )
    sys.exit()

try:
    import py_common.log as log
    import py_common.graphql as graphql
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr
    )
    sys.exit()

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
scene_index = None
scene_title = None

regex_obj_parse_name_with_scene = re.compile(r"(.*?) - Scene (\d+)\. (.*)", re.IGNORECASE | re.MULTILINE)

parsed_name = regex_obj_parse_name_with_scene.search(performer_name)
if parsed_name:
    performer_name = parsed_name.group(1)
    scene_index = int(parsed_name.group(2)) - 1
    scene_title = parsed_name.group(3)

performers_data = graphql.getPerformersByName(performer_name)
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

performer_scenes = graphql.getSceneByPerformerId(performer_data['id'])

result = []
for i, scene in enumerate(performer_scenes['scenes']):
    if 'paths' in scene and 'screenshot' in scene['paths'] and len(scene['paths']['screenshot']) > 0 and \
            ((scene_index is not None and i == scene_index) or scene_index is None):
        # result = performer_data
        if 'query' in sys.argv:
            result.append(
                {'Name': f'{performer_name} - Scene {i + 1}. {scene["title"]}', 'Image': scene['paths']['screenshot'],
                 'Gender': performer_data['gender'], 'Images': [scene['paths']['screenshot']],
                 'Ethnicity': performer_data['ethnicity'], 'Birthdate': performer_data['birthdate'],
                 'Details': performer_data['details']}
            )
        else:
            result = {'Name': performer_name, 'Image': scene['paths']['screenshot'],
                 'Gender': performer_data['gender'], 'Images': [scene['paths']['screenshot']],
                 'Ethnicity': performer_data['ethnicity'], 'Birthdate': performer_data['birthdate'],
                 'Details': performer_data['details']}
            break

announce_result_to_stash(result)
