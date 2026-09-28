"""JAVLibrary python scraper"""
import json
import re
import sys
from typing import List
from urllib.parse import urlparse, urlunparse

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! "
          "(CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.proxy import StashRequests
from py_common.ratelimit import get_limiter_session
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("lxml")
import lxml.html

def merge_config_data(base, local, replace_all=False):
    if replace_all:
        return local if local is not None else base
    if isinstance(base, list):
        return list(set(base) | set(local or []))
    if isinstance(base, dict):
        return base | (local or {})
    return local if local is not None else base

import base_config
try:
    import local_config
    replace_all = getattr(local_config, 'REPLACE_ALL', False)
    FIXED_TAGS = merge_config_data(base_config.FIXED_TAGS, getattr(local_config, 'FIXED_TAGS', None), replace_all)
    IGNORE_TAGS = merge_config_data(base_config.IGNORE_TAGS, getattr(local_config, 'IGNORE_TAGS', None), replace_all)
    REPLACE_TITLE = merge_config_data(base_config.REPLACE_TITLE, getattr(local_config, 'REPLACE_TITLE', None), replace_all)
except ImportError:
    FIXED_TAGS = base_config.FIXED_TAGS
    IGNORE_TAGS = base_config.IGNORE_TAGS
    REPLACE_TITLE = base_config.REPLACE_TITLE

config = get_config(
    default="""
language = en
title_template = {code}
details_template = {title}
import_performer_aliases = False
tag_separators =
"""
)

# which hostname will be stored as scene url
PERMALINK_HOSTNAME = "www.javlibrary.com"
PERMALINK_BASE_URL = f"https://{PERMALINK_HOSTNAME}"

# only crawl these hostnames
ALLOWED_HOSTNAMES = ["www.javlibrary.com", "javlib.com", "www.e100k.com"]
# hostname use order in case of get failures
HOST_QUERY_ORDER = ["www.javlibrary.com", "www.e100k.com"]

LANGUAGE = config['language']

