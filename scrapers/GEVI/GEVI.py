import json
import re
import sys
from collections.abc import Callable
from urllib.parse import urlencode, urlparse

import cloudscraper
from bs4 import BeautifulSoup, Comment, Tag

from py_common import log
from py_common.config import get_config
from py_common.types import ScrapedMovie, ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import guess_nationality, scraper_args

config = get_config(
    default="""# Should we include the parenthesized disambiguation in performer names?
# false: "John Doe" 
# true:  "John Doe (II)"

# For names
disambiguate_names = False

# For aliases
disambiguate_aliases = False
"""
)


base_url = urlparse("https://gayeroticvideoindex.com")


def abs_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return base_url._replace(path=url).geturl()


scraper = cloudscraper.create_scraper()
scraper.headers.update({"Referer": base_url.netloc})


def parse_name(name: str) -> tuple[str, str | None]:
    "Parses a name and optional disambiguation from a string"
    match = re.match(r"^(.+?)(?:\s*\((.*?)\))?$", name)
    if match:
        return match.group(1), match.group(2)
    return name, None


def containing(text: str) -> Callable[[str | None], bool]:
    "Attribute filter for find(): bs4 also calls it with None for tags lacking the attribute"
    return lambda value: value is not None and text in value


def link_name(link: Tag) -> str:
    name = link.get_text(strip=True)
    if not config.disambiguate_names:
        name, _ = parse_name(name)
    return name


def link_urls(link: Tag) -> list[str]:
    url = link.get("href")
    return [abs_url(url)] if isinstance(url, str) and url else []


# For performer links from episode pages
def performer_link(link: Tag) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": link_name(link), "gender": "MALE"}
    if urls := link_urls(link):
        performer["urls"] = urls
    return performer


# For studio links from episode/movie pages
def studio_link(link: Tag) -> ScrapedStudio:
    studio: ScrapedStudio = {"name": link_name(link)}
    if urls := link_urls(link):
        studio["urls"] = urls
    return studio


# Not really a HTML table, but the layout is consistent
def from_table(soup: Tag, key: str) -> str | None:
    if (tag := soup.find("div", string=key)) and (value := tag.find_next("div")):
        return value.get_text()


def collapse(text: str) -> str:
    return " ".join(text.split())


def paragraphs(box: Tag) -> str:
    "Paragraph texts, coping with the site's unclosed <p> tags nesting inside each other"
    texts = (
        collapse(
            "".join(
                child.get_text()
                for child in p.children
                if not isinstance(child, Comment)
                and not (isinstance(child, Tag) and child.name == "p")
            )
        )
        for p in box.find_all("p")
    )
    return "\n\n".join(text for text in texts if text)


def tattoos(soup: Tag) -> str | None:
    # "Tattoos: <locations><br/><span>per-location descriptions separated by <br/></span>"
    if not (label := soup.find("span", string=re.compile(r"^\s*Tattoos:"))) or not (
        cell := label.parent
    ):
        return None
    label.extract()
    for br in cell.find_all("br"):
        br.replace_with("\n")
    lines = (collapse(line) for line in cell.get_text().split("\n"))
    return "\n".join(line for line in lines if line) or None


def scene_from_url(url: str) -> ScrapedScene | None:
    res = scraper.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    soup = soup.select("div#data section")
    if not soup:
        log.error(f"Cannot find episode section in {url}")
        return None

    soup = soup[0]

    scene: ScrapedScene = {}

    if title := soup.find("h1"):
        scene["title"] = title.get_text(strip=True)

    if (image := soup.find("img", src=containing("Episodes"))) and isinstance(
        src := image.get("src"), str
    ):
        scene["image"] = abs_url(src)

    if (box := soup.select_one("div.wideCols-1")) and (details := paragraphs(box)):
        scene["details"] = details

    if (date := soup.find("span", string="Date:")) and (date := date.next_sibling):
        scene["date"] = date.get_text(strip=True)

    if performers := soup.find_all("a", href=containing("performer")):
        scene["performers"] = [performer_link(p) for p in performers]

    if studio := soup.find("a", href=containing("company")):
        scene["studio"] = studio_link(studio)

    scene["urls"] = [url]

    return scene


def scene_from_fragment(args: dict) -> ScrapedScene | None:
    if url := args.get("url"):
        return scene_from_url(url)
    log.error("Cannot scrape scene without a URL")


hair_map = {
    "Blond": "Blonde",
    "Brown": "Brunette",
}

# GEVI tracks skin color so there's no way to really know ethnicity
ethnicity_map = {
    "White": "Caucasian",
}


