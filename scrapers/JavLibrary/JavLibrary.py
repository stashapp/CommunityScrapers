"""JAVLibrary scraper using pydoll for Cloudflare bypass"""
import json
import re
import sys
import base64
import asyncio
from urllib.parse import urlparse

from py_common import log
from py_common.util import scraper_args
from py_common.deps import ensure_requirements

ensure_requirements("pydoll-python", "lxml")

from pydoll.browser import Chrome  # noqa: E402
from lxml import html  # noqa: E402

# Mirror sites to try
MIRROR_SITES = ["javlibrary", "o58c", "e59f", "p54u", "d52q", "n53i"]


def get_xpath_text(tree, xpath):
    """Extract text from XPath result, handling multiple results"""
    result = tree.xpath(xpath)
    if result:
        if isinstance(result, list):
            return result[0].strip() if isinstance(result[0], str) else result[0].text_content().strip()
        return result.strip() if isinstance(result, str) else result.text_content().strip()
    return None


def get_xpath_list(tree, xpath):
    """Extract list of text values from XPath result"""
    result = tree.xpath(xpath)
    if result:
        return [item.strip() if isinstance(item, str) else item.text_content().strip() for item in result]
    return []


async def fetch_page_html(url):
    """Fetch page HTML using pydoll browser automation"""
    try:
        log.info(f"Starting browser for URL: {url}")
        async with Chrome() as browser:
            tab = await browser.start()
            log.info(f"Navigating to: {url}")
            await tab.go_to(url)

            # Wait a bit for page to load
            await asyncio.sleep(2)

            # Get page HTML
            page_html = await tab.query('//html').get_attribute('outerHTML')

            log.info("Successfully fetched page HTML")
            return page_html, tab.url

    except Exception as e:
        log.error(f"Error fetching page with pydoll: {e}")
        return None, None


