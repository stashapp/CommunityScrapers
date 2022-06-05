import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to take the folder 'py_common' in the community repo (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()


def check_datelist(file: str, days=7):
    days_ago = datetime.now() - timedelta(days)
    filetime = datetime.fromtimestamp(os.path.getmtime(file))
    if filetime < days_ago:
        log.debug(f"{file} is older than {days} day(s) ({filetime})")
        # file older than
        return True
    return False


def reading_md(file: str):
    scrapers = []
    with open(file, "r") as md:
        lines = md.readlines()
    # https://github.com/stashapp/CommunityScrapers/blob/master/SCRAPERS-LIST.md
    # Supported Site|Scraper| S | G | M | P |Needs|Contents
    # 1000facials.com|GammaEntertainment.yml|:heavy_check_mark:|:x:|:x:|:x:|-|-
    for line in lines:
        if "Non url scrapers" in line:
            break
        if ".yml" not in line:
            continue
        if "FindScraper" in line:
            continue
        column = line.split("|")
        # not a scene scraper
        if column[2] != ":heavy_check_mark:":
            continue
        scrapers.append({"url": column[0], "filename": column[1], "needs": column[6]})
    return scrapers


def local_scrapers(scraper_list: list):
    scrapers = []
    for scraper in scraper_list:
        if "URL" not in scraper["scene"]["supported_scrapes"]:
            continue
        for url in scraper["scene"]["urls"]:
            try:
                scrapers.append({"url": get_domain(f"https://{url}"), "filename": f"{scraper['id']}.yml", "needs": "local"})
            except Exception as err:
                log.warning(f"Error with '{scraper['id']}' local scraper. ({err})")
    return scrapers


def get_domain(url: str):
    domain = urlparse(url).netloc
    if domain:
        domain = domain.replace("www.", "")
    return domain


def zip_extract(zip: str, destination: str, zip_folder=""):
    filename = os.path.basename(destination)
    with zipfile.ZipFile(zip) as z:
        with z.open(zip_folder + filename) as zf, open(destination, 'wb') as f:
            shutil.copyfileobj(zf, f)


def download_file(url: str, destination: str):
    filename = os.path.basename(destination)
    try:
        r = requests.get(url, timeout=10, headers=USER_AGENT)
        with open(destination, "wb") as zip_file:
            zip_file.write(r.content)
    except Exception as err:
        sys.exit(f"Error downloading {filename}. ({err})")


def get_scraper_byUrl(scene_url: str, scrapers: list):
    for scraper in scrapers:
        if scene_url == scraper["url"]:
            return scraper
    return None


def check_scraper_byName(name: str, scrapers: list):
    for scraper in scrapers:
        if name == scraper["filename"]:
            return True
    return False


def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)
    else:
        log.warning(f"The file you want to remove don't exist. ({path}) ")


