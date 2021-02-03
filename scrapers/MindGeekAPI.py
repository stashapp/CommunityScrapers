import json
import sys
import requests
import re
from datetime import datetime

# Not necessary but why not ?
UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

def debugPrint(t):
    sys.stderr.write(t + "\n")

def get_Info(url):
    url = fragment["url"]
    r = requests.get(url)
    id = re.search('(.+releaseId\":\")(.+?)(\".+)',
                   r.text, re.IGNORECASE).group(2)
    token = re.search('(.+jwt\":\")(.+?)(\".+)',
                      r.text, re.IGNORECASE).group(2)
    return id, token

fragment = json.loads(sys.stdin.read())
# Get the id and instance token
id, instance_token = get_Info(fragment["url"])
api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(id)
headers = {
    'Instance': instance_token,
    'User-Agent': UserAgent
}
# Send to the API
r = requests.get(api_URL, headers=headers)
api_JSON = r.json().get('result')
# Time to scrape all data
scrape = {}
scrape['title'] = api_JSON.get('title')
date = datetime.strptime(api_JSON.get(
    'dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
scrape['date'] = str(date.date())
scrape['details'] = api_JSON.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = api_JSON['collections'][0].get('name')
scrape['performers'] = [
    {"name": x.get('name')} for x in api_JSON.get('actors')]
scrape['tags'] = [{"name": x.get('name')} for x in api_JSON.get('tags')]
scrape['image'] = api_JSON['images']['poster'][0]['xx'].get('url')
print(json.dumps(scrape))

# Last Updated February 03, 2021