import difflib
import json
import os
import pathlib
import re
import requests
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse


USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON", "MindGeekAPI")
# Not necessary but why not ?
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

# Set Variable
SET_RATIO = 0.75
SET_FILE_URL = "MindGeekAPI.ini"


def scraping_url(url):
    my_domain = urlparse(url).netloc
    id, instance_token = get_info(url)
    headers = {
        'Instance': instance_token,
        'User-Agent': USER_AGENT,
        'Origin':	'https://' + my_domain,
        'Referer':	url
    }
    return id, headers


def debug(q):
    print(q, file=sys.stderr)


def get_info(url):
    today_string = datetime.today().strftime('%Y-%m-%d')
    today = datetime.strptime(today_string, '%Y-%m-%d')
    token, found_scene_id = check_config(url, today)
    if not token:
        debug("No instance token found, sending request...")
        try:
            r = requests.get(url, timeout=(3, 5))
        except requests.exceptions.RequestException:
            debug("Error with Request.")
            sys.exit(1)
        try:
            check_url = re.sub('.+/', '', url)
            if check_url.isdigit():
                found_scene_id = check_url
            else:
                found_scene_id = re.search(r"/(\d+)/*", url).group(1)
            token = r.cookies.get_dict().get("instance_token")
            if token is None:
                debug("Can't get the instance_token from the cookie")
                sys.exit(1)
        except ValueError:
            debug("Error to get information from the request\nAre you sure that the URL is from the MindGeek Network ?")
            sys.exit(1)
        write_config(url, token, today_string)
    if not found_scene_id.isdigit():
        debug("The ID is not a digit")
        sys.exit(1)
    return found_scene_id, token


def check_config(url, date_today):
    my_domain = urlparse(url).netloc
    token = ""
    found_scene_id = ""
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        try:
            file_instance = config.get(my_domain, 'instance')
            file_date = config.get(my_domain, 'date')
            past = datetime.strptime(file_date, '%Y-%m-%d')
            difference = date_today - past
            if difference.days == 0:
                # date is within 24 hours so using old instance
                match = re.search(r"/(\d+)/*", url)
                if match is None:
                    debug('The ID can\'t be determined (RegEx). Maybe wrong url?')
                    sys.exit(1)
                found_scene_id = match.group(1)
                token = file_instance
                #debug("Using token from {}".format(SET_FILE_URL))
            else:
                debug("Token from the past, getting new one".format(
                    SET_FILE_URL))
        except NoSectionError:
            pass
    return token, found_scene_id


def write_config(url, token, date_today):
    my_domain = urlparse(url).netloc
    config = ConfigParser()
    config.read(SET_FILE_URL)
    try:
        config.get(my_domain, 'url')
    except NoSectionError:
        config.add_section(my_domain)
    config.set(my_domain, 'url', url)
    config.set(my_domain, 'instance', token)
    config.set(my_domain, 'date', date_today)
    with open(SET_FILE_URL, 'w') as configfile:
        config.write(configfile)
    return


