import datetime
import difflib
import json
import os
import re
import sqlite3
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from bs4 import BeautifulSoup as bs
    import requests
    import lxml
except ModuleNotFoundError:
    print(
        "You need to install the following modules 'requests', 'bs4', 'lxml'.", file=sys.stderr)
    sys.exit()

try:
    from py_common import graphql
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

#
# User variables
#

# File to store the Algolia API key.
STOCKAGE_FILE_APIKEY = "Algolia.ini"
# Extra tag that will be added to the scene
FIXED_TAG = ""
# Include non female performers
NON_FEMALE = True

# a list of main channels (`mainChannelName` from the API) to use as the studio
# name for a scene
MAIN_CHANNELS_AS_STUDIO_FOR_SCENE = [
    "Buttman",
    "Cock Choking Sluts",
    "Devil's Film Parodies",
    "Euro Angels",
]

# a dict with sites having movie sections
# used when populating movie urls from the scene scraper
MOVIE_SITES = {
    "devilsfilm": "https://www.devilsfilm.com/en/dvd",
    "devilstgirls": "https://www.devilstgirls.com/en/dvd",
    "diabolic": "https://www.diabolic.com/en/movie",
    "falconstudios": "https://www.falconstudios.com/en/movie",
    "evilangel": "https://www.evilangel.com/en/movie",
    "genderx": "https://www.genderxfilms.com/en/movie",
    "girlfriendsfilms": "https://www.girlfriendsfilms.com/en/movie",
    "lewood": "https://www.lewood.com/en/movie",
    "hothouse": "https://www.hothouse.com/en/movie",
    "outofthefamily": "https://www.outofthefamily.com/en/dvd",
    "peternorth": "https://www.peternorth.com/en/dvd",
    "tsfactor": "https://www.tsfactor.com/en/movie/",
    "wicked": "https://www.wicked.com/en/movie",
    "zerotolerancefilms": "https://www.zerotolerancefilms.com/en/movie",
    "3rddegreefilms": "https://www.3rddegreefilms.com/en/movie",
    "roccosiffredi": "https://www.roccosiffredi.com/en/dvd",
}

# a dict of serie (`serie_name` from the API) which should set the value
# for the studio name for a scene
SERIE_USING_OVERRIDE_AS_STUDIO_FOR_SCENE = {
    "Jonni Darkko's Stand Alone Scenes": "Jonni Darkko XXX",
    "Big Boob Angels": "BAM Visions",
    "Mick's ANAL PantyHOES": "BAM Visions",
    "Real Anal Lovers": "BAM Visions",
    "XXXmailed": "Blackmailed"
}

# a list of serie (`serie_name` from the API) which should use the sitename
# for the studio name for a scene
SERIE_USING_SITENAME_AS_STUDIO_FOR_SCENE = [
    "Evil",         # sitename_pretty: Evil Angel
    "Trans-Active",  # sitename_pretty: Evil Angel
]

# a dict of sites (`sitename_pretty` from the API) which should set the value
# for the studio name for a scene
# this is because the `serie_name` is the Movie (series) title on these sites,
# not the studio
SITES_USING_OVERRIDE_AS_STUDIO_FOR_SCENE = {
    "Adamandevepictures": "Adam & Eve Pictures",
    "AgentRedGirl": "Agent Red Girl",
    "Devils Gangbangs": "Devil's Gangbangs",
    "Devilstgirls": "Devil's Tgirls",
    "Dpfanatics": "DP Fanatics",
    "Janedoe": "Jane Doe Pictures",
    "ModernDaySins": "Modern-Day Sins",
    "Transgressivexxx": "TransgressiveXXX",
    "Hot House": "Hot House Entertainment",
    "HotHouse.com": "Hot House Entertainment",
    "1000facials": "1000 Facials",
    "Immorallive": "Immoral Live",
    "Mommyblowsbest": "Mommy Blows Best",
    "Onlyteenblowjobs": "Only Teen Blowjobs"
}

# a list of sites (`sitename_pretty` from the API) which should pick out the
# `sitename_pretty` for the studio name for a scene
# this is because the `serie_name` is the Movie (series) title on these sites,
# not the studio
SITES_USING_SITENAME_AS_STUDIO_FOR_SCENE = [
    "ChaosMen",
    "Devil's Film",
    "GenderXFilms",
    "Give Me Teens",
    "Hairy Undies",
    "Lesbian Factor",
    "Oopsie",
    "Out of the Family",
    "Rocco Siffredi",
    "Squirtalicious",
    "3rd Degree Films",
]

