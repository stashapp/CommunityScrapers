"""JAVLibrary python scraper"""
import base64
import json
import re
import sys
import threading
import time
from urllib.parse import urlparse

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import lxml.html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)",
     file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml",
     file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
     file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
     file=sys.stderr)
    sys.exit()


# GLOBAL VAR ######
JAV_DOMAIN = "Check"
###################

JAV_SEARCH_HTML = None
JAV_MAIN_HTML = None
PROTECTION_CLOUDFLARE = False

# Flaresolverr
FLARESOLVERR_ENABLED = False
FLARESOLVERR_URL = "http://localhost:8191/v1"
FLARESOLVERR_TIMEOUT_MAX = 60000

JAV_HEADERS = {
    "User-Agent":
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    "Referer": "http://www.javlibrary.com/"
}
# We can't add movie image atm in the same time as Scene
STASH_SUPPORTED = False
# Stash doesn't support Labels yet
STASH_SUPPORT_LABELS = False
# ...and name order too...
STASH_SUPPORT_NAME_ORDER = False
# Tags you don't want to scrape
IGNORE_TAGS = [
    "Features Actress", "Hi-Def", "Beautiful Girl", "Blu-ray",
    "Featured Actress", "VR Exclusive", "MOODYZ SALE 4"
]
# Select preferable name order
NAME_ORDER_JAPANESE = False
# Some performers don't need to be reversed
IGNORE_PERF_REVERSE = ["Lily Heart"]

# Keep the legacy field scheme:
# Actual Code -> Title, actual Title -> Details, actual Details -> /dev/null
LEGACY_FIELDS = True
# Studio Code now in a separate field, so it may (or may not) be stripped from title
# Makes sense only if not LEGACY_FIELDS
KEEP_CODE_IN_TITLE = True

# Tags you want to be added in every scrape
FIXED_TAGS = ""
# Split tags if they contain [,·] ('Best, Omnibus' -> 'Best','Omnibus')
SPLIT_TAGS = False

# Don't fetch the Aliases (Japanese Name)
IGNORE_ALIASES = False
# Always wait for the aliases to load. (Depends on network response)
WAIT_FOR_ALIASES = False
# All javlib sites
SITE_JAVLIB = ["javlibrary", "o58c", "e59f"]

