import datetime
import difflib
import json
import os
import pathlib
import re
import sqlite3
import sys
from urllib.parse import urlparse

import requests

USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON", "Adultime")

SERVER_IP = "http://localhost:9999"
SERVER_URL = SERVER_IP + "/graphql"
# STASH API (Settings > Configuration > Authentication)
APIKEYS = ""

HEADERS = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin": "https://members.adulttime.com",
    "Referer": "https://members.adulttime.com/"
}

STASH_HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "keep-alive",
    "DNT": "1",
    "ApiKey": APIKEYS
}


def debug(q):
    print(q, file=sys.stderr)


def check_db(DB_PATH, SCENE_ID):
    try:
        sqliteConnection = sqlite3.connect("file:" + DB_PATH + "?mode=ro", uri=True)
        cursor = sqliteConnection.cursor()
        debug("Database successfully connected to SQLite")
        cursor.execute("SELECT size,duration,height from scenes WHERE id=?;",[SCENE_ID])
        record = cursor.fetchall()
        db_size = int(record[0][0])
        db_duration = int(record[0][1])
        db_height = int(record[0][2])
        cursor.close()
        sqliteConnection.close()
        debug("[Db] Size:{}, Duration:{}, Height:{}".format(db_size, db_duration, db_height))
        return db_size, db_duration, db_height
    except:
        debug("Error with the database")
    return None, None, None


def match_result(api_scene, range_duration=10, single=False, debug_log=True):
    api_title = api_scene.get("title")
    api_duration = int(api_scene.get("length"))
    api_filesize = ""
    try:
        if str(db_height) == "2160":
            api_filesize = int(api_scene["download_file_sizes"].get("4k"))
        else:
            api_filesize = int(api_scene["download_file_sizes"].get(str(db_height)+"p"))
    except:
        pass
    if not api_filesize or api_filesize is None:
        try:
            api_filesize = int(api_scene.get("index_size"))
        except:
            pass
    # Matching ratio
    match_ratio_title = difflib.SequenceMatcher(None, SCENE_TITLE, api_title).ratio()
    if url_title and api_scene.get("url_title"):
        match_ratio_title_url = difflib.SequenceMatcher(None, url_title, api_scene["url_title"]).ratio()
    else:
        match_ratio_title_url = None
    # Using db data
    match_duration = False
    match_size = False
    if db_duration is not None:
        if db_duration-range_duration <= api_duration <= db_duration+range_duration:
            match_duration = True
    if db_size is not None:
        db_size_max = db_size + (db_size/100)
        db_size_min = db_size - (db_size/100)
        try:
            if db_size_min <= api_filesize <= db_size_max:
                match_size = True
        except:
            pass
    if debug_log == True:
        debug("Title: {}, Ratio title: {}, Ratio url: {}, Match Duration: {}, Match Size: {}".format(api_title, match_ratio_title, match_ratio_title_url, match_duration, match_size))
    if single == True and match_duration == True:
        debug("[Single] Confirmed scene")
        return 1
    if match_ratio_title > 0.4 and match_duration == True and match_size == True:
        debug("[Best] Found scene: {}".format(api_title))
        return 1
    if match_ratio_title > 0.65 and match_duration == True:
        debug("[Title & Duration] Found scene: {}".format(api_title))
        return 1
    if match_ratio_title > 0.8:
        debug("[Title] Found scene: {}".format(api_title))
        return 1
    if match_ratio_title_url:
        if match_ratio_title_url > 0.8:
            debug("[Url_title] Found scene: {}".format(api_title))
            return 1
        if api_scene.get("sitename"):
            if match_ratio_title_url > 0.6 and api_scene["sitename"] == url_domain:
                debug("[Url_title + SiteName] Found scene: {}".format(api_title))
                return 1
        if api_scene.get("network_name"):
            if match_ratio_title_url > 0.6 and api_scene["network_name"] == url_domain:
                debug("[Url_title + NetworkName] Found scene: {}".format(api_title))
                return 1
    if match_duration == True and match_size == True:
        debug("[Duration & Size] Found scene: {}".format(api_title))
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
            remember_id = ""
            for line in f:
                list_line = line.split("|")
                json_id = list_line[0]
                api_title = re.sub('_', ' ', list_line[1])
                api_duration = int(list_line[2])
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
                api_filesize = ""
                if db_height:
                    try:
                        api_filesize = resolution.get(str(db_height))
                    except:
                        pass
                json_recreated = {
                    "title": api_title,
                    "length": api_duration,
                    "index_size": api_filesize
                }
                json_recreated = json.loads(json.dumps(json_recreated))
                r_match = match_result(json_recreated, 30, False, False)
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
    api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(app_id, api_key)
    try:
        r = requests.post(api_url, headers=HEADERS,json=request_api, timeout=5)
        api_result = r.json().get("results")[0].get("hits")
    except:
        debug("Error with Request Query")
        sys.exit(1)
    debug("Search give {} result(s)".format(len(api_result)))
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
    api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(app_id, api_key)
    try:
        r = requests.post(api_url, headers=HEADERS,json=request_api, timeout=5)
        api_result = r.json().get("results")[0].get("hits")[0]
    except:
        debug("Error with Request ID")
        sys.exit(1)
    if api_result:
        r_match = match_result(api_result, 120, True)
        if r_match is not None:
            return api_result
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
            sys.exit(1)
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
            sys.exit(1)
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
    scrape['details'] = re.sub(r'</br>|<br\s/>|<br>|<br/>', '\n', api_json.get('description'))
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
        scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(api_json['pictures']['nsfw']['top'].values()))
    except:
        try:
            scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(api_json['pictures']['sfw']['top'].values()))
        except:
            debug("Can't manage to get the image... Sorry :c")
    if url:
        scrape['url'] = url
    else:
        if api_json.get('member_url') is not None:
            scrape['url'] = api_json.get('member_url')
        else:
            try:
                scrape['url'] = 'https://members.adulttime.com/en/video/{}/{}/{}'.format(api_json['sitename'], api_json['url_title'], api_json['clip_id'])
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
    api_id = api_json["clip_id"]
    api_title = api_json["url_title"]
    api_length = api_json["length"]
    api_filesize_4k = ""
    api_filesize_1080 = ""
    api_filesize_720 = ""
    api_filesize_480 = ""
    try:
        if api_json.get("download_file_sizes") is not None:
            if api_json["download_file_sizes"].get("4k") is not None:
                api_filesize_4k = "4k:" + \
                    str(api_json["download_file_sizes"].get("4k")) + "|"
            if api_json["download_file_sizes"].get("1080p") is not None:
                api_filesize_1080 = "1080:" + \
                    str(api_json["download_file_sizes"].get("1080p")) + "|"
            if api_json["download_file_sizes"].get("720p") is not None:
                api_filesize_720 = "720:" + \
                    str(api_json["download_file_sizes"].get("720p")) + "|"
            if api_json["download_file_sizes"].get("480p") is not None:
                api_filesize_480 = "480:" + \
                    str(api_json["download_file_sizes"].get("480p")) + "|"
    except:
        print("[Index] Problem with filesize {}".format(api_id))
    index_value = "{}|{}|{}|{}{}{}{}".format(api_id, api_title, api_length, api_filesize_4k, api_filesize_1080, api_filesize_720, api_filesize_480)
    return index_value


