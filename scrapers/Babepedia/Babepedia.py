import base64
import json
import re
import sys
from datetime import datetime
from urllib.parse import urljoin

from py_common import log
from py_common.deps import ensure_requirements
from py_common.proxy import StashRequests
from py_common.types import (
    Ethnicity,
    EyeColor,
    HairColor,
    PerformerSearchResult,
    ScrapedPerformer,
)
from py_common.util import scraper_args

ensure_requirements("lxml")
from lxml import html

BASE_URL = "https://www.babepedia.com"

scraper = StashRequests(cloudflare=True)

ETHNICITIES: dict[str, Ethnicity] = {
    "caucasian": "Caucasian",
    "white": "Caucasian",
    "black": "Black",
    "asian": "Asian",
    "indian": "Indian",
    "latin": "Latin",
    "latina": "Latin",
    "middle eastern": "Middle Eastern",
    "middle_eastern": "Middle Eastern",
    "mixed": "Mixed",
    "other": "Other",
}

EYE_COLORS: dict[str, EyeColor] = {
    "blue": "Blue",
    "brown": "Brown",
    "green": "Green",
    "grey": "Grey",
    "gray": "Grey",
    "hazel": "Hazel",
    "red": "Red",
}

HAIR_COLORS: dict[str, HairColor] = {
    "blond": "Blonde",
    "blonde": "Blonde",
    "brown": "Brunette",
    "brunette": "Brunette",
    "black": "Black",
    "red": "Red",
    "auburn": "Auburn",
    "grey": "Grey",
    "gray": "Grey",
    "white": "White",
    "bald": "Bald",
    "various": "Various",
    "other": "Other",
}

# "Fake"/"Natural" is what Stash itself writes when importing from stash-box
BREAST_TYPES = {
    "fake/enhanced": "Fake",
    "real/natural": "Natural",
    "fake": "Fake",
    "enhanced": "Fake",
    "augmented": "Fake",
    "natural": "Natural",
    "real": "Natural",
}


def bio_field(tree, label: str, selector: str = "") -> str | None:
    elem = tree.xpath(
        f'//span[contains(text(), "{label}")]/following-sibling::span{selector}/text()'
    )
    return elem[0].strip() if elem else None


def parse_date(text: str) -> str | None:
    # "9th of July 1991"
    if m := re.search(r"(\d+)(?:st|nd|rd|th) of (\w+) (\d{4})", text):
        return datetime.strptime(" ".join(m.groups()), "%d %B %Y").date().isoformat()
    log.warning(f"Unrecognised date skipped: {text}")
    return None


def to_ethnicity(value: str) -> Ethnicity | None:
    # Babepedia writes e.g. "Mixed-race (primarily Caucasian)"
    normalized = value.lower()
    return ETHNICITIES.get(normalized) or ("Mixed" if "mixed" in normalized else None)


def image_data_uri(url: str) -> str | None:
    # Stash can't get past Babepedia's Cloudflare on its own, so images are fetched here
    res = scraper.get(url)
    if res.ok and (mime := res.headers.get("Content-Type", "")).startswith("image/"):
        return f"data:{mime};base64,{base64.b64encode(res.content).decode()}"
    log.warning(f"Image did not load, skipped: {url}")
    return None


