import json
import re
import sys
from datetime import datetime

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

def extract_info(table,cover_url=None):
    description = None
    if table.find(class_= ["blog_wide_new_text","entryBlurb"]):
        description=table.find(class_= ["blog_wide_new_text","entryBlurb"]).get_text(strip=True).replace("\x92","'")
    date = table.find(class_="blog-title-right").get_text(strip=True) #This is a BeautifulSoup element
    performer = table.find(class_= ["entryHeadingFlash","entryHeading"]).find_all("a")[1].get_text().replace("_"," ")
    performer = str(performer)
    debugPrint(f"performer:{performer}")
    date = datetime.strptime(date, '%d %b %Y').date().strftime('%Y-%m-%d') #Convert date to ISO format
    if cover_url == None:
        cover_url=str(table.find("img")['src'])
    title = table.find(class_= ["entryHeadingFlash","entryHeading"]).find('a').get_text()
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
        ret = extract_info(table,cover_url)
    else:
        debugPrint("Analyzing filename...")
        artist_id_match=re.search(r"(f\d{3,5})",filename,re.I)
        if artist_id_match:
            artist_id = artist_id_match.group(0)
            video_id = re.search(r"-(\d+)",filename,re.I).group(1)
            browser.open("https://ifeelmyself.com/public/main.php?page=search")
            browser.select_form()
            browser['keyword']=artist_id
            browser['view_by']="news"
            browser.submit_selected()
            response = browser.page
            debugPrint("Searching for video_id")
            debugPrint(artist_id+"-"+video_id)
            tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
            for table in tables:
                img=str(table.find("img")['src'])
                debugPrint(f"Image:{str(img)}")
                if (f"/{artist_id}-{video_id}" in img) and img.endswith(("vg.jpg","hs.jpg")):
                    debugPrint("Found a single match video!")
                    # Extract data from this single result
                    ret = extract_info(table)
                    break
            else:
                sys.stderr.write("0 matches found! Checking offset")
                pages=int(response.find_all("a", class_="pagging_nonsel")[-1].get_text())
                if pages:
                    for offset in range(10,pages*10,10):
                        browser.open("https://ifeelmyself.com/public/main.php?page=search_results&offset="+str(offset))
                        response = browser.page
                        tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                        for table in tables:
                            img=str(table.find("img"))
                            debugPrint(f"Image:{img}")
                            if (f"/{video_id}/{artist_id}-" in img) and img.endswith(("vg.jpg","hs.jpg")):
                                ret = extract_info(table)
                                break
                else:
                    sys.stderr.write("0 matches found!, check your filename")

        else:
            debugPrint("Name changed after downloading")
            filename = filename.lower()
            extract_from_filename = re.match(r"^([0-9\.]{6,10})?(?<title>.+)\s(?<artist>\w+)(\.mp4)?$",filename)
            if extract_from_filename:
                title = extract_from_filename.group('title')
            #if date:
            #    date_dbY = datetime.strptime(date, '%d.%m.%Y').date().strftime('%d %b %Y')
            #    month = datetime.strptime(date, '%d.%m.%Y').date().strftime('%B')
            #    year = datetime.strptime(date, '%d.%m.%Y').date().strftime('%Y')
            #    debugPrint("Date: "+date_dbY)
                if title:
                    title = title.lower().replace("ifeelmyself","")
                    title = title.replace("-","")
                    title = title.replace("by", "")
                    debugPrint(f"Title: {title}")
                browser.open("https://ifeelmyself.com/public/main.php?page=search")
                browser.select_form()
                debugPrint("Searching..")
                browser['keyword']=title
                browser['view_by']="news"
                browser.submit_selected()
                response = browser.page
                #Obtaining and counting the results. Ideally you only have a single result
                matches=response.find_all("a", href='javascript:;') #This a href javascript contains all the titles
                if len(matches)==1:
                    debugPrint("Found a single match!")
                    table = response.find(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                else:
                    if len(matches)==0:
                        sys.stderr.write("0 matches found! Check filename")
                        print("{}}")
                        exit
                    if len(matches)>1:
                        debugPrint("Multiple videos found, maybe refine search term?")
                        index = [i for i, s in enumerate(matches) if title in str(s)]
                        tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                        table=tables[0] #Getting first
                if table:
                    ret = extract_info(table)
            else:
                debugPrint("Not a supported filename")
                print("{}")
                exit
    return ret

# read the input
i = readJSONInput()
sys.stderr.write(json.dumps(i))

if sys.argv[1] == "query":
    ret = scrapeScene(i['title'],i['date'],i['url'])
    print(json.dumps(ret))

if sys.argv[1] == "url":
    ret = scrapeScene(filename=None,date=None,url=i['url'])
    print(json.dumps(ret))
