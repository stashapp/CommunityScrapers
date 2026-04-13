#!/usr/bin/env python3
"""
TheNude.com performer scraper — Python implementation.

Handles performer-by-url, performer-by-name, scene-search, and gallery-search.
Direct scene/gallery/image scraping by URL remains in the YAML file.

Notable behaviour:
  - URLs are normalized to the canonical ID-only form (/_NNNNN.htm), which is
    what StashDB uses and avoids the space-in-URL problem entirely.
  - Aliases: the performer's own name is filtered out. TheNude includes the
    canonical name in the AKA list, which StashDB rejects.
  - Birthdate: month+year-only dates (e.g. "November 1985") are not returned.
    Defaulting the day to 01 would produce a wrong date that overwrites better
    existing data.
  - Career length: formatted as "YYYY - YYYY" with spaces to match StashDB style.
  - Tattoos and piercings: not returned. TheNude's data for these fields is
    frequently wrong (reports "None" for performers known to have body art).
  - Cover search: searches TheNude's cover (scene/gallery) search endpoint by
    title and returns a list of results for the user to pick from.  Both
    scene-search and gallery-search call the same endpoint; the cover_type
    parameter ("video" / "gallery") is used to filter the results returned.
"""

import json
import re
import sys
from datetime import datetime

import requests
from lxml import html

import py_common.log as log
from py_common.util import scraper_args

BASE_URL = "https://www.thenude.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
        "Gecko/20100101 Firefox/122.0"
    )
}

# Maps raw site values to Stash/StashDB internal values.
HAIR_COLOR_MAP = {
    "Fair":    "Blonde",
    "Blonde":  "Blonde",
    "Brown":   "Brunette",
    "Brunette":"Brunette",
    "Black":   "Black",
    "Red":     "Red",
    "Auburn":  "Auburn",
    "Grey":    "Grey",
    "Bald":    "Bald",
    "Various": "Various",
}