def performer_from_url(url: str) -> ScrapedPerformer:
    res = scraper.get(url)
    res.raise_for_status()
    tree = html.fromstring(res.text)

    performer: ScrapedPerformer = {
        "name": tree.xpath('//h1[@id="babename"]')[0].text.strip(),
        "urls": [url],
        "gender": "FEMALE",
    }
    if aliases := tree.xpath('//h2[@id="aka"][1]/text()'):
        performer["aliases"] = ", ".join(aliases[0].strip().split(" - "))

    born = [
        a.text_content().strip()
        for a in tree.xpath(
            '//span[contains(text(), "Born:")]/following-sibling::span/a'
        )
    ]
    match born:
        case [year]:
            performer["birthdate"] = year
        case [day_month, year] if birthdate := parse_date(f"{day_month} {year}"):
            performer["birthdate"] = birthdate
    if (died := bio_field(tree, "Died")) and (death_date := parse_date(died)):
        performer["death_date"] = death_date
    if (career := bio_field(tree, "Years active")) and (
        m := re.match(r"(\d{4})(?:\s*[-–]\s*(\d{4}))?", career)
    ):
        performer["career_start"] = m[1]
        if m[2]:
            performer["career_end"] = m[2]

    # Only the first nationality, read from its flag icon's ISO code
    if (
        flags := tree.xpath(
            '//span[contains(text(), "Nationality")]/following-sibling::span//span[contains(@class, "fi-")]/@class'
        )
    ) and (m := re.search(r"fi fi-([a-z]{2})", flags[0])):
        performer["country"] = m[1].upper()
    if (ethnicity := bio_field(tree, "Ethnicity", "/a")) and (
        value := to_ethnicity(ethnicity)
    ):
        performer["ethnicity"] = value
    if (eye_color := bio_field(tree, "Eye color", "/a")) and (
        value := EYE_COLORS.get(eye_color.lower())
    ):
        performer["eye_color"] = value
    if (hair_color := bio_field(tree, "Hair color", "/a")) and (
        value := HAIR_COLORS.get(hair_color.lower())
    ):
        performer["hair_color"] = value

    if (height := bio_field(tree, "Height")) and (m := re.search(r"(\d+) cm", height)):
        performer["height"] = m[1]
    if (weight := bio_field(tree, "Weight")) and (m := re.search(r"(\d+) kg", weight)):
        performer["weight"] = m[1]
    if measurements := bio_field(tree, "Measurements"):
        # The bust in "36–23–32 in" is a band-less number, the bra size carries the cup
        if (cup_size := bio_field(tree, "Bra/cup size")) and (
            m := re.search(r"\d+[–-](\d+)[–-](\d+)", measurements)
        ):
            performer["measurements"] = f"{cup_size}-{m[1]}-{m[2]}"
        else:
            performer["measurements"] = measurements.removesuffix(" (")
    if (breasts := bio_field(tree, "Boobs", "/a")) and (
        value := BREAST_TYPES.get(breasts.lower())
    ):
        performer["fake_tits"] = value
    if (tattoos := bio_field(tree, "Tattoos")) and tattoos != "None":
        performer["tattoos"] = tattoos
    if (piercings := bio_field(tree, "Piercings")) and piercings != "None":
        performer["piercings"] = piercings
    if bio := tree.xpath('//p[@id="biotext"]'):
        performer["details"] = bio[0].text_content().strip()

    for href in tree.xpath('//div[@id="socialicons"]/a/@href'):
        # Babepedia proxies some links through its own domain, both relative and absolute
        href = re.sub(
            r"^(?:https://www\.babepedia\.com)?/onlyfans/",
            "https://onlyfans.com/",
            href,
        )
        if href.startswith("http"):
            performer["urls"].append(href)
        else:
            log.warning(f"Unrecognised relative URL skipped: {href}")

    # Main gallery first, then user uploads
    hrefs = tree.xpath('//div[@id="profbox2"]//a[@class="img"]/@href') + tree.xpath(
        '//div[contains(@class,"useruploads2")]//a[@class="img"]/@href'
    )
    if images := [
        image for href in hrefs if (image := image_data_uri(urljoin(BASE_URL, href)))
    ]:
        performer["images"] = images
    return performer


def performer_by_name(name: str) -> list[PerformerSearchResult]:
    # dashes stripped #2671
    res = scraper.get(
        f"{BASE_URL}/ajax-search.php", params={"term": name.replace("-", " ")}
    )
    res.raise_for_status()
    # The trailing "Search for <name>..." entry links to the full results page, not a performer
    return [
        {"name": p["label"], "url": f"{BASE_URL}/babe/{p['value'].replace(' ', '_')}"}
        for p in res.json()
        if p.get("type") != "search"
    ]


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
