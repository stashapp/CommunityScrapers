import base64
import datetime
import json
import re
import sys
import threading
import time

import lxml.html    # https://pypi.org/project/lxml/         | pip install lxml
import requests     # https://pypi.org/project/requests/     | pip install requests

R18_HEADERS = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Referer": "https://www.r18.com/"
}
JAV_HEADERS = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Referer": "http://www.javlibrary.com/"
}
# Print debug message
DEBUG_MODE = True
# We can't add movie image atm in same time as Scene
STASH_SUPPORTED = False
# Tags you don't want to see appear in Scraper window
IGNORE_TAGS = ["Features Actress", "Digital Mosaic", "Hi-Def", "Risky Mosaic",
               "Beautiful Girl", "Blu-ray", "Featured Actress", "VR Exclusive", "MOODYZ SALE 4"]
# Some performer don't need to be reversed
IGNORE_PERF_REVERSE = ["Lily Heart"]
# Tag you always want in Scraper window
FIXED_TAGS = ""
# Take Javlibrary and R18 tags
BOTH_TAGS = False
# Don't care about getting the Aliases (Japanese Name)
IGNORE_ALIASES = False
# Always wait for the aliases or you are not sure to have it. (Depends if request are quick)
WAIT_FOR_ALIASES = False

BANNED_WORDS = {
    "R**e": "Rape",
    "R**es": "Rapes",
    "R****g": "Raping",
    "R**ed": "Raped",
    "G******g": "Gangbang",
    "G*******g": "Gangbang",
    "G*******gs": "Gangbangs",
    "G******ged": "Gangbanged",
    "G*******ged": "Gangbanged",
    "G*********d": "Gang-Banged",
    "G*******ging": "Gangbanging",
    "P*ssy": "Pussy",
    "C*ck": "Cock",
    "C*cks": "Cocks",
    "Ma*ko": "Maiko",
    "K**l": "Kill",
    "K**ling": "Killing",
    "T*****e": "Torture",
    "T*****ed": "Tortured",
    "V*****t": "Violent",
    "S***e": "Slave",
    "S***es": "Slaves",
    "S***ery": "Slavery",
    "EnS***ed": "Enslaved",
    "D***king": "Drinking",
    "D***ks": "Drinks",
    "S*****t": "Student",
    "S*****ts": "Students",
    "SK**ls": "Skills",
    "SK**lfully": "Skillfully",
    "SK**lful": "Skillful",
    "SK**led": "Skilled",
    "P**hed": "Punished",
    "D**gged": "Drugged",
    "D**gs": "Drugs",
    "F***ed": "Fucked",
    "D***k": "Drunk",
    "D***kest": "Drunkest",
    "S********l": "Schoolgirl",
    "S*********s": "Schoolgirls",
    "S********ls": "Schoolgirls",
    "Sch**lgirl": "Schoolgirl",
    "Sch**lgirls": "Schoolgirls",
    "S*********l": "School Girl",
    "S*********ls": "School Girls",
    "P****hment": "Punishment",
    "P****h": "Punish",
    "M****ter": "Molester",
    "M****ters": "Molesters",
    "M****ted": "Molested",
    "M****t": "Molest",
    "I****t": "Incest",
    "I****tuous": "Incestuous",
    "V*****e": "Violate",
    "V*****ed": "Violated",
    "StepB****************r": "StepBrother And Sister",
    "StepK*ds ": "StepKids",
    "C***dhood": "Childhood",
    "V******e": "Violence",
    "C***dcare": "Childcare",
    "H*******m": "Hypnotism",
    "M****tation": "Molestation",
    "M****ting": "Molesting",
    "F***e": "Force",
    "A***es": "Abuses",
    "A***e": "Abuse",
    "S******g": "Sleeping",
    "A***ed": "Abused",
    "D**g": "Drug",
    "A*****ted": "Assaulted",
    "A*****t": "Assault",
    "S********n": "Submission",
    "K*d": "Kid",
    "K*ds": "Kids",
    "D******e": "Disgrace",
    "Y********ls": "Young Girls",
    "Y********l": "Young Girl",
    "H**t": "Hurt",
    "H**ts": "Hurts",
    "C***dren": "Children",
    "F***es": "Forces",
    "Chai*saw": "Chainsaw",
    "Lol*pop": "Lolipop",
    "K****pped": "Kidnapped",
    "K****pping": "Kidnapping",
    "B*****p": "Bang Up",
    "D***ken": "Drunken",
    "Lo**ta": "Lolita",
    "CrumB**d": "CrumBled",
    "K*dding": "Kidding",
    "C***d": "Child",
    "C*****y": "Cruelty",
    "H*********n": "Humiliation",
    "D******eful": "Disgraceful",
    "B***d": "Blood",
    "U*******g": "Unwilling",
    "HumB**d": "Humbled",
    "K**ler": "Killer",
    "J*": "Jo",
    "J*s": "Jos",
    "V*****es": "Violates",
    "D******ed": "Disgraced",
    "F***efully": "Forcefully",
    "I****ts": "Insults",
    "B***dy": "Bloody",
    "U*********sly": "Unconsciously",
    "Half-A****p": "Half-Asleep",
    "A****p": "Asleep",
    "StepM************n": "Stepmother And Son",
    "C***dish": "Childish",
    "G****gers": "Gangbangers",
    "K****pper": "Kidnapper",
    "M****tor": "Molestor",
    "F*****g": "Fucking",
    "B*****k": "Berserk",
    "H*******ed": "Hypnotized"
}