BANNED_WORDS = {
    "A******ation": "Asphyxiation",
    "A*****t": "Assault",
    "A*****ts": "Assaults",
    "A*****ted": "Assaulted",
    "A*****ting": "Assaulting",
    "A****p": "Asleep",
    "A***e": "Abuse",
    "A***ed": "Abused",
    "A***es": "Abuses",
    "B*****k": "Berserk",
    "B*****p": "Bang Up",
    "B***d": "Blood",
    "B***dcurdling": "Bloodcurdling",
    "B***dline": "Bloodline",
    "B***dy": "Bloody",
    "B*******y": "Brutality",
    "B******y": "Brutally",
    "C*****y": "Cruelty",
    "C***d": "Child",
    "C***dcare": "Childcare",
    "C***dhood": "Childhood",
    "C***dish": "Childish",
    "C***dren": "Children",
    "C*ck": "Cock",
    "C*cks": "Cocks",
    "C*llegiate": "Collegiate",
    "Chai*saw": "Chainsaw",
    "CrumB**d": "Crumbled",
    "D*ck": "Dick",
    "D******e": "Disgrace",
    "D******ed": "Disgraced",
    "D******eful": "Disgraceful",
    "D***k": "Drunk",
    "D***ken": "Drunken",
    "D***kest": "Drunkest",
    "D***king": "Drinking",
    "D***ks": "Drinks",
    "D**g": "Drug",
    "D**gged": "Drugged",
    "D**gs": "Drugs",
    "EnS***ed": "Enslaved",
    "F*****g": "Fucking",
    "F***e": "Force",
    "F***ed": "Fucked",
    "F***eful": "Forceful",
    "F***efully": "Forcefully",
    "F***es": "Forces",
    "G*********d": "Gang-Banged",
    "G*******g": "Gangbang",
    "G*******ged": "Gangbanged",
    "G*******ging": "Gangbanging",
    "G******ging": "Gangbanging",
    "G*******gs": "Gangbangs",
    "G******g": "Gangbang",
    "G******ged": "Gangbanged",
    "G****gers": "Gangbangers",
    "H*********n": "Humiliation",
    "H*******ed": "Hypnotized",
    "H*******m": "Hypnotism",
    "H**t": "Hurt",
    "H**ts": "Hurts",
    "Half-A****p": "Half-Asleep",
    "Hot-B***ded": "Hot-Blooded",
    "HumB**d": "Humbled",
    "H*******es": "Humiliates",
    "H******s": "Hypnosis",
    "I********ed": "Impregnated",
    "I****t": "Incest",
    "I****tual": "Incestual",
    "I****ted": "Insulted",
    "I****ting": "Insulting",
    "I****ts": "Insults",
    "I****tuous": "Incestuous",
    "J*": "Jo",
    "J*s": "Jos",
    "K****p": "Kidnap",
    "K****pped": "Kidnapped",
    "K****pper": "Kidnapper",
    "K****pping": "Kidnapping",
    "K**l": "Kill",
    "K**led": "Killed",
    "K**ler": "Killer",
    "K**ling": "Killing",
    "K*d": "Kid",
    "K*dding": "Kidding",
    "K*ds": "Kids",
    "Lo**ta": "Lolita",
    "Lol*pop": "Lolipop",
    "M****t": "Molest",
    "M****ts": "Molests",
    "M****tation": "Molestation",
    "M****ted": "Molested",
    "M****ter": "Molester",
    "M****ters": "Molesters",
    "M****ting": "Molesting",
    "M****tor": "Molestor",
    "Ma*ko": "Maiko",
    "P****h": "Punish",
    "P****hed": "Punished",
    "P****hing": "Punishing",
    "P****hment": "Punishment",
    "P********t": "Punishment",
    "P**hed": "Punished",
    "P*ssy": "Pussy",
    "R****g": "Raping",
    "R**e": "Rape",
    "R**ey": "Rapey",
    "R**ed": "Raped",
    "R**es": "Rapes",
    "S*********l": "School Girl",
    "S*********ls": "School Girls",
    "S*********s": "Schoolgirls",
    "S********l": "Schoolgirl",
    "S********ls": "Schoolgirls",
    "S********n": "Submission",
    "S**t": "Shit",
    "S******g": "Sleeping",
    "S*****t": "Student",
    "S*****ts": "Students",
    "S***e": "Slave",
    "S***ery": "Slavery",
    "S***es": "Slaves",
    "Sch**lgirl": "Schoolgirl",
    "Sch**lgirls": "Schoolgirls",
    "SK**led": "Skilled",
    "SK**lful": "Skillful",
    "SK**lfully": "Skillfully",
    "SK**ls": "Skills",
    "StepB****************r": "StepBrother And Sister",
    "StepK*ds ": "StepKids",
    "StepM************n": "Stepmother And Son",
    "T******e": "Tentacle",
    "T******es": "Tentacles",
    "T*****e": "Torture",
    "T*****ed": "Tortured",
    "T*****es": "Tortures",
    "U*********s": "Unconscious",
    "U*********sly": "Unconsciously",
    "U*******g": "Unwilling",
    "U*******gly": "Unwillingly",
    "V******e": "Violence",
    "V*****e": "Violate",
    "V*olated": "Violated",
    "V*****ed": "Violated",
    "V*****es": "Violates",
    "V*****t": "Violent",
    "V*****tly": "Violently",
    "Y********l": "Young Girl",
    "Y********ls": "Young Girls"
}

