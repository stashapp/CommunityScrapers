"""JAVLibrary/R18 python scraper"""
import base64
import json
import re
import sys
import threading
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
R18_SEARCH_HTML = None
JAV_MAIN_HTML = None
R18_MAIN_HTML = None
PROTECTION_CLOUDFLARE = False

R18_HEADERS = {
    "User-Agent":
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Referer": "https://www.r18.com/"
}
JAV_HEADERS = {
    "User-Agent":
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Referer": "http://www.javlibrary.com/"
}
# Print extra debug messages
DEBUG_MODE = False
# We can't add movie image atm in the same time as Scene
STASH_SUPPORTED = False
# Tags you don't want to scrape
IGNORE_TAGS = [
    "Features Actress", "Hi-Def", "Beautiful Girl", "Blu-ray",
    "Featured Actress", "VR Exclusive", "MOODYZ SALE 4", "Girl", "Tits"
]
# Some performers don't need to be reversed
IGNORE_PERF_REVERSE = ["Lily Heart"]

# Tags you want to be added in every scrape
FIXED_TAGS = ""
# Get both Javlibrary and R18 tags
BOTH_TAGS = False
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


def debug(to_print):
    """debug only prints using log.debug if DEBUG_MODE is set to True"""
    if DEBUG_MODE is False:
        return
    log.debug(to_print)


def checking_protection(url):
    global PROTECTION_CLOUDFLARE

    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    debug("=== Checking Status of Javlib site ===")
    PROTECTION_CLOUDFLARE = False
    for site in SITE_JAVLIB:
        url_n = url.replace(url_domain, site)
        try:
            response = requests.get(url_n, headers=JAV_HEADERS, timeout=10)
        except Exception as exc_req:
            log.warning(f"Exception error {exc_req} while checking protection for {site}")
            return None, None
        if response.url == "https://www.javlib.com/maintenance.html":
            log.error(f"[{site}] Maintenance")
        if "Why do I have to complete a CAPTCHA?" in response.text \
            or "Checking your browser before accessing" in response.text:
            log.error(f"[{site}] Protected by Cloudflare")
            PROTECTION_CLOUDFLARE = True
        elif response.status_code != 200:
            log.error(f"[{site}] Other issue ({response.status_code})")
        else:
            log.info(
                    f"[{site}] Using this site for scraping ({response.status_code})"
                )
            debug("======================================")
            return site, response
    debug("======================================")
    return None, None


def send_request(url, head, retries=0):
    if retries > 10:
        log.warning(f"Scrape for {url} failed after retrying")
        return None

    global JAV_DOMAIN

    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    response = None
    if url_domain in SITE_JAVLIB:
        # Javlib
        if JAV_DOMAIN == "Check":
            JAV_DOMAIN, response = checking_protection(url)
            if response:
                return response
        if JAV_DOMAIN is None:
            return None
        url = url.replace(url_domain, JAV_DOMAIN)
    debug(f"[{threading.get_ident()}] Request URL: {url}")
    try:
        response = requests.get(url, headers=head, timeout=10)
    except requests.exceptions.Timeout as exc_timeout:
        log.warning(f"Timed out {exc_timeout}")
        return send_request(url, head, retries+1)
    except Exception as exc_req:
        log.error(f"scrape error exception {exc_req}")
    if response.status_code != 200:
        debug(f"[Request] Error, Status Code: {response.status_code}")
        response = None
    return response


def replace_banned_words(matchobj):
    word = matchobj.group(0)
    if word in BANNED_WORDS:
        return BANNED_WORDS[word]
    return word


def regexreplace(input_replace):
    word_pattern = re.compile(r'(\w|\*)+')
    output = word_pattern.sub(replace_banned_words, input_replace)
    return re.sub(r"[\[\]\"]", "", output)


def getxpath(xpath, tree):
    xpath_result = []
    # It handles the union strangely so it is better to split and get one by one
    if "|" in xpath:
        for xpath_tmp in xpath.split("|"):
            xpath_result.append(tree.xpath(xpath_tmp))
        xpath_result = [val for sublist in xpath_result for val in sublist]
    else:
        xpath_result = tree.xpath(xpath)
    #debug(f"xPATH: {xpath}")
    #debug(f"raw xPATH result: {xpath_result}")
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