# a list of sites (`sitename_pretty` from the API) which should pick out the
# `network_name` for the studio name for a scene
# this is because the `serie_name` is the Movie (series) title on these sites,
# not the studio
SITES_USING_NETWORK_AS_STUDIO_FOR_SCENE = [
    "Extremepickups",   # network_name: Adult Time Originals
    "Isthisreal",       # network_name: Is This Real
    "Muses",            # network_name: Transfixed
    "Officemsconduct",  # network_name: Transfixed
    "Sabiendemonia",    # network_name: Sabien DeMonia
    "Upclosex"          # network_name: UpCloseX
]

# a list of networks (`network_name` from the API) which should pick out the
# `sitename_pretty` for the studio name for a scene
NETWORKS_USING_SITENAME_AS_STUDIO_FOR_SCENE = [
    "Fame Digital",  # this should support all sub-studios listed at https://stashdb.org/studios/cd5591a5-eb26-42fc-a406-b6969a8ef3dd
    "fistinginferno",
    "MyXXXPass",
]

# a dict of directors to use as the studio for a scene
DIRECTOR_AS_STUDIO_OVERRIDE_FOR_SCENE = {
    "Le Wood": "LeWood"
}


def clean_text(details: str) -> str:
    """
    remove escaped backslashes and html parse the details text
    """
    if details:
        details = re.sub(r"\\", "", details)
        details = re.sub(r"<\s*/?br\s*/?\s*>", "\n",
                         details)  # bs.get_text doesnt replace br's with \n
        details = bs(details, features='lxml').get_text()
    return details


def check_db(database_path: str, scn_id: str) -> dict:
    """
    get scene data (size, duration, height) directly from the database file
    """
    try:
        sqlite_connection = sqlite3.connect("file:" + database_path +
                                            "?mode=ro",
                                            uri=True)
        log.debug("Connected to SQLite database")
    except:
        log.warning("Fail to connect to the database")
        return None, None, None
    cursor = sqlite_connection.cursor()
    cursor.execute("SELECT size,duration,height from scenes WHERE id=?;",
                   [scn_id])
    record = cursor.fetchall()
    database = {}
    database["size"] = int(record[0][0])
    database["duration"] = int(record[0][1])
    database["height"] = str(record[0][2])
    cursor.close()
    sqlite_connection.close()
    return database


def send_request(url: str, head: str, send_json="") -> requests.Response:
    """
    get post response from url
    """
    log.debug(f"Request URL: {url}")
    try:
        response = requests.post(url, headers=head, json=send_json, timeout=10)
    except requests.RequestException as req_error:
        log.warning(f"Requests failed: {req_error}")
        return None
    #log.debug(f"Returned URL: {response.url}")
    if response.content and response.status_code == 200:
        return response
    log.warning(f"[REQUEST] Error, Status Code: {response.status_code}")
    #print(response.text, file=open("algolia_request.html", "w", encoding='utf-8'))
    return None


# API Authentification
def apikey_get(site_url, time):
    req = send_request(site_url, HEADERS)
    if req is None:
        return None, None
    script_html = fetch_page_json(req.text)
    if script_html is not None:
        app_id = script_html['api']['algolia']['applicationID']
        algolia_api_key = script_html['api']['algolia']['apiKey']
        # Write key into a file
        write_config(time, app_id, algolia_api_key)
        log.info(f"New API keys: {algolia_api_key}")
        return app_id, algolia_api_key
    log.error(f"Can't retrieve Algolia API keys from page ({site_url})")
    return None, None


def fetch_page_json(page_html):
    matches = re.findall(r'window.env\s+=\s(.+);', page_html, re.MULTILINE)
    return None if len(matches) == 0 else json.loads(matches[0])


def check_config(domain, time):
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        try:
            time_past = datetime.datetime.strptime(config.get(domain, 'date'),
                                                   '%Y-%m-%d %H:%M:%S.%f')

            if time_past.hour - 1 < time.hour < time_past.hour + 1 and (
                    time - time_past).days == 0:
                log.debug("Using old key")
                application_id = config.get(domain, 'app_id')
                api_key = config.get(domain, 'api_key')
                return application_id, api_key
            log.info(
                f"Need new api key: [{time.hour}|{time_past.hour}|{(time-time_past).days}]"
            )
        except NoSectionError:
            pass
    return None, None


