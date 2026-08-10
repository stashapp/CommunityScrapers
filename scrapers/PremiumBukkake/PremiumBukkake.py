import json
import re
import sys
import py_common.log as log
import datetime

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


free_url = ""
paywall_url = ""
members_url = ""
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

def generate_free_url(pagename):
    pagename = re.sub(r'-first-camera', '', pagename, flags=re.IGNORECASE)
    pagename = re.sub(r'-second-camera', '', pagename, flags=re.IGNORECASE)
    return f"https://free.premiumbukkake.com/updates/{pagename}.html"

def generate_members_url(pagename):
    return f"https://members.premiumbukkake.com/scenes/{pagename}_vids.html"

def generate_paywall_url(pagename):
    return f"https://premiumbukkake.com/tour2/updates/{pagename}.html"

def generate_site_urls(given_url):
    global paywall_url, free_url, members_url
    if "free.premiumbukkake.com" in given_url:
            # Extract page name from something like "mypage.html"
            match = re.search(r'/([^/]+)\.html$', given_url)
            if match:
                pagename = match.group(1)
            else:
                raise ValueError("Could not extract page name from free URL.")
            paywall_url = generate_paywall_url(pagename)
            members_url = generate_members_url(pagename)
            free_url = given_url
        
    # Check for members domain
    elif "members.premiumbukkake.com" in given_url:
        # Extract base page name from something like "mypage_test.html"
        match = re.search(r'/([^/]+)_vids\.html$', given_url)
        if match:
            pagename = match.group(1)
        else:
            raise ValueError("Could not extract page name from members URL.")
        paywall_url = generate_paywall_url(pagename)
        free_url = generate_free_url(pagename)
        members_url = given_url

    # Check for main domain (note: exclude other subdomains)
    elif "premiumbukkake.com/tour2" in given_url:
        # For main domain, expect a URL like .../mypage.html (note: might have extra path parts before 'updates')
        match = re.search(r'/([^/]+)\.html$', given_url)
        if match:
            pagename = match.group(1)
        else:
            raise ValueError("Could not extract page name from main URL.")
        free_url = generate_free_url(pagename)
        members_url = generate_members_url(pagename)
        paywall_url = given_url

def get_request(url):
    try:
        page = s.get(url, timeout=10)
        return page
    except Exception as e:
        log.error(f'Scrape error {e} for {url}')
        return

def scrape_info_from_paywalled():
    r = get_request(paywall_url)
    # Check if being redirected
    if not r.url == paywall_url:
        log.warning(f"Unable to scrape tags/performer from {paywall_url}")
        return False

    soup = BeautifulSoup(r.text, 'html.parser')
    html_text = soup.find('div', attrs={'class': 'section tour'})
   
    # Get studio code - contained within the image URLS in the format PB_nnn
    image_url = html_text.find('div', class_='slide_avatar').find('img')['data-src']    
    if image_url:    
        base_url = image_url.rsplit('/', 1)[0]
        image_url = f"https://premiumbukkake.com{base_url}/0.jpg"
        ret['image'] = image_url
        ret['code'] = re.search(r'PB_\d+', image_url).group(0)
    
    ret['title'] = html_text.find('h2', class_='slide_title').text

    # Details are not always full on this site, so overwritten by free site if exists
    ret['details'] = html_text.find('p', class_='slide_text').text

    # Get row information
    html_info = html_text.find_all('div', attrs={'class': 'slide_info_row'})

    # Find the tag and performer rows by their title
    tags_row = performer_row = None
    for info_row in html_info:
        if "Pornstars:" in info_row.get_text():
            performer_row = info_row
        elif "Categories:" in info_row.get_text():
            tags_row = info_row
        elif "Posted" in info_row.get_text():
            date_line = info_row.find('span').text
            date_str = date_line.replace('Posted ', '')
            date_obj = datetime.datetime.strptime(date_str, '%B %d, %Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            ret['date'] = formatted_date

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
        if perf and perf[0] is not None:    
            ret['performers'] = perf
    
    # Add paywalled url
    ret['urls'] = [paywall_url, members_url]
    return True


def scrape_info_from_free():
    # Check if scene is removed
    if not (r := get_request(free_url)):
        log.warning('Unable to retrieve scene details from free site, may not exist')
        return False

    soup = BeautifulSoup(r.text, 'html.parser')
    script_text = soup.find('script', attrs={'type': 'application/ld+json'})

    # Grab scene description first, grab rest later
    details = re.search(r".+?(?:\"description\":\s\")([^\"]+)", str(script_text)).group(1)

    # Remove leading/trailing/double whitespaces, details longer on free site
    ret['details'] = '\n'.join(
        [
            ' '.join([s for s in x.strip(' ').split(' ') if s != ''])
            for x in ''.join(details).split('\n')
        ]
    )

    # Now remove excessive linebreaks and parse it as json
    json_script = json.loads(script_text.string.replace('\n', ''))

    # Release Date on free site can be off by a few days so only use if paywalled site does not have it
    if not ret['date']:
        ret['date'] = json_script['uploadDate']

    # Get image if paywalled site not found
    if not ret['image']:
        ret['image'] = json_script['thumbnailUrl']

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

    ret['urls'] += [free_url]

    return True


FRAGMENT = json.loads(sys.stdin.read())
SCENE_URL = FRAGMENT.get("url")

def scrape_scene(given_url):

    # Generate all of the 3 URL's from the given URL
    generate_site_urls(given_url)

    ret['studio'] = {}
    ret['studio']['name'] = 'Premium Bukkake'
    ret['urls'] = []
    ret['performers'] = []
    ret['tags'] = []
    ret['image'] = ''
    ret['date'] = ''

    # Get info from the paywalled site first as the most accurate source
    # for most details and only source for some scenes
    scrape_info_from_paywalled()

    # Get additional info from the free site if the page exists
    scrape_info_from_free()

    return ret


if SCENE_URL:
    log.debug(f"[DEBUG] Url Scraping: {SCENE_URL}")
    
    if (result := scrape_scene(SCENE_URL)):
        # log.debug(result)
        print(json.dumps(result))
    else:
        print("null")