def callGraphQL(query, variables=None):
    json = {'query': query}
    if variables is not None:
        json['variables'] = variables
    try:
        response = requests.post(SERVER_URL, json=json, headers=STASH_HEADERS)
        if response.status_code == 200:
            result = response.json()
            if result.get("error"):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data"):
                return result.get("data")
        elif response.status_code == 401:
            sys.exit("HTTP Error 401, Unauthorised.")
        else:
            raise ConnectionError("GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
                response.status_code, response.content, query, variables))
    except Exception as err:
        debug(err)
        sys.exit(1)


def getdbPath():
    query = "query Configuration {  configuration {...ConfigData}}fragment ConfigData on ConfigResult {  general {...ConfigGeneralData}}fragment ConfigGeneralData on ConfigGeneralResult { databasePath }"
    result = callGraphQL(query)
    return result["configuration"]["general"]["databasePath"]


FRAGMENT = json.loads(sys.stdin.read())

# Get your database
DB_PATH = None
config_path = os.path.join(USERFOLDER_PATH, "config.yml")

DB_PATH = getdbPath()
debug("[DEBUG] DB PATH: {}".format(DB_PATH))
if (os.path.isfile(config_path) == True and DB_PATH is None):
    with open(config_path) as f:
        for line in f:
            if "database: " in line:
                DB_PATH = line.replace("database: ", "").rstrip('\n')
                break

SCENE_ID = FRAGMENT["id"]
SCENE_TITLE = FRAGMENT["title"]
SCENE_URL = FRAGMENT["url"]
if DB_PATH:
    db_size, db_duration, db_height = check_db(DB_PATH, SCENE_ID)
else:
    db_size = None
    db_duration = None
    db_height = None
    debug("[Warn] Can't find the database")

url_id = None
url_title = None

if SCENE_URL:
    # Gettings ID
    url_domain = urlparse(SCENE_URL).netloc
    url_domain = re.sub(r"www\.|\.com","",url_domain)
    url_check = re.sub('.+/', '', SCENE_URL)
    try:
        if url_check.isdigit():
            url_id = url_check
        else:
            url_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
        debug("ID: {}".format(url_id))
    except:
        url_id = None
        debug("Can't get ID from URL")
    # Gettings url_title
    try:
        url_title = re.match(r".+/(.+)/\d+", SCENE_URL).group(1)
        debug("URL_TITLE: {}".format(url_title))
    except:
        url_title = None
        debug("Can't get url_title from URL")

if SCENE_TITLE:
    SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
    # Remove resolution
    SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)
    # Remove Date
    SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)
    debug("Title: {}".format(SCENE_TITLE))

# Check local
result = None
api_json = None
use_local = False
if os.path.isdir(DIR_JSON):
    debug("=============\nSearching with local JSON...")
    if url_id is not None:
        if url_id.isdigit():
            debug("Using ID")
            result = check_local(url_id)
    if url_title is not None and result is None:
        debug("Using URL_TITLE")
        result = check_local(url_title)

    if SCENE_TITLE is not None and result is None:
        debug("Using TITLE")
        result = check_local(SCENE_TITLE)

    if result is not None:
        with open(os.path.join(DIR_JSON, result+".json"), encoding="utf-8") as json_file:
            api_json = json.load(json_file)
            use_local = True

# Time to search using different method (API)
if api_json is None:
    debug("=============\nUsing API...")
    if url_id is not None:
        if url_id.isdigit():
            debug("Searching with ID...")
            api_json = request_api_id(url_id)
    if url_title is not None and api_json is None:
        debug("Searching with URL_TITLE...")
        api_json = request_api_query(url_title)
    if SCENE_TITLE is not None and api_json is None:
        debug("Searching with Title...")
        api_json = request_api_query(SCENE_TITLE)

if api_json is not None:
    scraped_json = scraping_json(api_json, SCENE_URL)
    # Save the json if not using local or if we get the URL.
    if use_local is False or SCENE_URL:
        save_json(api_json, SCENE_URL)
    print(json.dumps(scraped_json))
else:
    debug("Can't find the scene")
    sys.exit(1)


# Last Updated July 04, 2021