def write_config(date, app_id, api_key):
    log.debug("Writing config!")
    config = ConfigParser()
    config.read(STOCKAGE_FILE_APIKEY)
    try:
        config.get(SITE, 'date')
    except NoSectionError:
        config.add_section(SITE)
    config.set(SITE, 'date', date.strftime("%Y-%m-%d %H:%M:%S.%f"))
    config.set(SITE, 'app_id', app_id)
    config.set(SITE, 'api_key', api_key)
    with open(STOCKAGE_FILE_APIKEY, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


# API Search Data
def api_search_req(type_search, query, url):
    api_request = None
    if type_search == "query_all_scenes":
        api_request = api_search_query("all_scenes", query, url)
    if type_search == "query_all_photosets":
        api_request = api_search_query("all_photosets", query, url)
    if type_search == "id":
        api_request = api_search_id(query, url)
    if api_request:
        api_search = api_request.json()["results"][0].get("hits")
        if api_search:
            return api_search
    return None


def api_search_id(scene_id, url):
    clip_id = [f"clip_id:{scene_id}"]
    request_api = {
        "requests": [{
            "indexName": "all_scenes",
            "params": "query=&hitsPerPage=20&page=0",
            "facetFilters": clip_id
        }]
    }
    req = send_request(url, HEADERS, request_api)
    return req


def api_search_movie_id(m_id, url):
    movie_id = [f"movie_id:{m_id}"]
    request_api = {
        "requests": [{
            "indexName": "all_movies",
            "params": "query=&hitsPerPage=20&page=0",
            "facetFilters": movie_id
        }]
    }
    req = send_request(url, HEADERS, request_api)
    return req

def api_search_gallery_id(p_id, url):
    gallery_id = [[f"set_id:{p_id}"]]
    request_api = {
        "requests": [{
            "indexName": "all_photosets",
            "params": "query=&hitsPerPage=20&page=0",
            "facetFilters": gallery_id,
            "facets": []
        }]
    }
    req = send_request(url, HEADERS, request_api)
    return req


def api_search_query(index_name, query, url):
    request_api = {
        "requests": [{
            "indexName": index_name,
            "params": "query=" + query + "&hitsPerPage=40&page=0"
        }]
    }
    res = send_request(url, HEADERS, request_api)
    return res


# Searching Result


def json_parser(search_json, range_duration=60, single=False, scene_id=None):
    result_dict = {}
    # Just for not printing the full JSON in log...
    debug_dict = {}
    with open("adultime_scene_search.json", 'w',
              encoding='utf-8') as search_file:
        json.dump(search_json, search_file, ensure_ascii=False, indent=4)
    for scene in search_json:
        r_match = match_result(scene, range_duration, single, clip_id=url_id)
        if r_match["info"]:
            if result_dict.get(r_match["info"]):
                # Url should be more accurate than the title
                if r_match["url"] > result_dict[r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "clip_id": r_match["clip_id"],
                        "json": scene
                    }
                    debug_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "scene": scene["title"]
                    }
                elif r_match["title"] > result_dict[r_match["info"]][
                        "title"] and r_match["title"] > result_dict[
                            r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "clip_id": r_match["clip_id"],
                        "json": scene
                    }
                    debug_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "scene": scene["title"]
                    }
            else:
                result_dict[r_match["info"]] = {
                    "title": r_match["title"],
                    "url": r_match["url"],
                    "clip_id": r_match["clip_id"],
                    "json": scene
                }
                debug_dict[r_match["info"]] = {
                    "title": r_match["title"],
                    "url": r_match["url"],
                    "scene": scene["title"]
                }
    # Engine whoaaaaa
    # A = ByID/Most likely | S = Size | D = Duration | N = Network | R = Only Ratio
    log.info("--- BEST RESULT ---")
    for key, item in debug_dict.items():
        log.info(
            f'[{key}] Title: {item["scene"]}; Ratio Title: {round(item["title"], 3)} - URL: {round(item["url"], 3)}'
        )
    log.info("--------------")
    #
    if result_dict.get("ASDN"):
        return result_dict["ASDN"]["json"]
    if result_dict.get("ASD"):
        return result_dict["ASD"]["json"]
    if result_dict.get("ASN"):
        return result_dict["ASN"]["json"]
    if result_dict.get("ADN"):
        return result_dict["ADN"]["json"]
    if result_dict.get("AS"):
        return result_dict["AS"]["json"]
    if result_dict.get("AD"):
        return result_dict["AD"]["json"]
    if result_dict.get("AN"):
        if result_dict["AN"]["clip_id"] or result_dict["AN"]["title"] > 0.5 or result_dict["AN"]["url"] > 0.5:
            return result_dict["AN"]["json"]
    if result_dict.get("A"):
        if result_dict["A"]["title"] > 0.7 or result_dict["A"]["url"] > 0.7:
            return result_dict["A"]["json"]
    if result_dict.get("SDN"):
        return result_dict["SDN"]["json"]
    if result_dict.get("SD"):
        return result_dict["SD"]["json"]
    if result_dict.get("SN"):
        if result_dict["SN"]["title"] > 0.5 or result_dict["SN"]["url"] > 0.5:
            return result_dict["SN"]["json"]
    if result_dict.get("DN"):
        if result_dict["DN"]["title"] > 0.5 or result_dict["DN"]["url"] > 0.5:
            return result_dict["DN"]["json"]
    if result_dict.get("S"):
        if result_dict["S"]["title"] > 0.7 or result_dict["S"]["url"] > 0.7:
            return result_dict["S"]["json"]
    if result_dict.get("D"):
        if result_dict["D"]["title"] > 0.7 or result_dict["D"]["url"] > 0.7:
            return result_dict["D"]["json"]
    if result_dict.get("N"):
        if result_dict["N"]["title"] > 0.7 or result_dict["N"]["url"] > 0.7:
            return result_dict["N"]["json"]
    if result_dict.get("R"):
        if result_dict["R"]["title"] > 0.8 or result_dict["R"]["url"] > 0.8:
            return result_dict["R"]["json"]
    return None


