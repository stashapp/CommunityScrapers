import json
import re
import sys
from datetime import datetime
from typing import cast

from py_common import log
from py_common.deps import ensure_requirements
from py_common.proxy import stash_requests
from py_common.types import Ethnicity, EyeColor, HairColor, ScrapedPerformer
from py_common.util import guess_nationality, scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402


def fetch(url: str) -> html.HtmlElement | None:
    # Cloudflare blocks plain requests, py_common.proxy falls back to FlareSolverr
    try:
        response = stash_requests.get(url)
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as e:  # noqa: BLE001
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if response.status_code != 200:
        log.error(f"HTTP {response.status_code} for {url}")
        return None
    return html.document_fromstring(response.text)


def bio(tree: html.HtmlElement, key: str) -> str | None:
    values = tree.xpath(
        f'//table[contains(@class, "biography")]//th[text()="{key}:"]/following-sibling::td//text()'
    )
    return "".join(values).strip() or None


def parse_date(text: str) -> str | None:
    # Dates come with the age appended: "March 4, 1990 (age 35)", some lack the year
    if match := re.search(r"\w+ \d+, \d{4}", text):
        return datetime.strptime(match.group(), "%B %d, %Y").strftime("%Y-%m-%d")
    if match := re.search(r"\d{4}", text):
        return match.group()
    return None


def centimeters(text: str) -> str | None:
    "Height in cm, from either '160 cm (5 ft 3 in)' or '1.63 m (5 ft 4 in)'"
    if match := re.search(r"(\d+)\s*cm", text):
        return match.group(1)
    if match := re.search(r"(\d)[.,](\d{2})\s*m\b", text):
        return match.group(1) + match.group(2)
    return None


def full_size(image: str) -> str:
    # Wiki thumbnails live under /thumb/ with the width appended to the file name
    return re.sub(r"/\d+px.*$", "", image.replace("/thumb/", "/"))


def performer_from_url(url: str) -> ScrapedPerformer | None:
    # The English articles moved from www. to en.
    url = url.replace("://www.pornopedia.com/", "://en.pornopedia.com/")
    if (tree := fetch(url)) is None:
        return None
    if not (name := "".join(tree.xpath('//h1[@id="firstHeading"]//text()')).strip()):
        log.error(f"No performer name found on {url}")
        return None

    performer: ScrapedPerformer = {"name": name, "urls": [url]}
    if (birthdate := bio(tree, "Date of birth")) and (date := parse_date(birthdate)):
        performer["birthdate"] = date
    if country := bio(tree, "Nationality"):
        performer["country"] = guess_nationality(country)
    # Bust-waist-hip in cm comes first: "81-61-86 cm(32-24-34 in)XS-XS-XS"
    if (sizes := bio(tree, "Measurements")) and (
        cm := re.search(r"\d+-\d+-\d+", sizes)
    ):
        performer["measurements"] = cm.group()
    elif bra_size := bio(tree, "Bra size"):
        performer["measurements"] = bra_size
    # Stash takes free text here, so the site's own labels pass through as-is
    if eye_color := bio(tree, "Eye color"):
        performer["eye_color"] = cast(EyeColor, eye_color)
    if hair_color := bio(tree, "Hair color"):
        performer["hair_color"] = cast(HairColor, hair_color)
    if ethnicity := bio(tree, "Ethnicity"):
        performer["ethnicity"] = cast(Ethnicity, ethnicity)
    if (height := bio(tree, "Height")) and (cm := centimeters(height)):
        performer["height"] = cm
    if (weight := bio(tree, "Weight")) and (kg := re.search(r"(\d+)\s*kg", weight)):
        performer["weight"] = kg.group(1)
    if aliases := bio(tree, "Alias(es)"):
        performer["aliases"] = aliases
    # Articles without a photo show a "Photo needed" placeholder
    if (image := tree.xpath('//td[@class="infobox-image"]//img/@src')) and (
        "Photo_needed" not in image[0]
    ):
        performer["images"] = [full_size(image[0])]
    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