ETHNICITY_MAP = {
    "Ebony":    "Black",
    "ebony":    "Black",
    "White":    "Caucasian",
    "white":    "Caucasian",
    "Hispanic": "Latin",
    "hispanic": "Latin",
    "Latina":   "Latin",
    "Asian":    "Asian",
    "Black":    "Black",
    "Arab":     "Middle Eastern",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_url(url):
    """
    Convert any TheNude performer URL to the canonical ID-only form.

    Accepts:
      https://www.thenude.com/Carli Banks_6444.htm   (raw space)
      https://www.thenude.com/Carli%20Banks_6444.htm (percent-encoded)
      https://www.thenude.com/_6444.htm              (already canonical)

    Returns:
      https://www.thenude.com/_6444.htm
    """
    # Decode %20 so the regex sees a uniform space
    url = url.replace("%20", " ")
    m = re.match(r"^(https://www\.thenude\.com/)[^_]*(_\d+\.htm)$", url)
    if m:
        return m.group(1) + m.group(2)
    return url


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_birthdate(text):
    """
    Parse a birthdate string from TheNude.
    Returns an ISO date string (YYYY-MM-DD) only when a specific day is present.
    Month+year-only strings (e.g. "November 1985") return None to avoid
    writing a wrong date that would overwrite a more precise existing value.
    """
    text = text.strip()

    for fmt in ("%B %d, %Y", "%d %B %Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Month + year only — deliberately not returned
    for fmt in ("%B %Y",):
        try:
            datetime.strptime(text, fmt)
            log.info(f"Birthdate '{text}' has no day — not returning (would default to 1st)")
            return None
        except ValueError:
            pass

    # Year only or unrecognised — not returned
    return None


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return html.fromstring(resp.content)
    except Exception as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Performer page scraping
# ---------------------------------------------------------------------------

def li_text(tree, label_fragment):
    """
    Return stripped text node(s) from the <li> that contains a <span> whose
    text includes label_fragment.  Combines multiple sibling text nodes.
    Works for both:
      - following-sibling::text()  (e.g. Born, Height, First/Last Seen)
      - /../text()                 (e.g. Hair, Breasts, Measurements)
    Returns the combined string, or None if empty.
    """
    # Try following-sibling first (most common)
    nodes = tree.xpath(
        f'//li/span[@class="list-quest"][contains(text(),"{label_fragment}")]'
        f'/following-sibling::text()'
    )
    combined = " ".join(n.strip() for n in nodes if n.strip())
    if combined:
        return combined

    # Fall back to parent <li> text nodes (catches cases where text is a
    # direct child of <li>, not a sibling of the span)
    nodes = tree.xpath(
        f'//li/span[@class="list-quest"][contains(text(),"{label_fragment}")]'
        f'/../text()'
    )
    combined = " ".join(n.strip() for n in nodes if n.strip())
    return combined if combined else None


def scrape_performer_page(tree, source_url):
    performer = {}

    # --- Name ---
    name_els = tree.xpath('//span[@class="model-name"]')
    name = name_els[0].text_content().strip() if name_els else None
    if name:
        performer["name"] = name
    name_lower = name.lower() if name else ""

    # --- URL — canonical ID-only form ---
    canonical_els = tree.xpath("//link[@rel='canonical']/@href")
    if canonical_els:
        performer["urls"] = [normalize_url(canonical_els[0].strip())]
    else:
        performer["urls"] = [normalize_url(source_url)]
    # Keep the raw canonical for image URL construction below
    raw_canonical = canonical_els[0].strip() if canonical_els else source_url

    # --- Aliases — exclude the performer's own name ---
    alias_metas = tree.xpath("//meta[@itemprop='additionalName']/@content")
    aliases = [
        a.strip() for a in alias_metas
        if a.strip() and a.strip().lower() != name_lower
    ]
    if aliases:
        performer["aliases"] = ", ".join(aliases)

    # --- Birthdate — day-precision only ---
    born_text = li_text(tree, "Born")
    if born_text:
        date = parse_birthdate(born_text)
        if date:
            performer["birthdate"] = date

    # --- Country ---
    country_els = tree.xpath("//span[@itemprop='nationality']/text()")
    if country_els:
        country = country_els[0].strip()
        if country == "United States of America":
            country = "United States"
        if country:
            performer["country"] = country

    # --- Ethnicity ---
    ethnicity_raw = li_text(tree, "Ethnicity")
    if ethnicity_raw:
        performer["ethnicity"] = ETHNICITY_MAP.get(ethnicity_raw, ethnicity_raw)

    # --- Hair color ---
    hair_raw = li_text(tree, "Hair")
    if hair_raw:
        hair = HAIR_COLOR_MAP.get(hair_raw, hair_raw)
        if hair:
            performer["hair_color"] = hair

    # --- Height (cm) ---
    height_raw = li_text(tree, "Height")
    if height_raw:
        m = re.match(r"(\d+)", height_raw)
        if m:
            performer["height"] = m.group(1)

    # --- Measurements (bust only: strip /...) ---
    meas_raw = li_text(tree, "Measurements")
    if meas_raw:
        meas = re.sub(r"/.*$", "", meas_raw).strip()
        if meas:
            performer["measurements"] = meas

    # --- Fake tits / breast enhancement ---
    breasts_raw = li_text(tree, "Breasts")
    if breasts_raw:
        m = re.match(r"^[^(]+\(([^)]+)\)", breasts_raw)
        if m:
            val = m.group(1).strip()
            if val == "Medium":
                val = ""
            elif val == "Real":
                val = "Natural"
            if val:
                performer["fake_tits"] = val

    # --- Career length — formatted as "YYYY - YYYY" ---
    seen_nodes = tree.xpath(
        '//li/span[@class="list-quest"][contains(text(),"Seen")]'
        '/following-sibling::text()'
    )
    seen_years = [n.strip() for n in seen_nodes if re.match(r"^\d{4}$", n.strip())]
    if len(seen_years) >= 2:
        performer["career_length"] = f"{seen_years[0]} - {seen_years[1]}"
    elif len(seen_years) == 1:
        performer["career_length"] = seen_years[0]

    # --- Tattoos / Piercings: intentionally not scraped ---
    # TheNude's data for these fields is unreliable and frequently says "None"
    # for performers who visibly have body art.  Returning wrong data here
    # would silently overwrite correct existing values.

    # --- Image — CDN URL with %20 encoding ---
    img_url = raw_canonical
    img_url = re.sub(r"^https://www\.thenude\.com/",
                     "https://static.thenude.com/models/", img_url)
    img_url = re.sub(r"\.htm$", "/medhead.jpg", img_url)
    img_url = img_url.replace(" ", "%20")
    performer["images"] = [img_url]

    # --- Gender ---
    gender_els = tree.xpath("//meta[@itemprop='gender']/@content")
    if gender_els:
        performer["gender"] = gender_els[0].strip()

    # --- Twitter ---
    twitter_els = tree.xpath('//a[text()="TWITTER"]//@href')
    if twitter_els:
        handle = re.sub(r"https?://(?:www\.)?(?:twitter|x)\.com/", "",
                        twitter_els[0]).strip("/")
        if handle:
            performer["twitter"] = handle

    # --- Instagram ---
    insta_els = tree.xpath('//a[text()="INSTAGRAM"]//@href')
    if insta_els:
        handle = re.sub(r"https?://(?:www\.)?instagram\.com/", "",
                        insta_els[0]).strip("/")
        if handle:
            performer["instagram"] = handle

    return performer


# ---------------------------------------------------------------------------
# Name search
# ---------------------------------------------------------------------------

def search_performers(name):
    query_url = (
        f"{BASE_URL}/index.php?page=search&action=searchModels"
        f"&__form_name=navbar-search&m_aka=on"
        f"&m_name={requests.utils.quote(name)}"
    )
    tree = fetch_page(query_url)
    if tree is None:
        return []

    results = []
    for figure in tree.xpath('//div[contains(@class,"blockIndexModels")]//figure'):
        # Name — strip leading "AKA:" that the site prepends in the figcaption
        name_nodes = figure.xpath(".//figcaption/span/text()")
        if not name_nodes:
            continue
        result_name = name_nodes[0].strip()
        if result_name.upper().startswith("AKA:"):
            result_name = result_name[4:].strip()

        # URL — normalize immediately
        url_els = figure.xpath('.//a[@class="model-name"]/@href')
        if not url_els:
            continue
        result_url = normalize_url(url_els[0].strip())

        results.append({"name": result_name, "urls": [result_url]})

    return results


# ---------------------------------------------------------------------------
# Cover (scene / gallery) search
# ---------------------------------------------------------------------------

def parse_cover_date(text):
    """
    Parse a date string from the cover search results listing.
    TheNude uses "7 June 2006" format in search results (vs ISO on cover pages).
    Returns YYYY-MM-DD or None.
    """
    text = text.strip()
    try:
        return datetime.strptime(text, "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_cover_title(meta_content):
    """
    Extract the set title from the <meta itemprop="description name"> content
    attribute, which looks like:  Anna L in 'Anna L Naked Forest Nymph Shoot'
    from HEGRE-ART VIDEO

    Returns the quoted set title, or None if the pattern does not match.
    """
    m = re.search(r"'([^']+)'", meta_content)
    return m.group(1) if m else None


def search_covers(title, cover_type=None):
    """
    Search TheNude for covers (scenes or galleries) matching *title*.

    cover_type — "video" to return only video covers (scenes),
                 "gallery" to return only photo-set covers (galleries),
                 None to return all results.

    Returns a list of dicts suitable for use as ScrapedScene / ScrapedGallery
    results.  Each dict contains:
      title, url, date, studio (dict), performers (list), image.
    """
    search_url = (
        f"{BASE_URL}/index.php?page=search&action=searchCovers"
        f"&__form_name=cover_search"
        f"&c_set_name={requests.utils.quote(title)}"
        f"&models_from=&models_to=&published_from=&published_to="
        f"&c_location=&c_m_names=&c_removed_from_site="
        f"&c_with_location=&c_cover_core_type="
    )
    tree = fetch_page(search_url)
    if tree is None:
        return []

    results = []
    for fig in tree.xpath('//figure[contains(@class,"gall-img")]'):
        # --- Cover URL and type ---
        link_els = fig.xpath('.//a[@itemprop="url"]')
        if not link_els:
            continue
        cover_url = link_els[0].get("href", "").strip()
        if not cover_url:
            continue

        # Determine cover type from the title attribute, which contains either
        # "video from" or "gallery from".  Used to filter results by caller.
        title_attr = link_els[0].get("title", "")
        if "video from" in title_attr.lower():
            this_type = "video"
        elif "gallery from" in title_attr.lower():
            this_type = "gallery"
        else:
            this_type = "unknown"

        if cover_type is not None and this_type != cover_type:
            continue

        # --- Set title ---
        meta_content = fig.xpath(
            './/meta[@itemprop="description name"]/@content'
        )
        set_title = (
            extract_cover_title(meta_content[0]) if meta_content else None
        )
        if not set_title:
            # Fall back: strip " (video|gallery) from ..." from title attribute
            set_title = re.sub(
                r"\s+(video|gallery|photos?)\s+from\s+.*$",
                "", title_attr, flags=re.IGNORECASE
            ).strip()
            # The title attr also starts with "Performer in …", so we need
            # only the set name — but without the meta tag we cannot cleanly
            # separate them; use the whole remainder as a best effort.

        # --- Date ---
        date_els = fig.xpath('.//div[@itemprop="datePublished"]/text()')
        date = parse_cover_date(date_els[0]) if date_els else None

        # --- Performers ---
        performers = []
        for a in fig.xpath('.//a[@class="model-title"]'):
            perf_name = a.text_content().strip()
            perf_href = a.get("href", "").strip()
            if perf_name:
                entry = {"name": perf_name}
                if perf_href:
                    entry["urls"] = [normalize_url(perf_href)]
                performers.append(entry)

        # --- Studio ---
        studio_els = fig.xpath('.//div[@class="website"]//a/text()')
        studio = {"name": studio_els[0].strip()} if studio_els else None

        # --- Thumbnail ---
        thumb_els = fig.xpath('.//img[@itemprop="thumbnailUrl"]/@src')
        image = thumb_els[0].strip() if thumb_els else None

        result = {"title": set_title, "url": cover_url}
        if date:
            result["date"] = date
        if studio:
            result["studio"] = studio
        if performers:
            result["performers"] = performers
        if image:
            result["image"] = image

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    op, args = scraper_args()

    if op == "performer-by-url":
        url = args.get("url", "")
        if not url:
            log.error("No URL provided")
            print("{}")
            sys.exit(1)
        tree = fetch_page(url)
        if tree is None:
            print("{}")
            sys.exit(1)
        print(json.dumps(scrape_performer_page(tree, url)))

    elif op == "performer-by-name":
        name = args.get("name", "")
        if not name:
            log.error("No name provided")
            print("[]")
            sys.exit(1)
        print(json.dumps(search_performers(name)))

    elif op == "scene-by-name":
        # sceneByName receives {"name": "<text>"} from a search popup.
        # Returns a picker list of video covers matching the search text.
        name = args.get("name", "")
        if not name:
            log.error("No name provided")
            print("[]")
            sys.exit(1)
        print(json.dumps(search_covers(name, cover_type="video")))

    elif op == "scene-by-query-fragment":
        # Called by Stash AFTER the user picks a result from the magnifying-glass
        # picker (which is powered by scene-by-name). Stash sends the picked
        # result's data — including its URL — and expects a SINGLE ScrapedScene
        # back, not an array.
        url = args.get("url", "").strip()
        title = args.get("title", "").strip()
        if url:
            # Look up the picked URL in a fresh title search and return
            # that one entry. Falls back to a URL-only stub if no match.
            results = search_covers(title or " ", cover_type="video") if title else []
            match = next((r for r in results if r.get("url") == url), None)
            print(json.dumps(match if match else {"url": url}))
        elif title:
            # Edge case: no URL provided, behave like a search.
            results = search_covers(title, cover_type="video")
            print(json.dumps(results[0] if results else {}))
        else:
            log.error("No title or URL provided")
            print("{}")
            sys.exit(1)

    elif op == "gallery-by-fragment":
        # galleryByFragment must return a single ScrapedGallery object, not an
        # array — there is no galleryByQueryFragment equivalent in Stash schema.
        # Return the first (best) match from the search, or {} if nothing found.
        title = args.get("title", "")
        if not title:
            log.error("No title provided")
            print("{}")
            sys.exit(1)
        results = search_covers(title, cover_type="gallery")
        # Stash's ScrapedGallery model has no image field — strip it
        # to avoid "unknown field" warnings on the gallery scrape.
        best = results[0] if results else {}
        best.pop("image", None)
        print(json.dumps(best))

    else:
        log.error(f"Unknown operation: {op}")
        sys.exit(1)
