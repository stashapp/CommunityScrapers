import json
import os
import pathlib
import re
import sys
from datetime import datetime

import py_common.log as log
import cloudscraper

### SET MEMBER ACCESS TOKEN HERE
### CAN BE access_token OR refresh_token
TEAMSKEET_ACCESS_TOKEN = ""
MYLF_ACCESS_TOKEN = ""
####

scraper = cloudscraper.create_scraper()


def try_url(url):
    return scraper.head(url).status_code == 200

def try_img_replacement(imgurl):
    # members/full - 1600x900
    # bio_big - 1500x844
    # shared/hi - 1280x720
    # shared/med - 765x430
    for replacement in ['members/full', 'bio_big', 'shared/hi']:
        newurl = imgurl.replace('shared/med', replacement)
        if (try_url(newurl)):
            return newurl
    # try shared/hi on /tour url
    # get the subsite name
    subsite = imgurl.split("/")[4]
    # replace with /tour/pics
    tourHi = imgurl.replace(f"/{subsite}", f"/{subsite}/tour/pics").replace('shared/med', 'shared/hi')
    if (try_url(tourHi)):
        return tourHi
    # fallback to original image
    return imgurl

def save_json(api_json, url):
    try:
        if sys.argv[1] == "logJSON":
            try:
                os.makedirs(DIR_JSON)
            except FileExistsError:
                pass  # Dir already exist
            api_json['url'] = url
            filename = os.path.join(DIR_JSON, str(api_json['id'])+".json")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(api_json, file, ensure_ascii=False, indent=4)
    except IndexError:
        pass


USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON","Teamskeet")


# Not necessary but why not ?
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'

### Studio Mapper, to match scraped Studio Name to Studio Name as it appears in StashDB
studioMap = {
# TeamSkeet
    "BadMilfs": "Bad MILFs",
    "DadCrush": "Dad Crush",
    "GingerPatch": "Ginger Patch",
    "Hussie Pass": "TeamSkeet X Hussie Pass",
    "Not My Grandpa": "Not My Grandpa!",
    "PervMom": "Perv Mom",
    "PervTherapy": "Perv Therapy",
    "StayHomePov": "Stay Home POV",
    "StepSiblings": "Step Siblings",
    "TeenJoi": "Teen JOI",
    "TeamSkeet X BritStudioxxx": "TeamSkeet X BritStudio.XXX",
    "TeamSkeet X EvilAngel": "TeamSkeet X Evil Angel",
    "TeamSkeet X Joy Bear": "TeamSkeet X JoyBear",
    "TeamSkeet X Molly RedWolf": "TeamSkeet X MollyRedWolf",
    "TeamSkeet X OZ Fellatio Queens": "TeamSkeet X Aussie Fellatio Queens",
    "TeamSkeet X SpankMonster": "TeamSkeet X Spank Monster",
## MYLF
    "AnalMom": "Anal Mom",
    "BBCParadise": "BBC Paradise",
    "FullOfJoi": "Full Of JOI",
    "GotMylf": "Got MYLF",
    "LoneMilf": "Lone MILF",
    "MilfBody": "MILF Body",
    "MomDrips": "Mom Drips",
    "MomShoot": "Mom Shoot",
    "MylfBlows": "MYLF Blows",
    "MylfBoss": "MYLF Boss",
    "MylfSelects": "MYLF Selects",
    "PervNana": "Perv Nana",
    "StayHomeMilf": "Stay Home MILF",
    "UsePOV": "Use POV",
## SayUncle
    "Black Godz": "BlackGodz",
    "BottomGames": "Bottom Games",
    "BoysDoPorn": "Boys Do Porn",
    "DadCreep": "Dad Creep",
    "DoctorTapes": "Doctor Tapes",
    "MilitaryDick": "Military Dick",
    "SayUncle AllStars": "SayUncle All Stars",
    "StayHomeBro": "Stay Home Bro",
    "StickyRub": "Sticky Rub",
    "TroopSex": "Troop Sex",
    "YesFather": "Yes Father",
}

