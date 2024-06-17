import json
import os
import pathlib
import re
import sys
from datetime import datetime

import py_common.log as log

try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()

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


# Check the URL and set the API URL
if 'sayuncle.com' in scene_url:
    ORIGIN = 'https://www.sayuncle.com'
    REFERER = 'https://www.sayuncle.com/'
    API_BASE = 'https://store2.psmcdn.net/sau-elastic-00gy5fg5ra-videoscontent/_doc/'
elif 'teamskeet.com' in scene_url:
    ORIGIN = 'https://www.teamskeet.com'
    REFERER = 'https://www.teamskeet.com/'
    API_BASE = 'https://store2.psmcdn.net/ts-elastic-d5cat0jl5o-videoscontent/_doc/'
elif 'mylf.com' in scene_url:
    ORIGIN = 'https://www.mylf.com'
    REFERER = 'https://www.mylf.com/'
    API_BASE = 'https://store2.psmcdn.net/mylf-elastic-hka5k7vyuw-videoscontent/_doc/'
else:
    log.error('The URL is not from a Teamskeet, MYLF or SayUncle URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)


scene_id = re.sub('.+/', '', scene_url)
if not scene_id:
    log.error("Error with the ID ({})\nAre you sure that the end of your URL is correct ?".format(scene_id))
    sys.exit(1)
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
    log.debug(f"Asking the API... {api_url}")
    scraper = cloudscraper.create_scraper()
    # Send to the API
    r = ""
    try:
        r = scraper.get(api_url, headers=headers, timeout=(3, 5))
    except:
        log.error("An error has occurred with the page request")
        log.error(f"Request status: `{r.status_code}`")
        log.error("Check your TeamskeetAPI.log for more details")
        with open("TeamskeetAPI.log", 'w', encoding='utf-8') as f:
            f.write(f"Scene ID: {scene_id}\n")
            f.write(f"Request:\n{r.text}")
        sys.exit(1)
    try:
        scene_api_json_check = r.json().get('found')
        if scene_api_json_check:
            scene_api_json = r.json()['_source']
        else:
            log.error('Scene not found (Wrong ID?)')
            sys.exit(1)

    except:
        if "Just a moment..." in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        else:
            log.error("Invalid page content")
        sys.exit(1)

# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
dt = scene_api_json.get('publishedDate')
if dt:
    dt = re.sub(r'T.+', '', dt)
    date = datetime.strptime(dt, '%Y-%m-%d')
    scrape['date'] = str(date.date())

#fix for TeamKseet including HTML tags in Description
CLEANR = re.compile('<.*?>') 
cleandescription = re.sub(CLEANR,'',scene_api_json.get('description'))
scrape['details'] = cleandescription
scrape['studio'] = {}
studioApiName = scene_api_json['site'].get('name')
log.debug("Studio API name is '" + studioApiName + "'")
scrape['studio']['name'] = studioMap[studioApiName] if studioApiName in studioMap else studioApiName
scrape['performers'] = [{"name": x.get('modelName')}
                        for x in scene_api_json.get('models')]
scrape['tags'] = [{"name": x} for x in scene_api_json.get('tags')]
scrape['code'] = scene_api_json.get('cId', '').split('/')[-1]
for tag in studioDefaultTags.get(studioApiName, []):
    log.debug("Assiging default tags - " + tag)
    scrape['tags'].append({"name": tag})
scrape['image'] = scene_api_json.get('img')

# Each of TeamSkeet, MYLF and SayUncle have different ways to handle 
# high resolution scene images.  SayUncle is a high resoution right
# from the scrape.  TeamSkeet and MYLF have different mappings between
# the scraped value and the higher resolution version.
match scene_url:
    case str(x) if 'sayuncle.com' in x:
        log.debug("Say Uncle image, using default size")
        high_res = scrape['image']
    case str(x) if 'teamskeet.com' in x:
        log.debug("TeamSkeet image, mapping members/full")
        high_res = scene_api_json.get('img').replace('shared/med', 'members/full')
    case str(x) if 'mylf.com' in x:
        log.debug("Mylf image, mapping bio_big")
        high_res = scene_api_json.get('img').replace('shared/med', 'bio_big')

log.debug(f"Image before: {scrape['image']}")
log.debug(f"Image after: {high_res}")
scrape['image'] = high_res

# If the scene is from sayuncle.com, we need to add the gay tag to the tags list
if 'sayuncle.com' in scene_url:
    scrape['tags'].append({"name": "Gay"})

if use_local == 0:
    save_json(scene_api_json, scene_url)
print(json.dumps(scrape))