REPLACE_TITLE = {
    "-uncensored": "",
    "-Uncensored": "",
    "uncensored": "",
    "Uncensored": "",
    "-uncensore": "",
    "-Uncensore": "",
    "_uncen": "",
    "_Uncen": "",
    "hd.": ".",
    "HD.": ".",
    "a.hd": "",
    "b.hd": "",
    "c.hd": "",
    "d.hd": "",
    "A.HD": "",
    "B.HD": "",
    "C.HD": "",
    "D.HD": "",
    "a.H": "",
    "b.H": "",
    "c.H": "",
    "d.H": "",
    "A.H": "",
    "B.H": "",
    "C.H": "",
    "D.H": "",
    ".hd": "",
    ".HD": "",
    "-hd": "",
    "-HD": "",
    "_hd": "",
    "_HD": "",
    "-4k": "",
    "-4K": "",
    ".4k": "",
    ".4K": "",
    "a.avi": ".avi",
    "b.avi": ".avi",
    "c.avi": ".avi",
    "d.avi": ".avi",
    "a.mp4": ".mp4",
    "b.mp4": ".mp4",
    "c.mp4": ".mp4",
    "d.mp4": ".mp4",
    "a.wmv": ".wmv",
    "b.wmv": ".wmv",
    "c.wmv": ".wmv",
    "d.wmv": ".wmv",  
    "A.avi": ".avi",
    "B.mp4": ".avi",
    "C.mp4": ".avi",
    "D.avi": ".avi",
    "A.mp4": ".mp4",
    "B.mp4": ".mp4",
    "C.mp4": ".mp4",
    "D.mp4": ".mp4",
    "A.wmv": ".wmv",
    "B.wmv": ".wmv",
    "C.wmv": ".wmv",
    "D.wmv": ".wmv",
    "A.AVI": ".AVI",
    "B.AVI": ".AVI",
    "C.AVI": ".AVI",
    "D.AVI": ".AVI",
    "A.MP4": ".MP4",
    "B.MP4": ".MP4",
    "C.MP4": ".MP4",
    "D.MP4": ".MP4",
    "A.WMV": ".WMV",
    "B.WMV": ".WMV",
    "C.WMV": ".WMV",
    "D.WMV": ".WMV",  
    "A.AVI": ".AVI",
    "B.MP4": ".AVI",
    "C.MP4": ".AVI",
    "D.AVI": ".AVI",
    "A.MP4": ".MP4",
    "B.MP4": ".MP4",
    "C.MP4": ".MP4",
    "D.MP4": ".MP4",
    "A.WMV": ".WMV",
    "B.WMV": ".WMV",
    "C.WMV": ".WMV",
    "D.WMV": ".WMV",
    ".3g2": "",
    ".3gp": "",
    ".amv": "",
    ".asf": "",
    ".avi": "",
    ".f4a": "",
    ".f4b": "",
    ".f4p": "",
    ".f4v": "",
    ".flv": "",
    ".flv": "",
    ".gifv": "",
    ".m4p": "",
    ".m4v": "",
    ".m4v": "",
    ".mkv": "",
    ".mng": "",
    ".mod": "",
    ".mov": "",
    ".mp2": "",
    ".mp4": "",
    ".mpe": "",
    ".mpeg": "",
    ".mpg": "",
    ".mpv": "",
    ".mxf": "",
    ".nsv": "",
    ".ogg": "",
    ".ogv": "",
    ".qt": "",
    ".rm": "",
    ".roq": "",
    ".rrc": "",
    ".svi": "",
    ".ts": "",
    ".vob": "",
    ".webm": "",
    ".wmv": "",
    ".yuv": "", 
    ".3G2": "",
    ".3GP": "",
    ".AMV": "",
    ".ASF": "",
    ".AVI": "",
    ".F4A": "",
    ".F4B": "",
    ".F4P": "",
    ".F4V": "",
    ".FLV": "",
    ".FLV": "",
    ".GIFV": "",
    ".M4P": "",
    ".M4V": "",
    ".M4V": "",
    ".MKV": "",
    ".MNG": "",
    ".MOD": "",
    ".MOV": "",
    ".MP2": "",
    ".MP4": "",
    ".MPE": "",
    ".MPEG": "",
    ".MPG": "",
    ".MPV": "",
    ".MXF": "",
    ".NSV": "",
    ".OGG": "",
    ".OGV": "",
    ".QT": "",
    ".RM": "",
    ".ROQ": "",
    ".RRC": "",
    ".SVI": "",
    ".TS": "",
    ".VOB": "",
    ".WEBM": "",
    ".WMV": "",
    ".YUV": ""
}

