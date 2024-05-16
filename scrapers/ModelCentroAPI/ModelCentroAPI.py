import datetime
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

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
    "anastasiagree":"Anastasia Gree",
    "anisyia.xxx":"Anisyia XXX",
    "aussiexxxhookups":"Aussie XXX HookUps",
    "bhalasada":"Bhala Sada",
    "bigjohnnyxxx":"Big Johnny XXX",
    "blondehexe.net":"BlondeHexe",
    "brandonlh":"Brandon Lee Harrington Productions",
    "brookelynnebriar":"Brookelynne Briar",
    "carlhubaygay.xxx":"Carl Hubay Gay",
    "cartoons4grownfolks":"Cartoons 4 Grown Folks",
    "claradeemembers":"Clara Dee Members",
    "cospimps":"CosPimps",
    "danidaniels":"Dani Daniels",
    "darkwetdreemz":"Dark Wet Dreemz",
    "deepsmashmedia":"Deep Smash Media",
    "denudeart":"DenudeArt",
    "dillionation":"Dillio Nation",
    "dirtytina":"Dirty Tina",
    "erinelectra":"Erin Electra",
    "erospiration":"Erospiration",
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
    "isinxxx":"iSinXXX",
    "jenysmith.net":"Jeny Smith",
    "jerkoffwithme":"Jerkoff With Me",
    "jessieminxxx":"JessieMinxxx.com",
    "kacytgirl":"Sexy Kacy",
    "katie71":"Katie 71",
    "katrinporto":"Katrin Porto",
    "kendrasinclaire":"Kendra Sinclaire",
    "kinkyrubberworld":"Kinky Rubber World",
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
    "mylifeinmiami":"My Life In Miami",
    "nataliek.xxx":"Natalie K",
    "natashanice":"Natasha Nice",
    "niarossxxx":"Nia Ross XXX",
    "niksindian":"Niks Indian",
    "officialelizabethmarxs":"ElizabethMarxs",
    "onedomproductions":"One Dom Productions",
    "peccatriciproduzioni":"Pecca Trici Produzioni",
    "peghim":"Peg Him",
    "platinumpuzzy.net":"Platinum Puzzy",
    "pornojuice":"Porno Juice",
    "porntugal":"Porntugal",
    "psychohenessy":"Henessy",
    "puremolly":"Molly Pills",
    "realagent.xxx":"Real Agent",
    "realpeachez":"Sarah Peachez",
    "sabrinasabrokporn":"Sabrina Sabrok Videos",
    "sallydangeloxxx":"City Girlz",
    "sam38g":"Samantha38g",
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
    "yourgoonspace":"Your Goon Space"
}

