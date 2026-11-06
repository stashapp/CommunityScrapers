import json
import re
import sys
from pathlib import Path
from typing import cast
from urllib.parse import quote

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.proxy import stash_requests
from py_common.types import (
    Ethnicity,
    EyeColor,
    HairColor,
    PerformerSearchResult,
    ScrapedGroup,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedTag,
)
from py_common.util import scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402

config = get_config(
    default="""
# 18+ entries are only shown to logged in users: log in to anidb.net in your browser,
# confirm once that you want to see 18+ content, then copy these two cookie values
adbsess =
adbuin =
"""
)

BASE = "https://anidb.net"
INFO = '//div[@class="g_section info"]'
PANE = f'{INFO}//div[@id="tab_1_pane"]'
# Tag categories describing the AniDB entry rather than the work:
# maintenance tags, technical aspects and origin
SKIPPED_TAG_GROUPS = ("animetb_30", "animetb_6151", "animetb_6173")


def fetch(url: str) -> html.HtmlElement | None:
    cookies = {
        name: value
        for name in ("adbsess", "adbuin")
        if (value := getattr(config, name))
    }
    # Cloudflare blocks plain requests, py_common.proxy falls back to FlareSolverr
    try:
        response = stash_requests.get(url, cookies=cookies)
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as e:  # noqa: BLE001
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if response.status_code != 200:
        log.error(f"HTTP {response.status_code} for {url}")
        return None
    tree = html.document_fromstring(response.text)
    if tree.xpath('//title[starts-with(., "Adult Content Warning")]'):
        log.error(f"{url} is 18+: set adbsess and adbuin in AniDB/config.ini to log in")
        return None
    return tree


def first(tree: html.HtmlElement, xpath: str) -> str | None:
    return next((text for node in tree.xpath(xpath) if (text := _text(node))), None)


def every(tree: html.HtmlElement, xpath: str) -> list[str]:
    return [text for node in tree.xpath(xpath) if (text := _text(node))]


def _text(node) -> str:
    return (node if isinstance(node, str) else node.text_content()).strip()


def absolute(href: str) -> str:
    return href if href.startswith("http") else BASE + href


def canonical(tree: html.HtmlElement, url: str) -> str:
    return first(tree, '//link[@rel="canonical"]/@href') or url


def description(tree: html.HtmlElement) -> str | None:
    if not (nodes := tree.xpath('//div[@itemprop="description"]')):
        return None
    for br in nodes[0].iter("br"):
        br.tail = "\n" + (br.tail or "")
    return nodes[0].text_content().strip() or None


def image(tree: html.HtmlElement) -> str | None:
    return first(tree, f'{INFO}//div[@class="image"]//img/@src')


def performer_from_tree(tree: html.HtmlElement, url: str) -> ScrapedPerformer | None:
    if not (
        name := first(
            tree, f'{PANE}//tr[contains(@class, "mainname")]//span[@itemprop="name"]'
        )
    ):
        log.error(f"No character name found on {url}")
        return None

    performer: ScrapedPerformer = {"name": name, "urls": [canonical(tree, url)]}
    if aliases := every(
        tree,
        f'{PANE}//tr[contains(@class, "official")]//label[@itemprop="alternateName"]',
    ):
        performer["aliases"] = ", ".join(aliases)
    if shortlink := first(
        tree, f'{PANE}//tr[contains(@class, "mainname")]//a[@class="shortlink"]'
    ):
        performer["disambiguation"] = shortlink
    # AniDB also uses "none/does not apply", which has no Stash equivalent
    match first(
        tree, f'{PANE}//tr[contains(@class, "gender")]//span[@itemprop="gender"]'
    ):
        case "male":
            performer["gender"] = "MALE"
        case "female":
            performer["gender"] = "FEMALE"
    # Stash takes free text here, so AniDB's own labels pass through as-is
    if entity := first(
        tree, f'{PANE}//tr[contains(@class, "entity")]//span[@class="tagname"]'
    ):
        performer["ethnicity"] = cast(Ethnicity, entity)
    looks = f'{PANE}//tr[contains(@class, "looks")]//span[contains(@class, "tagname")]'
    if hair := first(tree, f'{looks}[contains(text(), "hair")]'):
        performer["hair_color"] = cast(HairColor, hair)
    if eyes := first(tree, f'{looks}[contains(text(), "eyes")]'):
        performer["eye_color"] = cast(EyeColor, eyes)
    if (height := first(tree, f'{PANE}//span[@itemprop="height"]')) and (
        cm := re.search(r"\d+", height)
    ):
        performer["height"] = cm.group()
    if (weight := first(tree, f'{PANE}//span[@itemprop="weight"]')) and (
        kg := re.search(r"\d+", weight)
    ):
        performer["weight"] = kg.group()
    if details := description(tree):
        performer["details"] = details
    if tags := every(tree, f'{PANE}//span[@class="g_tag"]//span[@class="tagname"]'):
        performer["tags"] = [{"name": tag} for tag in tags]
    if cover := image(tree):
        performer["images"] = [cover]
    return performer


