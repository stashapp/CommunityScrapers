import sys
import json
import re
import requests
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    'Origin': 'https://www.mydirtyhobby.com'
}

def extract_from_site(site):
    regex_performer = re.compile(r'<dd class="right"><a href="/profil/\d+-[A-Za-z0-9-]+" title="[A-Za-z0-9-_]+">([A-Za-z0-9-_]+)</a>.<span class="flag', re.DOTALL)
    regex_performer_match = regex_performer.search(site)
    performer = regex_performer_match.group(1) if regex_performer_match else None
    
    regex_title = re.compile(r'<h1 class=\"page-title pull-left no-sub-title\">(.*)</h1>', re.DOTALL)
    regex_title_match = regex_title.search(site)
    title = regex_title_match.group(1) if regex_title_match else None

    regex_details = re.compile(r'<div class="section-info-box pull-right"></div></div><p class="well well-sm">([^<]+)', re.DOTALL)
    regex_details_match = regex_details.search(site)
    details = regex_details_match.group(1) if regex_details_match else None

    regex_date = re.compile(r'<dd><i class="fa fa-calendar fa-fw fa-dt"></i>(\d+/\d+/\d+)</dd>', re.DOTALL)
    regex_date_match = regex_date.search(site)
    if regex_date_match:
        dt = datetime.strptime(regex_date_match.group(1), '%m/%d/%y')
        date = '{0}-{1:02}-{2}'.format(dt.year, dt.month, dt.day)
    else:
        date = None

    regex_tags = re.compile(r'<dd><a href="/videos/\d+-[a-z0-9-]+" title="[A-Za-z0-9 -/]+">([A-Za-z0-9 -/]+)</a></dd>', re.DOTALL)
    regex_tags_match = regex_tags.findall(site)
    tags = regex_tags_match if regex_tags_match else None

    return performer, title, details, date, tags


data_input = sys.stdin.read()
json_data = json.loads(data_input)
url = json_data['url']

site = requests.get(url, headers=HEADERS)
output_performer, output_title, output_details, output_date, output_tags = extract_from_site(site.text)

output = {
    'title': output_title,
    'date': output_date,
    'details': output_details,
    'studio': {
        'name': 'MyDirtyHobby'
    },
    'performers': [{
        'name': output_performer
    }],
    'tags': [{ 'name': x } for x in output_tags],
}
print(json.dumps(output))

