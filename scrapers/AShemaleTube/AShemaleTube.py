import json
from lxml import html
import sys

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedPerformer,
)
from py_common.util import scraper_args

ensure_requirements("cloudscraper")
import cloudscraper  # noqa: E402

scraper = cloudscraper.create_scraper(
    # browser={
    #     'browser': 'firefox',
    #     'platform': 'windows',
    #     'mobile': False
    # }
    debug = True,
)

def scrapeUrl(url):
    page_content = scrapeUrlToString(url)
    log.debug(f"page_content: {page_content}")
    try:
        tree = html.document_fromstring(page_content)
        return tree
    except Exception as e:
        log.error(f"html parsing failed: {e}")
        sys.exit(1)


def scrapeUrlToString(url):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url)
        log.debug(f"scraped.status_code: {scraped.status_code}")
    except:
        log.error("scrape error")
        sys.exit(1)

    if scraped.status_code >= 400:
        log.error('HTTP Error: %s' % scraped.status_code)
        sys.exit(1)

    return scraped.content


def performer_from_url(url) -> ScrapedPerformer | None:
    performer: ScrapedPerformer = {}
    try:
        tree = scrapeUrl(url)
        log.debug(f"tree: {tree}")
        name_h1 = next(iter(tree.xpath('//h1[contains(@class, "content-name")]')), None)
        if name_h1 is not None:
            performer["name"] = name_h1.text
    except Exception as e:
        log.error(f'error happened: {e}')
    performer["url"] = url
    log.debug(f"performer: {performer}")
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

    print(json.dumps(result))