def debug(q):
    if "[DEBUG]" in q and DEBUG_MODE == False:
        return
    print(q, file=sys.stderr)


def sendRequest(url, head):
    debug("[DEBUG][{}] Request URL: {}".format(threading.get_ident(), url))
    for x in range(0, 5):
        response = requests.get(url, headers=head, timeout=10)
        if response.content and response.status_code == 200:
            break
        else:
            debug("[{}] Bad page...".format(x))
            time.sleep(5)
    if response.status_code == 200:
        pass
    else:
        debug("[Request] Error, Status Code: {}".format(response.status_code))
        response = None
    return response


def replace_banned_words(matchobj):
    word = matchobj.group(0)
    if word in BANNED_WORDS:
        return BANNED_WORDS[word]
    else:
        return word

def regexreplace(input):
    word_pattern = re.compile('(\w|\*)+')
    output = word_pattern.sub(replace_banned_words, input)
    return re.sub(r"[\[\]\"]", "", output)


def getxpath(xpath, tree):
    xPath_result = []
    # It handle the union strangely so it better to split and do one by one
    if "|" in xpath:
        for xpath_tmp in xpath.split("|"):
            xPath_result.append(tree.xpath(xpath_tmp))
        xPath_result = [val for sublist in xPath_result for val in sublist]
    else:
        xPath_result = tree.xpath(xpath)
    #debug("xPATH: {}".format(xpath))
    #debug("raw xPATH result: {}".format(xPath_result))
    list_tmp = []
    for a in xPath_result:
        # for xpath that don't end with /text()
        if type(a) is lxml.html.HtmlElement:
            list_tmp.append(a.text_content().strip())
        else:
            list_tmp.append(a.strip())
    if list_tmp:
        xPath_result = list_tmp
    xPath_result = list(filter(None, xPath_result))
    return xPath_result

# SEARCH PAGE


def r18_search(html, xpath):
    r18_search_tree = lxml.html.fromstring(html.content)
    r18_search_url = getxpath(xpath['url'], r18_search_tree)
    r18_search_serie = getxpath(xpath['series'], r18_search_tree)
    r18_search_scene = getxpath(xpath['scene'], r18_search_tree)
    # There is only 1 scene, with serie.
    # Could be useful is the movie already exist in Stash because you only need the name.
    if len(r18_search_scene) == 1 and len(r18_search_serie) == 1 and len(r18_search_url) == 1:
        r18_result["series_name"] = r18_search_serie
    if r18_search_url:
        r18_search_url = r18_search_url[0]
        r18_main_html = sendRequest(r18_search_url, R18_HEADERS)
        return r18_main_html
    else:
        debug("[R18] There is no result in search")
        return None


def jav_search(html, xpath):
    if "javlibrary.com/en/?v=" in html.url:
        return html
    jav_search_tree = lxml.html.fromstring(html.content)
    jav_url = getxpath(xpath['url'], jav_search_tree)  # ./?v=javme5it6a
    if jav_url:
        jav_url = re.sub(r"^\.", "https://www.javlibrary.com/en", jav_url[0])
        jav_main_html = sendRequest(jav_url, JAV_HEADERS)
        return jav_main_html
    else:
        debug("[JAV] There is no result in search")
        return None


