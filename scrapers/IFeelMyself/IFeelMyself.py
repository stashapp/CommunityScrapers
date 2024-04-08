import json
import re
import sys
from datetime import datetime
import unicodedata

# UNLESS logged in(and probably with an active subscription) scenes with certain tags(menstruation, pee) are hidden and can not be found by scraper.
# Also performer scraper will not be able to get country and details without being logged in.
# set value for ifeel_auth cookie here, may change and need to be renewed periodically.
# if no account available leave value empty and scraper won't find some videos and country and details fields will be missing from performer scrapes.

ifeelauth = ""

try:
    from mechanicalsoup import StatefulBrowser
except ModuleNotFoundError:
    print("You need to install the mechanicalsoup module. (https://mechanicalsoup.readthedocs.io/en/stable/introduction.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install MechanicalSoup", file=sys.stderr)
    sys.exit()

try:
    from requests.cookies import create_cookie
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()


def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)

def extract_SceneInfo(table,cover_url=None):
    description = None
    if table.find(class_= ["blog_wide_new_text","entryBlurb"]):
        description=table.find(class_= ["blog_wide_new_text","entryBlurb"]).get_text(" ", strip=True)
        description=unicodedata.normalize('NFKC', description).encode('ascii','ignore').decode('ascii')
    date = table.find(class_=["blog-title-right","entryDatestamp"]).get_text(strip=True) #This is a BeautifulSoup element. New IFM scenes are under blog-title-right clase for date. Older videos use entryDatestamp class
    performer = table.find(class_= ["entryHeadingFlash","entryHeading"]).find_all("a")[1].get_text().replace("_"," ")
    performer = str(performer)
    debugPrint(f"performer:{performer}")
    date = datetime.strptime(date, '%d %b %Y').date().strftime('%Y-%m-%d') #Convert date to ISO format
    if cover_url == None:
        if table.find("img"):
            cover_url=str(table.find("img")['src'])
        else:
            cover_url=str(table.find("video")['poster'])
    title = table.find(class_= ["entryHeadingFlash","entryHeading"]).find('a').get_text().replace("\x92","'")
    media_id = re.search(r"\/(\d{3,5})\/",cover_url,re.I).group(1)
    artist_id = re.search(r"\/(f\d{4,5})",cover_url,re.I).group(1)
    tags = table.find_all(class_="tags-list-item-tag")
    tag_list = []
    for tag in tags:
        tag_list.append({"name": tag.get_text()})
    debugPrint(f"tags: {str(tag_list)}")
    json_info = {"title": title, "performers": [{"name": performer}], "studio": {"name": "I Feel Myself"}, "tags": tag_list, "date":date, "image": cover_url,"details": description, "url": "https://ifeelmyself.com/public/main.php?page=flash_player&out=bkg&media_id="+media_id+"&artist_id="+artist_id}
    return json_info

def debugPrint(t):
    sys.stderr.write(t + "\n")