def r18_search(html, xpath):
    if html is None:
        return None
    search_tree = lxml.html.fromstring(html.content)
    search_url = getxpath(xpath['url'], search_tree)
    search_serie = getxpath(xpath['series'], search_tree)
    search_scene = getxpath(xpath['scene'], search_tree)
    # There is only 1 scene, with serie.
    # Could be useful if the movie already exists in Stash because you only need the name.
    if len(search_scene) == 1 and len(search_serie) == 1 and len(
            search_url) == 1:
        r18_result["series_name"] = search_serie
    if search_url:
        search_url = search_url[0]
        search_id = re.match(r".+id=(.+)/.*", search_url)
        if search_id:
            scene_url = f"https://www.r18.com/api/v4f/contents/{search_id.group(1)}?lang=en"
            log.debug(f"Using API URL: {scene_url}")
            main_html = send_request(scene_url, R18_HEADERS)
            return main_html
        log.warning(f"Can't find the 'id=' in the URL: {search_url}")
        return None
    debug("[R18] There is no result in search")
    return None


def jav_search(html, xpath):
    if "/en/?v=" in html.url:
        debug(f"Using the provided movie page ({html.url})")
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
            "image": f"https:{jav_image[count]}"
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
            if p_name not in IGNORE_PERF_REVERSE:
                # Invert name (Aoi Tsukasa -> Tsukasa Aoi)
                p_name = re.sub(r"([a-zA-Z]+)(\s)([a-zA-Z]+)", r"\3 \1", p_name)
        if type_scrape == "tags" and p_name in IGNORE_TAGS:
            continue
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
    #debug("[DEBUG] Aliases Thread: {}".format(threading.get_ident()))
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
                debug(f"Got the aliases: {list_tmp}")
        except:
            debug("Error with the aliases")
    else:
        debug("Can't get the Jap HTML")


def th_imageto_base64(imageurl, typevar):
    #debug("[DEBUG] {} thread: {}".format(typevar,threading.get_ident()))
    head = JAV_HEADERS
    if typevar in ("R18Series", "R18"):
        head = R18_HEADERS
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
                debug(
                    f"[{typevar}] Failed to get the base64 of the image"
                )
        if typevar == "R18Series":
            r18_result["series_image"] = imageurl
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
            if typevar == "R18":
                r18_result[
                    "image"] = "data:image/jpeg;base64," + base64image.decode(
                        'utf-8')
            debug(f"[{typevar}] Converted the image to base64!")
        except:
            debug(f"[{typevar}] Failed to get the base64 of the image")
    return


#debug(f"[DEBUG] Main Thread: {threading.get_ident()}")
FRAGMENT = json.loads(sys.stdin.read())

SEARCH_TITLE = FRAGMENT.get("name")
SCENE_URL = FRAGMENT.get("url")

if FRAGMENT.get("title"):
    SCENE_TITLE = FRAGMENT["title"]
    # Remove extension
    SCENE_TITLE = re.sub(r"\..{3}$", "", SCENE_TITLE)
    SCENE_TITLE = re.sub(r"-JG\d", "", SCENE_TITLE)
    SCENE_TITLE = re.sub(r"\s.+$", "", SCENE_TITLE)
    SCENE_TITLE = re.sub(r"[ABCDEFGH]$", "", SCENE_TITLE)
else:
    SCENE_TITLE = None

if "validSearch" in sys.argv and SCENE_URL is None:
    sys.exit()

if "searchName" in sys.argv:
    debug(f"Using search with Title: {SEARCH_TITLE}")
    JAV_SEARCH_HTML = send_request(
        f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={SEARCH_TITLE}",
        JAV_HEADERS)
else:
    if SCENE_URL:
        scene_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
        # Url from Javlib
        if scene_domain in SITE_JAVLIB:
            debug(f"Using URL: {SCENE_URL}")
            JAV_MAIN_HTML = send_request(SCENE_URL, JAV_HEADERS)
        elif "r18.com" in SCENE_URL:
            r18_id = re.match(r".+id=(.+)/.*", SCENE_URL)
            if r18_id:
                SCENE_URL = f"https://www.r18.com/api/v4f/contents/{r18_id.group(1)}?lang=en"
                debug(f"Using API URL: {SCENE_URL}")
                R18_MAIN_HTML = send_request(SCENE_URL, R18_HEADERS)
            else:
                log.warning(f"Can't find the 'id=' in the URL: {SCENE_URL}")
        else:
            log.warning(f"The URL is not from Javlib/R18 ({SCENE_URL})")
    if JAV_MAIN_HTML is None and R18_MAIN_HTML is None and SCENE_TITLE:
        debug(f"Using search with Title: {SCENE_TITLE}")
        JAV_SEARCH_HTML = send_request(
            f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={SCENE_TITLE}",
            JAV_HEADERS)

# XPATH
r18_xPath_search = {}
r18_xPath_search[
    'series'] = '//p[text()="TOP SERIES"]/following-sibling::ul//a/span[@class="item01"]/text()'
