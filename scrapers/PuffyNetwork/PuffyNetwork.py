import json
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

import requests
from lxml import html

import py_common.log as log
from py_common.util import scraper_args

# Maps bare sub-site domain → (network slug prefix, display name)
# eurobabefacials.com is excluded from URL construction — it has merged into
# puffynetwork.com and redirects there. See PREFIX_IMAGE_DOMAIN_MAP below.
SITE_MAP = {
    "wetandpuffy.com":  ("wnp-", "Wet And Puffy"),
    "wetandpissy.com":  ("wps-", "Wet And Pissy"),
    "weliketosuck.com": ("wls-", "We Like To Suck"),
    "simplyanal.com":   ("ana-", "Simply Anal"),
}

# Maps network slug prefix → studio display name (includes retired sites)
PREFIX_STUDIO_MAP = {
    "wnp-": "Wet And Puffy",
    "wps-": "Wet And Pissy",
    "wls-": "We Like To Suck",
    "ana-": "Simply Anal",
    "ebf-": "Euro Babe Facials",
}

# Maps network slug prefix → media CDN domain for image construction.
# eurobabefacials.com main site redirects to puffynetwork.com but CDN still serves images.
PREFIX_IMAGE_DOMAIN = {
    "wnp-": "wetandpuffy.com",
    "wps-": "wetandpissy.com",
    "wls-": "weliketosuck.com",
    "ana-": "simplyanal.com",
    "ebf-": "eurobabefacials.com",
}

# Maps the site name as it appears on puffynetwork.com → display name
STUDIO_NAME_MAP = {
    "Wetandpuffy":     "Wet And Puffy",
    "Wetandpissy":     "Wet And Pissy",
    "Weliketosuck":    "We Like To Suck",
    "Simplyanal":      "Simply Anal",
    "Eurobabefacials": "Euro Babe Facials",
}


def normalize_url(url):
    """
    Accept any recognized URL variant and return a tuple:
      (canonical_url, network_slug, subsite_domain, subsite_slug)

    canonical_url is always https://www.puffynetwork.com/videos/{network_slug}/
    subsite_domain and subsite_slug are None if no sub-site prefix is recognized.
    Returns None if the URL cannot be parsed or recognized.
    """
    parsed = urlparse(url)
    # Strip www. or members. to get the bare hostname
    hostname = re.sub(r'^(www\.|members\.)', '', parsed.netloc.lower())

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2 or path_parts[0] != "videos":
        log.error(f"URL does not look like a video page: {url}")
        return None

    slug = path_parts[1]

    if hostname == "puffynetwork.com":
        network_slug = slug
        subsite_domain = None
        subsite_slug = None
        for domain, (prefix, _) in SITE_MAP.items():
            if slug.startswith(prefix):
                subsite_domain = domain
                subsite_slug = slug[len(prefix):]
                break

    elif hostname in SITE_MAP:
        prefix, _ = SITE_MAP[hostname]
        subsite_domain = hostname
        subsite_slug = slug
        network_slug = prefix + slug

    else:
        log.error(f"Unrecognized hostname: {hostname}")
        return None

    canonical_url = f"https://www.puffynetwork.com/videos/{network_slug}/"
    return canonical_url, network_slug, subsite_domain, subsite_slug


def build_urls(network_slug, subsite_domain, subsite_slug):
    """Return the four canonical URL variants for this scene."""
    urls = [
        f"https://www.puffynetwork.com/videos/{network_slug}/",
        f"https://members.puffynetwork.com/videos/{network_slug}/",
    ]
    if subsite_domain and subsite_slug:
        urls += [
            f"https://www.{subsite_domain}/videos/{subsite_slug}/",
            f"https://members.{subsite_domain}/videos/{subsite_slug}/",
        ]
    return urls


def scrape(url):
    """
    Fetch and parse a puffynetwork.com video page.
    Used for both scene-by-url and gallery-by-url — the page contains
    all relevant metadata for both.
    Returns a dict suitable for JSON output, or None on failure.
    """
    result = normalize_url(url)
    if result is None:
        return None

    canonical_url, network_slug, subsite_domain, subsite_slug = result
    log.debug(f"Fetching: {canonical_url}")

    try:
        resp = requests.get(canonical_url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch {canonical_url}: {e}")
        return None

    tree = html.fromstring(resp.text)

    # Title: strip leading "Performer — " prefix
    title = ""
    title_nodes = tree.xpath("//h2[@class='title']/span/text()")
    if title_nodes:
        title = re.sub(r'^.*[—]\s+', '', title_nodes[0].strip())

    # Date: parse "Feb 27, 2026" → "2026-02-27"
    date = ""
    date_nodes = tree.xpath("//dl/dt[contains(text(),'Released on:')]/span/text()")
    if date_nodes:
        try:
            date = datetime.strptime(date_nodes[0].strip(), "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError as e:
            log.warning(f"Could not parse date '{date_nodes[0].strip()}': {e}")

    # Performers
    performers = [
        {"name": n.strip()}
        for n in tree.xpath("//dl/dd/a/text()")
        if n.strip()
    ]

    # Studio: derived from the site name in the title bar, or from the slug prefix
    # for legacy content (e.g. ebf- prefix for Euro Babe Facials)
    studio = None
    studio_nodes = tree.xpath(
        "//h2[@class='title']//div[contains(text(),'Site:')]/a/text()"
    )
    if studio_nodes:
        raw = studio_nodes[0].strip()
        studio = {"name": STUDIO_NAME_MAP.get(raw, raw)}
    elif network_slug:
        for prefix, name in PREFIX_STUDIO_MAP.items():
            if network_slug.startswith(prefix):
                studio = {"name": name}
                break

    # Details: first text node inside show_more div, before the tags paragraph
    details = ""
    details_nodes = tree.xpath("//div[@class='show_more']/text()")
    if details_nodes:
        details = details_nodes[0].strip()

    # Tags
    tags = [
        {"name": t.strip()}
        for t in tree.xpath("//p[@class='tags']/a/text()")
        if t.strip()
    ]

    # Cover image: poster attribute is set by JavaScript so it's not in the
    # server-rendered HTML. Construct directly from the CDN domain and sub-site slug.
    # eurobabefacials.com CDN still serves images even though main site redirects.
    image = ""
    for prefix, domain in PREFIX_IMAGE_DOMAIN.items():
        if network_slug.startswith(prefix):
            subsite_slug_for_image = network_slug[len(prefix):]
            image = f"https://media.{domain}/videos/{subsite_slug_for_image}/cover/hd.jpg"
            break

    # URLs
    urls = build_urls(network_slug, subsite_domain, subsite_slug)

    output = {
        "title": title,
        "date": date,
        "details": details,
        "urls": urls,
        "performers": performers,
        "tags": tags,
        "image": image,
    }
    if studio:
        output["studio"] = studio

    return output


if __name__ == "__main__":
    op, args = scraper_args()
    url = args.get("url")

    if op in ("scene-by-url", "gallery-by-url"):
        if not url:
            log.error("No URL provided")
            print(json.dumps({}))
            sys.exit(1)
        result = scrape(url)
        print(json.dumps(result or {}))

    else:
        log.error(f"Unknown operation: {op}")
        print(json.dumps({}))
        sys.exit(1)