def studio_name(tree: html.HtmlElement) -> str | None:
    # The "Work" credit, labelled differently on anime and episode pages
    return first(
        tree, '//tr[td/a[@href="/creator/?credit=122"]]/td[contains(@class, "name")]/a'
    )


def tag_list(names: list[str]) -> list[ScrapedTag]:
    return [{"name": name} for name in names]


def group_from_tree(tree: html.HtmlElement, url: str) -> ScrapedGroup | None:
    if not (name := first(tree, f'{PANE}//span[@itemprop="name"]')):
        log.error(f"No anime title found on {url}")
        return None

    group: ScrapedGroup = {"name": name, "urls": [canonical(tree, url)]}
    # Many official titles repeat the main romaji title
    titles = every(
        tree,
        f'{PANE}//tr[contains(@class, "official")]//label[@itemprop="alternateName"]',
    )
    aliases: list[str] = []
    for title in titles:
        if title.casefold() not in [t.casefold() for t in [name, *aliases]]:
            aliases.append(title)
    if aliases:
        group["aliases"] = ", ".join(aliases)
    if date := first(
        tree, f'{PANE}//*[@itemprop="datePublished" or @itemprop="startDate"]/@content'
    ):
        group["date"] = date
    if synopsis := description(tree):
        group["synopsis"] = synopsis
    if studio := studio_name(tree):
        group["studio"] = {"name": studio}
    if cover := image(tree):
        group["front_image"] = cover
    skipped = " or ".join(f'@data-anidb-groupid="{g}"' for g in SKIPPED_TAG_GROUPS)
    tags = every(
        tree,
        f'//div[@class="pane anime_tags"]//div[@class="tag"][not({skipped})]//span[@class="tagname"]',
    )
    # The same tag can be listed for the anime and for one of its episodes
    if unique := list(dict.fromkeys(tags)):
        group["tags"] = tag_list(unique)
    return group


def scene_from_episode(tree: html.HtmlElement, url: str) -> ScrapedScene | None:
    # "Episode: Bible Black - 1 - School of Black Magic"
    heading = first(tree, '//div[@id="layout-main"]//h1[@class="ep"]') or ""
    if not (parts := re.match(r"Episode: (.+) - (\w+) - (.+)$", heading)):
        log.error(f"No episode title found on {url}")
        return None

    anime, _, episode = parts.groups()
    scene: ScrapedScene = {
        "title": f"{anime} / {episode}",
        "urls": [canonical(tree, url)],
    }
    if href := first(
        tree, '//ul[@class="main-tabs"]//li[contains(@class, "anime")]//a/@href'
    ):
        scene["groups"] = [{"name": anime, "urls": [absolute(href)]}]
    if date := first(
        tree, '//div[@id="layout-main"]//span[@itemprop="datePublished"]/@content'
    ):
        scene["date"] = date
    if details := description(tree):
        scene["details"] = details
    if studio := studio_name(tree):
        scene["studio"] = {"name": studio}
    # The episode page shows its anime's cover
    if cover := first(
        tree, '//div[@id="layout-main"]//img[contains(@src, "/images/main/")]/@src'
    ):
        scene["image"] = cover
    if tags := every(
        tree, f'{INFO}//tr[contains(@class, "tags")]//span[@class="tagname"]'
    ):
        scene["tags"] = tag_list(tags)
    characters = tree.xpath(
        '//div[contains(@class, "g_section characters")]//div[@itemprop="character"]/a'
    )
    performers: list[ScrapedPerformer] = []
    for a in characters:
        if (
            (name := first(a, "span"))
            and (href := a.get("href"))
            and (character := absolute(href)) not in [p["urls"][0] for p in performers]
        ):
            performers.append({"name": name, "urls": [character]})
    if performers:
        scene["performers"] = performers
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch(url)) is None:
        return None
    return scene_from_episode(tree, url)


