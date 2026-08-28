import json
import re
import sys
import urllib.parse
from datetime import datetime
from html import unescape

from lxml import html

import py_common.log as log
from py_common import proxy
from py_common.util import scraper_args
from py_common.types import (
    PerformerSearchResult,
    ScrapedGroup,
    ScrapedPerformer,
    ScrapedScene,
)

scraper = proxy.StashRequests()

BASE_URL = "https://www.imdb.com"


def is_waf_challenged(res) -> bool:
    # IMDB fronts with AWS WAF: non-browser clients get HTTP 202 with an
    # empty body and an x-amzn-waf-action: challenge header.
    if res.status_code == 202:
        return True
    if any(k.lower() == "x-amzn-waf-action" for k in res.headers):
        return True
    return not res.text.strip()


def get_tree(url: str):
    res = None
    try:
        # Plain request first: py_common's cookie cache replays the
        # aws-waf-token cookie + user agent from a previous FlareSolverr
        # solve, so most requests never need the browser.
        res = scraper.get(url, timeout=15)
    except Exception as e:
        log.debug(f"plain request failed for {url}: {e}")
    if res is None or is_waf_challenged(res):
        log.info(f"AWS WAF challenge on {url}, solving via FlareSolverr")
        res = proxy.flaresolverr_req(url, proxy=proxy.PROXY_URL)
    if res.status_code >= 400:
        raise Exception(f"HTTP {res.status_code} fetching {url}")
    return html.fromstring(res.text)


def dig(obj, *keys):
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int) and key < len(obj):
            obj = obj[key]
        else:
            return None
    return obj


