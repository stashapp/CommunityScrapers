import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedScene, ScrapedStudio
from py_common.util import scraper_args

ensure_requirements("lxml", "requests")

import requests  # noqa: E402
from lxml import html  # noqa: E402

HEADERS = {"User-Agent": "stash-scraper/1.0"}

PARENT: ScrapedStudio = {"name": "VNA Girls"}

# StashDB models these pro-am sites under the performer's own name rather than
# the site's branding ("Best of Teal Conrad" -> "Teal Conrad"). Domains with no
# StashDB studio yet keep their site branding until one exists.
STUDIOS = {
    "angelinacastrolive.com": "Angelina Castro",
    "bestoftealconrad.com": "Best of Teal Conrad",
    "blownbyrone.com": "Blown By Rone",
    "bobbiedenlive.com": "Bobbi Eden Live",
    "carmenvalentina.com": "Carmen Valentina",
    "charleechaselive.com": "Charlee Chase",
    "deauxmalive.com": "Deauxma Live",
    "foxxedup.com": "FoXXedUp",
    "fuckedfeet.com": "Fucked Feet",
    "girlgirlmania.com": "Girl Girl Mania",
    "itscleolive.com": "It's Cleo Live",
    "jelenajensen.com": "Jelena Jensen",
    "juliaannlive.com": "Julia Ann Live",
    "kimberleelive.com": "Kimber Lee Live",
    "kink305.com": "Kink305",
    "maggiegreenlive.com": "Maggie Green Live",
    "maxinex.com": "MaxineX",
    "nikkibenz.com": "Nikki Benz",
    "ninakayy.com": "Nina Kayy",
    "pennypaxlive.com": "Penny Pax Live",
    "povmania.com": "POV Mania",
    "romemajor.com": "Rome Major",
    "rubberdoll.net": "RubberDoll.net",
    "samanthagrace.net": "Samantha Grace",
    "sarajay.com": "Sara Jay",
    "sexmywife.com": "Sex My Wife",
    "shandafay.com": "Shanda Fay",
    "siripornstar.com": "Siri Pornstar",
    "sophiedeelive.com": "Sophie Dee",
    "sunnylanelive.com": "Sunny Lane",
    "vickyathome.com": "Vicky at Home",
}

# StashDB has these as top-level studios rather than under the VNA Girls parent
NO_PARENT = {"maxinex.com", "rubberdoll.net"}


def domain_from_url(url: str) -> str:
    return re.sub(r"^www\.", "", urlparse(url).netloc.lower())


def studio_for(domain: str) -> ScrapedStudio | None:
    if not (name := STUDIOS.get(domain)):
        log.warning(f"No studio mapped for '{domain}'")
        return None
    studio: ScrapedStudio = {"name": name}
    if domain not in NO_PARENT:
        studio["parent"] = PARENT
    return studio


def clean(text: str) -> str:
    "Collapse whitespace, including the NBSP this CMS separates names with"
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def comma_list(element) -> list[str]:
    if element is None:
        return []
    return [v for part in element.text_content().split(",") if (v := clean(part))]


def details_from(element) -> str | None:
    "The description is one block with <br> line breaks, which text_content() drops"
    if element is None:
        return None
    markup = html.tostring(element, encoding="unicode")
    text = html.fromstring(re.sub(r"<br\s*/?>", "\n", markup)).text_content()
    lines = "\n".join(clean(line) for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", lines).strip() or None


def parse_date(text: str | None) -> str | None:
    if not (
        text
        and (
            m := re.search(
                r"([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th)? (\d{4})", clean(text)
            )
        )
    ):
        return None
    try:
        return datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%B %d %Y").strftime(  # noqa: DTZ007
            "%Y-%m-%d"
        )
    except ValueError:
        log.warning(f"Unparseable date: '{text}'")
        return None


def first(values: list, default=None):
    return values[0] if values else default


def image_from(tree, url: str) -> str | None:
    if image := first(tree.xpath('//img[contains(@src, "sd3.php?show=file")]/@src')):
        return image
    if trailer := first(tree.xpath('//video[starts-with(@id, "trailer_")]/@id')):
        path = f"/sd3.php?show=file&path=/videos/{trailer.removeprefix('trailer_')}/thumb_1.jpg"
        return urljoin(url, path)
    return None


def scene_from_url(url: str) -> ScrapedScene | None:
    res = requests.get(url, headers=HEADERS, timeout=30)
    if not res.ok:
        log.error(f"Request to '{url}' failed with status {res.status_code}")
        return None

    tree = html.fromstring(res.content)
    # Every asset on these pages is relative and the markup sets <base href="/">
    # so this is necessary for images etc.
    tree.make_links_absolute(url, resolve_base_href=True)
    if (content := first(tree.xpath('//*[contains(@class, "customcontent")]'))) is None:
        log.error(f"No scene content found at '{url}'")
        return None

    scene: ScrapedScene = {"urls": [url]}

    if title := clean(
        first(content.xpath("./h1//text()"), "")
        or first(tree.xpath("//head/title/text()"), "")
    ):
        scene["title"] = title
    # The description element is a <div> on most sites and an <h2> on others
    if details := details_from(
        first(content.xpath('.//*[contains(@class, "customhcolor2")]'))
    ):
        scene["details"] = details
    # The date is a <div> on most sites and a <span> on others, inside a wrapper whose own class also contains "date"
    if date := parse_date(
        first(
            tree.xpath(
                '//*[contains(@class, "date-and-covers")]'
                '//*[contains(concat(" ", normalize-space(@class), " "), " date ")]/text()'
            )
        )
    ):
        scene["date"] = date
    if performers := comma_list(first(content.xpath("./h3"))):
        scene["performers"] = [{"name": name} for name in performers]
    if tags := comma_list(first(content.xpath("./h4"))):
        scene["tags"] = [{"name": tag} for tag in tags]
    # The page never names its own host, so the request URL is the only source
    if image := image_from(tree, url):
        scene["image"] = image
    if studio := studio_for(domain_from_url(url)):
        scene["studio"] = studio

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_from_url(url)
        case _:
            log.error(f"Unsupported operation: {op}")

    print(json.dumps(result))