### Studio Default tags
studioDefaultTags = {
    "TeamSkeet Classics": ['Re-release'],
    "TeamSkeet Selects": ['Compilation'],
    "Mylf Classics": ['Re-release'],
    "MylfSelects": ['Compilation'],
    "SayUncle Classics": ['Re-release'],
}

fragment = json.loads(sys.stdin.read())
if fragment["url"]:
    scene_url = fragment["url"]
else:
    log.error('You need to set the URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

IS_MEMBER = False
# Check the URL and set the API URL
if 'app.teamskeet.com' in scene_url:
    ORIGIN = "https://app.teamskeet.com"
    REFERER = "https://app.teamskeet.com"
    API_BASE = "https://ma-store.teamskeet.com/ts_index/_doc/movie-"
    MEMBER_ACCESS_TOKEN = TEAMSKEET_ACCESS_TOKEN
    IS_MEMBER = True
elif 'app.mylf.com' in scene_url:
    ORIGIN = "https://app.mylf.com"
    REFERER = "https://app.mylf.com"
    API_BASE = "https://ma-store.mylf.com/mylf_movies/_doc/"
    MEMBER_ACCESS_TOKEN = MYLF_ACCESS_TOKEN
    IS_MEMBER = True
elif 'sayuncle.com' in scene_url:
    ORIGIN = 'https://www.sayuncle.com'
    REFERER = 'https://www.sayuncle.com/'
    API_BASE = 'https://tours-store.psmcdn.net/sau-elastic-alias-videoscontent/_doc/'
elif 'teamskeet.com' in scene_url:
    ORIGIN = 'https://www.teamskeet.com'
    REFERER = 'https://www.teamskeet.com/'
    API_BASE = 'https://tours-store.psmcdn.net/ts-elastic-alias-videoscontent/_doc/'
elif 'mylf.com' in scene_url:
    ORIGIN = 'https://www.mylf.com'
    REFERER = 'https://www.mylf.com/'
    API_BASE = 'https://tours-store.psmcdn.net/mylf-elastic-alias-videoscontent/_doc/'
elif 'swappz.com' in scene_url:
    ORIGIN = 'https://www.swappz.com'
    REFERER = 'https://www.swappz.com/'
    API_BASE = 'https://tours-store.psmcdn.net/swap_bundle/_search?size=1&q=id:'
elif 'freeuse.com' in scene_url:
    ORIGIN = 'https://www.freeuse.com'
    REFERER = 'https://www.freeus.com/'
    API_BASE = 'https://tours-store.psmcdn.net/freeusebundle/_search?size=1&q=id:'
else:
    log.error('The URL is not from a Teamskeet, MYLF, Freeuse, SayUncle or Swappz URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

# check for member access token
if (IS_MEMBER and MEMBER_ACCESS_TOKEN == ""):
    log.error("You are trying to scrape a member scene without an acess token")
    log.error("Please edit the scraper and populate the corresponding _ACCESS_TOKEN variable")

scene_id = re.match(r'.+\/([\w\d-]+)', scene_url)
if not scene_id:
    log.error("Error with the ID ({})\nAre you sure that the end of your URL is correct ?".format(scene_id))
    sys.exit(1)
scene_id = scene_id.group(1)
use_local = 0
json_file = os.path.join(DIR_JSON, scene_id+".json")
if os.path.isfile(json_file):
    log.debug("Using local JSON...")
    use_local = 1
    with open(json_file, encoding="utf-8") as json_file:
        scene_api_json = json.load(json_file)
else:
    api_url = f"{API_BASE}{scene_id}"
    headers = {
        'User-Agent': USER_AGENT,
        'Origin': ORIGIN,
        'Referer': REFERER
    }
    if IS_MEMBER:
        headers.update({"Cookie": f"access_token={MEMBER_ACCESS_TOKEN}"})
    log.debug(f"Asking the API... {api_url}")

    # Send to the API
    r = ""
    try:
        r = scraper.get(api_url, headers=headers, timeout=(3, 5))
    except Exception as e:
        log.error("An error has occurred with the page request")
        log.error(e)
        log.error("Check your TeamskeetAPI.log for more details")
        with open("TeamskeetAPI.log", 'w', encoding='utf-8') as f:
            f.write(f"Scene ID: {scene_id}\n")
            f.write(f"Request:\n{e}")
        sys.exit(1)
    try:
        scene_api_json_check = r.json().get('found')
        if scene_api_json_check:
            scene_api_json = r.json()['_source']
        # Get swappz search hit
        elif r.json().get("hits"):
            scene_api_json = r.json()['hits']['hits'][0]['_source']
        else:
            log.error('Scene not found (Wrong ID?)')
            sys.exit(1)

    except Exception:
        log.debug(r.status_code)
        if (r.status_code == 401 and IS_MEMBER):
            log.error("It's likely that your member access token needs to be replaced")
        if "Just a moment..." in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        else:
            log.error("Invalid page content")
        sys.exit(1)

# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
# for members, used publishedDateRank
dt = scene_api_json.get("publishedDateRank") if IS_MEMBER else scene_api_json.get('publishedDate')

if dt:
    dt = re.sub(r'T.+', '', dt)
    date = datetime.strptime(dt, '%Y-%m-%d')
    scrape['date'] = str(date.date())

# replace tags manually
tags = scene_api_json.get('tags')
if tags:
    for i, tag in enumerate(tags):
        # inconsistent use on TeamSkeet since it was added as a tag
        if tag == "Pumps":
            tags[i] = "Woman's Heels"
        if tag.lower() == "null":
            tags.pop(i)

#fix for TeamKseet including HTML tags in Description
CLEANR = re.compile('<.*?>') 
cleandescription = re.sub(CLEANR,'',scene_api_json.get('description'))
scrape['details'] = cleandescription.strip()
scrape['studio'] = {}
# pull directly from siteName if member
studioApiName = scene_api_json['site'].get('siteName') if IS_MEMBER else scene_api_json['site'].get('name')
log.debug("Studio API name is '" + studioApiName + "'")
scrape['studio']['name'] = studioMap[studioApiName] if studioApiName in studioMap else studioApiName
if " x " in scrape['studio']['name'].lower():
    tags.append("Redistribution")
scrape['tags'] = [{"name": x} for x in tags]
scrape['code'] = scene_id if IS_MEMBER else scene_api_json.get('cId', '').split('/')[-1]
for tag in studioDefaultTags.get(studioApiName, []):
    log.debug("Assiging default tags - " + tag)
    scrape['tags'].append({"name": tag})
scrape['image'] = scene_api_json.get('img')
# handle members performers differently
if IS_MEMBER:
    scrape['performers'] = [{"name": x.get('name')}
        for x in scene_api_json.get('models')]
# handle swappz and freeuse performers differently
elif any(u in scene_url for u in ['swappz.com','freeuse.com']):
    scrape['performers'] = [{"name": x.get('title')}
        for x in scene_api_json.get('models')]
else:
    scrape['performers'] = [{"name": x.get('modelName')}
        for x in scene_api_json.get('models')]

# Each of TeamSkeet, MYLF and SayUncle have different ways to handle 
# high resolution scene images.  SayUncle is a high resoution right
# from the scrape.  TeamSkeet and MYLF have different mappings between
# the scraped value and the higher resolution version.

# try to (and check) higher res images if possible
high_res = try_img_replacement(scene_api_json.get('img'))

log.debug(f"Image before: {scrape['image']}")
log.debug(f"Image after: {high_res}")
scrape['image'] = high_res

# If the scene is from sayuncle.com, we need to add the gay tag to the tags list
if 'sayuncle.com' in scene_url:
    scrape['tags'].append({"name": "Gay"})

if use_local == 0:
    save_json(scene_api_json, scene_url)
log.debug(json.dumps(scene_api_json))
print(json.dumps(scrape))