OBFUSCATED_TAGS = {
    "Girl": "Young Girl", # ロリ系 in Japanese
    "Tits": "Small Tits" # 微乳 in Japanese
}


class ResponseHTML:
    content = ""
    html = ""
    status_code = 0
    url = 0

def bypass_protection(url):
    global PROTECTION_CLOUDFLARE

    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    log.debug("=== Checking Status of Javlib site ===")
    PROTECTION_CLOUDFLARE = False
    response_html = ResponseHTML
    for site in SITE_JAVLIB:
        url_n = url.replace(url_domain, site)
        try:
            if FLARESOLVERR_ENABLED:             
                url = FLARESOLVERR_URL
                headers = {"Content-Type": "application/json"}
                data = {
                    "cmd": "request.get",
                    "url": url_n,
                    "maxTimeout": FLARESOLVERR_TIMEOUT_MAX
                }

                log.info(f"Using Flarsolverr: {FLARESOLVERR_URL}")
                log.info(f"Javlibrary input url: {url}")
                responseJson = requests.post(url, headers=headers, json=data)
                json_input = json.loads(str(responseJson.text))

                response_html.content = json_input['solution']['response']
                response_html.html = json_input['solution']['response']
                response_html.status_code = json_input['solution']['status']
                response_html.url = json_input['solution']['url']

                #log.info(f"Flaresolverr response html: {response_html}")
            else:
                response = requests.get(url_n, headers=JAV_HEADERS, timeout=10)
                response_html.html = response.text
                response_html.status_code = response.status_code
        except Exception as exc_req:
            log.warning(f"Exception error {exc_req} while checking protection for {site}")
            return None, None
        if response_html.url == "https://www.javlib.com/maintenance.html":
            log.error(f"[{site}] Maintenance")
        if "Why do I have to complete a CAPTCHA?" in response_html.html \
            or "Checking your browser before accessing" in response_html.html:
            log.error(f"[{site}] Protected by Cloudflare")
            PROTECTION_CLOUDFLARE = True
        elif response_html.status_code != 200:   
            log.error(f"[{site}] Other issue ({response_html.status_code})")
        else:
            log.info(
                    f"[{site}] Using this site for scraping ({response_html.status_code})"
                )
            log.debug("======================================")
            return site, response_html
    log.debug("======================================")
    return None, None


def send_request(url, head, retries=0, delay=1):
    if retries > 3:
        log.warning(f"Scrape for {url} failed after retrying {retries} times")
        return None

    global JAV_DOMAIN

    if delay != 0:
        log.info(f"Delaying request by {delay} seconds to prevent Cloudflare rate limiting")
        time.sleep(delay)
    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    response = None
    if url_domain in SITE_JAVLIB:
        # Javlib
        if JAV_DOMAIN == "Check":
            JAV_DOMAIN, response = bypass_protection(url)
            if response:
                return response
        if JAV_DOMAIN is None:
            return None
        url = url.replace(url_domain, JAV_DOMAIN)
    log.debug(f"[{threading.get_ident()}] Request URL: {url}")
    try:
        response = requests.get(url, headers=head, timeout=10)
    except requests.exceptions.Timeout as exc_timeout:
        log.warning(f"Timed out {exc_timeout}")
        return send_request(url, head, retries+1)
    except Exception as exc_req:
        log.error(f"scrape error exception {exc_req}")
        if delay != 0:
            error_delay = delay+2.75
            log.info(f"Delaying request by {error_delay} seconds and retrying")
            time.sleep(error_delay)
        return send_request(url, head, retries+1)
    if response.status_code != 200:
        log.debug(f"[Request] Error, Status Code: {response.status_code}")
        response = None
    return response


def replace_banned_words(matchobj):
    word = matchobj.group(0)
    if word in BANNED_WORDS:
        return BANNED_WORDS[word]
    return word

