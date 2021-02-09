import json
import os
import re
import requests
import sys
from datetime import datetime


# Not necessary but why not ?
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'


def debug(q):
    print(q, file=sys.stderr)


def save_json(api_json, url):
    try:
        if sys.argv[1] == "logJSON":
            try:
                os.makedirs('Teamskeet_JSON')
            except FileExistsError:
                pass  # Dir already exist
            api_json['url'] = url
            filename = os.path.join(
                "Teamskeet_JSON", str(api_json['id'])+".json")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(api_json, file, ensure_ascii=False, indent=4)
    except IndexError:
        pass


fragment = json.loads(sys.stdin.read())
if fragment["url"]:
    scene_url = fragment["url"]
else:
    debug('You need to set the URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

if "teamskeet.com/movies/" not in scene_url:
    debug('The URL is not from a Teamskeet URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

scene_id = re.sub('.+/', '', scene_url)
if not scene_id:
    debug("Error with the ID ({})\nAre you sure that the end of your URL is correct ?".format(scene_id))
    sys.exit(1)
use_local = 0
json_file = os.path.join("Teamskeet_JSON", scene_id+".json")
if os.path.isfile(json_file):
    print("Using local JSON...", file=sys.stderr)
    use_local = 1
    with open(json_file, encoding="utf-8") as json_file:
        scene_api_json = json.load(json_file)
else:
    print("Asking the API...", file=sys.stderr)
    api_url = 'https://store2.psmcdn.net/ts-elastic-d5cat0jl5o-videoscontent/_doc/{}'.format(
        scene_id)
    headers = {
        'User-Agent': USER_AGENT,
        'Origin': 'https://www.teamskeet.com',
        'Referer': 'https://www.teamskeet.com/'
    }

    # Send to the API
    r = ""
    try:
        r = requests.get(api_url, headers=headers, timeout=(3, 5))
    except requests.exceptions.RequestException:
        print("An error has occurred with Requests", file=sys.stderr)
        print(f"Request status: `{r.status_code}`", file=sys.stderr)
        print(f"Check your TeamskeetJSON.log for more details", file=sys.stderr)
        with open("TeamskeetJSON.log", 'w', encoding='utf-8') as f:
            f.write("Scene ID: {}\n".format(scene_id))
            f.write("Request:\n{}".format(r.text))
        sys.exit(1)
    scene_api_json_check = r.json()['found']
    if scene_api_json_check:
        scene_api_json = r.json()['_source']
    else:
        debug('Scene not found (Wrong ID?)')
        sys.exit(1)

# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
date = datetime.strptime(scene_api_json.get(
    'publishedDate'), '%Y-%m-%dT%H:%M:%S.%f%z')
scrape['date'] = str(date.date())
scrape['details'] = scene_api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = scene_api_json['site'].get('name')
scrape['performers'] = [{"name": x.get('modelName')}
                        for x in scene_api_json.get('models')]
scrape['tags'] = [{"name": x} for x in scene_api_json.get('tags')]
scrape['image'] = scene_api_json.get('img')

if use_local == 0:
    save_json(scene_api_json, scene_url)
print(json.dumps(scrape))

# Last Updated February 08, 2021
