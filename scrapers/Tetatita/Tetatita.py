import sys
import json
from playwright.sync_api import sync_playwright
import lxml.html

def get_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            # Handle age verification popup
            if page.query_selector('.agepop'):
                page.click('.agebuttons a:has-text("Yes")')
            content = page.content()
        finally:
            browser.close()
        return content

def scrape_tetatita(url):
    html = get_html(url)
    tree = lxml.html.fromstring(html)

    scenes = []

    scene_elements = tree.xpath("//div[contains(@class, 'videov2')]")

    for scene_element in scene_elements:
        scene = {}

        title_element = scene_element.xpath(".//h4[@class='title']/a/text()")
        if not title_element:
            continue
        scene['title'] = title_element[0]

        image_element = scene_element.xpath(".//picture/img/@src")
        if image_element:
            scene['image'] = image_element[0]
        else:
            scene['image'] = None

        detail_url_element = scene_element.xpath(".//h4[@class='title']/a/@href")
        if not detail_url_element:
            continue
        detail_url = detail_url_element[0]

        detail_html = get_html(detail_url)
        detail_tree = lxml.html.fromstring(detail_html)

        performers = detail_tree.xpath("//a[contains(@href, '/actors/')]/text()")
        scene['performers'] = [{"name": p.strip()} for p in performers]
        scene['tags'] = [{"name": p.strip()} for p in performers] # Using performers as tags as well
        scene['studio'] = "Tetatita"
        scene['url'] = detail_url

        # Date and Details are not available on the public-facing site.
        # They might be behind a login wall.
        scene['date'] = None
        scene['details'] = ''

        scenes.append(scene)

    return scenes

if __name__ == '__main__':
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")

    if url:
        scraped_data = scrape_tetatita(url)
        print(json.dumps(scraped_data))
    else:
        print(json.dumps([]))