def cleanup_title(title):
    if title == None:
        return title

    log.info(f"Starting title cleanup for: {title}")
    cleaned_title = False
    for key, value in REPLACE_TITLE.items():
        if key in title:
            title = title.replace(key, value)
            cleaned_title = True
    
    if cleaned_title:
        title = title.strip()
        log.info(f"Found match and using new clean title: {title}")
    return title

def regexreplace(input_replace):
    word_pattern = re.compile(r'(\w|\*)+')
    output = word_pattern.sub(replace_banned_words, input_replace)
    return re.sub(r"[\[\]\"]", "", output)


def getxpath(xpath, tree):
    if not xpath:
        return None
    xpath_result = []
    # It handles the union strangely so it is better to split and get one by one
    if "|" in xpath:
        for xpath_tmp in xpath.split("|"):
            xpath_result.append(tree.xpath(xpath_tmp))
        xpath_result = [val for sublist in xpath_result for val in sublist]
    else:
        xpath_result = tree.xpath(xpath)
    #log.debug(f"xPATH: {xpath}")
    #log.debug(f"raw xPATH result: {xpath_result}")
    list_tmp = []
    for x_res in xpath_result:
        # for xpaths that don't end with /text()
        if isinstance(x_res,lxml.html.HtmlElement):
            list_tmp.append(x_res.text_content().strip())
        else:
            list_tmp.append(x_res.strip())
    if list_tmp:
        xpath_result = list_tmp
    xpath_result = list(filter(None, xpath_result))
    return xpath_result


# SEARCH PAGE


def jav_search(html, xpath):
    if "/en/?v=" in html.url:
        log.debug(f"Using the provided movie page ({html.url})")
        return html
    jav_search_tree = lxml.html.fromstring(html.content)
    jav_url = getxpath(xpath['url'], jav_search_tree)  # ./?v=javme5it6a
    if jav_url:
        url_domain = urlparse(html.url).netloc
        jav_url = re.sub(r"^\.", f"https://{url_domain}/en", jav_url[0])
        log.debug(f"Using API URL: {jav_url}")
        main_html = send_request(jav_url, JAV_HEADERS)
        return main_html
    log.debug("[JAV] There is no result in search")
    return None


def jav_search_by_name(html, xpath):
    jav_search_tree = lxml.html.fromstring(html.content)
    jav_url = getxpath(xpath['url'], jav_search_tree)  # ./?v=javme5it6a
    jav_title = getxpath(xpath['title'], jav_search_tree)
    jav_image = getxpath(
        xpath['image'], jav_search_tree
    )  # //pics.dmm.co.jp/mono/movie/adult/13gvh029/13gvh029ps.jpg
    log.debug(f"There is/are {len(jav_url)} scene(s)")
    lst = []
    for count, _ in enumerate(jav_url):
        lst.append({
            "title": jav_title[count],
            "url":
            f"https://www.javlibrary.com/en/{jav_url[count].replace('./', '')}",
            "image": re.sub("^//","https://",jav_image[count])
        })
    return lst


def buildlist_tagperf(data, type_scrape=""):
    list_tmp = []
    dict_jav = None
    if type_scrape == "perf_jav":
        dict_jav = data
        data = data["performers"]
    for idx, data_value in enumerate(data):
        p_name = data_value
        if p_name == "":
            continue
        if type_scrape == "perf_jav":
            if p_name not in IGNORE_PERF_REVERSE and not NAME_ORDER_JAPANESE:
                # Invert name (Aoi Tsukasa -> Tsukasa Aoi)
                p_name = re.sub(r"([a-zA-Z]+)(\s)([a-zA-Z]+)", r"\3 \1", p_name)
            if STASH_SUPPORT_NAME_ORDER:
                # There is such names as "Aoi." and even "@you". Indeed, JAV is fun!
                parsed_name = re.search("([a-zA-Z\.@]+)(\s)?([a-zA-Z]+)?", p_name)
                p_name = {}
                if parsed_name[2] == ' ' and parsed_name[3]:
                    p_name[
                        "surname"] = parsed_name[1]
                    p_name[
                        "first_name"] = parsed_name[3]
                else:
                    p_name[
                        "nickname"] = parsed_name[0]
        if type_scrape == "tags" and p_name in IGNORE_TAGS:
            continue
        if type_scrape == "tags" and p_name in OBFUSCATED_TAGS:
            p_name = OBFUSCATED_TAGS[p_name]
        if type_scrape == "perf_jav" and dict_jav.get("performer_aliases"):
            try:
                list_tmp.append({
                    "name": p_name,
                    "aliases": dict_jav["performer_aliases"][idx],
                    "gender": "FEMALE"
                })
            except:
                list_tmp.append({"name": p_name, "gender": "FEMALE"})
        else:
            list_tmp.append({"name": p_name})
    # Adding personal fixed tags
    if FIXED_TAGS and type_scrape == "tags":
        list_tmp.append({"name": FIXED_TAGS})
    return list_tmp


