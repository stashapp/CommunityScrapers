import json
import sys

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup module. (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4", file=sys.stderr)
    sys.exit()

# Print debug message.
PRINT_DEBUG = True

def debug(q):
    q = str(q)
    if "[DEBUG]" in q and PRINT_DEBUG == False:
        return
    print(q, file=sys.stderr)

ret = {}

def scrape_scene_tags_and_performers(url):

    # Note this information is behind the paywall 

    # Redirect to https://premiumbukkake.com/
    url = url.replace("free.", "")
    url = url.replace(".com/", ".com/tour2/")

    r = requests.get(url)

    soup = BeautifulSoup(r.text, 'html.parser')
    html_text = soup.find('div', attrs={'class': 'section tour'})
    html_info = html_text.find_all('div', attrs={'class': 'slide_info_row'})

    # Find the tag and performer rows by their title
    tags_row = None
    performer_row = None
    for info_row in html_info:
        if "Pornstars:" in info_row.get_text():
            performer_row = info_row
        elif "Categories:" in info_row.get_text():
            tags_row = info_row

    # Get Tags
    if tags_row:
        scene_tags = tags_row.find_all('a')
        tags = []
        for tag in scene_tags:
            tags.append({'name': tag.text.strip()})
        ret['tags'] = tags

    # Get Performers
    if performer_row:
        scene_performers = performer_row.find_all('a')
        performers = []
        for performer in scene_performers:
            performers.append(performer.text.strip())
        perf = []
        for perf_name in performers:
            try:
                perf.append(scrape_performer(perf_name.strip()))
            except Exception:
                debug(f"[DEBUG] UNABLE TO SCRAPE PERFROMER {perf_name.strip()} ")
                pass
        ret['performers'] = perf


def scrape_performer(name):
    modified_name = name.replace(' ', '-')
    performer_url = f"https://premiumbukkake.com/tour2/models/{modified_name}.html"
    r = requests.get(performer_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    html_content = soup.find('div', attrs={'class': 'block-bio-content'})
    html_stats = soup.find('div', attrs={'class': 'block-bio-stats'}).find_all('dd')
    html_bio = soup.find('div', attrs={'class': 'block-bio-text'}).find('p').getText()
    html_img = soup.find('div', attrs={'class': 'block-bio-img'}).find('img').attrs['data-src']

    perfomer_details = {'name': name, 'gender': 'Female', 'height': html_stats[1].getText(),
                        'measurements': html_stats[2].getText(), 'url': performer_url,
                        'image': f"http{html_img}", 'details': html_bio}

    return perfomer_details


def scrape_scene_url(url):
    r = requests.get(url)

    soup = BeautifulSoup(r.text, 'html.parser')
    script_text = soup.find('script', attrs={'type': 'application/ld+json'}).string.replace("\n", '')
    json_script = json.loads(script_text)
    
    # Add Studio Details
    ret['studio'] = {}
    ret['studio']['name'] = 'Premium Bukkake'

    # Add Scene Details
    ret['title'] = json_script['name']
    ret['details'] = json_script['description']
    ret['date'] = json_script['uploadDate']
    ret['image'] = json_script['thumbnailUrl']

    # Get tags and performer from the paywalled site    
    ret['performers'] = []
    ret['tags'] = []
    scrape_scene_tags_and_performers(url)

    # Extract actor details in free site in case paywalled site does not have information
    # Actor field comma delimited and starts with actors names, ends with scene type tag.
    perf = []        
    actors = json_script['actor'].split(',')
    tag = actors.pop()

    if not ret['performers']:
        # No Performer(s) in paywalled site, get from free site
        for actor in actors:
            perf.append({ 'name': actor.strip() })
        ret['performers'] = perf

    if not ret['tags']:
        # No tags in paywalled site, get classification tag from free site
        ret['tags'] = [ { 'name': tag.strip() } ]

    return ret


FRAGMENT = json.loads(sys.stdin.read())
SCENE_URL = FRAGMENT.get("url")

if SCENE_URL:
    debug(f"[DEBUG] Url Scraping: {SCENE_URL}")
    result = scrape_scene_url(SCENE_URL)
    print(json.dumps(result))
else:
    debug("[DEBUG] Nothing Provided To Scrape")

