import sys
import json
import lxml.html
import re
from scrapers.py_common.browser import get_html, get_iframe_content

def parse_performers_from_description(description):
    # This is still fragile, but it's better than nothing.
    # It looks for capitalized words that are likely to be names.
    performers = re.findall(r'\b[A-Z][a-z]+\b', description)
    return list(set(performers)) # Use set to get unique names

def scrape_maverickmen(url):
    html = get_html(url)
    if not html:
        return []

    tree = lxml.html.fromstring(html)

    scenes = []

    scene_elements = tree.xpath('//div[contains(@id, "scene-")]')

    for scene_element in scene_elements:
        scene = {}

        title_element = scene_element.xpath('.//h5/a/text()')
        if not title_element:
            continue
        scene['title'] = title_element[0]

        description_element = scene_element.xpath('.//p/text()')
        description = "\n".join(description_element)
        scene['details'] = description

        detail_url_element = scene_element.xpath('.//h5/a/@href')
        if not detail_url_element:
            # No detail URL, so we can't get more info. Skip.
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
        scene['studio'] = "Maverick Men"
        scene['date'] = None

        scenes.append(scene)

    return scenes

if __name__ == '__main__':
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")

    if url:
        scraped_data = scrape_maverickmen(url)
        print(json.dumps(scraped_data, indent=2))
    else:
        print(json.dumps([]))