async def try_mirrors_async(url):
    """Try different mirror sites until one works"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '').replace('.com', '')

    # If not a javlib domain, try it directly
    if domain not in MIRROR_SITES:
        log.info(f"Not a javlib domain, trying directly: {url}")
        html_content, final_url = await fetch_page_html(url)
        if html_content:
            return url, html_content, final_url
        return url, None, None

    for mirror in MIRROR_SITES:
        try_url = url.replace(domain, mirror)
        log.info(f"Trying mirror: {mirror}")

        html_content, final_url = await fetch_page_html(try_url)
        if html_content and 'Access denied' not in html_content:
            log.info(f"Successfully connected to {mirror}")
            return try_url, html_content, final_url

        log.debug(f"Mirror {mirror} failed or blocked")

    log.error("All mirrors failed")
    return url, None, None


def try_mirrors(url):
    """Synchronous wrapper for try_mirrors_async"""
    return asyncio.run(try_mirrors_async(url))


async def fetch_image_base64_async(url):
    """Fetch image and convert to base64"""
    try:
        async with Chrome() as browser:
            tab = await browser.start()
            response = await tab.request.get(url)
            if response.status_code == 200:
                content = await response.content()
                b64_image = base64.b64encode(content).decode('utf-8')
                return f"data:image/jpeg;base64,{b64_image}"
    except Exception as e:
        log.warning(f"Failed to fetch image: {e}")
    return None


def fetch_image_base64(url):
    """Synchronous wrapper for fetch_image_base64_async"""
    return asyncio.run(fetch_image_base64_async(url))


def scrape_scene(url):
    """Scrape scene information from JavLibrary"""
    try:
        log.info(f"Scraping scene: {url}")

        # Try mirrors if needed
        working_url, html_content, final_url = try_mirrors(url)
        if html_content is None:
            log.error("Failed to connect to any mirror site")
            return {}

        tree = html.fromstring(html_content)
        scene = {}

        # Title: Get the DVD ID code
        code = get_xpath_text(tree, '//div[@id="video_id"]/table/tbody/tr/td[@class="text"]/text()')
        if code:
            scene['code'] = code
            scene['title'] = code

        # URL: Get from meta tag or use final URL
        url_xpath = get_xpath_text(tree, '//meta[@property="og:url"]/@content')
        if url_xpath:
            # Process URL to ensure correct format
            url_processed = url_xpath
            if '?' in url_processed:
                query_part = url_processed.split('?')[1]
                url_processed = f"https://www.javlibrary.com/en/?{query_part}"
            scene['url'] = url_processed
        else:
            scene['url'] = final_url

        # Date
        date = get_xpath_text(tree, '//div[@id="video_date"]/table/tbody/tr/td[@class="text"]/text()')
        if date:
            scene['date'] = date

        # Details: Get the title text (excluding code)
        title_text = get_xpath_text(tree, '//div[@id="video_title"]/h3/a/text()')
        if title_text:
            # Remove the code from the beginning
            details = re.sub(r'^(.*?\s){1}', '', title_text)
            scene['details'] = details

        # Director
        director = get_xpath_text(tree, '//div[@id="video_director"]/table/tbody/tr/td[@class="text"]/span/a/text()')
        if director:
            scene['director'] = director

        # Tags
        tags = get_xpath_list(tree, '//div[@id="video_genres"]/table/tbody/tr/td[@class="text"]/span/a/text()')
        if tags:
            scene['tags'] = [{"name": tag} for tag in tags]

        # Performers
        performers = get_xpath_list(tree, '//div[@id="video_cast"]/table/tbody/tr/td[@class="text"]/span/span/a/text()')
        if performers:
            scene['performers'] = [{"name": perf} for perf in performers]

        # Image
        image = get_xpath_text(tree, '//div[@id="video_jacket"]/img/@src')
        if image:
            # Clean the image URL
            image_clean = re.sub(r'(http:|https:)', '', image)
            image_url = f"https:{image_clean}"

            # Note: Image fetching with pydoll is slow, skip for now
            # Users can enable if needed
            log.debug(f"Image URL: {image_url} (skipping base64 conversion for performance)")
            # scene['image'] = fetch_image_base64(image_url)

        # Studio
        studio = get_xpath_text(tree, '//div[@id="video_maker"]/table/tbody/tr/td[@class="text"]/span/a/text()')
        if studio:
            scene['studio'] = {"name": studio}

        return scene

    except Exception as e:
        log.error(f"Error scraping scene: {e}")
        import traceback
        log.debug(traceback.format_exc())
        return {}


def scrape_movie(url):
    """Scrape movie information from JavLibrary"""
    try:
        log.info(f"Scraping movie: {url}")

        # Try mirrors if needed
        working_url, html_content, final_url = try_mirrors(url)
        if html_content is None:
            log.error("Failed to connect to any mirror site")
            return {}

        tree = html.fromstring(html_content)
        movie = {}

        # Name: DVD ID
        name = get_xpath_text(tree, '//div[@id="video_id"]/table/tbody/tr/td[@class="text"]/text()')
        if name:
            movie['name'] = name

        # Director
        director = get_xpath_text(tree, '//div[@id="video_director"]/table/tbody/tr/td[@class="text"]/span/a/text()')
        if director:
            movie['director'] = director

        # Duration: Get from video_length and convert to seconds (add :00 for mm:ss format)
        duration = get_xpath_text(tree, '//div[@id="video_length"]/table/tbody/tr/td/span[@class="text"]/text()')
        if duration:
            movie['duration'] = f"{duration}:00"

        # Date
        date = get_xpath_text(tree, '//div[@id="video_date"]/table/tbody/tr/td[@class="text"]/text()')
        if date:
            movie['date'] = date

        # Synopsis: Get the title (without code)
        synopsis = get_xpath_text(tree, '//div[@id="video_title"]/h3/a/text()')
        if synopsis:
            synopsis_clean = re.sub(r'^(.*?\s){1}', '', synopsis)
            movie['synopsis'] = synopsis_clean

        # Studio
        studio = get_xpath_text(tree, '//div[@id="video_maker"]/table/tbody/tr/td[@class="text"]/span/a/text()')
        if studio:
            movie['studio'] = {"name": studio}

        # Front Image - skip for performance
        log.debug("Skipping front image for performance")

        return movie

    except Exception as e:
        log.error(f"Error scraping movie: {e}")
        import traceback
        log.debug(traceback.format_exc())
        return {}


def search_scenes(query):
    """Search for scenes by name/code"""
    try:
        # Construct search URL
        search_url = f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={query}"
        log.info(f"Searching: {search_url}")

        # Try mirrors if needed
        working_url, html_content, final_url = try_mirrors(search_url)
        if html_content is None:
            log.error("Failed to connect to any mirror site")
            return []

        # Check if we landed directly on a scene page
        if "/en/?v=" in final_url:
            log.info("Direct match found, scraping scene page")
            # Parse the HTML we already have
            tree = html.fromstring(html_content)
            scene = {}

            # Extract basic info for search result
            code = get_xpath_text(tree, '//div[@id="video_id"]/table/tbody/tr/td[@class="text"]/text()')
            if code:
                scene['title'] = code
                scene['url'] = final_url
                return [scene]
            return []

        tree = html.fromstring(html_content)

        # Parse search results
        results = []

        # Get titles (excluding Blu-ray versions)
        titles = get_xpath_list(tree, '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@title')

        # Get URLs
        urls = get_xpath_list(tree, '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]/@href')

        # Get images
        images = get_xpath_list(tree, '//div[@class="videos"]/div/a[not(contains(@title,"(Blu-ray"))]//img/@src')

        for i in range(len(titles)):
            result = {
                "title": titles[i] if i < len(titles) else "",
                "url": f"https://www.javlibrary.com/en/{urls[i].replace('./', '')}" if i < len(urls) else "",
            }
            if i < len(images):
                # Clean image URL
                img_url = images[i]
                if img_url.startswith('//'):
                    img_url = f"https:{img_url}"
                result['image'] = img_url

            results.append(result)

        return results

    except Exception as e:
        log.error(f"Error searching: {e}")
        import traceback
        log.debug(traceback.format_exc())
        return []


def clean_filename(filename):
    """Clean filename to extract DVD code"""
    # Remove -JG\d pattern
    filename = re.sub(r'-JG\d', '', filename)
    # Extract code pattern: letters-numbers (e.g., ABC-123)
    match = re.search(r'(.*[^a-zA-Z0-9])*([a-zA-Z-]+\d+)(.+)', filename)
    if match:
        return match.group(2)
    return filename


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    try:
        if op == "scene-by-url":
            url = args.get("url")
            if url:
                result = scrape_scene(url)

        elif op == "scene-by-name":
            query = args.get("name")
            if query:
                result = search_scenes(query)

        elif op == "scene-by-fragment":
            # Extract filename and clean it
            filename = args.get("filename")
            if filename:
                cleaned = clean_filename(filename)
                log.info(f"Cleaned filename: {cleaned}")
                result = search_scenes(cleaned)

        elif op == "scene-by-query-fragment":
            # Use URL directly
            url = args.get("url")
            if url:
                result = search_scenes(url) if "vl_searchbyid" in url else scrape_scene(url)

        elif op == "movie-by-url":
            url = args.get("url")
            if url:
                result = scrape_movie(url)

        else:
            log.error(f"Unknown operation: {op}")
            sys.exit(1)

        print(json.dumps(result))

    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        log.debug(traceback.format_exc())
        print(json.dumps({}))
        sys.exit(1)
