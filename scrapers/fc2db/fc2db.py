"""FC2DB scraper for Stash — scrapes scene and performer data from fc2db.net

Uses JSON-LD structured data as the primary extraction method,
with HTML XPath fallback for fields not in JSON-LD (tags, mosaic status).
No authentication required.
"""
import json
import os
import re
import sys

try:
    from py_common import log
    from py_common.util import scraper_args
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! "
        "(CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import lxml.html
except ModuleNotFoundError:
    print(
        "You need to install the lxml module. (pip install lxml)",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import requests
except ModuleNotFoundError:
    print(
        "You need to install the requests module. (pip install requests)",
        file=sys.stderr,
    )
    sys.exit(1)


BASE_URL = "https://fc2db.net"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_page(url: str) -> lxml.html.HtmlElement | None:
    """Fetch a page and return the parsed HTML tree, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return lxml.html.fromstring(resp.content)
    except requests.RequestException as exc:
        log.error(f"Failed to fetch {url}: {exc}")
        return None


def extract_jsonld(tree: lxml.html.HtmlElement, expected_type: str) -> dict | None:
    """Extract the first JSON-LD block matching the expected @type."""
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            data = json.loads(script.text_content())
            if data.get("@type") == expected_type:
                return data
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def duration_to_seconds(duration_str: str) -> int | None:
    """Convert HH:MM:SS or MM:SS to total seconds."""
    if not duration_str:
        return None
    parts = duration_str.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass
    return None


def extract_fc2_number(text: str) -> str | None:
    """Extract an FC2 number (5+ digits) from a string."""
    match = re.search(r"(\d{5,})", text)
    return match.group(1) if match else None


def work_url_from_number(number: str) -> str:
    """Construct the fc2db work URL from an FC2 number."""
    return f"{BASE_URL}/work/{number}/"


# ---------------------------------------------------------------------------
# Scene scraping
# ---------------------------------------------------------------------------

def scene_from_url(url: str) -> dict:
    """Scrape a scene from a fc2db.net work page."""
    tree = fetch_page(url)
    if tree is None:
        return {}

    scene = {}

    # --- Primary: JSON-LD VideoObject ---
    ld = extract_jsonld(tree, "VideoObject")

    if ld:
        log.debug(f"Found JSON-LD VideoObject: {json.dumps(ld, ensure_ascii=False)[:200]}")

        # Title: JSON-LD "name" is typically "FC2PPV-NNNNNN"
        # Use the full title from <h1> instead, which includes the actual title text
        ld_name = ld.get("name", "")
        fc2_number = extract_fc2_number(ld_name)

        # Code
        if fc2_number:
            scene["code"] = f"FC2-PPV-{fc2_number}"

        # Date
        upload_date = ld.get("uploadDate", "")
        if upload_date:
            scene["date"] = upload_date

        # Duration
        duration_val = duration_to_seconds(ld.get("duration", ""))
        if duration_val:
            scene["duration"] = duration_val

        # Cover image
        thumbnail = ld.get("thumbnailUrl", "")
        if thumbnail:
            scene["image"] = thumbnail

        # Performers from JSON-LD actors
        actors = ld.get("actor", [])
        if isinstance(actors, dict):
            actors = [actors]
        performers = []
        for actor in actors:
            name = actor.get("name", "").strip()
            if name:
                actor_url = actor.get("url", "")
                if actor_url:
                    # Fetch full performer details (images, aliases) from their profile page
                    perf = performer_from_url(actor_url)
                else:
                    perf = {"name": name, "gender": "FEMALE"}
                performers.append(perf)
        if performers:
            scene["performers"] = performers

        # Director (seller/publisher)
        publisher = ld.get("publisher", {})
        if isinstance(publisher, dict):
            pub_name = publisher.get("name", "").strip()
            if pub_name:
                scene["director"] = pub_name

        # URL from JSON-LD
        ld_url = ld.get("url", "")
        if ld_url:
            scene["urls"] = [ld_url]
    else:
        log.warning("No JSON-LD VideoObject found, falling back to HTML only")
        scene["urls"] = [url]

    # --- HTML fallback / supplemental ---

    # Full title from <h1> (includes [FC2-PPV-NNNN] prefix + actual title)
    h1_elements = tree.xpath('//h1[contains(@class, "text-2xl")]')
    if h1_elements:
        full_title = h1_elements[0].text_content().strip()
        # Strip the [FC2-PPV-NNNN] prefix if present to get the clean title
        clean_title = re.sub(r"^\[FC2-PPV-\d+\]\s*", "", full_title).strip()
        if clean_title:
            scene["title"] = clean_title
        elif full_title:
            scene["title"] = full_title

    # Extract code from title if not already set from JSON-LD
    if "code" not in scene and h1_elements:
        h1_text = h1_elements[0].text_content()
        num = extract_fc2_number(h1_text)
        if num:
            scene["code"] = f"FC2-PPV-{num}"

    # Cover image fallback from og:image
    if "image" not in scene:
        og_images = tree.xpath('//meta[@property="og:image"]/@content')
        if og_images:
            scene["image"] = og_images[0]

    # Tags — extracted from work-tags links (NOT in JSON-LD)
    tag_elements = tree.xpath('//a[contains(@href, "/work-tags/")]')
    tags = []
    for tag_el in tag_elements:
        tag_name = tag_el.text_content().strip()
        if tag_name:
            tags.append({"name": tag_name})
    if tags:
        scene["tags"] = tags

    # Mosaic status — from the <dl> metadata grid
    dt_elements = tree.xpath('//dt[contains(@class, "text-text-sub")]')
    for dt in dt_elements:
        label = dt.text_content().strip()
        dd = dt.getnext()
        if dd is not None and label == "モザイク":
            mosaic_val = dd.text_content().strip()
            if mosaic_val == "なし":
                # Add "無修正" (uncensored) tag if not already present
                uncensored_tag = {"name": "無修正"}
                if not any(t.get("name") == "無修正" for t in tags):
                    scene.setdefault("tags", []).append(uncensored_tag)
            break

    # Performers fallback — from HTML links if not already set from JSON-LD
    if "performers" not in scene:
        perf_links = tree.xpath('//a[contains(@href, "/actress/")]')
        performers = []
        for link in perf_links:
            name = link.text_content().strip()
            href = link.get("href", "")
            # Filter out navigation links (only include actress profile links)
            if name and "/actress/" in href and href != f"{BASE_URL}/actress/":
                if href.startswith("http"):
                    perf = performer_from_url(href)
                else:
                    perf = {"name": name, "gender": "FEMALE"}
                performers.append(perf)
        if performers:
            scene["performers"] = performers

    # Director fallback — from seller link if not already set
    if "director" not in scene:
        seller_names = tree.xpath('//a[contains(@href, "/seller/")]//span[contains(@class, "font-medium")]/text()')
        if seller_names:
            scene["director"] = seller_names[0].strip()

    # Fixed studio
    scene["studio"] = {"name": "FC2"}

    log.info(f"Scraped scene: {scene.get('code', 'unknown')} - {scene.get('title', '')[:50]}")
    return scene


# ---------------------------------------------------------------------------
# Performer scraping
# ---------------------------------------------------------------------------

def performer_from_url(url: str) -> dict:
    """Scrape a performer from a fc2db.net actress page."""
    tree = fetch_page(url)
    if tree is None:
        return {}

    performer = {}

    # --- Primary: JSON-LD Person ---
    ld = extract_jsonld(tree, "Person")

    if ld:
        log.debug(f"Found JSON-LD Person: {json.dumps(ld, ensure_ascii=False)[:200]}")

        # Name
        name = ld.get("name", "").strip()
        if name:
            performer["name"] = name

        # Image
        image = ld.get("image", "")
        if image:
            performer["images"] = [image]

        # Aliases from alternateName
        alt_names = ld.get("alternateName", [])
        if isinstance(alt_names, str):
            alt_names = [alt_names]
        if alt_names:
            performer["aliases"] = ", ".join(alt_names)

        # URLs: fc2db URL + sameAs URLs
        urls = [url]
        same_as = ld.get("sameAs", [])
        if isinstance(same_as, str):
            same_as = [same_as]
        urls.extend(same_as)
        performer["urls"] = urls

    else:
        log.warning("No JSON-LD Person found, falling back to HTML only")

        # Name from <h1> or breadcrumb
        h1_elements = tree.xpath('//h1[contains(@class, "text-2xl")]')
        if h1_elements:
            # The <h1> on actress pages says "女優紹介" (actress intro), the name is in <h2>
            pass
        # Try breadcrumb
        breadcrumb = tree.xpath('//nav[@class="mc-breadcrumb"]//span[@class="mc-breadcrumb__current"]')
        if breadcrumb:
            name = breadcrumb[-1].text_content().strip()
            if name:
                performer["name"] = name

        # Image from og:image
        og_images = tree.xpath('//meta[@property="og:image"]/@content')
        if og_images:
            performer["images"] = [og_images[0]]

        performer["urls"] = [url]

    # Gender default
    performer["gender"] = "FEMALE"

    # Country (FC2 is a Japanese platform)
    performer["country"] = "Japan"

    log.info(f"Scraped performer: {performer.get('name', 'unknown')}")
    return performer


# ---------------------------------------------------------------------------
# Filename → URL resolution
# ---------------------------------------------------------------------------

def url_from_fragment(args: dict) -> str | None:
    """Extract an FC2 number from scene fragment data and construct a URL."""
    # Try title/code first
    for field in ("code", "title"):
        value = args.get(field, "")
        if value:
            num = extract_fc2_number(value)
            if num:
                return work_url_from_number(num)

    # Try URLs
    for u in args.get("urls", []):
        if "fc2db.net/work/" in u:
            return u
        num = extract_fc2_number(u)
        if num:
            return work_url_from_number(num)

    # Try files (for scene-by-fragment via stdin)
    files = args.get("files", [])
    if files:
        filepath = files[0].get("path") if isinstance(files[0], dict) else str(files[0])
        if filepath:
            # Try basename first
            basename = os.path.basename(filepath)
            num = extract_fc2_number(basename)
            if num:
                return work_url_from_number(num)
            # Fallback to parent directory
            parent = os.path.basename(os.path.dirname(filepath))
            num = extract_fc2_number(parent)
            if num:
                return work_url_from_number(num)

    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    if op == "scene-by-url":
        url = args.get("url", "")
        if url:
            scene = scene_from_url(url)
            result = scene if scene else None
        else:
            log.error("No URL provided for scene-by-url")
            sys.exit(1)

    elif op == "scene-by-name":
        name = args.get("name", "")
        if not name:
            log.error("No name provided for scene-by-name")
            sys.exit(1)
        num = extract_fc2_number(name)
        if num:
            url = work_url_from_number(num)
            scene = scene_from_url(url)
            result = [scene] if scene else []
        else:
            log.error(f"Could not extract FC2 number from: {name}")
            result = []

    elif op in ("scene-by-fragment", "scene-by-query-fragment"):
        url = url_from_fragment(args)
        if url:
            scene = scene_from_url(url)
            result = scene if scene else None
        else:
            log.error("Could not extract FC2 number from fragment data")
            sys.exit(1)

    elif op == "performer-by-url":
        url = args.get("url", "")
        if url:
            performer = performer_from_url(url)
            result = performer if performer else None
        else:
            log.error("No URL provided for performer-by-url")
            sys.exit(1)

    else:
        log.error(f"Unknown operation: {op}, arguments: {json.dumps(args)}")
        sys.exit(1)

    print(json.dumps(result))