r18_xPath_search[
    'url'] = '//li[contains(@class,"item-list")]/a//img[string-length(@alt)'\
        '=string-length(preceding::div[@class="genre01"]/span/text())]/ancestor::a/@href'
r18_xPath_search['scene'] = '//li[contains(@class,"item-list")]'

jav_xPath_search = {}
jav_xPath_search[
    'url'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@href'
jav_xPath_search[
    'title'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@title'
jav_xPath_search[
    'image'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]//img/@src'

jav_xPath = {}
jav_xPath[
    "title"] = '//td[@class="header" and text()="ID:"]/following-sibling::td/text()'
jav_xPath["details"] = '//div[@id="video_title"]/h3/a/text()'
jav_xPath["url"] = '//meta[@property="og:url"]/@content'
jav_xPath[
    "date"] = '//td[@class="header" and text()="Release Date:"]/following-sibling::td/text()'
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
jav_xPath["image"] = '//div[@id="video_jacket"]/img/@src'
jav_xPath["r18"] = '//a[text()="purchasing HERE"]/@href'

r18_result = {}
jav_result = {}

if "searchName" in sys.argv:
    if JAV_SEARCH_HTML:
        if "/en/?v=" in JAV_SEARCH_HTML.url:
            debug(f"Scraping the movie page directly ({JAV_SEARCH_HTML.url})")
            jav_tree = lxml.html.fromstring(JAV_SEARCH_HTML.content)
            jav_result["title"] = getxpath(jav_xPath["title"], jav_tree)
            jav_result["details"] = getxpath(jav_xPath["details"], jav_tree)
            jav_result["url"] = getxpath(jav_xPath["url"], jav_tree)
            jav_result["image"] = getxpath(jav_xPath["image"], jav_tree)
            for key, value in jav_result.items():
                if isinstance(value,list):
                    jav_result[key] = value[0]
                if key in ["image", "url"]:
                    jav_result[key] = f"https:{jav_result[key]}"
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

if JAV_MAIN_HTML is None and R18_MAIN_HTML is None and SCENE_TITLE:
    # If javlibrary don't have it, there is no way that R18 have it but why not trying...
    log.info("Javlib doesn't give any result, trying search with R18...")
    R18_SEARCH_HTML = send_request(
        f"https://www.r18.com/common/search/searchword={SCENE_TITLE}/?lg=en",
        R18_HEADERS)
    R18_MAIN_HTML = r18_search(R18_SEARCH_HTML, r18_xPath_search)

if JAV_MAIN_HTML:
    #debug("[DEBUG] Javlibrary Page ({})".format(JAV_MAIN_HTML.url))
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
                debug(
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
        if jav_result.get("details"):
            jav_result["details"] = re.sub(r"^(.*? ){1}", "",
                                           jav_result["details"][0])
        if jav_result.get("performers_url") and IGNORE_ALIASES is False:
            javlibrary_aliases_thread = threading.Thread(
                target=th_request_perfpage,
                args=(
                    JAV_MAIN_HTML.url,
                    jav_result["performers_url"],
                ))
            javlibrary_aliases_thread.daemon = True
            javlibrary_aliases_thread.start()
        # R18
        if jav_result.get("r18"):
            r18_search_url = re.sub(r".+\/\/", "https://",
                                    jav_result["r18"][0])
            r18_search_url += '/'
            R18_SEARCH_HTML = send_request(r18_search_url, R18_HEADERS)
            R18_MAIN_HTML = r18_search(R18_SEARCH_HTML, r18_xPath_search)

# MAIN PAGE
if R18_MAIN_HTML:
    r18_main_api = R18_MAIN_HTML.json()
    if r18_main_api["status"] != "OK":
        log.error(f"R18 API Status {r18_main_api.get('status')}")
    else:
        r18_main_api = r18_main_api["data"]
        if r18_main_api.get("title"):
            r18_result['title'] = r18_main_api["dvd_id"]
        if r18_main_api.get("release_date"):
            r18_result['date'] = re.sub(r"\s.+", "",
                                        r18_main_api["release_date"])
        if r18_main_api.get("detail_url"):
            r18_result['url'] = r18_main_api["detail_url"]
        if r18_main_api.get("comment"):
            r18_result[
                'details'] = f"{r18_main_api['title']}\n\n{r18_main_api['comment']}"
        else:
            r18_result['details'] = f"{r18_main_api['title']}"
        if r18_main_api.get("series"):
            r18_result['series_url'] = r18_main_api["series"].get("series_url")
            r18_result['series_name'] = r18_main_api["series"].get("name")
        if r18_main_api.get("maker"):
            r18_result['studio'] = r18_main_api["maker"]["name"]
        if r18_main_api.get("actresses"):
            r18_result['performers'] = [
                x["name"] for x in r18_main_api["actresses"]
            ]
        if r18_main_api.get("categories"):
            r18_result['tags'] = [
                x["name"] for x in r18_main_api["categories"]
            ]
        if r18_main_api.get("images"):
            # Don't know if it's possible no image ??????
            r18_result['image'] = r18_main_api["images"]["jacket_image"][
                "large"]
            imageBase64_r18_thread = threading.Thread(target=th_imageto_base64,
                                                      args=(
                                                          r18_result["image"],
                                                          "R18",
                                                      ))
            imageBase64_r18_thread.start()

if R18_MAIN_HTML is None and JAV_MAIN_HTML is None:
    log.info("No results found")
    sys.exit()

#debug('[DEBUG][JAV] {}'.format(jav_result))
#debug('[DEBUG][R18] {}'.format(r18_result))

# Time to scrape all data
scrape = {}

# Title - Javlibrary > r18
if r18_result.get('title'):
    scrape['title'] = r18_result['title']
if jav_result.get('title'):
    scrape['title'] = jav_result['title'][0]

# Date - R18 > Javlibrary
if jav_result.get('date'):
    scrape['date'] = jav_result['date'][0]
if r18_result.get('date'):
    scrape['date'] = r18_result['date']

# URL - Javlibrary > R18
if r18_result.get('url'):
    scrape['url'] = r18_result['url']
if jav_result.get('url'):
    scrape['url'] = jav_result['url']

# Details - R18 > Javlibrary
if jav_result.get('details'):
    scrape['details'] = regexreplace(jav_result['details'])
if r18_result.get('details'):
    scrape['details'] = regexreplace(r18_result['details'])
if r18_result.get('series_name'):
    if scrape.get('details'):
        scrape['details'] = scrape[
            'details'] + "\n\nFrom the series: " + regexreplace(
                r18_result['series_name'])
    else:
        scrape['details'] = "From the series: " + regexreplace(
            r18_result['series_name'])

# Studio - Javlibrary > R18
scrape['studio'] = {}
if r18_result.get('studio'):
    scrape['studio']['name'] = r18_result['studio']
if jav_result.get('studio'):
    scrape['studio']['name'] = jav_result['studio'][0]

# Performer - Javlibrary > R18
if r18_result.get('performers'):
    scrape['performers'] = buildlist_tagperf(r18_result['performers'])
if jav_result.get('performers'):
    if WAIT_FOR_ALIASES is True and IGNORE_ALIASES is False:
        try:
            if javlibrary_aliases_thread.is_alive() is True:
                javlibrary_aliases_thread.join()
        except NameError:
            debug("No Jav Aliases Thread")
    scrape['performers'] = buildlist_tagperf(jav_result, "perf_jav")

# Tags - Javlibrary > R18
if r18_result.get('tags') and jav_result.get('tags') and BOTH_TAGS is True:
    scrape['tags'] = buildlist_tagperf(r18_result['tags'],
                                       "tags") + buildlist_tagperf(
                                           jav_result['tags'], "tags")
else:
    if r18_result.get('tags'):
        scrape['tags'] = buildlist_tagperf(r18_result['tags'], "tags")
    if jav_result.get('tags'):
        scrape['tags'] = buildlist_tagperf(jav_result['tags'], "tags")

if scrape.get("tags") and SPLIT_TAGS:
    scrape['tags'] = [
        {
            "name": tag_name.strip()
        } for tag_dict in scrape['tags']
        for tag_name in tag_dict["name"].replace('·', ',').split(",")
    ]

# Image - Javlibrary > R18
try:
    if imageBase64_r18_thread.is_alive() is True:
        imageBase64_r18_thread.join()
    if r18_result.get('image'):
        scrape['image'] = r18_result['image']
except NameError:
    debug("No image R18 Thread")
try:
    if imageBase64_jav_thread.is_alive() is True:
        imageBase64_jav_thread.join()
    if jav_result.get('image'):
        scrape['image'] = jav_result['image']
except NameError:
    debug("No image JAV Thread")

# Movie - R18
if r18_result.get('series_url') and r18_result.get('series_name'):
    tmp = {}
    tmp['name'] = regexreplace(r18_result['series_name'])
    tmp['url'] = r18_result['series_url']
    if STASH_SUPPORTED is True:
        # If Stash support this part
        if jav_result.get('image'):
            tmp['front_image'] = jav_result["image"]
        if r18_result.get('image'):
            tmp['front_image'] = r18_result["image"]
        if scrape.get('studio'):
            tmp['studio'] = {}
            tmp['studio']['name'] = scrape['studio']['name']
    scrape['movies'] = [tmp]
print(json.dumps(scrape))
