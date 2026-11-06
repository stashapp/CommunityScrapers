import base64
import json
import re
import sys
from datetime import datetime

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer
from py_common.util import guess_nationality, scraper_args

ensure_requirements("lxml", "curl_cffi")

from curl_cffi import requests
from lxml import html

# Stash downloads scraped image URLs with its own Go client, which IAFD's WAF
# rejects, so headshots have to be fetched here with a browser TLS fingerprint
client = requests.Session(impersonate="chrome")

EMPTY_VALUES = re.compile(r"no data|no director|none|unknown", re.IGNORECASE)

GENDERS = {
    "Woman": "FEMALE",
    "Man": "MALE",
    "Trans woman": "TRANSGENDER_FEMALE",
    "Trans man": "TRANSGENDER_MALE",
}

HAIR_COLORS = {
    "Blond": "Blonde",
    "Brown": "Brunette",
    "Dark Brown": "Brunette",
    "Red": "Redhead",
    "Grey": "Gray",
}


def bio(tree, *headings: str) -> str | None:
    "Value under the first matching bio heading, unless IAFD marks it as missing"
    match_heading = " or ".join(f'normalize-space()="{h}"' for h in headings)
    if (
        (
            values := tree.xpath(
                f'//p[@class="bioheading"][{match_heading}]/following-sibling::p[1]'
            )
        )
        and (value := values[0].text_content().strip())
        and not EMPTY_VALUES.search(value)
    ):
        return value


def parse_date(value: str) -> str | None:
    # "August 8, 1944 (would be 82 years old)", "March 13, 1988 (details)"
    if date := re.match(r"\w+ \d{1,2}, \d{4}", value):
        for date_format in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(date.group(), date_format).strftime("%Y-%m-%d")
            except ValueError:
                pass
    log.warning(f"Unable to parse '{value}' as a date")


def aliases(tree) -> list[str]:
    return [
        re.sub(r"\s*\(.*$", "", alias)
        for alias in map(
            str.strip,
            tree.xpath(
                '//p[@class="bioheading"][normalize-space()="AKA" or normalize-space()="Performer AKA"]'
                '/following-sibling::div[@class="biodata"][1]/text()'
            ),
        )
        # "X or Y" is indeterminate
        if alias and alias != "No known aliases" and " or " not in alias
    ]


def headshot(url: str) -> str | None:
    if not (response := client.get(url)).ok:
        log.warning(f"Unable to fetch headshot {url}: HTTP {response.status_code}")
        return None
    mime = response.headers.get("content-type", "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(response.content).decode()}"


def to_scraped_performer(tree) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": tree.xpath("//h1")[0].text_content().strip()}

    if gender := bio(tree, "Gender"):
        performer["gender"] = GENDERS.get(gender, gender)  # type: ignore

    urls = [
        u.replace("matchups", "person") for u in tree.xpath("//*[@data-src]/@data-src")
    ]
    urls += tree.xpath('//a[@target="starlet"][img]/@href')
    if urls:
        performer["urls"] = urls

    if (birthday := bio(tree, "Birthday")) and (birthdate := parse_date(birthday)):
        performer["birthdate"] = birthdate

    if (death := bio(tree, "Date of Death")) and (death_date := parse_date(death)):
        performer["death_date"] = death_date

    if ethnicity := bio(tree, "Ethnicity"):
        performer["ethnicity"] = ethnicity  # type: ignore

    if nationality := bio(tree, "Nationality"):
        performer["country"] = guess_nationality(nationality)

    if (height := bio(tree, "Height")) and (cm := re.search(r"\((\d+)\s+cm", height)):
        performer["height"] = cm.group(1)

    if (weight := bio(tree, "Weight")) and (kg := re.search(r"\((\d+)\s+kg", weight)):
        performer["weight"] = kg.group(1)

    if hair_color := bio(tree, "Hair Color", "Hair Colors"):
        performer["hair_color"] = HAIR_COLORS.get(hair_color, hair_color)  # type: ignore

    if eye_color := bio(tree, "Eye Color"):
        performer["eye_color"] = eye_color  # type: ignore

    if measurements := bio(tree, "Measurements"):
        performer["measurements"] = measurements

    # "2003-2026 (Started around 18 years old)", a single year means both start and end
    if (active := bio(tree, "Years Active", "Years Active as Performer")) and (
        years := re.findall(r"\d{4}", active.split("(")[0])
    ):
        performer["career_start"] = years[0]
        # Still active if the range runs up to the current year
        if years[-1] != str(datetime.now().year):
            performer["career_end"] = years[-1]

    if tattoos := bio(tree, "Tattoos"):
        performer["tattoos"] = tattoos

    if piercings := bio(tree, "Piercings"):
        performer["piercings"] = piercings

    if aka := aliases(tree):
        performer["aliases"] = ", ".join(aka)

    if images := [
        i
        for url in tree.xpath('//div[@id="headshot"]//img/@src')
        if (i := headshot(url))
    ]:
        performer["images"] = images

    return performer


def performer_from_url(url: str) -> ScrapedPerformer:
    if not (response := client.get(url)).ok:
        log.error(f"Unable to fetch {url}: HTTP {response.status_code}")
        sys.exit(1)
    return to_scraped_performer(html.fromstring(response.content))


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