def buildlist_tagperf(data, type_scrape=""):
    list_tmp = []
    dict_jav = None
    if type_scrape == "perf_jav":
        dict_jav = data
        data = data["performers"]
    for i in range(0, len(data)):
        y = data[i]
        if y == "":
            continue
        if type_scrape == "perf_jav":
            if y not in IGNORE_PERF_REVERSE:
                # Invert name (Aoi Tsukasa -> Tsukasa Aoi)
                y = re.sub(r"([a-zA-Z]+)(\s)([a-zA-Z]+)", r"\3 \1", y)
        if type_scrape == "tags" and y in IGNORE_TAGS:
            continue
        if type_scrape == "perf_jav" and dict_jav.get("performer_aliases"):
            try:
                list_tmp.append({"name": y, "aliases": dict_jav["performer_aliases"][i]})
            except:
                list_tmp.append({"name": y})
        else:
            list_tmp.append({"name": y})
    # Adding personal fixed tags
    if FIXED_TAGS and type_scrape == "tags":
        list_tmp.append({"name": FIXED_TAGS})
    return list_tmp


def th_request_perfpage(page_url, perf_url):
    # vl_star.php?s=afhvw
    #debug("[DEBUG] Aliases Thread: {}".format(threading.get_ident()))
    javlibrary_ja_html = sendRequest(page_url.replace("/en/", "/ja/"), JAV_HEADERS)
    if javlibrary_ja_html:
        javlibrary_perf_ja = lxml.html.fromstring(javlibrary_ja_html.content)
        list_tmp = []
        try:
            for i in range(0, len(perf_url)):
                list_tmp.append(javlibrary_perf_ja.xpath('//a[@href="' + perf_url[i] + '"]/text()')[0])
            if list_tmp:
                jav_result['performer_aliases'] = list_tmp
                debug("[DEBUG] Got the aliases: {}".format(list_tmp))
        except:
            debug("[DEBUG] Error with the aliases")
    else:
        debug("[DEBUG] Can't get the Jap HTML")
    return


def th_imagetoBase64(imageurl, typevar):
    #debug("[DEBUG] {} thread: {}".format(typevar,threading.get_ident()))
    head = JAV_HEADERS
    if typevar == "R18Series" or typevar == "R18":
        head = R18_HEADERS
    if type(imageurl) is list:
        for image_index in range(0, len(imageurl)):
            try:
                img = requests.get(imageurl[image_index].replace("ps.jpg", "pl.jpg"), timeout=10, headers=head)
                if img.status_code != 200:
                    debug("[Image] Got a bad request (status: {}) for <{}>".format(img.status_code,imageurl[image_index]))
                    imageurl[image_index] = None
                    continue
                base64image =  base64.b64encode(img.content)
                imageurl[image_index] = "data:image/jpeg;base64," + base64image.decode('utf-8')
            except:
                debug("[DEBUG][{}] Failed to get the base64 of the image".format(typevar))
        if typevar == "R18Series":
            r18_result["series_image"] = imageurl
    else:
        try:
            img = requests.get(imageurl.replace("ps.jpg", "pl.jpg"), timeout=10, headers=head)
            if img.status_code != 200:
                debug("[Image] Got a bad request (status: {}) for <{}>".format(img.status_code,imageurl))
                return
            base64image = base64.b64encode(img.content)
            if typevar == "JAV":
                jav_result["image"] = "data:image/jpeg;base64," + base64image.decode('utf-8')
            if typevar == "R18":
                r18_result["image"] = "data:image/jpeg;base64," + base64image.decode('utf-8')
            debug("[DEBUG][{}] Converted the image to base64!".format(typevar))
        except:
            debug("[DEBUG][{}] Failed to get the base64 of the image".format(typevar))
    return


#debug("[DEBUG] Main Thread: {}".format(threading.get_ident()))
fragment = json.loads(sys.stdin.read())
if fragment["url"]:
    scene_url = fragment["url"]
else:
    scene_url = None

scene_title = fragment["title"]
# Remove extension
scene_title = re.sub(r"\..{3}$", "", scene_title)
scene_title = re.sub(r"-JG\d", "", scene_title)
scene_title = re.sub(r"\s.+$", "", scene_title)
scene_title = re.sub(r"[ABCDEFGH]$", "", scene_title)

jav_search_html = None
r18_search_html = None
jav_main_html = None
r18_main_html = None

