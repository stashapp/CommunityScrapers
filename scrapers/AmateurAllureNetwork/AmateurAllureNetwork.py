import sys
import json
import re
from datetime import datetime
from urllib.parse import urlparse
import requests
from lxml import html
from py_common import log

CENSOR_MAP = {
    # All text on these sites has been censored. This list has been made after looking through the tag lists and testing around 50 scenes
    # Longer strings should be added higher up than short similar strings, otherwise they won't match. ie: "deepthroat" should be above "deep" and "throat" but below "deepthroating".
    "a--l": "anal",
    "a-s": "ass",
    "b--l": "ball",
    "b---s": "balls",
    "b--w--b": "blowjob",
    "b--w--bs": "blowjobs",
    "b--w": "blow",
    "b--t": "butt",
    "c--k--g": "choking",
    "c--k": "cock",
    "c---s": "cocks",
    "c--g--l": "cowgirl",
    "c--a--ie": "creampie",
    "c----y": "creamy",
    "c-m": "cum",
    "c--s--t": "cumshot",
    "d--p--r--t--g": "deepthroating",
    "d--p--r--t": "deepthroat",
    "d--p": "deep",
    "d--k": "dick",
    "d--g--s--le": "doggiestyle",
    "d--g--t--e": "doggystyle",
    "f----l": "facial",
    "f--g--i-g": "fingering",
    "f--r--me": "foursome",
    "f--k--g": "fucking",
    "f----d": "fucked",
    "f---s": "fucks",
    "f--k": "fuck",
    "g---y h--e": "glory hole",
    "h--d--b": "handjob",
    # h--d could be "head" or "hard". Head is used more in titles so is what we'll use, as the title needs to be correct for the code/image subscraper to work. Might have to double-check your details to make sure they make sense.
    "h--d": "head",
    "j--k--g": "jerking",
    "j----d": "jerked",
    "j--k": "jerk",
    "j----s": "juices",
    "l--b--n": "lesbian",
    "l--k--g": "licking",
    "l--k": "lick",
    "l---s": "loads",
    "l--d": "load",
    "m--t": "meat",
    "m--f": "milf",
    "m--s--n--y": "missionary",
    "o----y": "orally",
    "o--l": "oral",
    "o--a--s": "orgasms",
    "o--y": "orgy",
    "p--e--a--s": "penetrates",
    "p--g": "plug",
    "p--n": "porn",
    "p--n--a-s": "pornstars",
    "p--s--s": "pussys",
    "p---y": "pussy",
    "r----b": "rimjob",
    "r--y": "ruby",
    "s---t": "shaft",
    "s---m": "sperm",
    "s--r--am": "spermcam",
    "s--n--r": "spinner",
    "s--k--g": "sucking",
    "s---s": "sucks",
    "s--k": "suck",
    "t--n": "teen",
    "t--e--o-e": "threesome",
    "t--s": "tits",
    "t---y": "titty",
    "t----t": "throat",
    "-h--at": "throat",
}

# Helpers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

def read_json_input():
    data = sys.stdin.read()
    if not data.strip():
        return {}
    return json.loads(data)