def main():
    # create tmp folder
    if not os.path.exists(PATH_TMP):
        log.info("Creating tmp folder")
        os.makedirs(PATH_TMP)
    # checking if list exist or too old
    file_outdated = True
    if os.path.exists(PATH_MDLIST):
        # 1 week old
        file_outdated = check_datelist(PATH_MDLIST, 7)
        if file_outdated:
            # remove old file
            remove_file(PATH_MDLIST)
            remove_file(PATH_ZIP)
    # download file from github (zip & list)
    if file_outdated:
        log.info("Downloading file (Zip) from github...")
        download_file(GITHUB_ZIP, PATH_ZIP)
        zip_extract(PATH_ZIP, PATH_MDLIST, "CommunityScrapers-master/")
    # reading the md
    try:
        stash_scraper = graphql.listSceneScrapers()
        scrapers = local_scrapers(stash_scraper)
        l_scrapers = scrapers
    except Exception as err:
        log.error(f"Error reading your local scraper ({err})")
        return None
    try:
        scrapers.extend(reading_md(PATH_MDLIST))
    except Exception as err:
        log.error(f"Error reading the scraper list ({err})")
        return None
    # url domain eg: google.com
    scene_domain = get_domain(SCENE_URL)
    # find scraper in the list with this domain
    scraper_file = get_scraper_byUrl(scene_domain, scrapers)
    if not scraper_file:
        log.error(f"There is no scraper for your url '{scene_domain}'")
        return None
    # local scraper
    if scraper_file["needs"] == "local":
        log.info(f"You already have the scraper ({scraper_file['filename']}), Using it...")
        graphql.reloadScrapers()
        scraped_data = graphql.scrape_SceneURL(SCENE_URL)
        return scraped_data

    # check if you have the scraper but it missed the url so you need to update
    if check_scraper_byName(scraper_file, l_scrapers):
        log.info(f"There is a update for this scraper '({scraper_file['filename']})' (Added site)")

    # don't want to deal with python script
    if scraper_file["needs"] == "Python":
        log.error(f"A scraper exist ({scraper_file['filename']}) but it's a python scraper.")
        return None
    log.debug(f"Scraper used: {scraper_file['filename']}")
    # path of the tmp scraper
    scraper_path = os.path.join(PATH_TMP, scraper_file['filename'])
    try:
        zip_extract(PATH_ZIP, scraper_path, 'CommunityScrapers-master/scrapers/')
        #if scraper_file["needs"] == "Python":
        #    scraper_path = os.path.join(PATH_TMP, scraper_file['filename'].replace(".yml", ".py"))
        #    zip_extract(PATH_ZIP, scraper_path, 'CommunityScrapers-master/scrapers/')
    except Exception as err:
        log.error(f"Error extracting the scraper from zip ({err})")
        return None
    if not os.path.exists(scraper_path):
        log.error(f"The scraper ({scraper_file['filename']}) didn't move.")
        return None
    graphql.reloadScrapers()
    try:
        scraped_data = graphql.scrape_SceneURL(SCENE_URL)
    except Exception as err:
        remove_file(scraper_path)
        log.error(f"Error with the scraper ({err})")
        return None

    remove_file(scraper_path)
    return scraped_data


FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

if SCENE_URL is None:
    sys.exit("You need to have a URL set")

if SCENE_URL and SCENE_ID is None:
    log.debug("URL Scraping: {}".format(SCENE_URL))
else:
    log.debug("Stash ID: {}".format(SCENE_ID))
    log.debug("Stash Title: {}".format(SCENE_TITLE))

STASH_CONFIG = graphql.configuration()

PATH_SCRAPER = STASH_CONFIG["general"]["scrapersPath"]
PATH_TMP = os.path.join(PATH_SCRAPER, "tmp")
PATH_MDLIST = os.path.join(PATH_TMP, "SCRAPERS-LIST.md")
PATH_ZIP = os.path.join(PATH_TMP, "scraper_master.zip")
PATH_MYSELF = os.path.realpath(__file__).replace(".py", ".yml")

GITHUB_LIST = "https://raw.githubusercontent.com/stashapp/CommunityScrapers/master/SCRAPERS-LIST.md"
GITHUB_ZIP = "https://github.com/stashapp/CommunityScrapers/archive/refs/heads/master.zip"
USER_AGENT = {
    "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0'
}

# trick to don't call himself  (for some reason, the request (scrape_SceneURL) can use this script)
os.rename(PATH_MYSELF, PATH_MYSELF + '.tmp')
try:
    result = main()
except Exception as err:
    result = None
    log.error(f"Error: {err}")

os.rename(PATH_MYSELF + '.tmp', PATH_MYSELF)
graphql.reloadScrapers()
#log.debug(result)
if result is None:
    result = {}
else:
    if result.get("url") is None:
        result["url"] = SCENE_URL
# Stash error when result is None ? runtime error: invalid memory address or nil pointer dereference
print(json.dumps(result))