def th_request_perfpage(page_url, perf_url):
    # vl_star.php?s=afhvw
    #log.debug("[DEBUG] Aliases Thread: {}".format(threading.get_ident()))
    javlibrary_ja_html = send_request(page_url.replace("/en/", "/ja/"),
                                      JAV_HEADERS)
    if javlibrary_ja_html:
        javlibrary_perf_ja = lxml.html.fromstring(javlibrary_ja_html.content)
        list_tmp = []
        try:
            for p_v in perf_url:
                list_tmp.append(
                    javlibrary_perf_ja.xpath('//a[@href="' + p_v +
                                             '"]/text()')[0])
            if list_tmp:
                jav_result['performer_aliases'] = list_tmp
                log.debug(f"Got the aliases: {list_tmp}")
        except:
            log.debug("Error with the aliases")
    else:
        log.debug("Can't get the Jap HTML")


def th_imageto_base64(imageurl, typevar):
    #log.debug("[DEBUG] {} thread: {}".format(typevar,threading.get_ident()))
    head = JAV_HEADERS
    if isinstance(imageurl,list):
        for image_index, image_url in enumerate(imageurl):
            try:
                img = requests.get(image_url.replace(
                    "ps.jpg", "pl.jpg"),
                                   timeout=10,
                                   headers=head)
                if img.status_code != 200:
                    log.debug(
                        "[Image] Got a bad request (status: "\
                        f"{img.status_code}) for <{image_url}>"
                    )
                    imageurl[image_index] = None
                    continue
                base64image = base64.b64encode(img.content)
                imageurl[
                    image_index] = "data:image/jpeg;base64," + base64image.decode(
                        'utf-8')
            except:
                log.debug(
                    f"[{typevar}] Failed to get the base64 of the image"
                )
    else:
        try:
            img = requests.get(imageurl.replace("ps.jpg", "pl.jpg"),
                               timeout=10,
                               headers=head)
            if img.status_code != 200:
                log.debug(
                    f"[Image] Got a bad request (status: {img.status_code}) for <{imageurl}>"
                )
                return
            base64image = base64.b64encode(img.content)
            if typevar == "JAV":
                jav_result[
                    "image"] = "data:image/jpeg;base64," + base64image.decode(
                        'utf-8')
            log.debug(f"[{typevar}] Converted the image to base64!")
        except:
            log.debug(f"[{typevar}] Failed to get the base64 of the image")
    return


#log.debug(f"[DEBUG] Main Thread: {threading.get_ident()}")
FRAGMENT = json.loads(sys.stdin.read())

SEARCH_TITLE = FRAGMENT.get("name")
SEARCH_TITLE = cleanup_title(SEARCH_TITLE)
SCENE_URL = FRAGMENT.get("url")

if FRAGMENT.get("title"):
    SCENE_TITLE = FRAGMENT["title"]
    SCENE_TITLE = cleanup_title(SCENE_TITLE)
else:
    SCENE_TITLE = None

if "validSearch" in sys.argv and SCENE_URL is None:
    sys.exit()

if "searchName" in sys.argv:
    log.debug(f"Using search with Title: {SEARCH_TITLE}")
    JAV_SEARCH_HTML = send_request(
        f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={SEARCH_TITLE}",
        JAV_HEADERS)