def match_result(api_scene, range_duration=60, single=False, clip_id: str=None):
    api_title = api_scene.get("title")
    api_duration = int(api_scene.get("length"))
    api_clip_id = str(api_scene["clip_id"])
    api_filesize = None
    match_duration = False
    match_size = False
    match_clip_id = False
    # Using database
    if database_dict:
        db_duration = int(database_dict[0]["duration"])
        db_height = str(database_dict[0]["height"])
        db_size = int(database_dict[0]["size"])
        if api_scene.get("download_file_sizes"):
            if db_height == "2160":
                api_filesize = api_scene["download_file_sizes"].get("4k")
            else:
                api_filesize = api_scene["download_file_sizes"].get(db_height +
                                                                    "p")
            if api_filesize:
                api_filesize = int(api_filesize)
        if api_filesize is None:
            api_filesize = api_scene.get("index_size")
            if api_filesize:
                api_filesize = int(api_filesize)
        if db_duration - range_duration <= api_duration <= db_duration + range_duration:
            match_duration = True
        db_size_max = db_size + (db_size / 100)
        db_size_min = db_size - (db_size / 100)
        if api_filesize:
            if db_size_min <= api_filesize <= db_size_max:
                match_size = True
    # Post process things
    match_domain = False
    if URL_DOMAIN:
        if api_scene.get("sitename"):
            #log.debug("API Sitename: {}".format(api_scene["sitename"]))
            if api_scene["sitename"].lower() == URL_DOMAIN:
                match_domain = True
        if api_scene.get("network_name"):
            #log.debug("API Network: {}".format(api_scene["network_name"]))
            if api_scene["network_name"].lower() == URL_DOMAIN:
                match_domain = True

    # Matching ratio
    if SCENE_TITLE:
        match_ratio_title = difflib.SequenceMatcher(None, SCENE_TITLE.lower(),
                                                    api_title.lower()).ratio()
    else:
        match_ratio_title = 0
    if url_title and api_scene.get("url_title"):
        match_ratio_title_url = difflib.SequenceMatcher(
            None, url_title.lower(), api_scene["url_title"].lower()).ratio()
    else:
        match_ratio_title_url = 0

    # Rank search result

    log.debug(
        f"[MATCH] Title: {api_title} |-RATIO-| Ratio: {round(match_ratio_title, 5)} / URL: {round(match_ratio_title_url, 5)} |-MATCH-| Duration: {match_duration}, Size: {match_size}, Domain: {match_domain}"
    )
    match_dict = {}
    match_dict["title"] = match_ratio_title
    match_dict["url"] = match_ratio_title_url

    information_used = ""
    if (single and (match_duration or
                    (database_dict is None and match_ratio_title_url > 0.5))
        ) or match_ratio_title_url == 1:
        information_used += "A"
    if match_size:
        information_used += "S"
    if match_duration:
        information_used += "D"
    if match_domain:
        information_used += "N"
    if clip_id:
        if clip_id == api_clip_id:
            match_clip_id = True
    if information_used == "":
        information_used = "R"
    match_dict["info"] = information_used
    match_dict["clip_id"] = match_clip_id
    #debug("[MATCH] {} - {}".format(api_title,match_dict))
    return match_dict