def scrapeScene(filename,date,url):
    ret = []
    browser = StatefulBrowser(session=None)
    browser.open("https://ifeelmyself.com/public/main.php")
    cookie_obj = create_cookie(name='tags_popup_shown', value='true', domain='ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    cover_url = None
    if url:
      debugPrint("Url found, using that to scrape")
      if url.endswith(".jpg"):
      #use the image url to extract the metadeta
          media_id = re.search(r"\/(\d{3,5})\/",url,re.I).group(1)
          artist_id = re.search(r"\/(f\d{4,5})",url,re.I).group(1)
          debugPrint(f"Artist id found: {artist_id}")
          debugPrint(f"Media id found: {media_id}")
          cover_url = url
          url = "https://ifeelmyself.com/public/main.php?page=flash_player&out=bkg&media_id="+str(media_id)+"&artist_id="+str(artist_id)
      browser.open(url)
      response = browser.page
      table = response.find(class_ = ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
      if table:
        ret = extract_SceneInfo(table,cover_url)
    else:
        debugPrint("Analyzing filename...")
        artist_id_match=re.search(r"(f\d{3,5})",filename,re.I)
        if artist_id_match:
            artist_id = artist_id_match.group(0)
            video_id = re.search(r"-(\d+)",filename,re.I).group(1)
            cookie_obj = create_cookie(name='ifm_search_keyword', value=artist_id, domain='ifeelmyself.com')
            browser.session.cookies.set_cookie(cookie_obj)
            cookie_obj = create_cookie(name='ifm_prefs', value="a%3A1%3A%7Bs%3A6%3A%22search%22%3Ba%3A17%3A%7Bs%3A8%3A%22category%22%3Ba%3A0%3A%7B%7Ds%3A7%3A%22view_by%22%3Bs%3A4%3A%22news%22%3Bs%3A7%3A%22date_by%22%3Bs%3A7%3A%22anytime%22%3Bs%3A10%3A%22from_month%22%3Bs%3A1%3A%221%22%3Bs%3A9%3A%22from_year%22%3Bs%3A4%3A%222006%22%3Bs%3A8%3A%22to_month%22%3Bs%3A2%3A%2212%22%3Bs%3A7%3A%22to_year%22%3Bs%3A4%3A%223000%22%3Bs%3A7%3A%22country%22%3Bs%3A3%3A%22all%22%3Bs%3A10%3A%22attributes%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_logical%22%3Bs%3A3%3A%22AND%22%3Bs%3A13%3A%22tags_remember%22%3Bs%3A1%3A%22n%22%3Bs%3A4%3A%22tags%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_exclude%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22hide_tags%22%3Ba%3A0%3A%7B%7Ds%3A8%3A%22age_from%22%3Bs%3A2%3A%2218%22%3Bs%3A6%3A%22age_to%22%3Bs%3A2%3A%2299%22%3Bs%3A16%3A%22profilevid_limit%22%3Bs%3A0%3A%22%22%3B%7D%7D", domain='.ifeelmyself.com')
            browser.session.cookies.set_cookie(cookie_obj)
            cookie_obj = create_cookie(name='ifeel_auth', value=ifeelauth, domain='.ifeelmyself.com')
            browser.session.cookies.set_cookie(cookie_obj)
            browser.open("https://ifeelmyself.com/public/main.php?page=search_results")
            response = browser.page
            debugPrint("Searching for video_id")
            debugPrint(artist_id+"-"+video_id)
            tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
            for table in tables:
                    if table.find('video'): #New scenes use the video tag
                        img=str(table.find("video")['poster'])
                    elif table.find('img'): #old scenes still use the old format of a img tag
                        img=str(table.find("img")['src'])
                    debugPrint(f"Image:{str(img)}") 
                    if (f"/{artist_id}-{video_id}vg.jpg" in img) or (f"/{artist_id}-{video_id}hs.jpg" in img):
                        debugPrint("Found a single match video!")
                        # Extract data from this single result
                        ret = extract_SceneInfo(table)
                        break
            else:
                sys.stderr.write("0 matches found! Checking offset")
                pages=int(response.find_all("a", class_="pagging_nonsel")[-1].get_text())
                debugPrint("Pages:  "+str(pages))
                if pages:
                    for offset in range(0,pages*10,10):
                        browser.open("https://ifeelmyself.com/public/main.php?page=search_results&offset="+str(offset))
                        response = browser.page
                        tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                        for table in tables:
                            if table.find('video'): #New scenes use the video tag
                                img=str(table.find("video")['poster'])
                            elif table.find('img'): #old scenes still use the old format of a img tag
                                img=str(table.find("img")['src'])
                            debugPrint(f"Image:{img}")
                            if (f"/{artist_id}-{video_id}vg.jpg" in img) or (f"/{artist_id}-{video_id}hs.jpg" in img):
                                sys.stderr.write("FOUND")
                                ret = extract_SceneInfo(table)
                                break
                else:
                    sys.stderr.write("0 matches found!, check your filename")

        else:
            debugPrint("Name changed after downloading")
            filename = filename.lower()
            extract_from_filename = re.match(r"^([0-9\.]{6,10})?(?<title>.+)\s(?<artist>\w+)(\.mp4)?$",filename)
            if extract_from_filename:
                title = extract_from_filename.group('title')
                if title:
                    title = title.lower().replace("ifeelmyself","")
                    title = title.replace("-","")
                    title = title.replace("by", "")
                    debugPrint(f"Title: {title}")
                cookie_obj = create_cookie(name='ifm_search_keyword', value=title, domain='ifeelmyself.com')
                browser.session.cookies.set_cookie(cookie_obj)
                cookie_obj = create_cookie(name='ifm_prefs', value="a%3A1%3A%7Bs%3A6%3A%22search%22%3Ba%3A17%3A%7Bs%3A8%3A%22category%22%3Ba%3A0%3A%7B%7Ds%3A7%3A%22view_by%22%3Bs%3A4%3A%22news%22%3Bs%3A7%3A%22date_by%22%3Bs%3A7%3A%22anytime%22%3Bs%3A10%3A%22from_month%22%3Bs%3A1%3A%221%22%3Bs%3A9%3A%22from_year%22%3Bs%3A4%3A%222006%22%3Bs%3A8%3A%22to_month%22%3Bs%3A2%3A%2212%22%3Bs%3A7%3A%22to_year%22%3Bs%3A4%3A%223000%22%3Bs%3A7%3A%22country%22%3Bs%3A3%3A%22all%22%3Bs%3A10%3A%22attributes%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_logical%22%3Bs%3A3%3A%22AND%22%3Bs%3A13%3A%22tags_remember%22%3Bs%3A1%3A%22n%22%3Bs%3A4%3A%22tags%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_exclude%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22hide_tags%22%3Ba%3A0%3A%7B%7Ds%3A8%3A%22age_from%22%3Bs%3A2%3A%2218%22%3Bs%3A6%3A%22age_to%22%3Bs%3A2%3A%2299%22%3Bs%3A16%3A%22profilevid_limit%22%3Bs%3A0%3A%22%22%3B%7D%7D", domain='.ifeelmyself.com')
                browser.session.cookies.set_cookie(cookie_obj)
                cookie_obj = create_cookie(name='ifeel_auth', value=ifeelauth, domain='.ifeelmyself.com')
                browser.session.cookies.set_cookie(cookie_obj)
                browser.open("https://ifeelmyself.com/public/main.php?page=search_results")
                response = browser.page
                #Obtaining and counting the results. Ideally you only have a single result
                matches=response.find_all("a", href='javascript:;') #This a href javascript contains all the titles
                if len(matches)==1:
                    debugPrint("Found a single match!")
                    table = response.find(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                else:
                    if len(matches)==0:
                        sys.stderr.write("0 matches found! Check filename")
                        print("{}")
                        exit
                    if len(matches)>1:
                        debugPrint("Multiple videos found, maybe refine search term?")
                        tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                        table=tables[0] #Getting first
                if table:
                    ret = extract_SceneInfo(table)
            else:
                debugPrint("Not a supported filename")
                print("{}")
                exit
    return ret





def extract_PerformerInfo(table,browser,cover_url=None):
    performer = table.find(class_= ["entryHeadingFlash","entryHeading"]).find_all("a")[1].get_text().replace("_"," ")
    performer = str(performer)
    debugPrint(f"Extracting info for performer: {performer}")
    if cover_url == None:
        cover_url=str(table.find("img")['src'])
    debugPrint(cover_url)
    artist_id = re.search(r"\/((f|m)\d{4,5})",cover_url,re.I).group(1)
    artist_img = (f"https://bcdn.ifeelmyself.com/artists/" + artist_id + ".jpg")
    if artist_id.startswith("f"):
        gender="female"
    else:
        gender="male"
    json_info = {"name": performer, "gender": gender, "url": (f"https://ifeelmyself.com/public/main.php?page=artist_bio&artist_id="+artist_id), "image": artist_img, "remote_site_id": artist_id}
    return json_info


def queryPerformer(perfname):
    browser = StatefulBrowser(session=None)
    perfname = perfname.lower()
    browser.open("https://ifeelmyself.com/public/main.php")
    cookie_obj = create_cookie(name='tags_popup_shown', value='true', domain='ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    cookie_obj = create_cookie(name='ifm_prefs', value="a%3A1%3A%7Bs%3A6%3A%22search%22%3Ba%3A17%3A%7Bs%3A8%3A%22category%22%3Ba%3A0%3A%7B%7Ds%3A7%3A%22view_by%22%3Bs%3A4%3A%22news%22%3Bs%3A7%3A%22date_by%22%3Bs%3A7%3A%22anytime%22%3Bs%3A10%3A%22from_month%22%3Bs%3A1%3A%221%22%3Bs%3A9%3A%22from_year%22%3Bs%3A4%3A%222006%22%3Bs%3A8%3A%22to_month%22%3Bs%3A2%3A%2212%22%3Bs%3A7%3A%22to_year%22%3Bs%3A4%3A%223000%22%3Bs%3A7%3A%22country%22%3Bs%3A3%3A%22all%22%3Bs%3A10%3A%22attributes%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_logical%22%3Bs%3A3%3A%22AND%22%3Bs%3A13%3A%22tags_remember%22%3Bs%3A1%3A%22n%22%3Bs%3A4%3A%22tags%22%3Ba%3A0%3A%7B%7Ds%3A12%3A%22tags_exclude%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22hide_tags%22%3Ba%3A0%3A%7B%7Ds%3A8%3A%22age_from%22%3Bs%3A2%3A%2218%22%3Bs%3A6%3A%22age_to%22%3Bs%3A2%3A%2299%22%3Bs%3A16%3A%22profilevid_limit%22%3Bs%3A0%3A%22%22%3B%7D%7D", domain='.ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    cookie_obj = create_cookie(name='ifm_search_keyword', value=perfname, domain='ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    cookie_obj = create_cookie(name='ifeel_auth', value=ifeelauth, domain='.ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    debugPrint("Analyzing perfname...")
    browser.open("https://ifeelmyself.com/public/main.php?page=search_results")
    response = browser.page
    #Obtaining and counting the results. Ideally you only have a single result
    matches=response.find_all("a", href='javascript:;') #This a href javascript contains all the titles
    debugPrint("Found: "+str(len(matches)))
    ret = []
    foundList = []
    if len(matches)==0:
        # often performer names use a underscore instead of a space, so replace spaces and try again
        perfname = perfname.replace(" ","_")
        cookie_obj = create_cookie(name='ifm_search_keyword', value=perfname, domain='ifeelmyself.com')
        browser.session.cookies.set_cookie(cookie_obj)
        browser.open("https://ifeelmyself.com/public/main.php?page=search_results")
        response = browser.page
        #Obtaining and counting the results. Ideally you only have a single result
        matches=response.find_all("a", href='javascript:;') #This a href javascript contains all the titles
        if len(matches)==0:
            sys.stderr.write("0 matches found! Check performer name")
            print("{}")
            exit
        if len(matches)>0:
            debugPrint("Multiple videos found, scraping multiple performers")
            tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
            for table in tables:
                result = extract_PerformerInfo(table,browser)
                if not result['name'] in foundList:
                    foundList.append(result['name'])
                    ret.append(result)
    if len(matches)>0:
        tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
        for table in tables:
            result = extract_PerformerInfo(table,browser)
            if not result['name'] in foundList:
                foundList.append(result['name'])
                ret.append(result)
    return ret





def scrapePerformer(artist_id):
    browser = StatefulBrowser(session=None)
    cookie_obj = create_cookie(name='tags_popup_shown', value='true', domain='ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    cookie_obj = create_cookie(name='ifeel_auth', value=ifeelauth, domain='.ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    browser.open(f"https://ifeelmyself.com/public/main.php?page=artist_bio&artist_id="+artist_id)
    response = browser.page
    tables = response.find_all(class_= ["bioTable"])
    table=tables[0]
    debugPrint(str(table))
    bio = str(table.find("td"))
    lines=bio.splitlines(True)
    countryline=bio.splitlines(0)[1]
    country=countryline.split("<br/>")[1]
    details=lines[3]+lines[4]+lines[5]+lines[6]+lines[7]+lines[8]
    details=details.replace("<strong>","").replace("</strong>","").replace("<br/>","")
    json_info = {"country": country , "details": details}
    return json_info




# read the input
i = readJSONInput()
sys.stderr.write(json.dumps(i))

if sys.argv[1] == "query" and sys.argv[2] == "scene":
    ret = scrapeScene(i['title'],i['date'],i['url'])
    print(json.dumps(ret))

if sys.argv[1] == "query" and sys.argv[2] == "performer":
    ret = queryPerformer(i['name'])
    print(json.dumps(ret))

if sys.argv[1] == "url":
    ret = scrapeScene(filename=None,date=None,url=i['url'])
    print(json.dumps(ret))

if sys.argv[1] == "scrape":
    country = ""
    details = ""
    if not ifeelauth == "":
        ret = scrapePerformer(i['remote_site_id'])
        country = ret['country']
        details = ret['details']

    json_info = {"name": i['name'], "gender": i['gender'], "url": i['url'],"country": country ,"details": details , "image": "https://bcdn.ifeelmyself.com/artists/" + i['remote_site_id'] + ".jpg"}
    print(json.dumps(json_info))
