import sys
import json
import lxml
import re
from scrapers.py_common.browser import get_html, get_iframe_content

def parse_performers_from_description(description):
    # This is still fragile, but it's better than nothing.
    # It looks for capitalized words that are likely to be names.
    performers = re.findall(r'\b[A-Z][a-z]+\b', description)
    return list(set(performers)) # Use set to get unique names

def scrape_deviantotter(url):
    html = get_html(url)
    if not html:
        return []

    tree = lxml.html.fromstring(html)

    scenes = []

    scene_elements = tree.xpath('//div[@class="update_box"]')

    for scene_element in scene_elements:
        scene = {}

        title_element = scene_element.xpath('.//div[@class="update_title"]/a/b/text()')
        if not title_element:
            continue
        scene['title'] = title_element[0]

        description_element = scene_element.xpath('.//div[@class="update_description"]/p/text()')
        description = "\n".join(description_element)
        scene['details'] = description

        detail_url_element = scene_element.xpath('.//div[@class="update_title"]/a/@href')
        if not detail_url_element:
            continue
        detail_url = detail_url_element[0]
        scene['url'] = detail_url

        iframe_src_element = scene_element.xpath('.//iframe/@src')
        if iframe_src_element:
            iframe_src = iframe_src_element[0]
            scene['image'] = get_iframe_content(iframe_src)
        else:
            scene['image'] = None

        performers = parse_performers_from_description(description)
        scene['performers'] = [{"name": p} for p in performers]
        scene['tags'] = []
        scene['studio'] = "Deviant Otter"
        scene['date'] = None

        scenes.append(scene)

    return scenes

if __name__ == '__main__':
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")

    if url:
        scraped_data = scrape_deviantotter(url)
        print(json.dumps(scraped_data, indent=2))
    else:
        print(json.dumps([]))
