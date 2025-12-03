from datetime import datetime
import json
import re
import sys

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer
from py_common.util import scraper_args

ensure_requirements("cloudscraper", "lxml")
import cloudscraper  # noqa: E402
from lxml import html

scraper = cloudscraper.create_scraper()

def scrape_url_to_string(url):
    try:
        scraped = scraper.get(url)
        if scraped.status_code == 200:
            log.debug('HTTP Status: 200')
            return scraped.text
        log.error('HTTP Error: %s' % scraped.status_code)
    except Exception as e:
        log.error("scraper.get error: %s" % e)
        return None

def scrape_url(url):
    return html.document_fromstring(scrape_url_to_string(url))

def parse_date(date_string: str) -> str:
    try:
        return datetime.strftime(datetime.strptime(date_string, "%B %d, %Y"), "%Y-%m-%d")
    except Exception:
        return date_string

def bio_value(key: str) -> str:
    return f'//table[contains(@class, "biography")]//th[text()="{key}:"]/following-sibling::td//text()'

def performer_from_url(url) -> ScrapedPerformer | None:
    performer: ScrapedPerformer = {}
    try:
        tree = scrape_url(url)
        if (name := next(iter(tree.xpath('//h1[@id="firstHeading"]//text()')), None)) is not None:
            log.debug("scraped name: %s" % name)
            performer["name"] = name.strip()
        else:
            log.warning("could not scrape name")
        if (birthdate := iter(tree.xpath(bio_value('Date of birth'))), None) is not None:
            birthdate = "".join(birthdate)
            log.debug("scraped birthdate: %s" % "".join(birthdate))
            birthdate = re.sub(r"(\w+ \d+, \d{4}).*", r"\1", birthdate)
            log.debug("pre-processed birthdate: %s" % birthdate)
            performer["birthdate"] = parse_date(birthdate.strip())
        else:
            log.warning("could not scrape birthdate")
        if (country := iter(tree.xpath(bio_value('Nationality'))), None) is not None:
            country = "".join(country)
            log.debug("scraped country: %s" % country)
            performer["country"] = country.strip()
        else:
            log.warning("could not scrape country")
        if (bra_size := next(iter(tree.xpath(bio_value('Bra size'))), None)) is not None:
            log.debug("scraped bra_size: %s" % bra_size)
            performer["measurements"] = bra_size.strip()
        else:
            log.warning("could not scrape bra_size")
        if (eye_color := next(iter(tree.xpath(bio_value('Eye color'))), None)) is not None:
            log.debug("scraped eye_color: %s" % eye_color)
            performer["eye_color"] = eye_color.strip()
        else:
            log.warning("could not scrape eye_color")
        if (hair_color := next(iter(tree.xpath(bio_value('Hair color'))), None)) is not None:
            log.debug("scraped hair_color: %s" % hair_color)
            performer["hair_color"] = hair_color.strip()
        else:
            log.warning("could not scrape hair_color")
        if (ethnicity := next(iter(tree.xpath(bio_value('Ethnicity'))), None)) is not None:
            log.debug("scraped ethnicity: %s" % ethnicity)
            performer["ethnicity"] = ethnicity.strip()
        else:
            log.warning("could not scrape ethnicity")
        if (height := next(iter(tree.xpath(bio_value('Height'))), None)) is not None:
            log.debug("scraped height: %s" % height)
            performer["height"] = re.sub(r"(\d+)\s*cm.*", r"\1", height.strip())
        else:
            log.warning("could not scrape height")
        if (weight := next(iter(tree.xpath(bio_value('Weight'))), None)) is not None:
            log.debug("scraped weight: %s" % weight)
            performer["weight"] = re.sub(r"(\d+)\s*kg.*", r"\1", weight.strip())
        else:
            log.warning("could not scrape weight")
        if (aliases := next(iter(tree.xpath(bio_value('Alias(es)'))), None)) is not None:
            log.debug("scraped aliases: %s" % aliases)
            performer["aliases"] = aliases.strip()
        else:
            log.warning("could not scrape aliases")
        if (image := next(iter(tree.xpath('//td[@class="infobox-image"]//img/@src')), None)) is not None:
            log.debug("scraped image: %s" % image)
            image = re.sub(r"/thumb/", "/", image)
            image = re.sub(r"/\d+px.*$", "", image)
            log.debug("processed image: %s" % image)
            performer["images"] = [image]
        else:
            log.warning("could not scrape image")
        performer["urls"] = [url] 
    except Exception as e:
        log.error('error happened: %s' % e)
    log.debug("performer: %s" % performer)
    return performer

if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

    log.debug("result: %s" % result)
    print(json.dumps(result))