else:
    if SCENE_URL:
        scene_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
        # Url from Javlib
        if scene_domain in SITE_JAVLIB:
            log.debug(f"Using URL: {SCENE_URL}")
            JAV_MAIN_HTML = send_request(SCENE_URL, JAV_HEADERS)
        else:
            log.warning(f"The URL is not from JavLibrary ({SCENE_URL})")
    if JAV_MAIN_HTML is None and SCENE_TITLE:
        log.debug(f"Using search with Title: {SCENE_TITLE}")
        JAV_SEARCH_HTML = send_request(
            f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={SCENE_TITLE}",
            JAV_HEADERS)

# XPATH
jav_xPath_search = {}
jav_xPath_search[
    'url'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@href'
jav_xPath_search[
    'title'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@title'
jav_xPath_search[
    'image'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]//img/@src'

jav_xPath = {}
jav_xPath[
    "code"] = '//td[@class="header" and text()="ID:"]/following-sibling::td/text()'
# or '//div[@id="video_id"]//td[2][@class="text"]/text()'
jav_xPath[
    "title"] = jav_xPath["code"] if LEGACY_FIELDS else '//div[@id="video_title"]/h3/a/text()'
#There are no actual Details in JavLibrary
#For legacy reasons we add the Title in Details by default
jav_xPath[
    "details"] = None if not LEGACY_FIELDS else '//div[@id="video_title"]/h3/a/text()'
jav_xPath["url"] = '//meta[@property="og:url"]/@content'
jav_xPath[
    "date"] = '//td[@class="header" and text()="Release Date:"]/following-sibling::td/text()'
jav_xPath[
    "director"] = '//div[@id="video_director"]//td[@class="text"]/span[@class="director"]/a/text()'
jav_xPath[
    "tags"] = '//td[@class="header" and text()="Genre(s):"]'\
            '/following::td/span[@class="genre"]/a/text()'
jav_xPath[
    "performers"] = '//td[@class="header" and text()="Cast:"]'\
                '/following::td/span[@class="cast"]/span/a/text()'
jav_xPath[
    "performers_url"] = '//td[@class="header" and text()="Cast:"]'\
                        '/following::td/span[@class="cast"]/span/a/@href'
jav_xPath[
    "studio"] = '//td[@class="header" and text()="Maker:"]'\
                '/following-sibling::td/span[@class="maker"]/a/text()'
#jav_xPath[
#    "label"] = '//td[@class="header" and text()="Label:"]'\
#                '/following-sibling::td/span[@class="label"]/a/text()'
jav_xPath["image"] = '//div[@id="video_jacket"]/img/@src'

jav_result = {}

if "searchName" in sys.argv:
    if JAV_SEARCH_HTML:
        if "/en/?v=" in JAV_SEARCH_HTML.url:
            log.debug(f"Scraping the movie page directly ({JAV_SEARCH_HTML.url})")
            jav_tree = lxml.html.fromstring(JAV_SEARCH_HTML.content)
            jav_result["title"] = getxpath(jav_xPath["title"], jav_tree)
            jav_result["details"] = getxpath(jav_xPath["details"], jav_tree)
            jav_result["url"] = getxpath(jav_xPath["url"], jav_tree)
            jav_result["image"] = getxpath(jav_xPath["image"], jav_tree)
            for key, value in jav_result.items():
                if isinstance(value,list):
                    jav_result[key] = value[0]
                if key in ["image", "url"]:
                    jav_result[key] = f"https:{jav_result[key]}".replace("https:https:", "https:")
            jav_result = [jav_result]
        else:
            jav_result = jav_search_by_name(JAV_SEARCH_HTML, jav_xPath_search)
        if jav_result:
            print(json.dumps(jav_result))
        else:
            print(json.dumps([{"title": "The search doesn't return any result."}]))
    else:
        if PROTECTION_CLOUDFLARE:
            print(
                json.dumps([{
                    "title": "Protected by Cloudflare, try later."
                }]))
        else:
            print(
                json.dumps([{
                    "title":
                    "The request has failed to get the page. Check log."
                }]))
    sys.exit()

if JAV_SEARCH_HTML:
    JAV_MAIN_HTML = jav_search(JAV_SEARCH_HTML, jav_xPath_search)

if JAV_MAIN_HTML:
    #log.debug("[DEBUG] Javlibrary Page ({})".format(JAV_MAIN_HTML.url))
    jav_tree = lxml.html.fromstring(JAV_MAIN_HTML.content)
    # is not None for removing the FutureWarning...
    if jav_tree is not None:
        # Get data from javlibrary
        for key, value in jav_xPath.items():
            jav_result[key] = getxpath(value, jav_tree)
        # PostProcess
        if jav_result.get("image"):
            tmp = re.sub(r"(http:|https:)", "", jav_result["image"][0])
            jav_result["image"] = "https:" + tmp
            if "now_printing.jpg" in jav_result[
                    "image"] or "noimage" in jav_result["image"]:
                # https://pics.dmm.com/mono/movie/n/now_printing/now_printing.jpg
                # https://pics.dmm.co.jp/mono/noimage/movie/adult_ps.jpg
                log.debug(
                    "[Warning][Javlibrary] Image was deleted or failed to load "\
                    f"({jav_result['image']})"
                )
                jav_result["image"] = None
            else:
                imageBase64_jav_thread = threading.Thread(
                    target=th_imageto_base64,
                    args=(
                        jav_result["image"],
                        "JAV",
                    ))
                imageBase64_jav_thread.start()
        if jav_result.get("url"):
            jav_result["url"] = "https:" + jav_result["url"][0]
        if jav_result.get("details") and LEGACY_FIELDS:
            jav_result["details"] = re.sub(r"^(.*? ){1}", "",
                                           jav_result["details"][0])
        if jav_result.get("title"):
            if LEGACY_FIELDS or KEEP_CODE_IN_TITLE:
                jav_result["title"] = jav_result["title"][0]
            elif not KEEP_CODE_IN_TITLE:
                jav_result["title"] = (re.sub(jav_result['code'][0], "",
                                            jav_result["title"][0])).lstrip()
        if jav_result.get("director"):
            jav_result["director"] = jav_result["director"][0]
        if jav_result.get("label"):
            jav_result["label"] = jav_result["label"][0]
        if jav_result.get("performers_url") and IGNORE_ALIASES is False:
            javlibrary_aliases_thread = threading.Thread(
                target=th_request_perfpage,
                args=(
                    JAV_MAIN_HTML.url,
                    jav_result["performers_url"],
                ))
            javlibrary_aliases_thread.daemon = True
            javlibrary_aliases_thread.start()

if JAV_MAIN_HTML is None:
    log.info("No results found")
    print(json.dumps({}))
    sys.exit()

log.debug('[JAV] {}'.format(jav_result))

# Time to scrape all data
scrape = {}

# DVD code
scrape['code'] = next(iter(jav_result.get('code', [])))
scrape['title'] = jav_result.get('title')
scrape['date'] = next(iter(jav_result.get('date', [])))
scrape['director'] = jav_result.get('director') or None
scrape['url'] = jav_result.get('url')
scrape['details'] = regexreplace(jav_result.get('details', ""))
scrape['studio'] = {
    'name': next(iter(jav_result.get('studio', []))),
}
scrape['label'] = {
    'name': jav_result.get('label'),
}

if WAIT_FOR_ALIASES and not IGNORE_ALIASES:
    try:
        if javlibrary_aliases_thread.is_alive():
            javlibrary_aliases_thread.join()
    except NameError:
        log.debug("No Jav Aliases Thread")
scrape['performers'] = buildlist_tagperf(jav_result, "perf_jav")

scrape['tags'] = buildlist_tagperf(jav_result.get('tags', []), "tags")
scrape['tags'] = [
    {
        "name": tag_name.strip()
    } for tag_dict in scrape['tags']
    for tag_name in tag_dict["name"].replace('·', ',').split(",")
]

try:
    if imageBase64_jav_thread.is_alive() is True:
        imageBase64_jav_thread.join()
    if jav_result.get('image'):
        scrape['image'] = jav_result['image']
except NameError:
    log.debug("No image JAV Thread")

print(json.dumps(scrape))
