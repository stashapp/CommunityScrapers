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
performers = []


def scrape_scene_img_and_tags(url):
    # Redirect to https://premiumbukkake.com/
    url = url.replace("free.", "")
    url = url.replace(".com/", ".com/tour2/")

    r = requests.get(url)

    soup = BeautifulSoup(r.text, 'html.parser')
    html_text = soup.find('div', attrs={'class': 'section tour'})

    # Get Image
    html_img = html_text.find('div', attrs={'class': 'slide_avatar'})
    scene_img = html_img.find('img').attrs['data-src']
    ret['image'] = f"https://premiumbukkake.com{scene_img}"

    html_info = html_text.find_all('div', attrs={'class': 'slide_info_row'})

    # Get Tags
    scene_tags = html_info[2].find_all('a')

    tags = []
    for tag in scene_tags:
        tags.append({'name': tag.text.strip()})
    ret['tags'] = tags

    # Get Performers
    scene_performers = html_info[1].find_all('a')

    for performer in scene_performers:
        performers.append(performer.text.strip())


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

    # Add Scene Details
    ret['title'] = json_script['name']
    ret['details'] = json_script['description']
    ret['date'] = json_script['uploadDate']

    scrape_scene_img_and_tags(url)

    # Add Studio Details
    ret['studio'] = {}
    ret['studio']['name'] = 'Premium Bukkake'

    # Add Performer Details
    ret['performers'] = {}

    perf = []
    for perf_name in performers:
        try:
            perf.append(scrape_performer(perf_name.strip()))
        except Exception:
            debug("[DEBUG] UNABLE TO SCRAPE PERFROMER")
            pass

    ret['performers'] = perf
    return ret


FRAGMENT = json.loads(sys.stdin.read())
SCENE_URL = FRAGMENT.get("url")

if SCENE_URL:
    debug(f"[DEBUG] Url Scraping: {SCENE_URL}")
    result = scrape_scene_url(SCENE_URL)
    print(json.dumps(result))
else:
    debug("[DEBUG] Nothing Provided To Scrape")
# Last Updated October 11, 2021