if scene_url:
    if "javlibrary.com" in scene_url:
        jav_main_html = sendRequest(scene_url, JAV_HEADERS)
    if "f50q.com" in scene_url:
        jav_main_html = sendRequest(scene_url, JAV_HEADERS)
    if "r18.com" in scene_url:
        r18_main_html = sendRequest(scene_url, R18_HEADERS)
else:
    jav_search_html = sendRequest("https://www.javlibrary.com/en/vl_searchbyid.php?keyword={}".format(scene_title), JAV_HEADERS)
    if jav_search_html is None:
        # A error for javlibrary, trying a mirror
        debug("[JAV] Error with Javlibrary, trying the mirror f50q")
        jav_search_html = sendRequest("https://www.f50q.com/en/vl_searchbyid.php?keyword={}".format(scene_title), JAV_HEADERS)

# XPATH
r18_xPath_search = {}
r18_xPath_search['series'] = '//p[text()="TOP SERIES"]/following-sibling::ul//a/span[@class="item01"]/text()'
r18_xPath_search['url'] = '//li[contains(@class,"item-list")]/a//img[string-length(@alt)=string-length(preceding::div[@class="genre01"]/span/text())]/ancestor::a/@href'
r18_xPath_search['scene'] = '//li[contains(@class,"item-list")]'

r18_xPath = {}
r18_xPath["title"] = '//section[@class="clearfix"]/div[@class="product-details"]/dl/dt[contains(.,"DVD ID")]/following-sibling::dd[1]/text()'
r18_xPath["details"] = '//div[@class="col01"]/h1/cite[@itemprop="name"]/text()|//div[contains(@class,"cmn-box-description")]/p'
r18_xPath["url"] = '//link[@rel="canonical"]/@href'
r18_xPath["date"] = '//section[@class="clearfix"]/div[@class="product-details"]/dl/dt[contains(.,"Release Date")]/../dd[@itemprop="dateCreated"]/text()'
r18_xPath["tags"] = '//div[@class="product-categories-list product-box-list"]/div[@class="pop-list"]/a'
r18_xPath["performers"] = '//div[@data-type="actress-list"]/span/a/span/text()'
r18_xPath["studio"] = '//section[@class="clearfix"]/div[@class="product-details"]/dl/dt[contains(.,"Studio")]/../dd[@itemprop="productionCompany"]/a/text()'
r18_xPath["image"] = '//meta[@itemprop="thumbnailUrl"]/@content'
r18_xPath["series_url"] = '//section[@class="clearfix"]/div[@class="product-details"]/dl/dt[contains(.,"Series:")]/following-sibling::dd[1]/a/@href'

jav_xPath_search = {}
jav_xPath_search['url'] = '//div[@class="videos"]/div/a/@title[not(contains(.,"(Blu-ray"))]/../@href'

jav_xPath = {}
jav_xPath["title"] = '//td[@class="header" and text()="ID:"]/following-sibling::td/text()'
jav_xPath["details"] = '//div[@id="video_title"]/h3/a/text()'
jav_xPath["url"] = '//meta[@property="og:url"]/@content'
jav_xPath["date"] = '//td[@class="header" and text()="Release Date:"]/following-sibling::td/text()'
jav_xPath["tags"] = '//td[@class="header" and text()="Genre(s):"]/following::td/span[@class="genre"]/a/text()'
jav_xPath["performers"] = '//td[@class="header" and text()="Cast:"]/following::td/span[@class="cast"]/span/a/text()'
jav_xPath["performers_url"] = '//td[@class="header" and text()="Cast:"]/following::td/span[@class="cast"]/span/a/@href'
jav_xPath["studio"] = '//td[@class="header" and text()="Maker:"]/following-sibling::td/span[@class="maker"]/a/text()'
jav_xPath["image"] = '//div[@id="video_jacket"]/img/@src'
jav_xPath["r18"] = '//a[text()="purchasing HERE"]/@href'

r18_result = {}
jav_result = {}

if jav_search_html:
    jav_main_html = jav_search(jav_search_html, jav_xPath_search)
    if jav_main_html is None:
        # If javlibrary don't have it, there is no way that R18 have it but why not trying...
        debug("Javlibrary don't give any result, trying search with R18...")
        r18_search_html = sendRequest("https://www.r18.com/common/search/searchword={}/?lg=en".format(scene_title), R18_HEADERS)
        r18_main_html = r18_search(r18_search_html, r18_xPath_search)


