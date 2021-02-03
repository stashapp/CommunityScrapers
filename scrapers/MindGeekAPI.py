import json
import re
import sys
from datetime import datetime

import requests

# Not necessary but why not ?
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'


def debugPrint(t):
    sys.stderr.write(t + "\n")


def get_info(url):
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
try:
    api_json = r.json().get('result')
    api_json['url'] = fragment["url"]
    try:
        # Saving the JSON to a file (Write '- logJSON' below MindGeekAPI.py in MindGeekAPI.yml)
        if sys.argv[1] == "logJSON":
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
    # Image can be poster or poster_fallback
    scrape['image'] = api_json['images']['poster'][0]['xx'].get('url')
    if '/poster/' not in scrape['image']:
        scrape['image'] = api_json['images']['poster'][1]['xx'].get('url')
    print(json.dumps(scrape))
except:
    print("An error has occurred", file=sys.stderr)
    print(f"Request status: `{r.status_code}`", file=sys.stderr)
    print(f"Check your MindGeekAPI.log for more details", file=sys.stderr)
    with open("MindGeekAPI.log", 'w', encoding='utf-8') as f:
        f.write("Instance Token: {}\n".format(instance_token))
        f.write("Scene ID: {}\n".format(id))
        f.write("Request:\n{}".format(r.text))
    exit(1)
# Last Updated February 03, 2021