def get_id_from_url(url: str) -> str:
    '''
    gets  the id from a valid url
    expects urls of the form www.example.com/.../title/id
    '''
    if url is None or url == "":
        return None

    id_check = re.sub('.+/', '', url)
    id_from_url = None
    try:
        if id_check.isdigit():
            id_from_url = id_check
        else:
            id_from_url = re.search(r"/(\d+)/*", url).group(1)
            log.info(f"ID: {id_from_url}")
    except:
        log.warning("Can't get ID from URL")
    return id_from_url


def parse_movie_json(movie_json: dict) -> dict:
    """
    process an api movie dictionary and return a scraped one
    """
    scrape = {}
    try:
        studio_name = determine_studio_name_from_json(movie_json[0])
    except IndexError:
        log.debug("No movie found")
        return scrape
    scrape["synopsis"] = clean_text(movie_json[0].get("description"))
    scrape["name"] = movie_json[0].get("title")
    scrape["studio"] = {"name": studio_name}
    scrape["duration"] = movie_json[0].get("total_length")

    date_by_studio = "date_created" # options are "date_created", "upcoming" (not always avaialble), "last_modified"
                                    # dates don't seem to be accurate (modifed multiple times by studio)
                                    # using date_created as default and we later override for each site when needed

    log.debug(
        f"Dates available: upcoming {movie_json[0].get('upcoming')} - created {movie_json[0].get('date_created')} - last modified {movie_json[0].get('last_modified')}"
    )
    studios_movie_dates = {
        "Diabolic": "last_modified",
        "Evil Angel": "date_created",
        "Wicked": "date_created",
        "Zerotolerance": "last_modified"
    }
    if studios_movie_dates.get(studio_name):
        date_by_studio = studios_movie_dates[studio_name]
    scrape["date"] = movie_json[0].get(date_by_studio)

    scrape[
        "front_image"] = f"https://transform.gammacdn.com/movies{movie[0].get('cover_path')}_front_400x625.jpg?width=450&height=636"
    scrape[
        "back_image"] = f"https://transform.gammacdn.com/movies{movie[0].get('cover_path')}_back_400x625.jpg?width=450&height=636"

    directors = []
    if movie_json[0].get('directors') is not None:
        for director in movie_json[0].get('directors'):
            directors.append(director.get('name').strip())
    scrape["director"] = ", ".join(directors)
    return scrape

def determine_studio_name_from_json(some_json):
    '''
    Reusable function to determine studio name based on what was scraped.
    This can be used for scraping:
    - scene
    - gallery
    - movie
    '''
    studio_name = None
    if some_json.get('sitename_pretty'):
        if some_json.get('sitename_pretty') in SITES_USING_OVERRIDE_AS_STUDIO_FOR_SCENE:
            studio_name = \
                    SITES_USING_OVERRIDE_AS_STUDIO_FOR_SCENE.get(some_json.get('sitename_pretty'))
        elif some_json.get('sitename_pretty') in SITES_USING_SITENAME_AS_STUDIO_FOR_SCENE \
                or some_json.get('serie_name') in SERIE_USING_SITENAME_AS_STUDIO_FOR_SCENE \
                or some_json.get('network_name') \
                and some_json.get('network_name') in NETWORKS_USING_SITENAME_AS_STUDIO_FOR_SCENE:
            studio_name = some_json.get('sitename_pretty')
        elif some_json.get('sitename_pretty') in SITES_USING_NETWORK_AS_STUDIO_FOR_SCENE \
                and some_json.get('network_name'):
            studio_name = some_json.get('network_name')
    if not studio_name and some_json.get('network_name') and \
            some_json.get('network_name') in NETWORKS_USING_SITENAME_AS_STUDIO_FOR_SCENE:
        studio_name = some_json.get('sitename_pretty')
    if not studio_name and some_json.get('mainChannelName') and \
            some_json.get('mainChannelName') in MAIN_CHANNELS_AS_STUDIO_FOR_SCENE:
        studio_name = some_json.get('mainChannelName')
    if not studio_name and some_json.get('directors'):
        for director in [ d.get('name').strip() for d in some_json.get('directors') ]:
            if DIRECTOR_AS_STUDIO_OVERRIDE_FOR_SCENE.get(director):
                studio_name = \
                        DIRECTOR_AS_STUDIO_OVERRIDE_FOR_SCENE.get(director)
    if not studio_name and some_json.get('serie_name'):
        if some_json.get('serie_name') in SERIE_USING_OVERRIDE_AS_STUDIO_FOR_SCENE:
            studio_name = \
                    SERIE_USING_OVERRIDE_AS_STUDIO_FOR_SCENE.get(some_json.get('serie_name'))
        else:
            studio_name = some_json.get('serie_name')
    return studio_name