XPATH_SEARCH = {}
XPATH_SEARCH['url'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@href'
XPATH_SEARCH['title'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@title'
XPATH_SEARCH['image'] = '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]//img/@src'

XPATH_SCENE = {}
XPATH_SCENE["code"] = '//div[@id="video_id"]//td[@class="text"]/text()'
XPATH_SCENE["title"] = '//div[@id="video_title"]/h3/a/text()'
XPATH_SCENE["url"] = '//meta[@property="og:url"]/@content'
XPATH_SCENE["date"] = '//div[@id="video_date"]//td[@class="text"]/text()'
XPATH_SCENE["director"] = '//div[@id="video_director"]//td[@class="text"]/span[@class="director"]/a/text()'
XPATH_SCENE["tags"] = '//div[@id="video_genres"]//span[@class="genre"]/a/text()'
XPATH_SCENE["cast_spans"] = '//div[@id="video_cast"]//span[@class="cast"]'
XPATH_SCENE["studio"] = '//div[@id="video_maker"]//span[@class="maker"]/a/text()'
XPATH_SCENE["label"] = '//td[@class="header" and text()="Label:"]/following-sibling::td/span[@class="label"]/a/text()'
XPATH_SCENE["image"] = '//div[@id="video_jacket"]/img/@src'

class ResponseHTML:
    def __init__(self):
        content = ""
        status_code = 0
        url = ""


def bypass_protection(scraper:StashRequests, url) -> ResponseHTML:

    response_html = ResponseHTML()
    for site in HOST_QUERY_ORDER:
        url_n = urlunparse(urlparse(url)._replace(netloc=site))

        try:
            response = scraper.get(url_n, flaresolverrParameters={"cookies": [{"name": "over18", "value": "18"}]})

            response_html.content = response.text
            response_html.status_code = response.status_code
            response_html.url = response.url

        except Exception as exc_req:
            log.warning(f"Exception \"{exc_req}\" while checking protection for {site}")
            continue

        if response_html.status_code == 200:
            # log.info(f"[{site}] Used this site for scraping | status code: ({response_html.status_code})")
            return response_html
        elif response_html.url.endswith("maintenance.html"):
            log.error(f"[{site}] Maintenance")
        else:
            log.error(f"[{site}] Other issue ({response_html.status_code})")

    return None

def send_request(scraper:StashRequests, url) -> ResponseHTML:
    url_domain = urlparse(url).netloc
    response = None
    if url_domain in ALLOWED_HOSTNAMES:
        response = bypass_protection(scraper, url)
        if response:
            return response
        else:
            print("{}")
            sys.exit(1)
    else:
        log.warning(f"Domain is not allowed {url}");
        print("{}")
        sys.exit(1)

def cleanup_title(title) -> str:
    original = title
    for old, new in REPLACE_TITLE.items():
        title = title.replace(old, new)

    if title != original:
        title = title.strip()
        log.info(f"Title was cleaned: {title}")

    return title


def build_performer_list(result) -> List[ScrapedPerformer]:
    cast_spans = result["cast_spans"]
    performers = []

    for cast_span in cast_spans:
        name_elem = cast_span.xpath('.//a/text()')
        name = name_elem[0] if name_elem else ""

        performer: ScrapedPerformer = {
            "name": name,
            "gender": "FEMALE"
            }
        if config['import_performer_aliases']:
            alias_elems = cast_span.xpath('.//span[starts-with(@id, "alias")]/text()')
            aliases = [a.strip().strip("()") for a in alias_elems]
            if aliases:
                performer['aliases'] = ",".join(aliases)

        performers.append(performer)
    return performers


def build_tag_list(result) -> List[ScrapedTag]:
    original_tags = result.get('tags', [])
    tags = []
    for tag_name in original_tags:
        if tag_name and tag_name not in IGNORE_TAGS:
            tags.append({"name": tag_name})

    if FIXED_TAGS:
        for tag_name in FIXED_TAGS:
            tags.append({"name": tag_name})

    if config['tag_separators']:
        trans_table = str.maketrans(config['tag_separators'], ',' * len(config['tag_separators']))
        tags = [
            {"name": tag_name.strip()}
            for tag_dict in tags
            for tag_name in (tag_dict["name"].translate(trans_table).split(","))
            if tag_name.strip()
        ]

    return tags


def print_search_for_scenes(scraper:StashRequests, keyword, single_result: bool = False):
    """
    Makes a search to the "vl_searchbyid.php" endpoint and prints the results.

    Typically used to find multiple results where output is in an array, but can also be used
    when only single ScrapedScene is wanted by calling with single_result = true.
    """
    response_html = send_request(scraper, f"https://www.javlibrary.com/{LANGUAGE}/vl_searchbyid.php?keyword={keyword}")

    #if f"/{LANGUAGE}/jav" in response_html.url or "?v=jav" in response_html.url:
    # movie page names start with "jav"
    if f"/{LANGUAGE}/jav" in response_html.url:
        # log.debug(f"Scraping the movie page directly ({response_html.url})")
        scene = scene_from_html(response_html)
        if not single_result:
            scene = [scene]
        print_json(scene)

    else:
        tree = lxml.html.fromstring(response_html.content)
        url = tree.xpath(XPATH_SEARCH['url'])  # ./javme5it6a
        title = tree.xpath(XPATH_SEARCH['title'])
        image = tree.xpath(XPATH_SEARCH['image'])  # //pics.dmm.co.jp/mono/movie/adult/13gvh029/13gvh029ps.jpg
        lst = []
        for count, _ in enumerate(url):
            lst.append({
                "title": title[count],
                "url": f"{PERMALINK_BASE_URL}/{LANGUAGE}/{url[count].replace('./', '')}",
                "image": re.sub("^//","https://",image[count])
            })
        log.debug(f"Search found {len(lst)} scene(s)")
        print_json(lst)


def print_scene_by_url(scraper:StashRequests, scene_url):
    response_html = send_request(scraper, scene_url)
    print_json(scene_from_html(response_html))


def scene_from_html(html: ResponseHTML) -> ScrapedScene:
    result = {}
    tree = lxml.html.fromstring(html.content)
    # is not None for removing the FutureWarning...
    if tree is not None:
        # Get data from javlibrary
        for key, value in XPATH_SCENE.items():
            result[key] = tree.xpath(value)

        # PostProcess
        if result.get("image"):
            result["image"] = result["image"][0].replace("http:", "https:")
            if "now_printing.jpg" in result["image"] or "noimage" in result["image"]:
                # https://pics.dmm.com/mono/movie/n/now_printing/now_printing.jpg
                # https://pics.dmm.co.jp/mono/noimage/movie/adult_ps.jpg
                log.warning(f"Image was deleted or failed to load ({result['image']})")
                result["image"] = None
        if result.get("url"):
            result["url"] = "https:" + result["url"][0]
            result["url"] = urlunparse(urlparse(result["url"])._replace(netloc=PERMALINK_HOSTNAME))
        if result.get("title"):
            # original title is "JAV-ID Title", remove the ID, we have it in 'code' already
            result["title"] = re.sub(r"^(.*? )", "", result["title"][0]).strip()
        if result.get("director"):
            result["director"] = result["director"][0]
        if result.get("label"):
            result["label"] = result["label"][0]
    return scene_from_result(result)


def interpret_escapes(template: str) -> str:
    """Decode escape sequences"""
    return template.encode('utf-8').decode('unicode_escape')


def scene_from_result(result) -> ScrapedScene:
    scene: ScrapedScene = {}
    try:
        scene['code'] = next(iter(result.get('code', [])), None)
        scene['title'] = result.get('title')
        scene['date'] = next(iter(result.get('date', [])), None)
        scene['director'] = result.get('director') or None
        scene['url'] = result.get('url')
        scene['studio'] = {'name': next(iter(result.get('studio', [])), None)}
        scene['image'] = result.get('image', None)
        scene['label'] = result.get('label', None)   # type: ignore
        scene['performers'] = build_performer_list(result)
        scene['tags'] = build_tag_list(result)

        formatted = {
            'title': interpret_escapes(config['title_template']).format(**scene),
            'details': interpret_escapes(config['details_template']).format(**scene)
        }
        scene = scene | formatted

        # remove label as it's not supported by stash
        scene.pop('label', None)

    except KeyError as e:
        log.error(f"Unknown variable in template: {e}")
    except Exception as e:
        log.error(f"Error mapping scraped data to fields: {e}")
        log.error(f"Raw result dump: {result}")
        raise e

    return scene


def print_json(output):
    print(json.dumps(output))


def is_valid_domain(scene_url) -> bool:
    scene_domain = urlparse(scene_url).netloc
    return scene_domain in ALLOWED_HOSTNAMES


if __name__ == "__main__":
    op, args = scraper_args()

    limiter_session = get_limiter_session(per_second = 1, per_minute = 40)
    scraper = StashRequests(cloudflare=True, session=limiter_session, backends=["requests", "flaresolverr"])

    match op, args:
        case "scene-by-url", {"url": scene_url} if scene_url:
            if is_valid_domain(scene_url):
                log.debug(f"scene-by-url {scene_url}")
                print_scene_by_url(scraper, scene_url)
            else:
                log.warning(f"scene-by-url skipping {scene_url}")

        case "scene-by-name", args:
            search_title = cleanup_title(args.get("name", ""))
            log.info(f"scene-by-name searching title: {search_title}")
            print_search_for_scenes(scraper, search_title)

        case "scene-by-fragment" | "scene-by-query-fragment", args:
            # 1. try url(s) first
            scene_urls = args.get("urls")
            for scene_url in scene_urls or []:
                scene_url = re.sub(r"/(en|ja|tw|cn)/", f"/{LANGUAGE}/", scene_url)
                if is_valid_domain(scene_url):
                    log.debug(f"scene-by[-query]-fragment using {scene_url}")
                    print_scene_by_url(scraper, scene_url)
                    break
                else:
                    log.debug(f"scene-by[-query]-fragment skipping {scene_url}")

            else:
                # 2. search by code
                if (args.get("code")):
                    keyword = args.get("code")
                    log.info(f"scene-by[-query]-fragment searching code: {keyword}")
                else:
                    # 3. search by (cleaned up) title
                    keyword = cleanup_title(args.get("title", None))
                    log.info(f"scene-by[-query]-fragment searching title: {keyword}")

                print_search_for_scenes(scraper, keyword, True)

        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            print("{}")
            sys.exit(1)