def search(query: str, entity: str) -> list:
    url = f"{BASE}/search/anime/?adb.search={quote(query)}&entity.{entity}=1"
    if (tree := fetch(url)) is None:
        return []
    return tree.xpath('//td[@class="relid"]/..')


def episode_rows(tree: html.HtmlElement) -> list[tuple[str, str, str]]:
    "(number, title, URL) for each episode in an anime page's episode list"
    return [
        (number, title, absolute(href))
        for row in tree.xpath('//table[@id="eplist"]//tr')
        if (number := first(row, 'td[contains(@class, "eid")]'))
        and (
            title := first(row, 'td[contains(@class, "title")]//label')
            or first(row, 'td[contains(@class, "title")]')
        )
        and (
            href := first(
                row,
                './/a[starts-with(@href, "/episode/")][not(contains(@href, "/edit")) and not(contains(@href, "/vote"))]/@href',
            )
        )
    ]


def find_anime(query: str, guess: bool) -> tuple[str, html.HtmlElement] | None:
    """
    The anime titled exactly like the query, as its title and page; otherwise the
    top result when guessing, or the only result when not
    """
    links = [
        link
        for row in search(query, "animetb")
        for link in row.xpath('td[@class="relid"]/a')[:1]
    ]
    # AniDB can rank a sequel above the series itself
    exact = [link for link in links if _text(link).casefold() == query.casefold()]
    if not (picked := exact or (links[:1] if guess or len(links) == 1 else [])):
        return None
    if (tree := fetch(absolute(picked[0].get("href")))) is None:
        return None
    return _text(picked[0]), tree


def scene_search(query: str) -> list[ScrapedScene]:
    results: list[ScrapedScene] = []
    # Episode titles rarely contain the anime's name, so list the best anime match first
    if anime := find_anime(query, guess=True):
        name, tree = anime
        results += [
            {"title": f"{name} / {title}", "urls": [url]}
            for _, title, url in episode_rows(tree)
        ]
    for row in search(query, "eptb"):
        links = row.xpath('td[@class="relid"]/a')
        if len(links) == 2 and (url := absolute(links[1].get("href"))) not in [
            r["urls"][0] for r in results
        ]:
            # "S4 - Complete BOX Luxury Recording" -> "Complete BOX Luxury Recording"
            episode = re.sub(r"^\w+ - ", "", _text(links[1]))
            results.append({"title": f"{_text(links[0])} / {episode}", "urls": [url]})
    return results


def performer_search(query: str) -> list[PerformerSearchResult]:
    return [
        {"name": _text(link), "urls": [absolute(link.get("href"))]}
        for row in search(query, "chartb")
        for link in row.xpath('td[@class="relid"]/a')[:1]
    ]


def scene_from_fragment(args: dict) -> ScrapedScene | None:
    if not (
        path := next(
            (f["path"] for f in args.get("files") or [] if f.get("path")), None
        )
    ):
        log.error("This scene has no file to take a title from")
        return None
    # "[Group] My Lewd Anime - 01 (720p) (x264).mkv" -> "My Lewd Anime", episode 1
    filename = re.sub(r"\[.*?\]|\(.*?\)", "", Path(path).stem)
    # Underscores count as word characters, so \b can't end the number
    number = re.search(r"[\s_]-[\s_](\d{1,3})(?:v\d)?(?!\d)", filename)
    name = re.sub(r"[\s_]-[\s_]\d{1,3}(?:v\d)?(?!\d).*", "", filename)
    query = " ".join(re.sub(r"[-_]", " ", name).split())
    if not (anime := find_anime(query, guess=False)):
        log.error(f"No unique anime found for '{query}', try scraping by name or URL")
        return None
    _, tree = anime
    episodes = [(n, url) for n, _, url in episode_rows(tree) if n.isdigit()]
    if number:
        url = next((url for n, url in episodes if int(n) == int(number.group(1))), None)
    else:
        url = episodes[0][1] if len(episodes) == 1 else None
    if not url:
        log.error(
            f"Could not tell which episode of '{query}' this is, try scraping by name or URL"
        )
        return None
    return scene_from_url(url)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if (
            url and (tree := fetch(url)) is not None
        ):
            result = performer_from_tree(tree, url)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name)
        case "scene-by-url" | "scene-by-query-fragment", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment", _:
            result = scene_from_fragment(args)
        case "group-by-url", {"url": url} if url and (tree := fetch(url)) is not None:
            result = group_from_tree(tree, url)
        case "performer-by-url" | "group-by-url", _:
            pass
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
