import json
import re
import sys
import os

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args, dig
from py_common.config import get_config

ensure_deps = ["requests"]

import requests

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")

# fc2ppvdb_session has to be manually defined and passed in
# but is **extremely** long lived (token from 5mos ago still valid????)
config = get_config(
    default="""
# F12 -> Application -> Cookies

fc2ppvdb_session =
age_pass =
"""
)

def get_flaresolverr_soln(url):
    response = requests.post(FLARESOLVERR_URL, json={
        "cmd": "request.get",
        "url": url,
        "cookies": [
            { "name": "age_pass", "value": config["age_pass"] },
            { "name": "fc2ppvdb_session", "value": config["fc2ppvdb_session"] },
        ],
        "session_ttl_minutes": 5, # destroy session after 5 minutes
    })
    if response.status_code != 200:
        raise Exception(f"FlareSolverr request failed with status code {response.status_code}: {response.text}")
    return response.json().get("solution")

def scene_from_url(url: str) -> ScrapedScene:
    # if no config, throw error
    if not config["age_pass"] or not config["fc2ppvdb_session"]:
        log.error("Missing required cookies in config. Please update config and try again.")
        log.debug(f"age_pass cookie: {config['age_pass']}")
        log.debug(f"fc2ppvdb_session cookie: {config['fc2ppvdb_session']}")
        return {}

    log.debug("getting fresh cloudflare cookies")
    # get solution
    solution = get_flaresolverr_soln(url)

    # set cookies from solution
    session = requests.Session()
    # disable proxies (ASN blocked)
    session.proxies = {}
    session.trust_env = False
    # end disable proxies
    soln_cookies = solution.get("cookies", [])
    for cookie in soln_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])
    session.headers.update({"User-Agent": solution.get("userAgent")})

    # parse url to hit json endpoint, has to be done immediately
    article_id = url.rstrip("/").split("/")[-1]
    article_info_url = f"https://fc2ppvdb.com/articles/article-info?videoid={article_id}"

    log.debug("cookies set, hitting article info endpoint")
    # scrape main page, then info page with session cookies
    init = session.get(url)
    # check for login text
    if "https://fc2ppvdb.com/login" in init.text.lower():
        log.error("Prompted for login, likely due to invalid cookies. Check config and try again.")
        log.debug(f"age_pass cookie: {config['age_pass']}")
        log.debug(f"fc2ppvdb_session cookie: {config['fc2ppvdb_session']}")
        return {}
    try:
        resp_json = session.get(article_info_url).json()
    except json.JSONDecodeError:
        log.error("Invalid JSON response from article info endpoint. Try again.")
        return {}

    info = resp_json.get("article", {})

    scene: ScrapedScene = {}
    # images - all removed, even the uncensored ones
    scene["title"] = info.get("title", "").strip()
    scene["code"] = "FC2-PPV-" + str(info.get("video_id", ""))
    scene["date"] = info.get("release_date", "")
    scene["studio"] = { "name": dig(info, "writer", "name") }
    scene["tags"] = [{ "name": tag.get("name", "").strip() } for tag in info.get("tags", [])]
    scene["performers"] = [{ "name": performer.get("name", "").strip() } for performer in info.get("actresses", [])]
    return scene

def url_from_frag(files) -> str:
    filename = files[0].get("path") if files else None
    basename = os.path.basename(filename) if filename else None
    if not basename:
        return ""
    code = re.match(r"(\d{5,})", basename)
    match = code.group(1) if code else None
    if match:
        return f"https://fc2ppvdb.com/articles/{match}"
    return ""

if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            files = args.get("files", [])
            url = url_from_frag(files)
            if url:
                result = scene_from_url(url)
            else:
                log.error("Could not extract article ID from filename")
                sys.exit(1)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))