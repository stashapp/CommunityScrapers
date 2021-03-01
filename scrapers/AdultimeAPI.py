import datetime
import difflib
import json
import os
import pathlib
import re
import sqlite3
import sys

import requests

USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON","Adultime")

HEADERS = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin": "https://members.adulttime.com",
    "Referer": "https://members.adulttime.com/"
}


def debug(q):
    print(q, file=sys.stderr)


def check_db(DB_PATH, scene_id):
    try:
        sqliteConnection = sqlite3.connect("file:" + DB_PATH + "?mode=ro",uri=True)
        cursor = sqliteConnection.cursor()
        debug("Database successfully connected to SQLite")
        sqlite_select_Query = "SELECT size,duration,height from scenes WHERE id="+scene_id+";"
        cursor.execute(sqlite_select_Query)
        record = cursor.fetchall()
        db_size = int(record[0][0])
        db_duration = int(record[0][1])
        db_height = int(record[0][2])
        cursor.close()
        sqliteConnection.close()
        debug("[Db] Size:{}, Duration:{}, Height:{}".format(
            db_size, db_duration, db_height))
        return db_size, db_duration, db_height
    except:
        debug("Error with the database")
    return None, None, None


def match_result(json_scene, range_duration=10, single=False, debug_log=True):
    json_title = json_scene.get("title")
    json_duration = int(json_scene.get("length"))
    json_size = ""
    try:
        json_size = int(json_scene["download_file_sizes"].get(str(db_height)+"p"))
    except:
        pass
    if not json_size or json_size is None:
        try:
            json_size = int(json_scene.get("index_size"))
        except:
            pass
    match_ratio = difflib.SequenceMatcher(
        None, scene_title, json_title).ratio()
    match_duration = False
    match_size = False
    if db_duration is not None:
        if db_duration-range_duration <= json_duration <= db_duration+range_duration:
            match_duration = True
    if db_size is not None:
        db_size_max = db_size + (db_size/100)
        db_size_min = db_size - (db_size/100)
        try:
            if db_size_min <= json_size <= db_size_max:
                match_size = True
        except:
            pass
    if debug_log == True:
        debug("Title: {}, Ratio title: {}, Match Duration: {}, Match Size: {}".format(
            json_title, match_ratio, match_duration, match_size))
    if single == True and match_duration == True:
        debug("[Single] Confirmed scene")
        return 1
    if match_ratio > 0.4 and match_duration == True and match_size == True:
        debug("[Best] Found scene: {}".format(json_title))
        return 1
    if match_ratio > 0.65 and match_duration == True:
        debug("[Title & Duration] Found scene: {}".format(json_title))
        return 1
    if match_ratio > 0.8:
        debug("[Title] Found scene: {}".format(json_title))
        return 1
    if match_duration == True and match_size == True:
        debug("[Duration & Size] Found scene: {}".format(json_title))
        return 2
    return None


def check_local(q):
    if q.isdigit():
        filename = os.path.join(DIR_JSON, q+".json")
        if (os.path.isfile(filename) == True):
            print("Using local JSON...", file=sys.stderr)
            with open(filename, encoding="utf-8") as json_file:
                api_json = json.load(json_file)
            r_match = match_result(api_json, 120, True)
            if r_match is not None:
                return str(api_json['clip_id'])
        else:
            return None
    index = os.path.join(DIR_JSON, "index.txt")
    if (os.path.isfile(index) == True):
        with open(index) as f:
            remember_id=""
            for line in f:
                list_line = line.split("|")
                json_id = list_line[0]
                json_title = re.sub('_', ' ', list_line[1])
                json_duration = int(list_line[2])
                resolution = {}
                try:
                    if list_line[3]:
                        tmp_reso = list_line[3].split(":")
                        resolution[tmp_reso[0]] = tmp_reso[1]
                    if list_line[4]:
                        tmp_reso = list_line[4].split(":")
                        resolution[tmp_reso[0]] = tmp_reso[1]
                    if list_line[5]:
                        tmp_reso = list_line[5].split(":")
                        resolution[tmp_reso[0]] = tmp_reso[1]
                except:
                    pass
                json_recreated = ""
                json_size=""
                if db_height:
                    try:
                        json_size = resolution.get(str(db_height))
                    except:
                        pass
                json_recreated = {
                    "title": json_title,
                    "length": json_duration,
                    "index_size": json_size
                }
                json_recreated = json.loads(json.dumps(json_recreated))
                r_match = match_result(json_recreated, 10, False,False)
                if r_match is not None:
                    if r_match == 2:
                        # Trying to get better result
                        remember_id = json_id
                        continue
                    return json_id
            if remember_id:
                return remember_id
            return None
    else:
        debug("No local JSON.")
        return None