def performer_from_url(url: str) -> ScrapedPerformer | None:
    res = scraper.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    soup = soup.select("div#data section")
    if not soup:
        log.error(f"Cannot find performer section in {url}")
        return None

    soup = soup[0]

    if not (name := soup.find("h1", attrs={"class": "text-yellow-200"})):
        log.error(f"Cannot find performer name in {url}")
        return None

    if config.disambiguate_names:
        name, disambiguation = parse_name(name.text)
    else:
        name = name.text
        disambiguation = None

    performer: ScrapedPerformer = {
        "name": name,
        "urls": [url],
        "gender": "MALE",
    }

    if disambiguation:
        performer["disambiguation"] = disambiguation

    if (image := soup.find("img", src=containing("Stars"))) and isinstance(
        src := image.get("src"), str
    ):
        performer["image"] = abs_url(src)

    if (hair_color := from_table(soup, "Hair:")) and (hair := hair_map.get(hair_color)):
        performer["hair_color"] = hair.split(",")[0]  # type: ignore because we've mapped all hair colors

    if eye_color := from_table(soup, "Eyes:"):
        performer["eye_color"] = eye_color  # type: ignore

    if height := from_table(soup, "Height:"):
        performer["height"] = height.split("/")[-1].strip().removesuffix("cm")

    if foreskin := from_table(soup, "Foreskin:"):
        performer["circumcised"] = foreskin

    if dick_size := from_table(soup, "Dick Size:"):
        performer["penis_length"] = dick_size.split("/")[-1].strip().removesuffix("cm")

    if weight := from_table(soup, "Weight:"):
        performer["weight"] = weight.split("/")[-1].strip().removesuffix("kg")

    if tattoo_text := tattoos(soup):
        performer["tattoos"] = tattoo_text

    if piercings := from_table(soup, "Piercing:"):
        performer["piercings"] = piercings.strip()

    if skin_color := from_table(soup, "Skin:"):
        performer["ethnicity"] = ethnicity_map.get(skin_color, skin_color)  # type: ignore

    if country := from_table(soup, "From:"):
        performer["country"] = guess_nationality(country)

    if birth_year := from_table(soup, "Born:"):
        # Unfortunately GEVI only tracks birth years, not full dates
        performer["birthdate"] = f"{birth_year[-4:]}"

    if death_year := from_table(soup, "Died:"):
        performer["death_date"] = f"{death_year[-4:]}"

    if (
        (bio := soup.find("div", string="Notes:"))
        and (bio := bio.find_next("div"))
        and (notes := bio.get_text(separator="\n")) != "none available"
    ):
        performer["details"] = notes

    if aliases := soup.find_all("h2"):
        if config.disambiguate_aliases:
            performer["aliases"] = ", ".join(alias.text for alias in aliases)
        else:
            deduplicated = {parse_name(alias.text)[0] for alias in aliases}
            performer["aliases"] = ", ".join(sorted(deduplicated))

    return performer


def performer_from_fragment(args: dict) -> ScrapedPerformer | None:
    if url := args.get("url"):
        return performer_from_url(url)
    elif (
        (name := args.get("name"))
        and (candidate := next(iter(performer_search(name)), None))
        and (urls := candidate.get("urls"))
    ):
        return performer_from_url(urls[0])
    log.error("Cannot scrape performer without a URL or name")


def performer_search(name: str) -> list[ScrapedPerformer]:
    search_params = {
        "draw": 2,
        "start": 0,
        "length": 10,
        "search[value]": name,
        "search[regex]": "false",
    }
    search_url = base_url._replace(path="shpr", query=urlencode(search_params)).geturl()
    res = scraper.get(search_url)
    links = (
        BeautifulSoup(row[1], "html.parser").find("a") for row in res.json()["data"]
    )
    return [
        {"name": link.get_text(), "urls": link_urls(link)}
        for link in links
        if isinstance(link, Tag)
    ]


def movie_from_url(url: str) -> ScrapedMovie | None:
    res = scraper.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    movie_section = next(iter(soup.select("section#data section")), None)
    if not movie_section:
        log.error(f"Cannot find movie section in {url}")
        return None

    movie: ScrapedMovie = {}

    if name := movie_section.find("h1"):
        movie["name"] = name.get_text(strip=True)

    covers = [
        abs_url(src)
        for img in movie_section.find_all("img", src=containing("Covers"))
        if isinstance(src := img.get("src"), str)
    ]
    if covers:
        movie["front_image"] = covers[0]
    if len(covers) > 1:
        movie["back_image"] = covers[1]

    if (
        (source := soup.find("span", string="Description source:"))
        and (source := source.parent)
        and isinstance(details := source.find_next("div"), Tag)
        and (synopsis := paragraphs(details))
    ):
        movie["synopsis"] = synopsis

    if (table := movie_section.find("table")) and isinstance(table, Tag):
        headers = [th.get_text() for th in table.find_all("th")]
        values = table.find_all("td")
        table = dict(zip(headers, values))

        # both cells can be blank, and Released can be "?"
        if (length := table.get("Length")) and (
            minutes := length.get_text(strip=True)
        ).isdigit():
            movie["duration"] = f"{minutes}:00"

        if (released := table.get("Released")) and (
            year := released.get_text(strip=True)
        ).isdigit():
            # Unfortunately GEVI only tracks release years, not full dates
            movie["date"] = year

        if (distributor_cell := table.get("Distributor")) and isinstance(
            link := distributor_cell.find("a"), Tag
        ):
            distributor = studio_link(link)
            # "<distributor link><br/>studio name" when they differ
            if (
                (br := distributor_cell.find("br"))
                and (sibling := br.next_sibling)
                and (studio := sibling.get_text(strip=True))
            ):
                movie["studio"] = {"name": studio, "parent": distributor}
            else:
                movie["studio"] = distributor

    if directors := movie_section.find_all("a", href=containing("director")):
        movie["director"] = ", ".join(d.get_text(strip=True) for d in directors)

    movie["urls"] = [url]

    return movie


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-fragment", args:
            result = scene_from_fragment(args)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": _domains} if name:
            result = performer_search(name)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