def next_data_props(tree) -> dict:
    if scripts := tree.xpath('//script[@id="__NEXT_DATA__"]/text()'):
        try:
            return json.loads(scripts[0])["props"]["pageProps"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning(f"Could not parse __NEXT_DATA__: {e}")
    return {}


def json_ld(tree) -> dict:
    if scripts := tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            return json.loads(scripts[0])
        except json.JSONDecodeError as e:
            log.warning(f"Could not parse JSON-LD: {e}")
    return {}


def xpath_text(tree, expr: str) -> str | None:
    for node in tree.xpath(expr):
        text = node if isinstance(node, str) else node.text_content()
        text = text.strip()
        if text:
            return text
    return None


def xpath_texts(tree, expr: str) -> list[str]:
    texts = []
    for node in tree.xpath(expr):
        text = node if isinstance(node, str) else node.text_content()
        text = text.strip()
        if text:
            texts.append(text)
    return texts


def parse_date(text: str) -> str | None:
    # e.g. "December 25, 2003 (United States)" or just "2003"
    text = re.sub(r"\s*\(.+$", "", text).strip()
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-01-01"
    try:
        return datetime.strptime(text, "%B %d, %Y").date().isoformat()
    except ValueError:
        log.warning(f"Could not parse date: {text}")
        return None


def date_from_components(components) -> str | None:
    # __NEXT_DATA__ dateComponents: {"day": 27, "month": 11, "year": 1985}
    year = dig(components, "year")
    if not year:
        return None
    month = dig(components, "month") or 1
    day = dig(components, "day") or 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def og_image(tree) -> str | None:
    image = xpath_text(tree, '//meta[@property="og:image"]/@content')
    # Placeholder images are the IMDB logo, e.g. .../imdb_logo.png
    if image and re.search(r"/imdb[^/]*\.png", image):
        return None
    return image


def og_url(tree, fallback: str) -> str:
    return xpath_text(tree, '//meta[@property="og:url"]/@content') or fallback


def parse_height(text: str) -> str | None:
    # e.g. "5′ 8″ (1.73 m)" -> centimeters
    if m := re.search(r"([\d.]+)\s*m", text):
        return str(round(float(m.group(1)) * 100))
    digits = re.sub(r"\D", "", text)
    return digits or None


def parse_duration(text: str) -> str | None:
    # e.g. "2h 22m" or ISO-8601 "PT2H22M" -> "2:22:00"
    hours = re.search(r"(\d+)[hH]", text)
    minutes = re.search(r"(\d+)[mM](?![a-zA-Z])", text)
    if not hours and not minutes:
        return None
    return f"{hours.group(1) if hours else '00'}:{minutes.group(1).zfill(2) if minutes else '00'}:00"


# IMDB writes birthplaces as e.g. "Toronto, Ontario, Canada"; stash's country
# field expects an ISO 3166-1 alpha-2 code. Unmapped countries pass through
# by name.
COUNTRY_CODES = {
    "usa": "US", "united states": "US", "puerto rico": "PR",
    "uk": "GB", "england": "GB", "scotland": "GB", "wales": "GB",
    "northern ireland": "GB", "ireland": "IE",
    "canada": "CA", "mexico": "MX", "brazil": "BR", "argentina": "AR",
    "chile": "CL", "colombia": "CO", "venezuela": "VE", "peru": "PE",
    "cuba": "CU",
    "france": "FR", "germany": "DE", "west germany": "DE", "east germany": "DE",
    "italy": "IT", "spain": "ES", "portugal": "PT", "netherlands": "NL",
    "belgium": "BE", "switzerland": "CH", "austria": "AT", "greece": "GR",
    "sweden": "SE", "norway": "NO", "denmark": "DK", "finland": "FI",
    "iceland": "IS", "poland": "PL", "czech republic": "CZ",
    "czechoslovakia": "CZ", "slovakia": "SK", "hungary": "HU",
    "romania": "RO", "bulgaria": "BG", "ukraine": "UA", "russia": "RU",
    "soviet union": "RU", "ussr": "RU", "estonia": "EE", "latvia": "LV",
    "lithuania": "LT", "croatia": "HR", "serbia": "RS", "yugoslavia": "RS",
    "slovenia": "SI",
    "australia": "AU", "new zealand": "NZ",
    "japan": "JP", "china": "CN", "hong kong": "HK", "taiwan": "TW",
    "south korea": "KR", "korea": "KR", "india": "IN", "pakistan": "PK",
    "thailand": "TH", "vietnam": "VN", "philippines": "PH",
    "indonesia": "ID", "malaysia": "MY", "singapore": "SG",
    "israel": "IL", "turkey": "TR", "iran": "IR", "egypt": "EG",
    "south africa": "ZA",
}


def country_from_location(location: str) -> str | None:
    country = location.split(",")[-1].strip()
    if not country:
        return None
    return COUNTRY_CODES.get(country.lower(), country)


def performer_from_url(url: str) -> ScrapedPerformer:
    tree = get_tree(url)
    props = next_data_props(tree)
    atf = props.get("aboveTheFold") or {}
    main = props.get("mainColumnData") or {}

    name = dig(atf, "nameText", "text") or xpath_text(
        tree, '//*[@data-testid="hero__primary-text"]'
    )
    if not name:
        raise Exception(f"Could not find performer name at {url}")
    performer: ScrapedPerformer = {
        "name": name,
        "urls": [url],
    }

    birthdate = date_from_components(dig(main, "birthDate", "dateComponents"))
    if not birthdate:
        raw = xpath_text(tree, '(//li[@data-testid="nm_pd_bl"]//li)[1]')
        birthdate = parse_date(raw) if raw else None
    if birthdate:
        performer["birthdate"] = birthdate

    if death_date := date_from_components(dig(main, "deathDate", "dateComponents")):
        performer["death_date"] = death_date

    # actress/actor credit category is the only gender signal IMDB exposes
    professions = [
        dig(p, "category", "id") for p in atf.get("primaryProfessions") or []
    ]
    if "actress" in professions:
        performer["gender"] = "FEMALE"
    elif "actor" in professions:
        performer["gender"] = "MALE"

    if birth_location := dig(main, "birthLocation", "text"):
        if country := country_from_location(birth_location):
            performer["country"] = country

    if bio := dig(atf, "bio", "text", "plainText"):
        performer["details"] = bio

    image = dig(atf, "primaryImage", "url") or og_image(tree)
    if image:
        performer["images"] = [image]

    external_links = [
        dig(edge, "node", "url")
        for edge in dig(main, "personalDetailsExternalLinks", "edges") or []
    ]
    external_links = [link for link in external_links if link] or tree.xpath(
        '//li[@data-testid="details-officialsites"]//a[@target="_blank"]/@href'
    )
    performer["urls"].extend(external_links)

    alias_texts = [
        dig(nick, "displayableProperty", "value", "plainText")
        for nick in main.get("nickNames") or []
    ]
    alias_texts += [
        dig(edge, "node", "displayableProperty", "value", "plainText")
        or dig(edge, "node", "text")
        for edge in dig(main, "akas", "edges") or []
    ]
    alias_texts = [a for a in alias_texts if a] or xpath_texts(
        tree,
        '//li[@data-testid="nm_pd_ans"]//li'
        ' | //span[contains(text(), "Nicknames")]/following-sibling::*//li/span',
    )
    aliases = sorted(
        {a.strip() for text in alias_texts for a in text.split(",") if a.strip()}
    )
    if aliases:
        performer["aliases"] = ", ".join(aliases)

    height = dig(main, "height", "displayableProperty", "value", "plainText") or xpath_text(
        tree, '//li[@data-testid="nm_pd_he"]//li'
    )
    if height and (parsed := parse_height(height)):
        performer["height"] = parsed

    return performer


def performer_by_name(name: str) -> list[PerformerSearchResult]:
    query = urllib.parse.quote(name)
    tree = get_tree(f"{BASE_URL}/search/name/?name={query}")

    # The search page is client-side rendered: the server HTML carries the
    # results only in the embedded __NEXT_DATA__ JSON.
    props = next_data_props(tree)
    items = dig(props, "searchResults", "nameResults", "nameListItems")
    if items is not None:
        return [
            {
                "name": item["nameText"],
                "url": f"{BASE_URL}/name/{item['nameId']}/",
            }
            for item in items
            if item.get("nameId") and item.get("nameText")
        ]

    # Fallback: result anchors, present when the DOM was rendered by a browser
    results: list[PerformerSearchResult] = []
    for anchor in tree.xpath("//a[./h3]"):
        href = anchor.get("href", "")
        if "/name/" not in href:
            continue
        # Remove result index, like '1. Performer Performerson'
        result_name = re.sub(r"^\d+\.\s+", "", anchor.text_content().strip())
        if not href.startswith("http"):
            href = f"{BASE_URL}{href}"
        # Strip query parameters used for tracking
        href = re.sub(r"\?.+$", "", href)
        results.append({"name": result_name, "url": href})
    return results


def ld_names(value) -> list[str]:
    # JSON-LD person lists: [{"name": "..."}, ...] or a single object
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return [unescape(v["name"]) for v in value if isinstance(v, dict) and v.get("name")]


def title_common(tree, url: str) -> dict:
    # Fields shared between the scene and group scrapers
    ld = json_ld(tree)
    props = next_data_props(tree)
    atf = props.get("aboveTheFoldData") or props.get("aboveTheFold") or {}
    common = {}

    # JSON-LD's "name" is the original-language title; prefer the localized
    # display title from __NEXT_DATA__ (e.g. "Amélie", not "Le Fabuleux
    # Destin d'Amélie Poulain")
    title = (
        dig(atf, "titleText", "text")
        or xpath_text(tree, "//section//h1")
        or (unescape(ld["name"]) if ld.get("name") else None)
    )
    if title:
        common["title"] = title
    common["url"] = og_url(tree, url)

    date = ld.get("datePublished")
    if not date:
        raw = xpath_text(
            tree, "//li[@data-testid='title-details-releasedate']/div/ul/li/a/text()"
        )
        date = parse_date(raw) if raw else None
    if date:
        common["date"] = date

    details = xpath_text(tree, '//span[@data-testid="plot-xl"]') or (
        unescape(ld["description"]) if ld.get("description") else None
    )
    if details:
        common["details"] = details

    image = ld.get("image") or og_image(tree)
    if image and not re.search(r"/imdb[^/]*\.png", image):
        common["image"] = image

    if studio := xpath_text(tree, '(//li[@data-testid="title-details-companies"]/div//a)[1]'):
        common["studio"] = {"name": studio}

    if directors := ld_names(ld.get("director")):
        common["director"] = ", ".join(directors)

    tags = xpath_texts(
        tree,
        '//div[@data-testid="interests"]//a | //div[@data-testid="genres"]/a/span',
    )
    genres = [unescape(g) for g in ld.get("genre") or []]
    seen = set()
    common["tags"] = [
        t for t in tags + genres if t.lower() not in seen and not seen.add(t.lower())
    ]

    common["ld"] = ld
    common["atf"] = atf
    return common


def scene_from_url(url: str) -> ScrapedScene:
    tree = get_tree(url)
    common = title_common(tree, url)

    scene: ScrapedScene = {"urls": [common["url"]]}
    if code := re.search(r"/title/(tt\d+)", common["url"]):
        scene["code"] = code.group(1)
    if "title" in common:
        scene["title"] = common["title"]
        scene["groups"] = [{"name": common["title"], "urls": [common["url"]]}]
    for key in ("date", "details", "image", "studio", "director"):
        if key in common:
            scene[key] = common[key]
    if common["tags"]:
        scene["tags"] = [{"name": tag} for tag in common["tags"]]

    performers = xpath_texts(
        tree, '//a[@data-testid="title-cast-item__actor"]'
    ) or ld_names(common["ld"].get("actor"))
    if performers:
        scene["performers"] = [{"name": performer} for performer in performers]

    return scene


def group_from_url(url: str) -> ScrapedGroup:
    tree = get_tree(url)
    common = title_common(tree, url)
    ld = common["ld"]

    group: ScrapedGroup = {"urls": [common["url"]]}
    if "title" in common:
        group["name"] = common["title"]
    if "date" in common:
        group["date"] = common["date"]
    if "details" in common:
        group["synopsis"] = common["details"]
    if "image" in common:
        group["front_image"] = common["image"]
    if "studio" in common:
        group["studio"] = common["studio"]
    if "director" in common:
        group["director"] = common["director"]
    if common["tags"]:
        group["tags"] = [{"name": tag} for tag in common["tags"]]

    # Original title (e.g. for non-English films) as alias
    original_title = dig(common["atf"], "originalTitleText", "text") or (
        unescape(ld["name"]) if ld.get("name") else None
    )
    if original_title and original_title != group.get("name"):
        group["aliases"] = original_title

    if rating := dig(ld, "aggregateRating", "ratingValue"):
        group["rating"] = str(rating)

    duration = xpath_text(
        tree,
        '//li[@data-testid="title-techspec_runtime"]/div'
        ' | //ul[@data-testid="hero-title-block__metadata"]/li[last()]',
    ) or ld.get("duration")
    if duration and (parsed := parse_duration(duration)):
        group["duration"] = parsed

    return group


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "group-by-url" | "movie-by-url", {"url": url} if url:
            result = group_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
