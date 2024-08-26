import json
import re
import sys
import py_common.log as log

try:
    from requests import Session
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


ret = {}
s = Session()
s.headers['User-Agent'] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                           " (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")


def get_request(url):
    try:
        page = s.get(url, timeout=10)
        return page
    except Exception as e:
        log.error(f'Scrape error {e} for {url}')
        return


def scrape_scene_tags_and_performers(url):

    # Note this information is behind the paywall

    # Redirect to https://premiumbukkake.com/
    url = url.replace("free.", "")
    url = url.replace(".com/", ".com/tour2/")

    r = get_request(url)
    # Check if being redirected
    if not r.url == url:
        log.warning('Unable to scrape tags/performer from https://premiumbukkake.com')
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    html_text = soup.find('div', attrs={'class': 'section tour'})
    html_info = html_text.find_all('div', attrs={'class': 'slide_info_row'})

    # Add paywalled url
    ret['urls'] += [url]

    # Find the tag and performer rows by their title
    tags_row = performer_row = None
    for info_row in html_info:
        if "Pornstars:" in info_row.get_text():
            performer_row = info_row
        elif "Categories:" in info_row.get_text():
            tags_row = info_row

    # Get Tags
    if tags_row:
        ret['tags'] = [{'name': tag.text.strip()} for tag in tags_row.find_all('a')]

    # Get Performers
    if performer_row:
        performers = [performer.text.strip() for performer in performer_row.find_all('a')]
        perf = []
        for perf_name in performers:
            try:
                perf.append(scrape_performer(perf_name))
            except Exception:
                log.warning(f"[DEBUG] UNABLE TO SCRAPE PERFROMER {perf_name} ")
                pass
        ret['performers'] = perf


def scrape_performer(name):
    modified_name = name.replace(' ', '-')
    performer_url = f"https://premiumbukkake.com/tour2/models/{modified_name}.html"
    r = get_request(performer_url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Check for performer bio paywalled site
    if not (html_content := soup.find('div', attrs={'class': 'block-bio-content'})):
        return

    html_stats = soup.find('div', attrs={'class': 'block-bio-stats'}).find_all('dd')
    html_bio = soup.find('div', attrs={'class': 'block-bio-text'}).find('p')
    html_bio = '\n'.join([x.get_text() for x in html_bio if x.get_text() !=''])
    html_img = soup.find('div', attrs={'class': 'block-bio-img'}).find('img').attrs['data-src']

    perfomer_details = {'name': name, 'gender': 'Female', 'height': html_stats[1].getText(),
                        'measurements': html_stats[2].getText().split()[0], 'url': performer_url,
                        'images': [f'https:{html_img}'], 'details': html_bio}

    return perfomer_details


def scrape_scene_url(url):
    # Check if scene is removed
    if not (r := get_request(url)):
        log.warning('Unable to retrieve scene details. Wrong URL or scene is removed?')
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    script_text = soup.find('script', attrs={'type': 'application/ld+json'})

    # Grab scene description first, grab rest later
    details = re.search(r".+?(?:\"description\":\s\")([^\"]+)", str(script_text)).group(1)

    # Remove leading/trailing/double whitespaces
    ret['details'] = '\n'.join(
        [
            ' '.join([s for s in x.strip(' ').split(' ') if s != ''])
            for x in ''.join(details).split('\n')
        ]
    )

    # Now remove excessive linebreaks and parse it as json
    json_script = json.loads(script_text.string.replace('\n', ''))

    # Add Studio Details
    ret['studio'] = {}
    ret['studio']['name'] = 'Premium Bukkake'

    # Populate URLs
    ret['urls'] = [url]

    # Add Scene Details
    ret['title'] = json_script['name']
    ret['date'] = json_script['uploadDate']
    ret['image'] = json_script['thumbnailUrl']

    # Get tags and performer from the paywalled site
    ret['performers'] = ret['tags'] = []
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
    log.debug(f"[DEBUG] Url Scraping: {SCENE_URL}")
    if (result := scrape_scene_url(SCENE_URL)):
        # log.debug(result)
        print(json.dumps(result))
    else:
        print("null")
