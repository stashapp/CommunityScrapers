#this scraper scrapes title and uses it to search the site and grab a cover from the search results, among other things
import base64
import datetime
import json
import re
import sys
import urllib.parse
# extra modules below need to be installed

try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()
    
try:
    from lxml import html, etree
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()

STUDIO_MAP = {
    'https://missax.com/tour/': 'MissaX',
    'https://allherluv.com/tour/': 'All Her Luv',
}

proxy_list = {
    }


def log(*s):
    print(*s, file=sys.stderr)
    ret_null = {}
    print(json.dumps(ret_null))
    sys.exit(1)

def scrape_url(scraper, url):
    try:
        scraped = scraper.get(url, proxies=proxy_list)
    except:
        log("scrape error")
    if scraped.status_code >= 400:
        log('HTTP Error: %s' % scraped.status_code)
    return html.fromstring(scraped.content)

def scrape_scene_page(url): #scrape the main url
    tree = scrape_url(scraper, url) #get the page
    title = tree.xpath('//p[@class="raiting-section__title"]/text()')[0].strip() #title scrape
    date = tree.xpath('//p[@class="dvd-scenes__data"][1]/text()[1]')[0] #get date
    date = re.sub("(?:.+Added:\s)([\d\/]*).+", r'\g<1>', date).strip() #date cleanup
    date = datetime.datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d") #date parse
    studio = tree.xpath('//base/@href')[0].strip() #studio scrape
    studio = STUDIO_MAP[studio] # studio map
    performers = tree.xpath('//p[@class="dvd-scenes__data"][1]/a/text()') #performers scrape
    tags = tree.xpath('//p[@class="dvd-scenes__data"][2]/a/text()') #tags scrape
    details = tree.xpath('//p[count(preceding-sibling::p[@class="dvd-scenes__title"])=1]/text()|//p[@class="text text--marg"]/strong/text()|//p/em/text()') #details scrape
    details = ''.join(details) #join details
    details = '\n'.join(' '.join(line.split()) for line in details.split('\n')) #get rid of double spaces
    details = re.sub("\r?\n\n?", r'\n', details) #get rid of double newlines
    datauri = "data:image/jpeg;base64,"
    b64img = scrape_cover(scraper, studio, title)
    return output_json(title,tags,date,details,datauri,b64img,studio,performers)


def scrape_cover(scraper, studio, title):
    p = 1
    # loop throught search result pages until img found
    while True:
        url = 'https://'+studio.replace(" ", "")+'.com/tour/search.php?query='+urllib.parse.quote(title)+f'&page={p}'
        tree = scrape_url(scraper, url)
        if tree.xpath('//*[@class="errorMsg"]'):
            print("cover not found")
        else:
            try:
                imgurl = tree.xpath(f'//img[@alt="{title}"]/@src0_4x')[0]
                img = scraper.get(imgurl).content
                b64img = base64.b64encode(img)
                return b64img
            except:
                p+=1

def output_json(title,tags,date,details,datauri,b64img,studio,performers):
    return {
    'title': title,
    'tags': [{
        'name': x
    } for x in tags],
    'date': date,
    'details': details.strip(),
    'image': datauri + b64img.decode('utf-8'),
    'studio': {
        'name': studio
    },
    'performers': [{
        'name': x.strip()
    } for x in performers]
}



# frag = {"url": "https://allherluv.com/tour/trailers/Like-I-Do.html"}

frag = json.loads(sys.stdin.read())
if not frag['url']:
    log('No URL entered.')
url = frag["url"]

scraper = cloudscraper.create_scraper()
ret = scrape_scene_page(url)
print(json.dumps(ret))


# Based on PerfectGonzo scraper
# Last Updated September 11, 2022