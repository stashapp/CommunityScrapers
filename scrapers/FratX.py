import base64
from datetime import datetime
import json
import re
import sys
# extra modules below need to be installed
try:
    from py_common import log as stash_log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup4 package. (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4", file=sys.stderr)
    sys.exit()
try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests package. (https://pypi.org/project/requests/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

# NOTES:
# This scraper both scrapes scenes from exact URLs and attempts to
# lookup scenes based on title fragments.

# Scene by URL
# Items returned include:
# title: In many cases, the title listed on the current site is
#   different from the scene's original title recorded on IAFD.com, etc.
# date: The dates listed on the site are almost all altered to give the
#   appearence of a more regular update schedule. If uploading to
#   StashDB, use a more reliable source for the scene date and confirm
#   the original title.
# image: The background image from the video preview. This is usually, but
#   not always, the same as the preview image on the episodes listing page.

# Scene by Fragment
# There isn't a search or API on the site so a best-effort is made to
# guess the url slug based on the given title. Always confirm the returned
# scene matches your content. Many scenes (include all those before
# FX142A, 2017-10-11) have been removed from the site and can't be scraped.
# Many url slugs are still based on the original titles, so search on
# that if you know it.


def log(msg):
    stash_log.error(msg)
    ret_null = {}
    print(json.dumps(ret_null))
    sys.exit(1)


def scene_from_url(url, page=None):
    ret = {
        "studio": {"name": "FratX"},
        "url": url
    }

    if not page:
        page = requests.get(url)
        if page.status_code != 200:
            log(f"HTTP Errror: {page.status_code} returned when requesting {url}")

    page_soup = BeautifulSoup(page.text, "html.parser")

    # Try to get the image first
    try:
        stream_link = page_soup.find("iframe").attrs["src"]
        stream = requests.get(stream_link)
        stream_soup = BeautifulSoup(stream.text, "html.parser")
        script_text = stream_soup.find("script").text
        match_obj = re.search(r"token:\s+[\'|\"](.*)[\'|\"],", script_text)
        token = match_obj.group(1)
        vss = "https://videostreamingsolutions.net/api:ov-embed/parseToken?token="

        video_data = requests.get(vss + token)
        video_json = json.loads(video_data.text)
        img_path = video_json['_video']['xdo']['banner']['path']
        img_url = f"https://videostreamingsolutions.net{img_path}?tpl=large.jpg"
        img_b64 = base64.b64encode(requests.get(img_url).content)
        ret["image"] = "data:image/jpeg;base64," + img_b64.decode('utf-8')
    except Exception as img_e:
        stash_log.error(f"Unable to retrieve cover image due to exception:{img_e}")
        img_b64 = ""
        stash_log.info("Attempting to collect other metadata.")


    scene_data = page_soup.find(class_="episode-description")
    ret["title"] = scene_data.find("h1").text.strip().title()

    date_and_details = scene_data.find("p").text
    try:
        # try to get date from the paragraph text
        match_obj = re.search(r"(.*2\d{3})\s+-\s+(.*)", date_and_details)
        ret["details"] = match_obj.group(2).strip()

        date_str = match_obj.group(1)
        # Handle dates with 1st, 2nd, 3rd, 4th, etc.
        date_str = re.sub(r"(?<=\d)st|nd|rd|th", "", date_str).strip()
        ret["date"] = str(datetime.strptime(date_str, "%B %d, %Y").date())
    except AttributeError:
        # if no date is found use all text as details
        ret["details"] = date_and_details

    print(json.dumps(ret))


def guess_url_from_title(title):
    title = title.strip().lower()
    #remove file extension
    title = re.sub(r"\.[\da-z]{2,4}$", "", title)
    # clean the title of punctuation not likely to be in the url slug
    title = "".join(c for c in title if c.isalnum() or c.isspace())
    tokens = title.split()
    # remove studio names and production numbers
    tokens = [
        t for t in tokens if
        (
            t not in ['fraternityx', 'fratx', 'fx'] and
            not re.search(r"^(?:fx)?\d{3}\w?$", t)
        )
    ]
    if not tokens:
        return((None, None))

    base_url = "https://fratx.com/episode/"
    for connector in ["_", "-", ""]:
        url = base_url + connector.join(tokens)
        page = requests.get(url)
        if page.status_code == 200:
            return((url, page))

    # Some episodes' url slugs are just the longest word
    longest_word = sorted(tokens, key=lambda t: len(t))[-1]
    url = base_url + longest_word
    page = requests.get(url)
    if page.status_code == 200:
        return((url, page))

    return((None, None))


if sys.argv[1] == "scene_from_url":
    frag = json.loads(sys.stdin.read())
    if 'url' not in frag or not frag['url']:
        log('No URL entered.')
    scene_from_url(frag['url'])
elif sys.argv[1] == "scene_query":
    frag = json.loads(sys.stdin.read())
    if 'title' not in frag or not frag['title']:
        log('No URL entered.')
    scene_url, scene_page = guess_url_from_title(frag['title'])
    if scene_url and scene_page:
        scene_from_url(scene_url, page=scene_page)
    else:
        log(f"Couldn't find scene URL from '{frag['title']}'")
