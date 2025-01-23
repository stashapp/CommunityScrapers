from datetime import datetime
import json
from lxml import html
import re
import sys
from urllib.parse import urlparse, urlunparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedPerformer,
)
from py_common.util import scraper_args

ensure_requirements("cloudscraper")
import cloudscraper  # noqa: E402
ensure_requirements("fp:free-proxy")
from fp.fp import FreeProxy


scraper = cloudscraper.create_scraper()

free_proxies = None


def get_proxies() -> dict:
    proxy = FreeProxy(rand=True).get()
    log.debug("proxy: %s" % proxy)
    return { 'http': proxy } if proxy.startswith('http:') else { 'https': proxy }

def li_value(key: str) -> str:
    return f'//div[@class="info-box info"]/ul/li/span[text()="{key}:"]/../text()[2]'


def parse_date(date_string: str) -> str:
    try:
        return datetime.strftime(datetime.strptime(date_string, "%d %B %Y"), "%Y-%m-%d")
    except:
        return date_string


def scrapeUrl(url):
    return html.document_fromstring(scrapeUrlToString(url))


def scrapeUrlToString(url, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            log.debug('about to execute scraper.get, attempt %d' % (retries + 1))
            global free_proxies
            free_proxies = get_proxies()
            scraped = scraper.get(url, proxies=free_proxies)
            if scraped.status_code == 200:
                log.debug('HTTP Status: 200')
                return scraped.text
            else:
                log.error('HTTP Error: %s' % scraped.status_code)
        except Exception as e:
            log.error("scraper.get error: %s" % e)
        
        retries += 1
        log.debug('Retrying (%d/%d)...' % (retries, max_retries))
    
    raise Exception('Failed to scrape the URL after %d retries' % max_retries)


def remove_query(url: str) -> str:
    return urlunparse(urlparse(url)._replace(query=""))


def performer_from_url(url) -> ScrapedPerformer | None:
    performer: ScrapedPerformer = {}
    try:
        tree = scrapeUrl(url)
        if (name := next(iter(tree.xpath('//h1[contains(@class, "content-name") or contains(@class, "username")]/text()')), None)) is not None:
            performer["name"] = name.strip()
        else:
            log.warning("could not scrape name")
        if (aliases := next(iter(tree.xpath(li_value('AKA'))), None)) is not None:
            performer["aliases"] = aliases.strip()
        else:
            log.warning("could not scrape aliases")
        if (birthdate := next(iter(tree.xpath(li_value('Date of Birth'))), None)) is not None:
            performer["birthdate"] = parse_date(birthdate.strip())
        else:
            log.warning("could not scrape birthdate")
        if (status := next(iter(tree.xpath(li_value('Status'))), None)) is not None:
            if (match := re.search(r"\d{1,2} \w+ \d{4}", status.strip())):
                performer["death_date"] = parse_date(match.group())
            else:
                log.warning('could not parse death_date from status: %s' % status)
        else:
            log.debug("could not scrape death_date")
        if (country := next(iter(tree.xpath(li_value('Country'))), None)) is not None:
            performer["country"] = country.strip()
        else:
            log.warning("could not scrape country")
        if (eye_color := next(iter(tree.xpath(li_value('Eye Color'))), None)) is not None:
            performer["eye_color"] = eye_color.strip()
        else:
            log.warning("could not scrape eye_color")
        if (hair_color := next(iter(tree.xpath(li_value('Hair Color'))), None)) is not None:
            performer["hair_color"] = hair_color.strip()
        else:
            log.warning("could not scrape hair_color")
        if (ethnicity := next(iter(tree.xpath(li_value('Ethnicity'))), None)) is not None:
            performer["ethnicity"] = ethnicity.strip()
        else:
            log.warning("could not scrape ethnicity")
        if (height := next(iter(tree.xpath(li_value('Height'))), None)) is not None:
            performer["height"] = re.sub(r"(\d+) cm.*", r"\1", height.strip())
        else:
            log.warning("could not scrape height")
        if (tags := iter(tree.xpath('//a[@class="tag-item"]/text()')), None) is not None:
            performer["tags"] = [ { 'name': tag } for tag in tags ]
        else:
            log.warning("could not scrape tags")
        if (image := next(iter(tree.xpath('//div[@class="user-photo"]/img/@src')), None)) is not None:
            performer["images"] = [image]
        else:
            log.warning("could not scrape image")
        performer["urls"] = [url] 
        if (social_media_links_out := iter(tree.xpath('//a[starts-with(@class, " social-")]/@href')), None) is not None:
            social_media_urls = [
                remove_query(scraper.get(f"https://www.ashemaletube.com{link_out}", proxies=free_proxies).url)
                for link_out in social_media_links_out
            ]
            log.debug("social media urls: %s" % social_media_urls)
            performer["urls"].extend(social_media_urls)
        else:
            log.warning("could not scrape social media links")
        if (website_links := iter(tree.xpath('//div[@class="info-box info"]/ul/li/span[text()="Website:"]/following-sibling::a/@href')), None) is not None:
            website_urls = [ remove_query(url) for url in website_links ]
            log.debug("website_urls: %s" % website_urls)
            performer["urls"].extend(website_urls)
        else:
            log.warning("could not scrape website links")
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
