import json
from base64 import b64encode
import sys
import string
import mechanicalsoup
from requests.sessions import session
import regex as re
import requests
from datetime import datetime

def readJSONInput():
	input = sys.stdin.read()
	return json.loads(input)

def extract_info(table):
    description=table.find(class_= ["blog_wide_new_text","entryBlurb"]).get_text(strip=True).replace("\x92","'")
    date = table.find(class_="entryDatestamp").get_text(strip=True) #This is a BeautifulSoup element
    performer = table.find(class_= ["entryHeadingFlash","entryHeading"]).find_all("a")[1].get_text().replace("_"," ")
    performer = str(performer)
    debugPrint(performer)
    date = datetime.strptime(date, '%d %b %Y').date().strftime('%Y-%m-%d') #Convert date to ISO format
    cover_url=str(table.find("img")['src'])
    title = table.find(class_= ["entryHeadingFlash","entryHeading"]).find('a').get_text()
    media_id = re.search("\/(\d{4,5})\/",cover_url)
    media_id = media_id[0].replace("/","")
    artist_id = re.search("(f\d{3,5})",cover_url).group(0)
    tags = table.find_all(class_="tags-list-item-tag")
    tag_list = []
    for tag in tags:
        tag_list.append({"name": tag.get_text()})
    debugPrint(str(tag_list))
    json_info = {"title": title, "performers": [{"name": performer}], "studio": {"name": "I Feel Myself"}, "tags": tag_list, "date":date, "image": cover_url,"details": description, "url": "https://ifeelmyself.com/public/main.php?page=flash_player&out=bkg&media_id="+media_id+"&artist_id="+artist_id}
    return json_info

def debugPrint(t):
    sys.stderr.write(t + "\n")

def scrapeScene(filename,date,url):
    ret = []
    browser = mechanicalsoup.StatefulBrowser(session=None)
    browser.open("https://ifeelmyself.com/public/main.php")
    cookie_obj = requests.cookies.create_cookie(name='tags_popup_shown', value='true', domain='ifeelmyself.com')
    browser.session.cookies.set_cookie(cookie_obj)
    if url:
      debugPrint("Url found, using that to scrape")
      browser.open(url)
      response = browser.page
      table = response.find(class_ = ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
      ret = extract_info(table)
    else: 
        debugPrint("Analyzing filename...")
        artist_id=re.search("(f\d{3,5})",filename.lower()).group(0)
        if artist_id:
            video_id = re.search("\-(\d{1,})",filename.lower()).group(0).replace("-","")
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
                debugPrint(str(img))
                if (artist_id+"-"+video_id+"vg.jpg" in img)|(artist_id+"-"+video_id+"hs.jpg" in img):
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
                            debugPrint(img)
                            if (artist_id+"-"+video_id+"vg.jpg" in img)|(artist_id+"-"+video_id+"hs.jpg" in img):
                                ret = extract_info(table)
                                break
                else:
                    sys.stderr.write("0 matches found!, check your filename")

        else:
            debugPrint("Name changed after downloading")
            filename = filename.lower()
            extract_from_filename = re.match(r"^([0-9\.]{6,10}|)(?<title>.+)\s(?<artist>\w+)(\.mp4|)$",filename)
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
                debugPrint("Title: "+title)
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
                    exit
                if len(matches)>1:
                    debugPrint("Multiple videos found, maybe refine search term?")
                    index = [i for i, s in enumerate(matches) if title in str(s)]
                    tables = response.find_all(class_= ["blog_wide_news_tbl entry ppss-scene","entry ppss-scene"])
                    table=tables[0] #Getting first
            ret = extract_info(table)
    return ret

# read the input 
i = readJSONInput()
sys.stderr.write(json.dumps(i))

if sys.argv[1] == "query":    
    ret = scrapeScene(i['title'],i['date'],i['url'])
    print(json.dumps(ret))