if jav_main_html:
    #debug("[DEBUG] Javlibrary Page ({})".format(jav_main_html.url))
    jav_tree = lxml.html.fromstring(jav_main_html.content)
    # Get data from javlibrary
    for key, value in jav_xPath.items():
        jav_result[key] = getxpath(value, jav_tree)
    # PostProcess
    if jav_result.get("image"):
        tmp = re.sub(r"(http:|https:)", "", jav_result["image"][0])
        jav_result["image"] = "https:" + tmp
        if "now_printing.jpg" in jav_result["image"] or "noimage" in jav_result["image"]:
            # https://pics.dmm.com/mono/movie/n/now_printing/now_printing.jpg
            # https://pics.dmm.co.jp/mono/noimage/movie/adult_ps.jpg
            debug("[Warning][Javlibrary] Image was deleted or fail to loaded ({})".format(jav_result["image"]))
            jav_result["image"] = None
        else:
            imageBase64_jav_thread = threading.Thread(target=th_imagetoBase64, args=(jav_result["image"], "JAV",))
            imageBase64_jav_thread.start()
    if jav_result.get("url"):
        jav_result["url"] = "https:" + jav_result["url"][0]
    if jav_result.get("details"):
        jav_result["details"] = re.sub(
            r"^(.*? ){1}", "", jav_result["details"][0])
    if jav_result.get("performers_url") and IGNORE_ALIASES == False:
        javlibrary_aliases_thread = threading.Thread(target=th_request_perfpage, args=(jav_main_html.url, jav_result["performers_url"],))
        javlibrary_aliases_thread.daemon = True
        javlibrary_aliases_thread.start()
    # R18
    if jav_result.get("r18"):
        r18_search_url = re.sub(r"^redirect\.php\?url=\/\/", "https://", jav_result["r18"][0])
        r18_search_html = sendRequest(r18_search_url, R18_HEADERS)
        r18_main_html = r18_search(r18_search_html, r18_xPath_search)

# MAIN PAGE
if r18_main_html:
    #debug("[DEBUG] R18 Page ({})".format(r18_main_html.url))
    r18_tree = lxml.html.fromstring(r18_main_html.content)
    # Get data from data18
    for key, value in r18_xPath.items():
        r18_result[key] = getxpath(value, r18_tree)
    # PostProcess
    # We can get the full name during the r18 search
    if r18_result.get("image"):
        r18_result["image"] = r18_result["image"][0].replace("ps.jpg", "pl.jpg")
        if "now_printing.jpg" in r18_result["image"] or "noimage" in r18_result["image"]:
            debug("[Warning][R18] Image was deleted or fail to loaded ({})".format(r18_result["image"]))
            r18_result["image"] = None
        else:
            imageBase64_r18_thread = threading.Thread(target=th_imagetoBase64, args=(r18_result["image"], "R18",))
            imageBase64_r18_thread.start()
    if r18_result.get("series_url"):
        r18_result['series_url'] = r18_result["series_url"][0]
        if r18_result.get("series_name") is None:
            r18_series_search = sendRequest(r18_result['series_url'], r18_tree)
            if r18_series_search is None:
                debug("[R18] Error getting to serie page")
            else:
                debug("[DEBUG] Access to series page")
                r18_series_search_tree = lxml.html.fromstring(r18_series_search.content)
                r18_result['series_name'] = r18_series_search_tree.xpath('//h1[@class="txt01"]/text()')
                xPath_series_scene = r18_series_search_tree.xpath('//li[contains(@class,"item-list")]')
                if STASH_SUPPORTED == True:
                    if len(xPath_series_scene) == 0:
                        debug("[DEBUG] Series have 0 scene")
                    else:
                        # It's useless to try to get the image there is no scene card
                        r18_result['series_image'] = r18_series_search_tree.xpath('//li[@class="item-list"]//img/@data-original')
                        imageBase64_serie_thread = threading.Thread(target=th_imagetoBase64, args=(r18_result["series_image"], "R18Series",))
                        imageBase64_serie_thread.start()
    else:
        if r18_result.get("series_name"):
            debug("[Warning] There is a serie but no URL ????")
        else:
            debug("[DEBUG] No series URL")
    if r18_result.get("details"):
        # Concat
        r18_result["details"] = "\n\n".join(r18_result["details"])
    if r18_result.get("date"):
        r18_date = r18_result["date"][0]
        tmp = re.sub(r"\.", "", r18_date)
        tmp = re.sub(r"Sept", "Sep", tmp)
        tmp = re.sub(r"July", "Jul", tmp)
        tmp = re.sub(r"June", "Jun", tmp)
        try:
            r18_result["date"] = str(datetime.datetime.strptime(tmp, "%b %d, %Y").date())
            pass
        except ValueError:
            r18_result["date"] = None
            pass


