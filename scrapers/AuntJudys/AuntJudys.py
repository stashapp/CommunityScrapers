import json
import urllib.request
import urllib.parse
import py_common.log as log
from py_common.util import scraper_args
from py_common.deps import ensure_requirements

ensure_requirements("lxml")
from lxml import html  # noqa: E402

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}


def scene_from_url(url):
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    if not res.status == 200:
        log.error(f"Request to '{url}' failed with status code {res.status}")
        return {}

    tree = html.fromstring(res.read().decode())

    date = "-".join(
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
        "date": date,
    }

    try:
        next_url = tree.xpath("//p/span[@class='update_models']/a/@href[1]").pop(0)
        while next_url:
            req = urllib.request.Request(next_url, headers=headers)
            res = urllib.request.urlopen(req)
            tree = html.fromstring(res.read().decode())
            next_url = None
            links = tree.xpath(f"//div[a[@href='{url}']]")
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
                ).replace("-4x", "-full")
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
        log.error(f"Unable to find image for scene: {e}")

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    if op != "scene-by-url":
        log.error(f"Unsupported operation: {op}")
        exit(-1)

    result = scene_from_url(args["url"])
    print(json.dumps(result))
