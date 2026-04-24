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
xsrf_token = 
"""
)

def check_login(text):
    if 'https://fc2ppvdb.com/login' in text.lower():
        log.error("Login prompt detected. Check cookies and try again.")
        log.error("fc2ppv_session ends with %3D, age_pass with %3D%3D")
        log.debug(f"age_pass cookie: {config['age_pass']}")
        log.debug(f"fc2ppvdb_session cookie: {config['fc2ppvdb_session']}")
        log.debug(f"XSRF-TOKEN cookie: {config['xsrf_token']}")
        return True
    return False

def get_flaresolverr_soln(url):
    response = requests.post(FLARESOLVERR_URL, json={
        "cmd": "request.get",
        "url": url,
        "cookies": [
            { "name": "age_pass", "value": config["age_pass"] },
            { "name": "fc2ppvdb_session", "value": config["fc2ppvdb_session"] },
            { "name": "XSRF-TOKEN", "value": config["xsrf_token"] },
        ],
        "session_ttl_minutes": 5, # destroy session after 5 minutes
    })
    if response.status_code != 200:
        raise Exception(f"FlareSolverr request failed with status code {response.status_code}: {response.text}")
    return response.json().get("solution")

def scene_from_url(url: str) -> ScrapedScene:
    # if no config, throw error
    if not config["age_pass"] or not config["fc2ppvdb_session"] or not config["xsrf_token"]:
        log.error("Missing required cookies in config. Please update config and try again.")
        log.debug(f"age_pass cookie: {config['age_pass']}")
        log.debug(f"fc2ppvdb_session cookie: {config['fc2ppvdb_session']}")
        log.debug(f"XSRF-TOKEN cookie: {config['xsrf_token']}")
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

    # add get solution cookies
    session.cookies.set("age_pass", config["age_pass"], domain="fc2ppvdb.com", path="/")
    session.cookies.set("fc2ppvdb_session", config["fc2ppvdb_session"], domain="fc2ppvdb.com", path="/")
    session.cookies.set("XSRF-TOKEN", config["xsrf_token"], domain="fc2ppvdb.com", path="/")

    # parse url to hit json endpoint, has to be done immediately
    article_id = url.rstrip("/").split("/")[-1]
    article_info_url = f"https://fc2ppvdb.com/articles/article-info?videoid={article_id}"

    log.debug("cookies set, hitting article info endpoint")
    # scrape main page, then info page with session cookies
    init = session.get(url)
    # check for CF ASN block
    if init.status_code == 403 and "1005" in init.text:
        log.error("Cloudflare ASN block detected. This scraper will not work from this IP address.")
        return {}
    if check_login(init.text):
        return {}
    # get actual info afterwards
    try:
        info_res = session.get(article_info_url)
        if check_login(info_res.text):
            return {}
        resp_json = info_res.json()
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