if r18_main_html is None and jav_main_html is None:
    debug("All request don't find anything")
    sys.exit(1)

#debug('[DEBUG][JAV] {}'.format(jav_result))
#debug('[DEBUG][R18] {}'.format(r18_result))

# Time to scrape all data
scrape = {}

# Title - Javlibrary > r18
if r18_result.get('title'):
    scrape['title'] = regexreplace(r18_result['title'][0])
if jav_result.get('title'):
    scrape['title'] = regexreplace(jav_result['title'][0])

# Date - R18 > Javlibrary
if jav_result.get('date'):
    scrape['date'] = jav_result['date'][0]
if r18_result.get('date'):
    scrape['date'] = r18_result['date']

# URL - Javlibrary > R18
if r18_result.get('url'):
    scrape['url'] = r18_result['url'][0]
if jav_result.get('url'):
    scrape['url'] = jav_result['url']

# Details - R18 > Javlibrary
if jav_result.get('details'):
    scrape['details'] = regexreplace(jav_result['details'])
if r18_result.get('details'):
    scrape['details'] = regexreplace(r18_result['details'])
if r18_result.get('series_name'):
    scrape['details'] = scrape['details'] + "\n\nFrom the series: " + regexreplace(r18_result['series_name'][0])

# Studio - Javlibrary > R18
scrape['studio'] = {}
if r18_result.get('studio'):
    scrape['studio']['name'] = r18_result['studio'][0]
if jav_result.get('studio'):
    scrape['studio']['name'] = jav_result['studio'][0]

# Performer - Javlibrary > R18
if r18_result.get('performers'):
    scrape['performers'] = buildlist_tagperf(r18_result['performers'])
if jav_result.get('performers'):
    if WAIT_FOR_ALIASES == True and IGNORE_ALIASES == False:
        try:
            if javlibrary_aliases_thread.is_alive() == True:
                javlibrary_aliases_thread.join()
        except NameError:
            debug("[DEBUG] No Jav Aliases Thread")
    scrape['performers'] = buildlist_tagperf(jav_result, "perf_jav")
# Tags - Javlibrary > R18
if r18_result.get('tags') and jav_result.get('tags') and BOTH_TAGS == True:
    scrape['tags'] = buildlist_tagperf(r18_result['tags'], "tags") + buildlist_tagperf(jav_result['tags'], "tags")
else:
    if r18_result.get('tags'):
        scrape['tags'] = buildlist_tagperf(r18_result['tags'], "tags")
    if jav_result.get('tags'):
        scrape['tags'] = buildlist_tagperf(jav_result['tags'], "tags")

# Image - Javlibrary > R18
try:
    if imageBase64_r18_thread.is_alive() == True:
        imageBase64_r18_thread.join()
    if r18_result.get('image'):
        scrape['image'] = r18_result['image']
except NameError:
    debug("[DEBUG] No R18 Thread")
try:
    if imageBase64_jav_thread.is_alive() == True:
        imageBase64_jav_thread.join()
    if jav_result.get('image'):
        scrape['image'] = jav_result['image']
except NameError:
    debug("[DEBUG] No JAV Thread")

# Movie - R18

if r18_result.get('series_url'):
    tmp = {}
    tmp['name'] = regexreplace(r18_result['series_name'][0])
    tmp['url'] = r18_result['series_url']
    if STASH_SUPPORTED == True:
        # If Stash support this part
        if jav_result.get('image'):
            tmp['front_image'] = jav_result["image"]
        if r18_result.get('image'):
            tmp['front_image'] = r18_result["image"]
        if r18_result.get('series_image'):
            try:
                if imageBase64_serie_thread.is_alive() == True:
                    imageBase64_r18_thread.join()
                try:
                    tmp['front_image'] = r18_result["series_image"][0]
                    tmp['back_image'] = r18_result["series_image"][1]
                except:
                    pass
            except NameError:
                debug("[DEBUG] No r18 series Thread")
        if scrape.get('studio'):
            tmp['studio'] = {}
            tmp['studio']['name'] = scrape['studio']['name']
    scrape['movies'] = [tmp]

print(json.dumps(scrape))

# Last Updated July 06, 2021
