import datetime
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

from py_common import log
import requests

def sendRequest(url, req_headers):
    req = ""
    try:
        req = requests.get(url, headers=req_headers, timeout=(3, 5))
    except requests.exceptions.RequestException:
        log.error("An error has occurred with Requests")
        log.error("Check your ModelCentroAPI.log for more details")
        with open("ModelCentroAPI.log", 'w', encoding='utf-8') as log_file:
            log_file.write(f"Request:\n{req}")
        sys.exit(1)
    return req


def check_config(time_now):
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        try:
            ini_keys1 = config.get(DOMAIN_URL, 'keys1')
            ini_keys2 = config.get(DOMAIN_URL, 'keys2')
            ini_date = config.get(DOMAIN_URL, 'date')
            time_past = datetime.datetime.strptime(ini_date, '%Y-%m-%d %H:%M:%S.%f')
            # Key for 1 days
            if time_past.day - time_now == 0:
                log.debug("Using old API keys")
                return ini_keys1, ini_keys2
            log.debug("Need new API keys")
        except NoSectionError:
            pass
    return None, None


def write_config(keys1, keys2):
    config = ConfigParser()
    config.read(SET_FILE_URL)
    try:
        config.get(DOMAIN_URL, 'date')
    except NoSectionError:
        config.add_section(DOMAIN_URL)
    config.set(DOMAIN_URL, 'keys1', keys1)
    config.set(DOMAIN_URL, 'keys2', keys2)
    config.set(DOMAIN_URL, 'date', str(datetime.datetime.now()))
    with open(SET_FILE_URL, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

FRAGMENT = json.loads(sys.stdin.read())
SCENE_URL = FRAGMENT["url"]
DOMAIN_URL = urlparse(SCENE_URL).netloc
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
SET_FILE_URL = "ModelCentroAPI.ini"

studioMap = {
    "amberlilyshow":"Amber Lily Show",
    "amberspanks":"Amber Spanks",
    "americankitten":"American Kitten",
    "amirahadaraxxx":"Amirah Adara XXX",
    "anastasiagree":"Anastasia Gree",
    "anisyia.xxx":"Anisyia XXX",
    "arabellesplayground": "Arabelle's Playground",
    "arinna-cum": "Arinna Cum",
    "aussiexxxhookups":"Aussie XXX HookUps",
    "bhalasada":"Bhala Sada",
    "bigjohnnyxxx":"Big Johnny XXX",
    "blondehexe.net":"BlondeHexe",
    "bohonude.art":"Nude Art Boho",
    "brandonlh":"Brandon Lee Harrington Productions",
    "brianaleecams":"Briana Lee Cams",
    "brookelynnebriar":"Brookelynne Briar",
    "carlhubaygay.xxx":"Carl Hubay Gay",
    "cartoons4grownfolks":"Cartoons 4 Grown Folks",
    "claradeemembers":"Clara Dee Members",
    "clubmaseratixxx": "Club Maserati XXX",
    "cospimps":"CosPimps",
    "danidaniels":"Dani Daniels",
    "darkwetdreemz":"Dark Wet Dreemz",
    "deepsmashmedia":"Deep Smash Media",
    "denudeart":"DenudeArt",
    "dillionation":"Dillio Nation",
    "dirtytina":"Dirty Tina",
    "erinelectra":"Erin Electra",
    "erospiration":"Erospiration",
    "eroticcecelia":"Erotic Cecelia",
    "euroslut.club":"Euro Slut",
    "facialcasting":"Facial Casting",
    "fallinlovia":"Fall In Lovia",
    "fallonfuckingwest":"Fallon Fucking West",
    "getyourkneesdirty":"Get Your Knees Dirty",
    "ginagerson.xxx":"Gina Gerson",
    "hentacles":"Hentacles",
    "hollandswing":"Holland Swing",
    "honeybarefeet":"Miss Honey Barefeet",
    "hurricanefury":"Hurricane Fury",
    "immoralfantasy":"Immoral Fantasy",
    "irenerouse":"Irene Rouse",
    "isinxxx":"iSinXXX",
    "jenysmith.net":"Jeny Smith",
    "jerkoffwithme":"Jerkoff With Me",
    "jessieminxxx":"JessieMinxxx.com",
    "kacytgirl":"Sexy Kacy",
    "katie71":"Katie 71",
    "katrinporto":"Katrin Porto",
    "kendrasinclaire":"Kendra Sinclaire",
    "kinkyrubberworld":"Kinky Rubber World",
    "klubkelli": "Klub Kelli",
    "krisskiss":"Kriss Kiss",
    "kyleenash":"Kylee Nash",
    "ladysublime":"Lady Sublime",
    "lilcandy":"LilCandy",
    "lilumoon":"Lilu Moon",
    "lilychey":"Lily Chey",
    "lonelymeow":"LonelyMeow",
    "lornablu.net":"Lorna Blu",
    "lynnasexworld":"Lynna Sex World",
    "masculinejason":"Masculine Jason",
    "melenamariarya":"Melena Maria Rya",
    "miamaffia":"Mia Maffia",
    "monstermalesprod":"MonsterMales",
    "mugursworld":"Mugur Porn",
    "mylifeinmiami":"My Life In Miami",
    "nancyace":"Nancy Ace",
    "nataliek.xxx":"Natalie K",
    "natashanice":"Natasha Nice",
    "naughty-lada": "Naughty Lada",
    "niarossxxx":"Nia Ross XXX",
    "nikkojordan":"Nikko Jordan",
    "niksindian":"Niks Indian",
    "officialelizabethmarxs":"ElizabethMarxs",
    "onedomproductions":"One Dom Productions",
    "openlegsxxx": "Open Legs",
    "peccatriciproduzioni":"Pecca Trici Produzioni",
    "peghim":"Peg Him",
    "platinumpuzzy.net":"Platinum Puzzy",
    "pornojuice":"Porno Juice",
    "porntugal":"Porntugal",
    "psychohenessy":"Henessy",
    "puremolly":"Molly Pills",
    "pvgirls": "Porn Valley Girls",
    "realagent.xxx":"Real Agent",
    "realpeachez":"Sarah Peachez",
    "rebeccalordproductions":"Rebecca Lord Productions",
    "rexringoxxx.xxx":"Rex Ringo XXX Productions",
    "sabrinasabrokporn":"Sabrina Sabrok Videos",
    "sallydangeloxxx":"City Girlz",
    "sam38g":"Samantha38g",
    "samantalily.xxx": "Samanta Lily",
    "santalatina":"Santalatina",
    "shalinadevine":"Shalina Devine",
    "shootingstar4u.me":"Orgasmic Shooting Star",
    "sirberusssanctum.net":"Sir Berus's Sanctum",
    "sluttywildthing":"Slutty Wild Thing",
    "southerncumsluts":"Southern Cum Sluts",
    "stefolino":"Stefolino",
    "sweetiefox.net":"Sweetie Fox",
    "sylviasucker":"Sylvia Chrystall",
    "tahliaparis":"Tahlia Paris",
    "tanyatate.xxx":"Tanya Tate",
    "theamofficial":"Ass Monkey",
    "theaudreyhollander":"Audrey Hollander Anal Queen",
    "thiccvision":"Thicc Vision",
    "ticklehotness":"Tickle Hotness",
    "trinetyguess":"Trinety Guess",
    "vinaskyxxx":"VinaSkyXXX",
    "womenwhosmoke":"Women Who Smoke",
    "xtcpov":"XTC POV",
    "xtremestudios.studio69swf.live":"Xtreme Studios Media",
    "xxxotikangelzent": "xXxOTIK ANGELZ",
    "yourgoonspace":"Your Goon Space"
}

# Map of studios that don't list performers, but have a fixed set of performers for all scenes.
# Or sites that have a primary performer that is in all scenes but not always listed.
# These are lists in case a future studio has more than one performer in all scenes.
# Use the site name as it shows up in the URL.  Where the TLD is not .com, include the TLD (eg, .xxx)
fixedPerformerStudio = {
    "amberlilyshow" : ["Amber Lily"],
    "amberspanks" : ["Amber Spanks"],
    "amirahadaraxxx" : ["Amirah Adara"],
    "anastasiagree" : ["Anastasia Gree"],
    "anisyia.xxx" : ["Anisyia"],
    "arabellesplayground": ["Arabelle Raphael"],
    "arinnacum": ["Arinna Cum"],
    "blondehexe.net" : ["Blonde Hexe"],
    "brianaleecams" : ["Briana Lee"],
    "brookelynnebriar" : ["Brookelynne Briar"],
    "claradeemembers" : ["Clara Dee"],
    "clubmaseratixxx": ["Maserati XXX"],
    "danidaniels" : ["Dani's Things"],
    "eroticcecelia" : ["Cecelia"],
    "fallinlovia" : ["Eva Lovia"],
    "ginagerson.xxx": ["Gina Gerson"],
    "hollandswing": ["Nikki Holland"],
    "honeybarefeet": ["Miss Honey Barefeet"],
    "hurricanefury": ["Hurricane Fury"],
    "irenerouse": ["Irene Rouse"],
    "jenysmith.net": ["Jeny Smith"],
    "jessieminxxx": ["Jessie Minx"],
    "kacytgirl": ["Kacy"],
    "katie71": ["Katlynn"],
    "kendrasinclaire": ["Kendra Sinclaire"],
    "krisskiss" : ["Kriss Kiss"],
    "kyleenash": ["Kylee Nash"],
    "ladysublime": ["Lady Sublime"],
    "lilcandy": ["Lil Candy"],
    "lilumoon": ["Lilu Moon"],
    "lilychey": ["Lily Chey"],
    "lonelymeow": ["LonelyMeow"],
    "lornablu.net": ["Lorna Blu"],
    "lynnasexworld": ["Lynna Nilsson"],
    "masculinejason": ["Jason Collins"],
    "melenamariarya": ["Melena Maria Rya"],
    "nancyace": ["Nancy Ace"],
    "nataliek.xxx": ["Natalie K"],
    "natashanice": ["Natasha Nice"],
    "naughty-lada": ["Naughty Lada"],
    "niarossxxx": ["Nia Ross"],
    "nikkojordan": ["Nikko Jordan"],
    "officialelizabethmarxs":["Elizabeth Marxs"],
    "psychohenessy": ["Alina Henessy"],
    "puremolly": ["Molly Pills"],
    "realpeachez": ["Sarah Peachez"],
    "rexringoxxx.xxx": ["Rex Ringo"],
    "sabrinasabrokporn": ["Sabrina Sabrok"],
    "sallydangeloxxx": ["Sally D'angelo"],
    "sam38g": ["Samantha 38g"],
    "samantalily.xxx": ["Samanta Lily"],
    "shootingstar4u.me": ["Orgasmic Shooting Star"],
    "sweetiefox.net": ["Sweetie Fox"],
    "sylviasucker": ["Sylvia Chrystall"],
    "tahliaparis": ["Tahlia Paris"],
    "tanyatate.xxx": ["Tanya Tate"],
    "theaudreyhollander": ["Audrey Hollander"],
    "trinetyguess": ["Trinety Guess"],
    "vinaskyxxx": ["Vina Sky"],
}

# Map of studios that don't list tags, but have a fixed set of tags for all scenes.
# Or sites that have tags, but don't include the obvious ones since it applies to every scene
# Use the site name as it shows up in the URL.  Where the TLD is not .com, include the TLD (eg, .xxx)

defaultStudioTags= {
    "amirahadaraxxx": ["Brown Hair (Female)", "Hungarian", "Natural Tits", "Small Tits", "White Woman"],
    "anastasiagree": ["BBW","Brown Hair (Female)","Solo Female","White Woman"],
    "anisyia.xxx": ["Fake Tits","Brown Hair (Female)","Long Hair","White Woman"],
    "arabellesplayground": ["Big Tits", "Natural Tits", "White Woman"],
    "arinna-cum": ["Blonde Hair (Female)", "White Woman"],
    "blondehexe.net": ["Blonde Hair (Female)","Solo Female","White Woman","Natural Tits"],
    "bohonude.art": ["Softcore","Solo Female"],
    "brookelynnebriar.net": ["Brown Hair (Female)","Natural Tits","White Woman"],
    "brianaleecams": ["Brown Hair (Female)","Natural Tits","White Woman","Long Hair","Natural Tits"],
    "carlhubaygay.net": ["Mature","Gay","White Man"],
    "cartoons4grownfolks": ["Animated"],
    "claradeemembers": ["Brown Hair (Female)","Natural Tits","White Woman"],
    "clubmaseratixxx": ["Brown Hair (Female)", "Natural Tits", "Big Tits", "Black Woman"],
    "danidaniels": ["Brown Hair (Female)","Natural Tits","White Woman"],
    "darkwetdreemz": ["Natural Tits","Black Woman"],
    "erinelectra": ["Natural Tits","White Woman", "White Man","Twosome (Straight)"],
    "eroticcecelia": ["Solo Female","Softcore"],
    "facialcasting": ["Facial","Cumshot"],
    "getyourkneesdirty": ["Small Dick","Cumshot","White Man","Blowjob"],
    "ginagerson.xxx": ["Blonde Hair (Female)","White Woman","Natural Tits"],
    "hollandswing": ["White Woman","Natural Tits"],
    "irenerouse": ["Brown Hair (Female)","Long Hair","White Woman","Natural Tits","Solo Female"],
    "jenysmith.net": ["Brown Hair (Female)","Long Hair","White Woman","Natural Tits"],
    "kacytgirl": ["Blonde Hair (Female)","Trans Woman","White Woman"],
    "katie71": ["Brown Hair (Female)","Long Hair","White Woman"],
    "kendrasinclaire": ["Trans Woman","White Woman","Brown Hair (Female)","Long Hair"],
    "klubkelli": ["Redistribution"],
    "krisskiss": ["White Woman","Brown Hair (Female)","Long Hair"],
    "kyleenash": ["Fake Tits","Solo Female","MILF","White Woman"],
    "ladysublime": ["BBW","Brown Hair (Female)","Solo Female","White Woman", "Long Hair"],
    "lilcandy": ["White Woman","Natural Tits"],
    "lilumoon": ["White Woman","Natural Tits","Brown Hair (Female)","Long Hair"],
    "lilychey": ["White Woman","Natural Tits","Brown Hair (Female)","Long Hair"],
    "lonelymeow": ["Asian Woman","Natural Tits","Black Hair (Female)","Long Hair"],
    "lornablu.net": ["Mature","Blonde Hair (Female)","White Woman","Natural Tits"],
    "lynnasexworld": ["Blonde Hair (Female)","White Woman","Fake Tits"],
    "masculinejason": ["Bald","White Man","Gay","Tattoos"],
    "melenamariarya": ["White Woman","Natural Tits","Brown Hair (Female)","Long Hair"],
    "miamaffia.xxx": ["Trans Woman","White Woman","Tattoos","Long Hair"],
    "nancyace": ["White Woman","Blonde Hair (Female)","Long Hair","Natural Tits"],
    "nataliek.xxx": ["White Woman","Blonde Hair (Female)","Long Hair","MILF","Natural Tits"],
    "natashanice": ["White Woman","Brown Hair (Female)","Long Hair","Natural Tits"],
    "naughty-lada": ["White Woman","Brown Hair (Female)", "MILF", "Big Tits", "Natural Tits"],
    "niarossxxx": ["Black Woman","Black Hair (Female)","Natural Tits"],
    "niksindian": ["South Asian Woman"],
    "officialelizabethmarxs": ["White Woman","Natural Tits","Red Hair"],
    "peccatriciproduzioni": ["Mature","Brown Hair (Female)","White Woman","Natural Tits"],
    "peghim": ["Pegging","Toys","Anal Toys","Strap-on"],
    "platinumpuzzy.net": ["BBW"],
    "psychohenessy": ["White Woman","Brown Hair (Female)","Long Hair","Natural Tits"],
    "puremolly": ["White Woman","Blonde Hair (Female)","Long Hair","Natural Tits"],
    "realpeachez": ["White Woman","Blonde Hair (Female)","Long Hair","Natural Tits"],
    "rexringoxxx.xxx": ["Black Male"],
    "sabrinasabrokporn": ["White Woman","Blonde Hair (Female)","Long Hair","Fake Tits"],
    "sallydangeloxxx": ["White Woman","Blonde Hair (Female)","Long Hair","Fake Tits","Mature"],
    "sam38g": ["White Woman","Red Head","Long Hair","Natural Tits","Big Tits","Solo Female"],
    "samantalily.xxx": ["White Woman", "Big Tits", "Natural Tits"],
    "santalatina": ["Latina Woman","Black Hair (Female)","Long Hair","Natural Tits"],
    "shalinadevine": ["White Woman","Blonde Hair (Female)","Long Hair","Fake Tits"],
    "shootingstar4u.me": ["White Woman","Blonde Hair (Female)","Natural Tits"],
    "sirberusssanctum.net": ["Black Man","Black Hair (Male)"],
    "sluttywildthing": ["White Woman","Brown Hair (Female)","Long Hair","Natural Tits"],
    "sweetiefox.net": ["White Woman","Fake Tits"],
    "sylviasucker": ["White Woman","Brown Hair (Female)","Blowjob","Natural Tits"],
    "tahliaparis": ["White Woman","Fake Tits","Blonde Hair (Female)"],
    "tanyatate.xxx": ["White Woman","Fake Tits","Blonde Hair (Female)"],
    "theaudreyhollander": ["White Woman","Natural Tits","Red Hair"],
    "ticklehotness": ["Tickling"],
    "trinetyguess": ["BBW","Solo Female","White Woman"],
    "vinaskyxxx": ["Asian Woman","Natural Tits","Black Hair (Female)","Long Hair"],
    "womenwhosmoke": ["Smoking"],
    "xtcpov": ["POV"],
}

## At least one studio has seriously managed to mess up their tags by not splitting them properly.
## Do what we can to break the mess of a single tag they return with spaces.  It might not be
## perfect but it's better than what's returned by the API.
studioTagsNeedSplitting = [
	'rexringoxxx.xxx',
]

scene_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
if not scene_id:
    log.error(f"Error with the ID ({SCENE_URL})\nAre you sure that your URL is correct ?")
    sys.exit(1)

timenow = datetime.datetime.now()
api_key1, api_key2 = check_config(timenow.day)
if api_key1 is None:
    log.debug("Going to the URL...")
    url_headers = {
        'User-Agent': USER_AGENT
    }
    r = sendRequest(SCENE_URL, url_headers)
    page_html = r.text
    try:
        api_function = re.findall(
            r'_fox_init(.+)</script>', page_html, re.DOTALL | re.MULTILINE)[0]
        api_key1 = re.findall(
            r'ah":"([a-zA-Z0-9_-]+)"', api_function, re.MULTILINE)[0]
        api_key2 = re.findall(r'aet":(\d+),"', api_function, re.MULTILINE)[0]
        # Need to reverse this key
        api_key1 = api_key1[::-1]
        write_config(api_key1, api_key2)
    except IndexError:
        log.error("There is a problem with getting API identification")
        sys.exit(1)

log.debug("Asking the Scene API...")
api_url = f"https://{DOMAIN_URL}/sapi/{api_key1}/{api_key2}/content.load?_method=content.load&tz=1&filter[id][fields][0]=id&filter[id][values][0]={scene_id}&transitParameters[v1]=ykYa8ALmUD&transitParameters[preset]=scene"
headers = {
    'User-Agent': USER_AGENT,
    'Referer': SCENE_URL
}
r = sendRequest(api_url, headers)
log.debug(r.content)
try:
    scene_api_json = r.json()['response']['collection'][0]
except Exception as e:
    log.error("Error with Request API:" + str(e))
    sys.exit(1)

log.debug("Trying the Performer API...")
perf_list = []
api_url = f"https://{DOMAIN_URL}/sapi/{api_key1}/{api_key2}/model.getModelContent?_method=model.getModelContent&tz=1&fields[0]=modelId.stageName&transitParameters[contentId]={scene_id}"
r = sendRequest(api_url, headers)
try:
    performer_api_json = r.json()['response']['collection']
    for perf_id in performer_api_json:
        for perf_id2 in performer_api_json[perf_id]['modelId']['collection']:
            performer_name=performer_api_json[perf_id]['modelId']['collection'][perf_id2]['stageName'].strip()
            perf_list.append({"name": performer_name})
except:
    log.error("Performer API failed")
# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
date = datetime.datetime.strptime(scene_api_json['sites']['collection'][scene_id].get('publishDate'), '%Y-%m-%d %H:%M:%S')
scrape['date'] = str(date.date())
scrape['details'] = scene_api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = re.sub(r'www\.|\.com', '', DOMAIN_URL)
scrape['tags'] = []
scrape['performers'] = []

if perf_list:
    scrape['performers'] = perf_list

if scrape['studio']['name'] in fixedPerformerStudio:
    for performer in fixedPerformerStudio[scrape['studio']['name']]:
        if not any(d['name'].lower() == performer.lower() for d in scrape['performers']):
            scrape['performers'].append({'name':performer})

if scrape['studio']['name'] in studioTagsNeedSplitting:
    for x in scene_api_json['tags']['collection']:
        for tag in scene_api_json['tags']['collection'][x].get('alias').split(' '):
            if not any(d['name'].lower() == tag.lower() for d in scrape['tags']):
                scrape['tags'].append({"name": tag.strip()})
else:
    scrape['tags'] = [{"name": scene_api_json['tags']['collection'][x].get('alias')} for x in scene_api_json['tags']['collection']]

if scrape['studio']['name'] in defaultStudioTags:
    for tag in defaultStudioTags[scrape['studio']['name']]:
        if not any(d['name'].lower() == tag.lower() for d in scrape['tags']):
            scrape['tags'].append({"name": tag})

if scrape['studio']['name'] in studioMap:
    scrape['studio']['name'] = studioMap[scrape['studio']['name']]

scrape['image'] = scene_api_json['_resources']['primary'][0]['url']
for key_name, key_value in scrape.items():
    log.debug(f'[{key_name}]:{key_value}')

print(json.dumps(scrape))