def search_scene(title):
    # Clean your title
    # Remove extension and replace .-_ by a space
    title_filter = re.sub(r'[-._\']', ' ', os.path.splitext(title)[0])
    # Remove resolution
    title_filter = re.sub(
        r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', title_filter)
    # Remove Date
    title_filter = re.sub(
        r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', title_filter)
    debug("Your title:{}".format(title_filter))
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        dict_config = dict(config.items())
        for section in dict_config:
            if section == "DEFAULT":
                continue
            url = config.get(section, 'url')
            debug("============\nSearching on: {}".format(
                urlparse(url).netloc))
            _, headers = scraping_url(url)
            # Filter the filename to remove possible mistake

            search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene'.format(
                title_filter)
            api_json = send_request(search_url, headers)
            for result in api_json:
                title_filename = ""
                try:
                    filename = result['videos']['mediabook']['files']["320p"]['urls']['download']
                    title_filename = re.sub(r'^.+filename=', '', filename)
                    title_filename = re.sub(r'_.+$', '', title_filename)
                except:
                    pass
                if title_filename:
                    making_url = re.sub(
                        r'/\d+/*.+', '/' + str(result.get("id")) + "/" + title_filename, url)
                else:
                    making_url = re.sub(
                        r'/\d+/*.+', '/' + str(result.get("id")) + "/", url)
                save_json(result, making_url)
                ratio = round(difflib.SequenceMatcher(
                    None, title_filter, result.get('title')).ratio(), 3)

                debug("Title:{} |Ratio:{}".format(
                    result.get('title'), ratio))
                if ratio > SET_RATIO:
                    return result, making_url, headers
        debug("Didn't find a match")
        sys.exit(1)
    else:
        debug("Can't search the scene ({} is missing)".format(
            SET_FILE_URL))
        sys.exit(1)


def send_request(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=(3, 5))
    except requests.exceptions.RequestException:
        debug("An error has occurred")
        debug("Request status: {}".format(r.status_code))
        try:
            debug("Message: {}".format(r.json()[0].get('message')))
        except:
            pass
        debug("Check your MindGeekAPI.log for more details")
        with open("MindGeekAPI.log", 'w', encoding='utf-8') as f:
            f.write("Headers used: {}\n".format(headers))
            f.write("API URL: {}\n".format(url))
            f.write("Response:\n{}".format(r.text))
        sys.exit(1)
    try:
        api_json = r.json().get('result')
    except:
        debug("Error getting the JSON from request")
        sys.exit(1)
    return api_json

# Scrape JSON for Stash


def scraping_json(api_json, url=""):
    scrape = {}
    scrape['title'] = api_json.get('title')
    date = datetime.strptime(api_json.get(
        'dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
    scrape['date'] = str(date.date())
    scrape['details'] = api_json.get('description')
    if url:
        scrape['url'] = url
    try:
        api_json['collections'][0].get('name') # If this create a error it wont continue so no studio at all
        scrape['studio'] = {}
        scrape['studio']['name'] = api_json['collections'][0].get('name')
    except:
        debug("No studio")
    if 'female_only' in sys.argv:
        perf = []
        for x in api_json.get('actors'):
            if x.get('gender') == "female":
                perf.append({"name": x.get('name')})
        scrape['performers'] = perf
    else:
        scrape['performers'] = [{"name": x.get('name')} for x in api_json.get('actors')]
    scrape['tags'] = [{"name": x.get('name')} for x in api_json.get('tags')]
    # Image can be poster or poster_fallback
    if type(api_json['images']['poster']) is list:
        for image_type in api_json['images']['poster']:
            if '/poster/' in image_type['xx'].get('url'):
                scrape['image'] = image_type['xx'].get('url')
                break
    else:
        if type(api_json['images']['poster']) is dict:
            for _, img_value in api_json['images']['poster'].items():
                if '/poster/' in img_value['xx'].get('url'):
                    scrape['image'] = img_value['xx'].get('url')
                    break
    return scrape

# Saving the JSON to a file (Write '- logJSON' below MindGeekAPI.py in MindGeekAPI.yml)


def save_json(api_json, url):
    if "logJSON" in sys.argv:
        try:
            os.makedirs(DIR_JSON)
        except FileExistsError:
            pass  # Dir already exist
        api_json['url'] = url
        filename = os.path.join(DIR_JSON, str(api_json['id'])+".json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(api_json, f, ensure_ascii=False, indent=4)


def checking_local(url):
    check_url = re.sub('.+/', '', url)
    if check_url.isdigit():
        found_scene_id = check_url
    else:
        found_scene_id = re.search(r"/(\d+)/*", url).group(1)
    filename = os.path.join(DIR_JSON, found_scene_id+".json")
    if (os.path.isfile(filename) == True):
        debug("Using local JSON...")
        with open(filename, encoding="utf-8") as json_file:
            api_json = json.load(json_file)
        return api_json
    else:
        return None


fragment = json.loads(sys.stdin.read())

if not fragment["url"]:
    if fragment["title"]:
        # Trying to find the scene
        scene_api_json, scene_url, _ = search_scene(fragment["title"])
        scraped_json = scraping_json(scene_api_json, scene_url)
    else:
        debug("There is no URL or Title.")
        sys.exit(1)
else:
    # URL scraping
    scene_url = fragment["url"]
    # Check if the URL has a old format
    if 'brazzers.com/scenes/view/id/' in scene_url:
        debug("Probably a old url, need to redirect")
        try:
            r = requests.get(scene_url, headers={
                             'User-Agent': USER_AGENT}, timeout=(3, 5))
            scene_url = r.url
        except:
            debug("Redirect fail, could give incorrect result.")
    # Search local JSON, return none if not found
    use_local = checking_local(scene_url)
    if use_local is None:
        scene_id, request_headers = scraping_url(scene_url)
        # Send to the API
        api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(scene_id)
        scene_api_json = send_request(api_URL, request_headers)
    else:
        scene_api_json = use_local
    if scene_api_json.get('parent') is not None:
        if scene_api_json['parent']['type'] == "scene":
            scene_api_json = scene_api_json.get('parent')
    scraped_json = scraping_json(scene_api_json, scene_url)
    if use_local is None:
        save_json(scene_api_json, scene_url)

print(json.dumps(scraped_json))

# Last Updated February 23, 2021
