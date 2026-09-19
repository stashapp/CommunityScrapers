from py_common.config import get_config
from py_common.util import scraper_args
from py_common.proxy import StashRequests
from py_common.types import ScrapedScene, ScrapedTag, ScrapedPerformer
from lxml import html
import py_common.log as log
import json
import re
import base64
from datetime import datetime

from py_common.deps import ensure_requirements
ensure_requirements("lxml")

# Scene info for this site is paywalled, so you must set cookies in config.ini

config = get_config(
    # CONFIG_NOTES

    # Cookies should be set as a semicolon-delimited string of name=value pair(s) without any newlines.
    # You may copy and paste Chrome network tools 'Request' tab "Cookie:" value.
    # e.g., COOKIES = foo=sUsll2; pcar%5fUmVzdHJpY3RlZA%3d%3d=YY/69aljfoojfg|kljgg/420A==
    # Only the cookie with key `pcar%5fUmVzdHJpY3RlZA%3d%3d` is used. Others are ignored.

    default="""
    # See CONFIG_NOTES in CathysCraving.py for documentation
    COOKIES =
"""
)


requests = StashRequests()


def get_cookies_dict() -> dict[str, str]:
    cookie_name = "pcar%5fUmVzdHJpY3RlZA%3d%3d"
    cookie_val = None
    config_val = config.config_dict.get("COOKIES") or ""
    for part in str(config_val).split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip()
            if k == cookie_name:
                cookie_val = v.strip()
                break

    if not cookie_val:
        log.error(f"Missing necessary cookie: {cookie_name}")
        return {}
    return {cookie_name: cookie_val}


def fetch_html_tree(url: str) -> html.HtmlElement | None:
    """Fetches HTML content from a URL and returns the parsed
       lxml HTML tree, with relative links converted to absolute."""
    cookies = get_cookies_dict()

    if not cookies:
        log.error("Exiting due to missing cookies")
        return None

    log.debug(f"Fetching URL: {url}")

    try:
        response = requests.get(url, cookies=cookies, timeout=10)
        response.raise_for_status()
    except Exception as e:
        log.error(f"Failed to fetch URL '{url}': {e}")
        return None

    tree = html.fromstring(response.content)
    tree.make_links_absolute(base_url=url)
    return tree


def get_scene_title(tree: html.HtmlElement) -> str | None:
    # Title is on its own page that's inside an iframe.
    iframe_urls = tree.xpath("//iframe/@src")
    title_page_url = None
    for iframe_url in iframe_urls:
        if re.search(r"/iframe-\d+\.html$", iframe_url):
            title_page_url = iframe_url
            break

    if not title_page_url:
        log.warning("No iframe found for title")
        return None
    
    title_page_tree = fetch_html_tree(title_page_url)
    if title_page_tree is None:
        log.warning("Could not load title page")
        return None
    
    number_portion = extract_text_with_linebreaks(title_page_tree.xpath("//span[contains(@class, 'scene')]")[0])
    title_portion = extract_text_with_linebreaks(title_page_tree.xpath("//span[contains(@class, 'title')]")[0])
    if number_portion and title_portion:
        return f"{number_portion}: {title_portion}"
    else:
        return number_portion or title_portion or None


def get_scene_index_subtree(index_url: str, scene_url: str) -> html.HtmlElement | None:
    tree = fetch_html_tree(index_url)
    if tree is None:
        log.warning("Could not load scene index")
        return None
    # On the index page, there should be a <table> that includes the release date and an <a> that links to the scene_url.
    # Locate it by finding the <a> with text content 'View Scene' and the expected URL, then going up to the nearest <table> ancestor.
    tables = tree.xpath(f"(//a[normalize-space()='View Scene' and @href = '{scene_url}']/ancestor::table[1])[1]")
    if tables:
        return tables[0]
    else:
        log.warning(f"Could not find corresponding <table> on scene index page '{index_url}'")
        return None
    


