import sys
import json
import requests
import lxml.html
import re

def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def parse_performers_from_title(title):
    # This is a simple example, a more robust implementation would be needed for a real-world scenario
    # The performer names are only available in the title, so we have to parse them from there.
    # This is fragile and might not work for all titles.
    # Example titles: "Jhon Poll Fucks Caio Rodrigues", "Seb Leblan, Texas Twink – Are You Devoted?"
    parts = re.split(r' Fucks | & | and |, | – ', title)
    performers = [p.strip() for p in parts]
    return performers

def scrape_gaysonic(url):
    html = get_html(url)
    if not html:
        return []

    tree = lxml.html.fromstring(html)

    scenes = []

    scene_elements = tree.xpath("//div[contains(@class, 'post')]")

    for scene_element in scene_elements:
        scene = {}

        title_element = scene_element.xpath(".//h1[@class='title']/a/text() | .//h2[@class='title']/a/text()")
        if not title_element:
            continue
        title = title_element[0]
        scene['title'] = title

        date_element = scene_element.xpath(".//span[@class='meta_date']/text()")
        if date_element:
            scene['date'] = date_element[0]
        else:
            scene['date'] = None

        image_element = scene_element.xpath(".//div[contains(@class, 'entry')]//img/@src")
        if image_element:
            scene['image'] = image_element[0]
        else:
            scene['image'] = None

        detail_url_element = scene_element.xpath(".//h1[@class='title']/a/@href | .//h2[@class='title']/a/@href")
        if not detail_url_element:
            continue
        detail_url = detail_url_element[0]

        detail_html = get_html(detail_url)
        if not detail_html:
            continue

        detail_tree = lxml.html.fromstring(detail_html)

        description_elements = detail_tree.xpath("//div[contains(@class, 'entry')]//p/text()")
        scene['details'] = "\n".join(description_elements)

        performers = parse_performers_from_title(title)
        scene['performers'] = [{"name": p} for p in performers]

        tags = scene_element.xpath(".//span[@class='meta_categories']/a/text()")
        scene['tags'] = [{"name": t.strip()} for t in tags]

        # The studio name is parsed from the alt text of the promo image.
        studio_alt_text_element = detail_tree.xpath(".//div[contains(@class, 'entry')]//img/@alt")
        if studio_alt_text_element:
            alt_text = studio_alt_text_element[0]
            studio_match = re.search(r'Promo image: (.*?) ', alt_text)
            if studio_match:
                scene['studio'] = studio_match.group(1).strip()
            else:
                scene['studio'] = "Gaysonic"
        else:
            scene['studio'] = "Gaysonic"

        scene['url'] = detail_url

        scenes.append(scene)

    return scenes

if __name__ == '__main__':
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")

    if url:
        scraped_data = scrape_gaysonic(url)
        print(json.dumps(scraped_data, indent=2))
    else:
        print(json.dumps([]))