def fetch_dom(url: str) -> html.HtmlElement:
    log.debug(f"[fetch_dom] GET {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return html.fromstring(resp.content)

def first_or_none(items):
    return items[0] if items else None

def clean_str(s):
    if s is None:
        return None
    return " ".join(str(s).split()).strip()

def parse_date_mdy(text: str):
    if not text:
        return None
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def debug_fragment_values(site, data):
    data = apply_censor_map_to_value(data)
    for key in [
        "url", "title", "code", "date", "details",
        "image", "studio", "tags", "performers"
    ]:
        log.debug(f"[{site}] {key}: {data.get(key)}")

def match_case(replacement: str, original: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement.capitalize()
    return replacement.lower()

# Applying the uncensor list above
def apply_censor_map_to_value(value):
    if isinstance(value, str):
        for bad, good in CENSOR_MAP.items():
            pattern = re.compile(re.escape(bad), re.IGNORECASE)
            value = pattern.sub(lambda m: match_case(good, m.group()), value)
        return value

    if isinstance(value, list):
        return [apply_censor_map_to_value(v) for v in value]

    if isinstance(value, dict):
        return {k: apply_censor_map_to_value(v) for k, v in value.items()}

    return value

# Subscraper functions
def build_search_url(site_base: str, path: str, title: str | None):
    if not title:
        return None

    query = title.strip()
    query = re.sub(r"\s+", "+", query)
    query = query.replace(",", "%2C")

    url = f"{site_base}{path}?st=advanced&qall={query}"
    log.debug(f"subscraper  url: {url}")
    return url

def resolve_relative_url(base_url: str, maybe_relative: str) -> str | None:
    if not maybe_relative:
        return None

    if maybe_relative.startswith("//"):
        return "https:" + maybe_relative

    if maybe_relative.startswith("http://") or maybe_relative.startswith("https://"):
        return maybe_relative

    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if maybe_relative.startswith("/"):
        return origin + maybe_relative
    return origin + "/" + maybe_relative.lstrip("/")

# The old method used the actual gallery images the scene covers were based on, this meant the scene covers were 16:10 instead of 16:9 and had watermarks 
# This method grabs upscaled versions of the scene covers (8K for amateur allure 2K for swallow salon)
def find_high_res_and_code(search_url: str | None):
    if not search_url:
        return None, None

    try:
        tree = fetch_dom(search_url)
    except Exception as e:
        log.error(f"fetch_dom failed for {search_url}: {e}")
        return None, None

    details_div = first_or_none(
        tree.xpath('//div[contains(@class, "update_details")]')
    )
    if details_div is None:
        log.debug(f"No update_details found at {search_url}")
        return None, None

    # Site redesign now obfuscates code on the scene page, have to use the search subscraper instead
    code = details_div.attrib.get("data-setid")
    if code:
        img_el = first_or_none(details_div.xpath('.//img'))
        img_url = None

    if img_el is not None:
        for attr in ["src0_4x", "src0_3x", "src0_2x", "src0_1x", "src"]:
            val = img_el.attrib.get(attr)
            if val:
                img_url = val
                break

        if not img_url:
            srcset = img_el.attrib.get("srcset")
            if srcset:
                first_entry = srcset.split(",")[0].strip()
                img_url = first_entry.split(" ")[0].strip()

    if not img_url:
        return code, None

    img_url = img_url.strip()

    if "swallowsalon.com" in search_url:
        # change the "-4x.jpg" for smaller sizes
        # 4x = 8K, 3x = 6K, 2x = 4K, 1x is the original 1080. swallow salon's public scene covers are 1/4 the size 
        img_url = re.sub(r"-1x\.jpg$", "-4x.jpg", img_url)
    else:
        if re.search(r"-[123]x\.jpg$", img_url):
            img_url = re.sub(r"-[123]x\.jpg$", "-4x.jpg", img_url)

    resolved = resolve_relative_url(search_url, img_url)
    return code, resolved

# lists
def build_tag_list(names):
    tags = []
    for name in names or []:
        name = clean_str(name)
        if name:
            tags.append({"name": name, "Name": name})
    return tags

def build_performer_list(names):
    performers = []
    for name in names or []:
        name = clean_str(name)
        if name:
            performers.append({"name": name, "Name": name})
    return performers

# Fragment builder
def build_fragment(
    url: str,
    title=None,
    code=None,
    date=None,
    details=None,
    image=None,
    studio_name=None,
    tag_names=None,
    performer_names=None,
):
    frag = {}

    if title:
        title = clean_str(title)
        frag["title"] = title
        frag["Title"] = title

    if code:
        code = clean_str(code)
        frag["code"] = code
        frag["Code"] = code

    if date:
        frag["date"] = date
        frag["Date"] = date

    if details:
        details = clean_str(details)
        frag["details"] = details
        frag["Details"] = details

    if image:
        image = clean_str(image)
        frag["image"] = image
        frag["Image"] = image

    if url:
        frag["url"] = url
        frag["URL"] = url

    if studio_name:
        studio_name = clean_str(studio_name)
        studio = {"name": studio_name, "Name": studio_name}
        frag["studio"] = studio
        frag["Studio"] = studio

    tags = build_tag_list(tag_names)
    if tags:
        frag["tags"] = tags
        frag["Tags"] = tags

    performers = build_performer_list(performer_names)
    if performers:
        frag["performers"] = performers
        frag["Performers"] = performers

    frag = apply_censor_map_to_value(frag)

    return frag

# Site scrapers
def scrape_amateurallure(url: str, tree: html.HtmlElement):
    title = first_or_none(tree.xpath("//span[@class='title_bar_hilite']/text()"))
    details = first_or_none(tree.xpath("//span[@class='update_description']/text()"))

    raw_date = "".join(
        tree.xpath("//div[@class='backgroundcolor_info']//div[@class='cell update_date']//text()")
    )
    raw_date = raw_date.replace("Added:", "").strip()
    date = parse_date_mdy(raw_date)

    code = first_or_none(tree.xpath('//div[contains(@class, "update_details")]/@data-setid'))
    if not code:
        code = first_or_none(tree.xpath('//div[@class="rating_box"]/@data-id'))
    if not code:
        img_id = first_or_none(tree.xpath('//div[@class="column"]/a/img/@id'))
        if img_id and img_id.startswith("set-target-"):
            code = img_id[len("set-target-"):]

    image = first_or_none(tree.xpath("//meta[@property='og:image']/@content"))

    clean_title_for_search = apply_censor_map_to_value(title or "")
    search_url = build_search_url(
        "https://www.amateurallure.com",
        "/tour/search.php",
        clean_title_for_search
    )
    search_code, search_image = find_high_res_and_code(search_url)

    if not code and search_code:
        code = search_code
    if search_image:
        image = search_image

    performer_names = tree.xpath("//div[@class='backgroundcolor_info']//span[@class='update_models']//a/text()")
    tag_names = tree.xpath("//span[@class='update_tags']//a/text()")

    debug_fragment_values("Amateur Allure", {
        "url": url,
        "title": title,
        "code": code,
        "date": date,
        "details": details,
        "image": image,
        "studio": "Amateur Allure",
        "tags": tag_names,
        "performers": performer_names,
    })

    return build_fragment(
        url=url,
        title=title,
        code=code,
        date=date,
        details=details,
        image=image,
        studio_name="Amateur Allure",
        tag_names=tag_names,
        performer_names=performer_names,
    )

def scrape_amateurallure_classics(url: str, tree: html.HtmlElement):
    scene_root = first_or_none(tree.xpath('//div[contains(@class, "gallery_info")]')) or tree

    title = first_or_none(tree.xpath("//title/text()"))
    details = first_or_none(scene_root.xpath('.//span[@class="update_description"]/text()'))

    date_text = " ".join(
        scene_root.xpath(
            './/*[(contains(@class, "availdate") or contains(@class, "update_date")) and contains(., "/")]/text()'
        )
    )
    date = parse_date_mdy(date_text)

    script_text = " ".join(tree.xpath('//script[contains(., "setid:")]/text()'))
    m = re.search(r'setid:"(\d+)', script_text)
    code = m.group(1) if m else None

    if not code:
        code = first_or_none(tree.xpath('//div[contains(@class, "update_details")]/@data-setid'))

    image = first_or_none(tree.xpath("//meta[@property='og:image']/@content"))

    clean_title_for_search = apply_censor_map_to_value(title or "")
    search_url = build_search_url(
        "https://www.amateurallureclassics.com",
        "/search.php",
        clean_title_for_search
    )
    search_code, search_image = find_high_res_and_code(search_url)

    if not code and search_code:
        code = search_code
    if search_image:
        image = search_image

    performer_names = scene_root.xpath('.//span[@class="update_models"]/a/text()')
    tag_names = scene_root.xpath('.//span[contains(@class, "update_tags")]/a/text()')

    debug_fragment_values("Amatuer Allure Classics", {
        "url": url,
        "title": title,
        "code": code,
        "date": date,
        "details": details,
        "image": image,
        "studio": "Amateur Allure",
        "tags": tag_names,
        "performers": performer_names,
    })

    return build_fragment(
        url=url,
        title=title,
        code=code,
        date=date,
        details=details,
        image=image,
        studio_name="Amateur Allure Classics",
        tag_names=tag_names,
        performer_names=performer_names,
    )

def scrape_swallowsalon(url: str, tree: html.HtmlElement):
    title = first_or_none(tree.xpath("//span[@class='title_bar_hilite']/text()"))
    details = first_or_none(tree.xpath("//span[@class='update_description']/text()"))

    raw_date = "".join(
        tree.xpath("//div[@class='backgroundcolor_info']//div[@class='cell update_date']//text()")
    ).strip()
    date = parse_date_mdy(raw_date)

    code = first_or_none(tree.xpath('//div[contains(@class, "update_details")]/@data-setid'))
    if not code:
        code = first_or_none(tree.xpath('//div[@class="rating_box"]/@data-id'))

    image = first_or_none(tree.xpath("//meta[@property='og:image']/@content"))

    clean_title_for_search = apply_censor_map_to_value(title or "")
    search_url = build_search_url(
        "https://www.swallowsalon.com",
        "/search.php",
        clean_title_for_search
    )
    search_code, search_image = find_high_res_and_code(search_url)

    if not code and search_code:
        code = search_code
    if search_image:
        image = search_image

    performer_names = tree.xpath("//div[@class='backgroundcolor_info']//span[@class='update_models']//a/text()")
    tag_names = tree.xpath("//span[@class='update_tags']//a/text()")

    debug_fragment_values("Swallow Salon", {
        "url": url,
        "title": title,
        "code": code,
        "date": date,
        "details": details,
        "image": image,
        "studio": "Amateur Allure",
        "tags": tag_names,
        "performers": performer_names,
    })

    return build_fragment(
        url=url,
        title=title,
        code=code,
        date=date,
        details=details,
        image=image,
        studio_name="Swallow Salon",
        tag_names=tag_names,
        performer_names=performer_names,
    )

# Actions
def scrape_scene_by_url(url: str):
    host = urlparse(url).netloc.lower()
    tree = fetch_dom(url)

    if "amateurallureclassics.com" in host:
        return scrape_amateurallure_classics(url, tree)
    elif "amateurallure.com" in host:
        return scrape_amateurallure(url, tree)
    elif "swallowsalon.com" in host:
        return scrape_swallowsalon(url, tree)

    raise ValueError(f"Unsupported host: {host}")

def scrape_gallery_by_url(url: str):
    return scrape_scene_by_url(url)

# Main
def main():
    if len(sys.argv) < 2:
        print("Usage: script.py [sceneByURL|galleryByURL]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    payload = read_json_input()
    url = payload.get("url")

    if mode == "sceneByURL":
        out = scrape_scene_by_url(url)

    elif mode == "galleryByURL":
        out = scrape_gallery_by_url(url)

    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(json.dumps(out))

if __name__ == "__main__":
    main()
