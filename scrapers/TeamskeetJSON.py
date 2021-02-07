import json
import os
import re
import sys
from datetime import datetime

import requests

# Not necessary but why not ?
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'


def saveJSON(api_json, url):
    try:
        if sys.argv[1] == "logJSON":
            try:
                os.makedirs('Teamskeet_JSON')
            except FileExistsError:
                pass  # Dir already exist
            api_json['url'] = url
            filename = os.path.join(
                "Teamskeet_JSON", str(api_json['id'])+".json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(api_json, f, ensure_ascii=False, indent=4)
    except IndexError:
        pass


fragment = json.loads(sys.stdin.read())
if fragment["url"]:
    url = fragment["url"]
else:
    print("You need to set the URL (teamskeet.com/movies/*****)", file=sys.stderr)
    exit(1)

id = re.sub('.+/', '', url)
api_URL = 'https://store2.psmcdn.net/ts-elastic-d5cat0jl5o-videoscontent/_doc/{}'.format(
    id)
headers = {
    'User-Agent': user_agent
}

# Send to the API
try:
    r = requests.get(api_URL, headers=headers, timeout=(3, 5))
except:
    print("An error has occurred with Requests", file=sys.stderr)
    print(f"Request status: `{r.status_code}`", file=sys.stderr)
    print(f"Check your TeamskeetJSON.log for more details", file=sys.stderr)
    with open("TeamskeetJSON.log", 'w', encoding='utf-8') as f:
        f.write("Scene ID: {}\n".format(id))
        f.write("Request:\n{}".format(r.text))
    exit(1)
api_json_check = r.json()['found']
if api_json_check == True:
    api_json = r.json()['_source']
else:
    print("Scene not found (Wrong ID)", file=sys.stderr)
    exit(1)

# Time to scrape all data
scrape = {}
scrape['title'] = api_json.get('title')
date = datetime.strptime(api_json.get(
    'publishedDate'), '%Y-%m-%dT%H:%M:%S.%f%z')
scrape['date'] = str(date.date())
scrape['details'] = api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = api_json['site'].get('name')
scrape['performers'] = [{"name": x.get('modelName')}
                        for x in api_json.get('models')]
scrape['tags'] = [{"name": x} for x in api_json.get('tags')]
scrape['image'] = api_json.get('img')

saveJSON(api_json, url)
print(json.dumps(scrape))

# Last Updated February 07, 2021