def parse_scene_json(scene_json, url=None):
    """
    process an api scene dictionary and return a scraped one
    """
    scrape = {}
    # Title
    if scene_json.get('title'):
        scrape['title'] = scene_json['title'].strip()
    # Date
    scrape['date'] = scene_json.get('release_date')
    # Details
    scrape['details'] = clean_text(scene_json.get('description'))

    # Studio Code
    if scene_json.get('clip_id'):
        scrape['code'] = str(scene_json['clip_id'])

    # Director
    directors = []
    if scene_json.get('directors') is not None:
        for director in scene_json.get('directors'):
            directors.append(director.get('name').strip())
    scrape["director"] = ", ".join(directors)

    # Studio
    scrape['studio'] = {}
    studio_name = determine_studio_name_from_json(scene_json)
    if studio_name:
        scrape['studio']['name'] = studio_name

    log.debug(
        f"[STUDIO] {scene_json.get('serie_name')} - {scene_json.get('network_name')} - {scene_json.get('mainChannelName')} - {scene_json.get('sitename_pretty')}"
    )
    # Performer
    perf = []
    for actor in scene_json.get('actors'):
        if actor.get('gender') == "female" or NON_FEMALE:
            perf.append({
                "name": actor.get('name').strip(),
                "gender": actor.get('gender')
            })
    scrape['performers'] = perf

    # Tags
    list_tag = []
    for tag in scene_json.get('categories'):
        if tag.get('name') is None:
            continue
        tag_name = tag.get('name')
        tag_name = " ".join(tag.capitalize() for tag in tag_name.split(" "))
        if tag_name:
            list_tag.append({"name": tag.get('name')})
    if FIXED_TAG:
        list_tag.append({"name": FIXED_TAG})
    scrape['tags'] = list_tag

    # Image
    try:
        scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(
            iter(scene_json['pictures']['nsfw']['top'].values()))
    except:
        try:
            scrape[
                'image'] = 'https://images03-fame.gammacdn.com/movies' + next(
                    iter(scene_json['pictures']['sfw']['top'].values()))
        except:
            log.warning("Can't locate image.")
    # URL
    try:
        hostname = scene_json.get('sitename')
        if hostname is None:
            hostname = SITE
        # Movie
        if scene_json.get('movie_title'):
            scrape['movies'] = [{
                "name": scene_json["movie_title"],
                "synopsis": clean_text(scene_json.get("movie_desc")),
                "date": scene_json.get("movie_date_created")
                }]
            log.debug(f"domain to use for movie url: {URL_DOMAIN}")
            if scene_json.get("url_movie_title") and scene_json.get(
                    "movie_id"):
                if URL_DOMAIN and MOVIE_SITES.get(URL_DOMAIN):
                    scrape['movies'][0][
                        'url'] = f"{MOVIE_SITES[URL_DOMAIN]}/{scene_json['url_movie_title']}/{scene_json['movie_id']}"
        net_name = scene_json.get('network_name')
        if net_name:
            if net_name.lower() == "21 sextury":
                hostname = "21sextury"
            elif net_name.lower() == "21 naturals":
                hostname = "21naturals"
            elif net_name.lower() == 'transfixed':
                hostname = 'transfixed'
            
        scrape[
            'url'] = f"https://{hostname.lower()}.com/en/video/{hostname.lower()}/{scene_json['url_title']}/{scene_json['clip_id']}"
    except Exception as exc:
        log.debug(f"{exc}")
        if url:
            scrape['url'] = url
    #log.debug(f"{scrape}")
    return scrape

