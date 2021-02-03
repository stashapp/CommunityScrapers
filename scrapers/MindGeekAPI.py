import json
import os
import re
import sys
from datetime import datetime

import requests

# Not necessary but why not ?
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

def debugPrint(t):
    sys.stderr.write(t + "\n")

def get_info(url):
    url = fragment["url"]
    r = requests.get(url)
    id = re.search('(.+releaseId\":\")(.+?)(\".+)',
                   r.text, re.IGNORECASE).group(2)
    token = re.search('(.+jwt\":\")(.+?)(\".+)',
                      r.text, re.IGNORECASE).group(2)
    return id, token

fragment = json.loads(sys.stdin.read())
# Get the id and instance token
id, instance_token = get_info(fragment["url"])
api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(id)
headers = {
    'Instance': instance_token,
    'User-Agent': user_agent
}
# Send to the API
r = requests.get(api_URL, headers=headers)
api_json = r.json().get('result')

try:
    # Saving the JSON to a file (Write '- logJSON' below MindGeekAPI.py in MindGeekAPI.yml)
    if sys.argv[1] == "logJSON":
        if (os.path.isfile(id+".json") != True): # Don't re-write to the file if it's exist
            with open(id+".json", 'w', encoding='utf-8') as f:
                json.dump(api_json, f, ensure_ascii=False, indent=4)
except IndexError:
    pass

# Time to scrape all data
scrape = {}
scrape['title'] = api_json.get('title')
date = datetime.strptime(api_json.get(
    'dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
scrape['date'] = str(date.date())
scrape['details'] = api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = api_json['collections'][0].get('name')
scrape['performers'] = [
    {"name": x.get('name')} for x in api_json.get('actors')]
scrape['tags'] = [{"name": x.get('name')} for x in api_json.get('tags')]
scrape['image'] = api_json['images']['poster'][0]['xx'].get('url')
print(json.dumps(scrape))

# Last Updated February 03, 2021