def get_release_date(tree: html.HtmlElement, scene_url: str) -> str | None:
    # We need to load the scene index page to get the release date.
    scene_index_url = tree.xpath("string(//a[contains(text(), 'SCENE INDEX')]/@href)")
    if not scene_index_url:
        log.warning("Could not find scene index URL")
        return None
    
    scene_index_subtree = get_scene_index_subtree(scene_index_url, scene_url)
    if scene_index_subtree is None:
        log.warning("Could not find scene index subtree")
        return None
    
    # Important that path part of this expression begins with `.` in order to only search the
    # subtree. Without `.`, the entire document would be searched.
    # HTML looks like: <span>Added - <b>01-20-2025</b></span>
    raw_date_string = scene_index_subtree.xpath("string(.//span[contains(., 'Added -')]/b)").strip()
    if raw_date_string:
        # Convert MM-DD-YYYY to YYYY-MM-DD
        try:
            parsed_date = datetime.strptime(raw_date_string, "%m-%d-%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            log.warning(f"Could not parse date string: {raw_date_string}")

    # Some versions have "When - <Month> <Year>", e.g. "When - September 2015"
    raw_when_string = scene_index_subtree.xpath("string(.//span[contains(., 'When -')]/b)").strip()
    if raw_when_string:
        try:
            parsed_date = datetime.strptime(raw_when_string, "%B %Y")
            return parsed_date.strftime("%Y-%m")
        except ValueError:
            log.warning(f"Could not parse 'When' date string: {raw_when_string}")

    log.warning("Could not find release date string")
    return None


def extract_text_with_linebreaks(element: html.HtmlElement) -> str:
    """Extracts text content from an element, converting <br> tags to newlines and
    collapsing all non-<br> whitespace into single spaces.
    """
    # The plan:
    # 1) Append a sentinel character to each <br> tag
    # 2) Get the text content of `element` (which strips tags)
    # 3) Collapse whitespace chunks
    # 4) Convert sentinels to newlines

    # Use a Unicode Private Use Area (PUA) character so it never collides with
    # any real text.
    sentinel_token = "\uE000"

    for br in element.xpath(".//br"):
        br.tail = f" {sentinel_token} " + (br.tail or "")

    raw_text = element.text_content()
    collapsed = " ".join(raw_text.split())

    sentinels_reversed = "\n".join(x.strip() for x in collapsed.split(sentinel_token)).strip()
    return sentinels_reversed


def get_description(tree: html.HtmlElement) -> str | None:
    description_spans = tree.xpath("//span[contains(@class, 'description')]")
    if not description_spans:
        log.warning("Could not find description <span>")
        return None

    # The page also uses <span>s with class `description` for picture
    # download links, but only the first one is the actual scene description.
    description_span = description_spans[0]
    description = extract_text_with_linebreaks(description_span)
    
    if description:
        log.debug(f"Found description: {description}")
        return description
    else:
        log.warning("Could not find description")
        return None


# Maps a performer's page name (minus .html) to a more specific display name when known.
# These have been determined visually, often with the help of `cc1234475/visage`.
PERFORMER_NAME_MAP = {
    # Guys
    "chrism2": "Chris Cock",
    "dick": "Dick James",
    "dirk": "Dirk Huge",
    "donny": "Donny Sins",
    "isiah": "Isiah Maxwell",
    "lawson": "Lawson Jones",
    "ray": "Ray Black",
    "rion": "Rion King",
    "robby": "Robby Apples",
    # Girls
    "aja": "Aja Cummings",
    "alanna": "Alana Thomas",
    "alicia": "Alicia Daniels",
    "amanda": "Amanda Ryder",
    "cathy": "Cathy Craving",
    "darian": "Darians Fire",
    "janey": "Janey Web",
    "lily": "Lilly Lixx",
    "lilyf": "Lilly Lit",
    "mia": "Mia Knight",
}


def get_performers(tree: html.HtmlElement) -> list[ScrapedPerformer] | None:
    # Locating the exact location of the performer list in the document is tedious,
    # but fortunately each performer has a link with a URL that includes `/girls+guys/`
    # but unfortunately there is also a non-performer link with a URL that includes
    # `/girls+guys/girls.html` on each page.
    anchors = tree.xpath("//a[contains(@href, '/girls+guys/') and not(contains(@href, '/girls+guys/girls.html'))]")
    performers: list[ScrapedPerformer] = []
    for anchor in anchors:
        performer_page_name = None
        performer_page_name_search = re.search(r"/([a-zA-Z0-9]+)\.html", anchor.xpath("string(@href)"))
        if performer_page_name_search:
            performer_page_name = performer_page_name_search.group(1)
        performer_display_name = anchor.text_content().strip()
        performer_display_name = PERFORMER_NAME_MAP.get(performer_page_name, performer_display_name)
        if performer_display_name:
            performers.append({"name": performer_display_name})

    if performers:
        return performers
    else:
        log.warning("Could not find any performers")
        return None

def get_tags(tree: html.HtmlElement) -> list[str] | None:
    anchors = tree.xpath("//span[contains(@class, 'keywords')]//a[contains(@href, 'categories')]")

    tags: list[ScrapedTag] = []
    for anchor in anchors:
        tag_name = anchor.text_content().strip()
        if tag_name:
            tags.append({"name": tag_name})

    return tags


def get_image(tree: html.HtmlElement) -> str | None:
    # Loading image requires cookies, so we'll fetch it now with the cookies we have
    # and return the full image file as a base64 encoded data URI so that the client
    # doesn't need cookies to load the image.
    img_src = tree.xpath("//img//@src")
    if img_src:
        image_url = img_src[0]
        log.debug(f"Found image URL: {image_url}")
    else:
        log.warning("No image URL found")
        return None

    try:
        response = requests.get(
            image_url, cookies=get_cookies_dict(), timeout=10)
        response.raise_for_status()
    except Exception as e:
        log.error(f"Failed to fetch image URL '{image_url}': {e}")
        return None

    base64_string = base64.b64encode(response.content).decode("utf-8")
    content_type = response.headers.get("Content-Type", "image/jpeg")
    mime_type = content_type.split(";")[0].strip() or "image/jpeg"
    data_url = f"data:{mime_type};base64,{base64_string}"

    return data_url


def get_scene_number(title: str) -> str | None:
    # Most scene titles begin with "Scene XYZ: "
    match = re.match(r"Scene\s+(\d+):", title)
    if match:
        return match.group(1)
    else:
        log.warning(f"Could not extract scene number from title: {title}")
        return None


def scrape_scene_data(url: str) -> ScrapedScene:
    """Scrapes metadata for the scene at the URL.

    Args:
        url: The scene URL.

    Returns:
        A dictionary of scraped scene metadata.
    """
    log.debug(f"Scraping scene URL: {url}")

    tree = fetch_html_tree(url)
    if tree is None:
        return {}

    scene: ScrapedScene = {}

    title_text = get_scene_title(tree)
    if title_text:
        scene["title"] = title_text
    else:
        log.error("Unable to find title. Exiting")
        return {}

    date_str = get_release_date(tree, url)
    if date_str:
        scene["date"] = date_str

    description = get_description(tree)
    if description:
        scene["details"] = description

    performers = get_performers(tree)
    if performers:
        scene["performers"] = performers

    scene["tags"] = get_tags(tree)
    # All scene pages require member login:
    scene["tags"].append({"name": "Members Only"})

    image_url = get_image(tree)
    if image_url:
        scene["image"] = image_url

    scene["studio"] = {"name": "Cathy's Craving"}

    scene_number = get_scene_number(title_text)
    if scene_number:
        scene["code"] = scene_number

    scene["urls"] = [url]

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    if op in ["scene-by-url", "scene-by-query-fragment"]:
        url = args.get("url")
        if url:
            result = scrape_scene_data(url)

    if result:
        print(json.dumps(result))
    else:
        print(json.dumps({}))