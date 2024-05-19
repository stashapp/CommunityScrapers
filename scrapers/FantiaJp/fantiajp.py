import sys
import json
import re
from datetime import datetime

re_post_id = re.compile(r'https://fantia.jp/posts/(\d+).*')

try:
    import requests
    from lxml import etree
except ModuleNotFoundError:
    print(
        "You need to install the following modules 'requests', 'bs4', 'lxml'.", file=sys.stderr)
    sys.exit()

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

def readJSONInput():
	input = sys.stdin.read()
	return json.loads(input)

def send_request(url: str, headers: dict = None):
    """
    get post response from url
    """
    log.debug(f"Request URL: {url}")
    headers = headers or {}
    headers.setdefault("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
    except requests.RequestException as req_error:
        log.warning(f"Requests failed: {req_error}")
        return None
    return response

def get_csrf() -> str:
    response = send_request("https://fantia.jp/")
    tree = etree.HTML(text=response.text)
    try:
        return tree.xpath("//meta[@name='csrf-token']/@content")[0]
    except IndexError:
        log.warning(f"csrf not found")
        sys.exit()

def get_post_id(url: str) -> str:
    try:
        return re_post_id.findall(url)[0]
    except IndexError:
        log.warning(f"Post id not found in the url")
        sys.exit()

def get_post_data(url: str):
    post_id = get_post_id(url=url)
    csrf_token = get_csrf()
    return send_request(
        f"https://fantia.jp/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}
    ).json()

def get_post_infos(url: str):
    data = get_post_data(url=url)
    data = data["post"]
    return {
        "title": data["title"].strip(),
        'details': data["comment"].strip(),
        'image': data["thumb_micro"].replace("micro_", ""),
        'date': datetime.strptime(data["posted_at"], "%a, %d %b %Y %H:%M:%S %z").strftime("%Y-%m-%d"),
        'performers': [{"name": data["fanclub"]["creator_name"], "image": data["fanclub"]["user"]["image"]["large"]}],
        "tags": [{"name": item["name"]} for item in data["tags"]],
        "studio": {"name": "Fantia.jp"},
    }

i = readJSONInput()

if sys.argv[1] == "post":
    ret = get_post_infos(i['url'])
    print(json.dumps(ret))
