import sys
import json
import datetime
import urllib.parse
from bs4 import BeautifulSoup
import requests


css_paths = {
    "title": ".memberPicV > h2:nth-child(1)",
    "detail": ".description > p:nth-child(2)",
    "date": ".info > p:nth-child(2)",
    "featuring": ".info > p:nth-child(3)",
    "tags": ".tags > ul:nth-child(2)",
    "image": ".player-thumb",
}


def read_json_input():
    raw_input = sys.stdin.read()
    json_input = json.loads(raw_input)
    return json_input


def get_html(url: str) -> str:
    request_result = requests.get(url)
    if request_result.status_code != 200:
        return ""

    html_doc = request_result.text
    return html_doc


def extract_title(soup: BeautifulSoup, paths: dict) -> str:
    node = paths.get("title")
    element = soup.select(node)
    element = element[0]
    text = element.get_text()
    return text.strip()


def extract_detail(soup: BeautifulSoup, paths: dict) -> str:
    node = paths.get("detail")
    element = soup.select(node)
    element = element[0]
    text = element.get_text()
    return text.strip()


def extract_date(soup: BeautifulSoup, paths: dict) -> str:

    node = paths.get("date")
    element = soup.select(node)
    element = element[0]
    text = element.get_text()

    i = text.index(":")
    j = text.index("|")
    text = text[i + 1 : j]
    text = text.strip()

    # MM/DD/YYYY
    # YYYY-MM-DD
    date = datetime.datetime.strptime(text, "%m/%d/%Y").strftime("%Y-%m-%d")
    return date


def extract_featuring(soup: BeautifulSoup, paths: dict) -> list:
    node = paths.get("featuring")
    element = soup.select(node)
    element = element[0]
    stars = []
    for a_elem in element.find_all("a"):
        star = a_elem.get_text().strip()
        stars.append({"name": star})

    return stars


def extract_tags(soup: BeautifulSoup, paths: dict) -> list:
    node = paths.get("tags")
    element = soup.select(node)
    if element is None or len(element) == 0:
        return []

    element = element[0]
    tags = []
    for a_elem in element.find_all("a"):
        tag = a_elem.get_text().strip()
        tags.append({"name": tag})
    return tags


def extract_image(soup: BeautifulSoup, paths: dict):
    base_url = "https://thirdsexxxx.com"
    element = soup.select("img[src0_1x]")
    element = element[0]
    src = element["src0_1x"]
    image_url = urllib.parse.urljoin(base_url, src)
    return image_url


def main():
    json_input = read_json_input()
    url = json_input.get("url")
    ret = {}
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    ret["title"] = extract_title(soup, css_paths)
    ret["details"] = extract_detail(soup, css_paths)
    ret["date"] = extract_date(soup, css_paths)
    ret["performers"] = extract_featuring(soup, css_paths)
    ret["tags"] = extract_tags(soup, css_paths)
    ret["image"] = extract_image(soup, css_paths)
    ret["studio"] = {}
    ret["studio"]["name"] = "ThirdSexXXX"
    return ret


ret_obj = main()
print(json.dumps(ret_obj))