# Map of studios that don't list performers, but have a fixed set of performers for all scenes.
# Or sites that have a primary performer that is in all scenes but not always listed.
# These are lists in case a future studio has more than one performer in all scenes.
# Use the site name as it shows up in the URL.  Where the TLD is not .com, include the TLD (eg, .xxx)
fixedPerformerStudio = {
    "amberlilyshow" : ["Amber Lily"],
    "amberspanks" : ["Amber Spanks"],
    "anastasiagree" : ["Anastasia Gree"],
    "anisyia.xxx" : ["Anisyia"],
    "blondehexe.net" : ["Blonde Hexe"],
    "brookelynnebriar" : ["Brookelynne Briar"],
    "claradeemembers" : ["Clara Dee"],
    "danidaniels" : ["Dani's Things"],
    "fallinlovia" : ["Eva Lovia"],
    "ginagerson.xxx": ["Gina Gerson"],
    "hollandswing": ["Nikki Holland"],
    "honeybarefeet": ["Miss Honey Barefeet"],
    "hurricanefury": ["Hurricane Fury"],
    "jenysmith.net": ["Jeny Smith"],
    "jessieminxxx": ["Jessie Minx"],
    "kacytgirl": ["Kacy"],
    "katie71": ["Katlynn"],
    "kendrasinclaire": ["Kendra Sinclaire"],
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
    "nataliek.xxx": ["Natalie K"],
    "natashanice": ["Natasha Nice"],
    "niarossxxx": ["Nia Ross"],
    "officialelizabethmarxs":["Elizabeth Marxs"],
    "psychohenessy": ["Alina Henessy"],
    "puremolly": ["Molly Pills"],
    "realpeachez": ["Sarah Peachez"],
    "sabrinasabrokporn": ["Sabrina Sabrok"],
    "sallydangeloxxx": ["Sally D'angelo"],
    "sam38g": ["Samantha 38g"],
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
    "anastasiagree": ["BBW","Brunette","Solo Female","White Woman"],
    "anisyia.xxx": ["Fake Tits","Brunette","Long Hair","White Woman"],
    "blondehexe.net": ["Blonde","Solo Female","White Woman","Natural Tits"],
    "brookelynnebriar.net": ["Brunette","Natural Tits","White Woman"],
    "carlhubaygay.net": ["Mature","Gay","White Man"],
    "cartoons4grownfolks": ["Animated"],
    "claradeemembers": ["Brunette","Natural Tits","White Woman"],
    "danidaniels": ["Brunette","Natural Tits","White Woman"],
    "darkwetdreemz": ["Natural Tits","Black Woman"],
    "erinelectra": ["Natural Tits","White Woman", "White Man","Twosome (Straight)"],
    "facialcasting": ["Facial","Cumshot"],
    "getyourkneesdirty": ["Small Dick","Cumshot","White Man","Blowjob"],
    "ginagerson.xxx": ["Blonde","White Woman","Natural Tits"],
    "hollandswing": ["White Woman","Natural Tits"],
    "jenysmith.net": ["Brunette","Long Hair","White Woman","Natural Tits"],
    "kacytgirl": ["Blonde","Trans Woman","White Woman"],
    "katie71": ["Brunette","Long Hair","White Woman"],
    "kendrasinclaire": ["Trans Woman","White Woman","Brunette","Long Hair"],
    "kyleenash": ["Fake Tits","Solo Female","MILF","White Woman"],
    "ladysublime": ["BBW","Brunette","Solo Female","White Woman", "Long Hair"],
    "lilcandy": ["White Woman","Natural Tits"],
    "lilumoon": ["White Woman","Natural Tits","Brunette","Long Hair"],
    "lilychey": ["White Woman","Natural Tits","Brunette","Long Hair"],
    "lonelymeow": ["Asian Woman","Natural Tits","Black Hair","Long Hair"],
    "lornablu.net": ["Mature","Blonde","White Woman","Natural Tits"],
    "lynnasexworld": ["Blonde","White Woman","Fake Tits"],
    "masculinejason": ["Bald","White Man","Gay","Tattoos"],
    "melenamariarya": ["White Woman","Natural Tits","Brunette","Long Hair"],
    "miamaffia.xxx": ["Trans Woman","White Woman","Tattoos","Long Hair"],
    "nataliek.xxx": ["White Woman","Blonde","Long Hair","MILF","Natural Tits"],
    "natashanice": ["White Woman","Brunette","Long Hair","Natural Tits"],
    "niarossxxx": ["Black Woman","Black Hair","Natural Tits"],
    "niksindian": ["South Asian Woman"],
    "officialelizabethmarxs": ["White Woman","Natural Tits","Red Hair"],
    "peccatriciproduzioni": ["Mature","Brunette","White Woman","Natural Tits"],
    "peghim": ["Pegging","Toys","Anal Toys","Strap-on"],
    "platinumpuzzy.net": ["BBW"],
    "psychohenessy": ["White Woman","Brunette","Long Hair","Natural Tits"],
    "puremolly": ["White Woman","Blonde","Long Hair","Natural Tits"],
    "realpeachez": ["White Woman","Blonde","Long Hair","Natural Tits"],
    "sabrinasabrokporn": ["White Woman","Blonde","Long Hair","Fake Tits"],
    "sallydangeloxxx": ["White Woman","Blonde","Long Hair","Fake Tits","Mature"],
    "sam38g": ["White Woman","Red Head","Long Hair","Natural Tits","Big Tits","Solo Female"],
    "santalatina": ["Latina Woman","Black Hair","Long Hair","Natural Tits"],
    "shalinadevine": ["White Woman","Blonde","Long Hair","Fake Tits"],
    "shootingstar4u.me": ["White Woman","Blonde","Natural Tits"],
    "sirberusssanctum.net": ["Black Man","Black Hair"],
    "sluttywildthing": ["White Woman","Brunette","Long Hair","Natural Tits"],
    "sweetiefox.net": ["White Woman","Fake Tits"],
    "sylviasucker": ["White Woman","Brunette","Blowjob","Natural Tits"],
    "tahliaparis": ["White Woman","Fake Tits","Blonde"],
    "tanyatate.xxx": ["White Woman","Fake Tits","Blonde"],
    "theaudreyhollander": ["White Woman","Natural Tits","Red Hair"],
    "ticklehotness": ["Tickling"],
    "trinetyguess": ["BBW","Solo Female","White Woman"],
    "vinaskyxxx": ["Asian Woman","Natural Tits","Black Hair","Long Hair"],
    "womenwhosmoke": ["Smoking"],
    "xtcpov": ["POV"],
    
}

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
            performer_name=performer_api_json[perf_id]['modelId']['collection'][perf_id2]['stageName']
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
scrape['performers'] = []

if perf_list:
    scrape['performers'] = perf_list
if scrape['studio']['name'] in fixedPerformerStudio:
    for performer in fixedPerformerStudio[scrape['studio']['name']]:
        if not performer in scrape['performers']:
            scrape['performers'].append({'Name':performer})

scrape['tags'] = [{"name": scene_api_json['tags']['collection'][x].get('alias')} for x in scene_api_json['tags']['collection']]
if scrape['studio']['name'] in defaultStudioTags:
    for tag in defaultStudioTags[scrape['studio']['name']]:
        scrape['tags'].append({"name": tag})

if scrape['studio']['name'] in studioMap:
    scrape['studio']['name'] = studioMap[scrape['studio']['name']]

scrape['image'] = scene_api_json['_resources']['primary'][0]['url']
for key_name, key_value in scrape.items():
    log.debug(f'[{key_name}]:{key_value}')

print(json.dumps(scrape))