def parse_gallery_json(gallery_json: dict, url: str = None) -> dict:
    """
    process an api gallery dictionary and return a scraped one
    """
    scrape = {}
    # Title
    if gallery_json.get('clip_title'):
        scrape['title'] = gallery_json['clip_title'].strip()
    elif gallery_json.get('title'):
        scrape['title'] = gallery_json['title'].strip()
    # Date
    scrape['date'] = gallery_json.get('date_online') or gallery_json.get('release_date')
    # Details
    scrape['details'] = clean_text(gallery_json.get('description'))

    # Studio Code # not yet supported in stash
    #if gallery_json.get('set_id'):
    #    scrape['code'] = str(gallery_json['set_id'])

    # Director # not yet supported in stash
    #directors = []
    #if gallery_json.get('directors') is not None:
    #    for director in gallery_json.get('directors'):
    #        directors.append(director.get('name').strip())
    #scrape["director"] = ", ".join(directors)

    # Studio
    scrape['studio'] = {}
    studio_name = determine_studio_name_from_json(gallery_json)
    if studio_name:
        scrape['studio']['name'] = studio_name

    log.debug(
        f"[STUDIO] {gallery_json.get('serie_name')} - {gallery_json.get('network_name')} - {gallery_json.get('mainChannelName')} - {gallery_json.get('sitename_pretty')}"
    )
    # Performer
    perf = []
    for actor in gallery_json.get('actors'):
        if actor.get('gender') == "female" or NON_FEMALE:
            perf.append({
                "name": actor.get('name').strip(),
                "gender": actor.get('gender')
            })
    scrape['performers'] = perf

    # Tags
    list_tag = []
    for tag in gallery_json.get('categories'):
        if tag.get('name') is None:
            continue
        tag_name = tag.get('name')
        tag_name = " ".join(tag.capitalize() for tag in tag_name.split(" "))
        if tag_name:
            list_tag.append({"name": tag.get('name')})
    if FIXED_TAG:
        list_tag.append({"name": FIXED_TAG})
    scrape['tags'] = list_tag

    # URL
    try:
        hostname = gallery_json['sitename']
        net_name = gallery_json['network_name']
        if net_name.lower() == "21 sextury":
            hostname = "21sextury"
        elif net_name.lower() == "21 naturals":
            hostname = "21naturals"
        scrape['url'] = f"https://www.{hostname.lower()}.com/en/photo/" \
            f"{gallery_json['url_title']}/{gallery_json['set_id']}"
    except:
        if url:
            scrape['url'] = url
    return scrape
#
# Start processing
#

try:
    USERFOLDER_PATH = re.match(r".+\.stash.", __file__).group(0)
    CONFIG_PATH = USERFOLDER_PATH + "config.yml"
    log.debug(f"Config Path: {CONFIG_PATH}")
except:
    USERFOLDER_PATH = None
    CONFIG_PATH = None
    log.debug("No config")

SITE = sys.argv[1]
HEADERS = {
    "User-Agent":
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin": f"https://www.{SITE}.com",
    "Referer": f"https://www.{SITE}.com"
}

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

# log.trace(f"fragment: {FRAGMENT}")

# ACCESS API
# Check existing API keys
CURRENT_TIME = datetime.datetime.now()
application_id, api_key = check_config(SITE, CURRENT_TIME)
# Getting new key
if application_id is None:
    application_id, api_key = apikey_get(f"https://www.{SITE}.com/en",
                                         CURRENT_TIME)
# Failed to get new key
if application_id is None:
    sys.exit(1)
api_url = f"https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={application_id}&x-algolia-api-key={api_key}"

#log.debug(HEADERS)
#log.debug(FRAGMENT)
URL_DOMAIN = None
if SCENE_URL:
    URL_DOMAIN = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc).lower()
    log.info(f"URL Domain: {URL_DOMAIN}")

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit(1)

if SCENE_URL and SCENE_ID is None:
    log.debug(f"URL Scraping: {SCENE_URL}")
else:
    log.debug(f"Stash ID: {SCENE_ID}")
    log.debug(f"Stash Title: {SCENE_TITLE}")

