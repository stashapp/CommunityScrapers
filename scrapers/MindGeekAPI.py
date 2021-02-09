import difflib
import json
import os
import re
import requests
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse


# Not necessary but why not ?
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

# Set Variable
SET_RATIO = 0.8
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


def print_exit(q):
    print(q, file=sys.stderr)
    sys.exit(1)


def get_info(url):
    today_string = datetime.today().strftime('%Y-%m-%d')
    today = datetime.strptime(today_string, '%Y-%m-%d')
    token, found_scene_id = check_config(url, today)
    if not token:
        print("No instance token found, sending request...", file=sys.stderr)
        try:
            r = requests.get(url, timeout=(3, 5))
        except requests.Timeout:
            print_exit("Request Timeout")
        # Working: https://www.sneakysex.com/scene/4405530/test
        # Not Work: https://www.sneakysex.com/scene/4405530
        try:
            check_url = re.sub('.+/', '', url)
            if check_url.isdigit():
                found_scene_id = check_url
            else:
                found_scene_id = re.match(r"(.+/)(\d+)/*", url).group(2)
            token = r.cookies.get_dict().get("instance_token")
            if token is None:
                print_exit("Can't get the instance_token from the cookie")
        except ValueError:
            print_exit(
                "Error to get information from the request\nAre you sure that the URL is from the MindGeek Network ?")
        write_config(url, token, today_string)
    if not found_scene_id.isdigit():
        print_exit("The ID is not a digit")
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
                match = re.match(r'(.+/)(\d+)/*', url)
                if match is None:
                    print_exit('The ID can\'t be determined (RegEx). Maybe wrong url?')
                found_scene_id = match.group(2)
                token = file_instance
                print("Using token from {}".format(
                    SET_FILE_URL), file=sys.stderr)
            else:
                print("Token from the past, getting new one".format(
                    SET_FILE_URL), file=sys.stderr)
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
    print("Your title:{}".format(title_filter), file=sys.stderr)
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        dict_config = dict(config.items())
        for section in dict_config:
            if section == "DEFAULT":
                continue
            url = config.get(section, 'url')
            print("Searching on: {}".format(
                urlparse(url).netloc), file=sys.stderr)
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
                ratio = difflib.SequenceMatcher(
                    None, title_filter, result.get('title')).ratio()
                print("Found:{}\nRatio:{}".format(
                    result.get('title'), ratio), file=sys.stderr)
                if ratio > SET_RATIO:
                    return result, making_url, headers
        print_exit("Didn't find a match")
    else:
        print_exit("Can't search the scene ({} is missing)".format(
            SET_FILE_URL))


def send_request(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=(3, 5))
    except requests.Timeout:
        print_exit("Request Timeout")
    try:
        api_json = r.json().get('result')
    except (NameError, ValueError):
        print("An error has occurred", file=sys.stderr)
        print(f"Request status: `{r.status_code}`", file=sys.stderr)
        print(f"Check your MindGeekAPI.log for more details", file=sys.stderr)
        with open("MindGeekAPI.log", 'w', encoding='utf-8') as f:
            f.write("Headers used: {}\n".format(headers))
            f.write("API URL: {}\n".format(url))
            f.write("Request:\n{}".format(r.text))
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

# Saving the JSON to a file (Write '- logJSON' below MindGeekAPI.py in MindGeekAPI.yml)


def save_json(api_json, url):
    try:
        if sys.argv[1] == "logJSON":
            try:
                os.makedirs('MindGeekAPI_JSON')
            except FileExistsError:
                pass  # Dir already exist
            api_json['url'] = url
            filename = os.path.join(
                "MindGeekAPI_JSON", str(api_json['id'])+".json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(api_json, f, ensure_ascii=False, indent=4)
    except IndexError:
        pass

def checking_local(url):
    check_url = re.sub('.+/', '', url)
    if check_url.isdigit():
        found_scene_id = url
    else:
        found_scene_id = re.match(r"(.+/)(\d+)/*", url).group(2)
    filename = os.path.join("MindGeekAPI_JSON", found_scene_id+".json")
    if (os.path.isfile(filename) == True):
        print("Using local JSON...", file=sys.stderr)
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
        print_exit("There is no URL or Title.")
else:
    # URL scraping
    scene_url = fragment["url"]
    # Search local JSON, return none if not found
    use_local = checking_local(scene_url)
    if use_local is None:
        scene_id, request_headers = scraping_url(scene_url)
        # Send to the API
        api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(scene_id)
        scene_api_json = send_request(api_URL, request_headers)
    else:
        scene_api_json = use_local
    scraped_json = scraping_json(scene_api_json)
    if use_local is None:
        save_json(scene_api_json, scene_url)

print(json.dumps(scraped_json))

# Last Updated February 09, 2021