def request_api_query(title):
    request_api = {
        "requests": [
            {
                "indexName": "all_scenes_latest_desc",
                "params": "query="+title+"&hitsPerPage=20&page=0"
            }
        ]
    }
    app_id, api_key = get_apikey()
    api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(
        app_id, api_key)
    try:
        r = requests.post(api_url, headers=HEADERS,
                          json=request_api, timeout=5)
        api_result = r.json().get("results")[0].get("hits")
    except:
        debug("Error with Request Query")
        exit(1)
    for scene in api_result:
        r_match = match_result(scene)
        if r_match is not None:
            return scene
    return None


def request_api_id(clip_id):
    clip_id = ["clip_id:{}".format(clip_id)]
    request_api = {
        "requests": [
            {
                "indexName": "all_scenes_latest_desc",
                "params": "query=&hitsPerPage=20&page=0",
                "facetFilters": clip_id
            }
        ]
    }
    app_id, api_key = get_apikey()
    api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(
        app_id, api_key)
    try:
        r = requests.post(api_url, headers=HEADERS,
                          json=request_api, timeout=5)
        api_result = r.json().get("results")[0].get("hits")[0]
    except:
        debug("Error with Request ID")
        exit(1)
    if api_result:
        r_match = match_result(api_result, 120, True)
        if r_match is not None:
            return api_result
    else:
        return None


def request_api_urltitle(url_title):
    url_title = ["url_title:{}".format(url_title)]
    request_api = {
        "requests": [
            {
                "indexName": "all_scenes_latest_desc",
                "params": "query=&hitsPerPage=20&page=0",
                "facetFilters": url_title
            }
        ]
    }
    app_id, api_key = get_apikey()
    api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(
        app_id, api_key)
    try:
        r = requests.post(api_url, headers=HEADERS,
                          json=request_api, timeout=5)
        api_result = r.json().get("results")[0].get("hits")
    except:
        debug("Error with Request url_title")
        exit(1)
    for scene in api_result:
        r_match = match_result(scene)
        if r_match is not None:
            return scene
    return None


def get_apikey():
    timenow = datetime.datetime.now()
    site_url = "https://www.girlsway.com/en"
    application_id, api_key = check_apikey(timenow)
    if application_id is None:
        try:
            r = requests.post(site_url, headers=HEADERS, timeout=5)
        except:
            debug("Error with request API Key")
            exit(1)
        html = r.text
        script_html = fetch_page_json(html)
        if script_html is not None:
            application_id = script_html['api']['algolia']['applicationID']
            api_key = script_html['api']['algolia']['apiKey']
            print("{}|{}|{}".format(timenow, application_id,
                                    api_key), file=open("Adultime_key.txt", "w"))
            debug("New API keys:{}".format(api_key))
            return application_id, api_key
        else:
            debug("Can't get API keys")
            exit(1)
    else:
        return application_id, api_key


def check_apikey(timenow):
    if (os.path.isfile("Adultime_key.txt") == True):
        f = open("Adultime_key.txt", "r")
        list_f = f.read().split("|")
        time_past = datetime.datetime.strptime(
            list_f[0], '%Y-%m-%d %H:%M:%S.%f')
        if time_past.hour-1 < timenow.hour < time_past.hour+1:
            debug("Using old api keys")
            application_id = list_f[1]
            api_key = list_f[2]
            return application_id, api_key
        else:
            debug("Need new api key")
    return None, None


def fetch_page_json(page_html):
    matches = re.findall(r'window.env\s+=\s(.+);', page_html, re.MULTILINE)
    return None if len(matches) == 0 else json.loads(matches[0])


def scraping_json(api_json, url):
    scrape = {}
    scrape['title'] = api_json.get('title')
    scrape['date'] = api_json.get('release_date')
    scrape['details'] = re.sub(
        r'</br>|<br\s/>|<br>|<br/>', '\n', api_json.get('description'))
    scrape['studio'] = {}
    scrape['studio']['name'] = api_json.get('network_name')
    perf = []
    for x in api_json.get('actors'):
        if x.get('gender') == "female":
            perf.append({"name": x.get('name')})
    scrape['performers'] = perf
    scrape['tags'] = [
        {"name": x.get('name')} for x in api_json.get('categories')]
    try:
        scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + \
            next(iter(api_json['pictures']['nsfw']['top'].values()))
    except:
        try:
            scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + \
                next(iter(api_json['pictures']['sfw']['top'].values()))
        except:
            debug("Can't manage to get the image... Sorry :c")
    if url:
        scrape['url'] = url
    else:
        if api_json.get('member_url') is not None:
            scrape['url'] = api_json.get('member_url')
        else:
            try:
                scrape['url'] = 'https://members.adulttime.com/en/video/{}/{}/{}'.format(api_json['sitename'],api_json['url_title'],api_json['clip_id'])
            except:
                pass
    return scrape


