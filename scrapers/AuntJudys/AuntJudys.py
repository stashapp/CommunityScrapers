import json
import os
import sys
import urllib.request
import urllib.parse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from lxml import html
except ModuleNotFoundError:
    print(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python),",
        "run this command in a terminal (cmd): python -m pip install lxml",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from py_common.log import debug
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo",
        "https://github.com/stashapp/CommunityScrapers",
        file=sys.stderr,
    )
    sys.exit(1)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}


def sceneByURL(url):
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    if not res.status == 200:
        debug(f"Request to '{url}' failed with status code {res.status}")
        return {}

    tree = html.fromstring(res.read().decode())

    m, d, y = (
        tree.xpath("//div[contains(@class,'update_date')]/text()[1]")
        .pop(0)
        .strip()
        .split("/")
    )
    url_parts = urllib.parse.urlparse(url)

    scene = {
        "title": tree.xpath("//span[@class='title_bar_hilite']/text()").pop(),
        "details": tree.xpath("//span[@class='update_description']/text()")
        .pop()
        .strip(),
        "studio": {
            "name": "Aunt Judy's" if "auntjudys.com" in url else "Aunt Judy's XXX"
        },
        "performers": [
            {"name": x}
            for x in tree.xpath("//p/span[@class='update_models']/a/text()[1]")
        ],
        "tags": [
            {"name": x} for x in tree.xpath("//span[@class='update_tags']/a/text()")
        ],
        "date": "-".join([y, m, d]),
    }

    try:
        next_url = tree.xpath("//p/span[@class='update_models']/a/@href[1]").pop(0)
        while next_url:
            req = urllib.request.Request(next_url, headers=headers)
            res = urllib.request.urlopen(req)
            tree = html.fromstring(res.read().decode())
            next_url = None
            links = tree.xpath("//div[a[@href='{}']]".format(url))
            if len(links):
                link = links[0]
                scene["code"] = link.get("data-setid")
                scene["image"] = urllib.parse.urlunparse(
                    (
                        url_parts.scheme,
                        url_parts.netloc,
                        link.xpath("./a/img/@src0_4x").pop(0),
                        "",
                        "",
                        "",
                    )
                )
            else:
                n = tree.xpath("//a[@class='pagenav' and span[text()='>']]/@href")
                if len(n):
                    next_url = urllib.parse.urlunparse(
                        (
                            url_parts.scheme,
                            url_parts.netloc,
                            "/tour/" + n.pop(0),
                            "",
                            "",
                            "",
                        )
                    )
    except Exception as e:
        debug(f"Unable to find image for scene: {e}")

    return scene


if sys.argv[1] == "sceneByURL":
    j = json.loads(sys.stdin.read())
    print(json.dumps(sceneByURL(j["url"])))
