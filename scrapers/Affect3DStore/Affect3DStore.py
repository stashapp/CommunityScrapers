"""
Stash scraper made to circumvent Cloudflare DDOS protection
"""
import json
import sys

from py_common.deps import ensure_requirements
ensure_requirements("cloudscraper", "fp:free-proxy", "lxml")
import cloudscraper  # noqa: E402
from fp.fp import FreeProxy
from lxml import html

from py_common import log
from py_common.util import scraper_args
from py_common.types import ScrapedScene

scraper = cloudscraper.create_scraper()

free_proxies = None

STUDIO_MAPPER = {
    "Miro Affect3D": "Miro",
}

def get_proxies() -> dict:
    proxy = FreeProxy(rand=True).get()
    log.debug("proxy: %s" % proxy)
    return { 'http': proxy } if proxy.startswith('http:') else { 'https': proxy }

def scrape_url(_url: str, max_retries=5):
    "Scrapes a web page and returns a HTML tree"
    retries = 0
    while retries < max_retries:
        try:
            log.debug('about to execute scraper.get, attempt %d' % (retries + 1))
            global free_proxies
            free_proxies = get_proxies()
            scraped = scraper.get(_url, proxies=free_proxies)
            if scraped.status_code == 200:
                log.debug('HTTP Status: 200')
                return html.document_fromstring(scraped.text)
            log.error('HTTP Error: %s' % scraped.status_code)
        except Exception as e:
            log.error("scraper.get error: %s" % e)

        retries += 1
        log.debug('Retrying (%d/%d)...' % (retries, max_retries))

    raise Exception(f'Failed to scrape the URL after {max_retries} retries')

def scene_from_url(_url: str) -> ScrapedScene | None:
    "Scrapes a scene from a URL, running an optional postprocess function on the result"
    scene: ScrapedScene = {}

    try:
        tree = scrape_url(_url)
        # title
        if title := tree.xpath('//h1/span'):
            scene['title'] = title[0].text_content()
        # date
        if year_released := tree.xpath('//div[contains(@class, "info-details-xl")]//table[contains(@class, "additional-attributes")]//td[@data-th="Year Released"]'):
            scene['date'] = year_released[0].text_content()
        # details
        if description_paragraphs := tree.xpath(
            '//div[contains(@class, "info-details-xl")]//div[contains(@class, "description")]//p'
        ):
            scene['details'] = "\n\n".join([p.text_content() for p in description_paragraphs])
        # studio
        if artist_name := tree.xpath(
            '//div[@class="box-inner1"]//span[@class="artist_name_m"]//a/text()'
        ):
            scene['studio'] = {"name": STUDIO_MAPPER.get(artist_name[0]) or artist_name[0]}
        # tags
        if tags := tree.xpath(
            '//div[contains(@class, "info-details-xl")]//table[contains(@class, "additional-attributes")]//td[not(@data-th="Artist/Circle")]/a/text()'
        ):
            scene['tags'] = [{"name": t.strip()} for t in tags]
        # image
        if main_product_photo := tree.xpath('//img[@alt="main product photo"]/@src'):
            scene['image'] = main_product_photo[0]
        # url
        scene["urls"] = [_url]
    except Exception as e:
        log.error("Error scraping scene from URL: %s" % e)
        return None

    return scene

def scene_search(_name: str) -> list[ScrapedScene] | None:
    "Searches for scenes by name"
    results: list[ScrapedScene] = []

    try:
        tree = scrape_url(f"https://affect3dstore.com/catalogsearch/result/?q={_name}")
        # parse search results and populate the results list
        if product_items := tree.xpath(
            '//div[contains(@class, "products-grid") and contains(@class, "wrapper")]//li[contains(@class, "product-item")]'
        ):
            for product_item in product_items:
                scene: ScrapedScene = {}
                # link
                if scene_link := product_item.xpath('.//a[contains(@class, "product-item-link")]'):
                    # get href for URL
                    scene["urls"] = [scene_link[0].get("href")]
                    # get link text for title
                    if scene_title := scene_link[0].text_content():
                        scene["title"] = scene_title.strip()
                # photo
                if scene_photo := product_item.xpath('.//a[contains(@class, "product-item-photo")]//img/@src'):
                    # sometimes this is lazy-loaded with JS for like image 7 onwards, for example,
                    # and doesn't resolve the image URL, but it can resolve sometimes if you retry
                    # the first several result images are not affected and always appear to
                    # resolve correctly
                    scene["image"] = scene_photo[0]
                # artist name
                if artist_name := product_item.xpath('.//span[contains(@class, "artist_name_m")]/a/text()'):
                    scene["studio"] = {"name": STUDIO_MAPPER.get(artist_name[0]) or artist_name[0]}
                results.append(scene)
    except Exception as e:
        log.error("Error searching for scenes by name: %s" % e)
        return None
    
    return results

def scene_from_fragment(fragment: dict) -> ScrapedScene | None:
    "Retrieves a scene from a fragment containing either a URL or a title"
    if 'url' in fragment:
        return scene_from_url(fragment['url'])
    if 'title' in fragment:
        search_results = scene_search(fragment['title'])
        return search_results[0] if search_results else None
    return None


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"result: {result}")

    print(json.dumps(result))
