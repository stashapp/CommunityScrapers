import difflib
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse

import requests

# Not necessary but why not ?
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

# Set Variable
set_ratio = 0.8
set_fileurl = "MindGeekAPI.ini"


def scraping_url(url):
    id, instance_token = get_info(url)
    headers = {
        'Instance': instance_token,
        'User-Agent': user_agent
    }
    return id, headers


def get_info(url):
    todaystr = datetime.today().strftime('%Y-%m-%d')
    today = datetime.strptime(todaystr, '%Y-%m-%d')
    token, id = check_config(url, today)
    if not token:
        try:
            r = requests.get(url,timeout=(3, 5))
        except requests.Timeout:
            print("Request Timeout", file=sys.stderr)
            exit(1)
        id = re.search('(.+releaseId\":\")(.+?)(\".+)',
                       r.text, re.IGNORECASE).group(2)
        token = re.search('(.+jwt\":\")(.+?)(\".+)',
                          r.text, re.IGNORECASE).group(2)
        write_config(url, token, todaystr)
    return id, token


def check_config(url, date_today):
    mydomain = urlparse(url).netloc
    token = ""
    id = ""
    if (os.path.isfile(set_fileurl) == True):
        config = ConfigParser()
        config.read(set_fileurl)
        try:
            file_instance = config.get(mydomain, 'instance')
            file_date = config.get(mydomain, 'date')
            past = datetime.strptime(file_date, '%Y-%m-%d')
            difference = date_today - past
            if difference.days == 0:
                # date is within 24 hours so using old instance
                regex = re.match(r"(.+/)(\d+)(/.+)", url)
                id = regex.group(2)
                token = file_instance
        except NoSectionError:
            pass
    return token, id


def write_config(url, token, date_today):
    mydomain = urlparse(url).netloc
    config = ConfigParser()
    config.read(set_fileurl)
    try:
        config.get(mydomain, 'url')
    except NoSectionError:
        config.add_section(mydomain)
    config.set(mydomain, 'url', url)
    config.set(mydomain, 'instance', token)
    config.set(mydomain, 'date', date_today)
    with open(set_fileurl, 'w') as configfile:
        config.write(configfile)
    return


def search_scene(title):
    # Clean your title
    # Remove extension and replace .-_ by a space
    title_filter = re.sub('[-\._\']', ' ', os.path.splitext(title)[0])
    # Remove resolution
    title_filter = re.sub(
        '\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|\]|\sHD|\sSD|', '', title_filter)
    # Remove Date
    title_filter = re.sub(
        '\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', title_filter)
    print("Your title:{}".format(title_filter), file=sys.stderr)
    if (os.path.isfile(set_fileurl) == True):
        config = ConfigParser()
        config.read(set_fileurl)
        dict_config = dict(config.items())
        for section in dict_config:
            if section == "DEFAULT":
                continue
            url = config.get(section, 'url')
            print("Searching on: {}".format(
                urlparse(url).netloc), file=sys.stderr)
            id, headers = scraping_url(url)
            # Filter the filename to remove possible mistake

            search_URL = 'https://site-api.project1service.com/v2/releases?title={}&type=scene'.format(
                title_filter)
            api_json = sendrequest(search_URL, headers)
            for result in api_json:
                ratio = difflib.SequenceMatcher(
                    None, title_filter, result.get('title')).ratio()
                print("Found:{}\nRatio:{}".format(
                    result.get('title'), ratio), file=sys.stderr)
                if ratio > set_ratio:
                    return result, url, headers
        print("Didn't find a match", file=sys.stderr)
        exit(1)
    else:
        print("Can't search the scene ({} is missing)".format(
            set_fileurl), file=sys.stderr)
        exit(1)


def sendrequest(url, headers):
    try:
        r = requests.get(url, headers=headers,timeout=(3, 5))
    except requests.Timeout:
        print("Request Timeout", file=sys.stderr)
        exit(1)
    try:
        api_json = r.json().get('result')
    except:
        print("An error has occurred", file=sys.stderr)
        print(f"Request status: `{r.status_code}`", file=sys.stderr)
        print(f"Check your MindGeekAPI.log for more details", file=sys.stderr)
        with open("MindGeekAPI.log", 'w', encoding='utf-8') as f:
            f.write("Headers used: {}\n".format(headers))
            f.write("API URL: {}\n".format(url))
            f.write("Request:\n{}".format(r.text))
        exit(1)
    return api_json


def scraping_json(api_json,url=""):
    # Scrape JSON
    scrape = {}
    scrape['title'] = api_json.get('title')
    date = datetime.strptime(api_json.get(
        'dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
    scrape['date'] = str(date.date())
    scrape['details'] = api_json.get('description')
    if url:
        scrape['url'] = url
    scrape['studio'] = {}
    scrape['studio']['name'] = api_json['collections'][0].get('name')
    scrape['performers'] = [
        {"name": x.get('name')} for x in api_json.get('actors')]
    scrape['tags'] = [{"name": x.get('name')} for x in api_json.get('tags')]
    # Image can be poster or poster_fallback
    for image_type in api_json['images']['poster']:
        if '/poster/' in image_type['xx'].get('url'):
            scrape['image'] = image_type['xx'].get('url')
            break
    return scrape


fragment = json.loads(sys.stdin.read())
print("", file=sys.stderr)

if not fragment["url"]:
    if fragment["title"]:
        # Trying to find the scene
        api_json, url_used, headers = search_scene(fragment["title"])
        id = str(api_json.get("id"))
        url = re.sub('/\d+/.+', '/' + id + "/", url_used)
        scrape = scraping_json(api_json,url)
    else:
        print("There is no URL or Title.", file=sys.stderr)
        exit(1)
else:
    # URL scraping
    url = fragment["url"]
    id, headers = scraping_url(url)
    # Send to the API
    api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(id)
    api_json = sendrequest(api_URL, headers)
    scrape = scraping_json(api_json)

# Saving the JSON to a file (Write '- logJSON' below MindGeekAPI.py in MindGeekAPI.yml)
try:
    if sys.argv[1] == "logJSON":
        try:
            os.makedirs('MindGeekAPI_JSON')
        except FileExistsError:
            pass  # Dir already exist
        api_json['url'] = url
        filename = os.path.join("MindGeekAPI_JSON", id+".json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(api_json, f, ensure_ascii=False, indent=4)
except IndexError:
    pass

print(json.dumps(scrape))

# Last Updated February 04, 2021
