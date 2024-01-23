import html
import json
import os
import re
import sys

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo!"
        " (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit(1)

# make sure to install below modules if needed
try:
    import requests
except ModuleNotFoundError:
    log.error(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)"
    )
    log.error("Run this command in a terminal (cmd): python -m pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    log.error(
        "You need to install the BeautifulSoup module. (https://pypi.org/project/beautifulsoup4/)"
    )
    log.error(
        "Run this command in a terminal (cmd): python -m pip install beautifulsoup4"
    )
    sys.exit(1)


def parse_url(url):
    if m := re.match(r"https?://tour\.((\w+)\.com)/scenes/(\d+)/([a-z0-9-]+)", url):
        return m.groups()
    log.error("The URL could not be parsed")
    sys.exit(1)


def make_request(request_url):
    try:
        r = requests.get(
            request_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
                "Referer": request_url,
            },
            timeout=(3, 6),
        )
    except requests.exceptions.RequestException as e:
        log.error(f"Request to '{request_url}' failed: {e}")
        exit(1)

    if r.status_code != 200:
        log.error(f": {r.status_code}")
        exit(1)
    return BeautifulSoup(r.text, "html.parser")


if __name__ == "__main__":
    fragment = json.loads(sys.stdin.read())

    if not (url := fragment["url"]):
        log.error("No URL entered.")
        sys.exit(1)
    log.debug(f"Scraping URL: {url}")

    soup = make_request(url)
    props = soup.find("script", {"type": "application/json"})
    if not props:
        log.error("Could not find JSON in page")
        sys.exit(1)

    props = json.loads(props.text)
    content = props["props"]["pageProps"]["content"]

    with open("debug.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(content, indent=2))

    if not (scene_id := content.get("id")):
        log.error("Could not find scene ID")
        sys.exit(1)
    log.info(f"Scene {scene_id} found")

    scene = {
        "code": str(scene_id),
    }

    if title := content.get("title"):
        scene["title"] = html.unescape(title)
    if date := content.get("publish_datedate"):
        from datetime import datetime

        scene["date"] = datetime.strptime(date[:10], "%Y/%m/%d").strftime("%Y-%m-%d")
    if description := content.get("description"):
        scene["details"] = html.unescape(description).replace("\u00a0", " ")
    if site := content.get("site"):
        scene_studio = site
        scene["studio"] = {"name": scene_studio}
    if models := content.get("models"):
        scene["performers"] = [{"name": x} for x in models]
    if tags := content.get("tags"):
        scene["tags"] = [{"name": x} for x in tags]
    if scene_cover := content.get("thumb"):
        if not scene_cover.endswith(".gif"):
            scene["image"] = scene_cover
        elif alternative_covers := content.get("thumbs"):
            # We don't want gifs
            scene["image"] = alternative_covers[0]
    print(json.dumps(scene))