if "movie" not in sys.argv and "gallery" not in sys.argv:
    # Get your sqlite database
    stash_config = graphql.configuration()
    DB_PATH = None
    if stash_config:
        DB_PATH = stash_config["general"]["databasePath"]

    if (CONFIG_PATH and DB_PATH is None):
        # getting your database from the config.yml
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, encoding='utf-8') as f:
                for line in f:
                    if "database: " in line:
                        DB_PATH = line.replace("database: ", "").rstrip('\n')
                        break
    log.debug(f"Database Path: {DB_PATH}")
    if DB_PATH:
        if SCENE_ID:
            # Get data by GraphQL
            database_dict = graphql.getScene(SCENE_ID)
            if database_dict is None:
                # Get data by SQlite
                log.warning(
                    "GraphQL request failed, accessing database directly...")
                database_dict = check_db(DB_PATH, SCENE_ID)
            else:
                database_dict = database_dict["files"]
            log.debug(f"[DATABASE] Info: {database_dict}")
        else:
            database_dict = None
            log.debug("URL scraping... Ignoring database...")
    else:
        database_dict = None
        log.warning("Database path missing.")

    # Extract things
    url_title = None
    url_id = None
    url_domain = None
    if SCENE_URL:
        url_id = get_id_from_url(SCENE_URL)
        try:
            url_title = re.match(r".+/(.+)/\d+", SCENE_URL).group(1)
            log.info(f"URL_TITLE: {url_title}")
        except:
            log.warning("Can't get url_title from URL")

    # Filter title
    if SCENE_TITLE:
        SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
        # Remove resolution
        SCENE_TITLE = re.sub(
            r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '',
            SCENE_TITLE)
        # Remove Date
        SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}',
                             '', SCENE_TITLE)
        log.debug(f"Title: {SCENE_TITLE}")

    # Time to search the API
    api_search = None
    api_json = None

    # sceneByName
    if SEARCH_TITLE:
        SEARCH_TITLE = SEARCH_TITLE.replace(".", " ")
        log.debug(f"[API] Searching for: {SEARCH_TITLE}")
        api_search = api_search_req("query_all_scenes", SEARCH_TITLE, api_url)
        final_json = None
        if api_search:
            result_search = []
            for scene in api_search:
                scraped_json = parse_scene_json(scene)
                if scraped_json.get("tags"):
                    scraped_json.pop("tags")
                result_search.append(scraped_json)
            if result_search:
                final_json = result_search
        if final_json is None:
            log.error("API Search finished. No results!")
        print(json.dumps(final_json))
        sys.exit()

    if url_id:
        log.debug(f"[API] Searching using URL_ID {url_id}")
        api_search = api_search_req("id", url_id, api_url)
        if api_search:
            log.info(f"[API] Search gives {len(api_search)} result(s)")
            api_json = json_parser(api_search, 120, True)
        else:
            log.warning("[API] No result")
    if url_title and api_json is None:
        log.debug("[API] Searching using URL_TITLE")
        api_search = api_search_req("query_all_scenes", url_title, api_url)
        if api_search:
            log.info(f"[API] Search gives {len(api_search)} result(s)")
            api_json = json_parser(api_search)
    if SCENE_TITLE and api_json is None:
        log.debug("[API] Searching using STASH_TITLE")
        api_search = api_search_req("query_all_scenes", SCENE_TITLE, api_url)
        if api_search:
            log.info(f"[API] Search gives {len(api_search)} result(s)")
            api_json = json_parser(api_search)

    # Scraping the JSON
    if api_json:
        log.info(f"Scene found: {api_json['title']}")
        scraped_json = parse_scene_json(api_json, SCENE_URL)
        print(json.dumps(scraped_json))
    else:
        log.error("Can't find the scene")
        print(json.dumps({}))
        sys.exit()
elif "movie" in sys.argv:
    log.debug("Scraping movie")
    movie_id = get_id_from_url(SCENE_URL)
    if movie_id:
        movie_results = api_search_movie_id(movie_id, api_url)
        movie = movie_results.json()["results"][0].get("hits")
        scraped_movie = parse_movie_json(movie)
        #log.debug(scraped_movie)
        print(json.dumps(scraped_movie))
elif "gallery" in sys.argv:
    scraped_gallery = None
    if SCENE_URL:
        if "/video/" in SCENE_URL:
            log.debug("Scraping scene by URL")
            scene_id = get_id_from_url(SCENE_URL)
            api_search_response = api_search_req("id", scene_id, api_url)
            if api_search_response:
                # log.debug(f"[API] Search gives {len(api_search_response)} result(s)")
                # log.trace(f"api_search_response: {api_search_response}")
                scraped_gallery = parse_gallery_json(api_search_response[0])
        else:
            log.debug("Scraping gallery by URL")
            gallery_id = get_id_from_url(SCENE_URL)
            if gallery_id:
                gallery_results = api_search_gallery_id(gallery_id, api_url)
                gallery = gallery_results.json()["results"][0].get("hits")
                if gallery:
                    #log.debug(gallery[0])
                    scraped_gallery = parse_gallery_json(gallery[0])
                    #log.debug(scraped_gallery)
    elif SCENE_TITLE:
        log.debug("Scraping gallery by fragment")
        # log.debug(f"[API] Searching using SCENE_TITLE: {SCENE_TITLE}")
        api_search = api_search_req("query_all_photosets", SCENE_TITLE, api_url)
        if api_search:
            log.info(f"[API] Search gives {len(api_search)} result(s)")
            # log.trace(f"api_search: {api_search}")
            log.debug(f"Galleries found: {'; '.join([g['title'] for g in api_search])}")
            scraped_gallery = parse_gallery_json(api_search[0])
    # Scraping the JSON
    if scraped_gallery:
        print(json.dumps(scraped_gallery))
    else:
        log.error("Can't find the gallery")
        print(json.dumps({}))
        sys.exit()