def save_json(api_json, url):
    if "logJSON" in sys.argv:
        try:
            os.makedirs(DIR_JSON)
        except FileExistsError:
            pass  # Dir already exist
        if url:
            api_json['url'] = url
        filename = os.path.join(DIR_JSON, str(api_json['clip_id'])+".json")
        if (os.path.isfile(filename) == False):
            filename_index = os.path.join(DIR_JSON, "index.txt")
            index_value = create_index(api_json)
            print(index_value, file=open(filename_index, "a"))
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(api_json, f, ensure_ascii=False, indent=4)
        debug("Saved to JSON")



def create_index(api_json):
    json_id = api_json["clip_id"]
    json_title = api_json["url_title"]
    json_length = api_json["length"]
    json_size_1080 = ""
    json_size_720 = ""
    json_size_480 = ""
    try:
        if api_json.get("download_file_sizes") is not None:
            if api_json["download_file_sizes"].get("1080p") is not None:
                json_size_1080 = "1080:" + \
                    str(api_json["download_file_sizes"].get("1080p")) + "|"
            if api_json["download_file_sizes"].get("720p") is not None:
                json_size_720 = "720:" + \
                    str(api_json["download_file_sizes"].get("720p")) + "|"
            if api_json["download_file_sizes"].get("480p") is not None:
                json_size_480 = "480:" + \
                    str(api_json["download_file_sizes"].get("480p")) + "|"
    except:
        print("[Index] Problem with filesize {}".format(json_id))
    index_value = "{}|{}|{}|{}{}{}".format(
        json_id, json_title, json_length, json_size_1080, json_size_720, json_size_480)
    return index_value


fragment = json.loads(sys.stdin.read())

# Get your database
DB_PATH=""
config_path = os.path.join(USERFOLDER_PATH, "config.yml")
if (os.path.isfile(config_path) == True):
    with open(config_path) as f:
        for line in f:
            if "database: " in line:
                DB_PATH = line.replace("database: ","").rstrip('\n')
                break

scene_id = fragment["id"]
scene_title = fragment["title"]
scene_url = fragment["url"]
if DB_PATH:
    db_size, db_duration, db_height = check_db(DB_PATH, scene_id)
else:
    debug("Can't find the database")
search_api_id = None
search_api_urltitle = None

if scene_url:
    # Gettings ID
    check_url = re.sub('.+/', '', scene_url)
    try:
        if check_url.isdigit():
            search_api_id = check_url
        else:
            search_api_id = re.search(r"/(\d+)/*", scene_url).group(1)
        debug("ID: {}".format(search_api_id))
    except:
        search_api_id = None
        debug("Can't get ID from URL")
    # Gettings url_title
    try:
        search_api_urltitle = re.match(r".+/(.+)/\d+", scene_url).group(1)
        debug("URL_TITLE: {}".format(search_api_urltitle))
    except:
        search_api_urltitle = None
        debug("Can't get url_title from URL")

if scene_title:
    scene_title = re.sub(r'[-._\']', ' ', os.path.splitext(scene_title)[0])
    # Remove resolution
    scene_title = re.sub(
        r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', scene_title)
    # Remove Date
    scene_title = re.sub(
        r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', scene_title)
    debug("Title: {}".format(scene_title))

# Check local
result = None
api_json = None
use_local = False
debug("=============\nSearching with local JSON...")
if search_api_id is not None:
    if search_api_id.isdigit():
        debug("Using ID")
        result = check_local(search_api_id)
if search_api_urltitle is not None and result is None:
    debug("Using URL_TITLE")
    result = check_local(search_api_urltitle)

if scene_title is not None and result is None:
    debug("Using TITLE")
    result = check_local(scene_title)

if result is not None:
    with open(os.path.join(DIR_JSON, result+".json"), encoding="utf-8") as json_file:
        api_json = json.load(json_file)
        use_local = True

# Time to search using different method (API)
if api_json is None:
    debug("=============\nSearching with API...")
    if search_api_id is not None:
        if search_api_id.isdigit():
            debug("Using with ID from URL...")
            api_json = request_api_id(search_api_id)
    if search_api_urltitle is not None and api_json is None:
        debug("Using with URL_TITLE...")
        api_json = request_api_urltitle(search_api_urltitle)
    if scene_title is not None and api_json is None:
        debug("Using with Title...")
        api_json = request_api_query(scene_title)

if api_json is not None:
    scraped_json = scraping_json(api_json,scene_url)
    # Save the json if not using local or if we get the URL.
    if use_local is False or scene_url:
        save_json(api_json, scene_url)
    print(json.dumps(scraped_json))
else:
    debug("Can't find the scene")
    exit(1)


# Last Updated February 18, 2021
