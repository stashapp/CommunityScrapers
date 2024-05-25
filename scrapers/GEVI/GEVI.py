import json
import re
import sys
from urllib.parse import urlparse, urlencode

from bs4 import BeautifulSoup, Tag
import cloudscraper

from py_common.config import get_config
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedMovie, ScrapedStudio
from py_common.util import scraper_args
import py_common.log as log


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


# For performer/studio links from episode/movie pages
def name_with_url(link: Tag) -> dict:
    name = link.get_text(strip=True)
    if not config.disambiguate_names:
        name, _ = parse_name(name)

    performer = {"name": name}
    if (url := link.get("href")) and isinstance(url, str):
        performer["url"] = abs_url(url)
    return performer


# Not really a HTML table, but the layout is consistent
def from_table(soup: Tag, key: str) -> str | None:
    if (tag := soup.find("div", string=key)) and (value := tag.find_next("div")):
        return value.get_text()


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

    if image := soup.find("img", src=lambda x: "Episodes" in x):
        scene["image"] = abs_url(image["src"])  # type: ignore

    if details := soup.find("p"):
        scene["details"] = details.get_text(strip=True)

    if (date := soup.find("span", string="Date:")) and (date := date.next_sibling):
        scene["date"] = date.get_text(strip=True)

    if performers := soup.find_all("a", href=lambda x: "performer" in x):
        scene["performers"] = [  # type: ignore
            {**name_with_url(p), "gender": "MALE"} for p in performers
        ]

    if studio := soup.find("a", href=lambda x: "company" in x):
        scene["studio"] = name_with_url(studio)  # type: ignore

    scene["url"] = url

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
        "url": url,
        "gender": "MALE",
    }

    if disambiguation:
        performer["disambiguation"] = disambiguation

    if image := soup.find("img", src=lambda x: "Stars" in x):
        performer["image"] = base_url._replace(path=image["src"]).geturl()  # type: ignore

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

    if tattoos := from_table(soup, "Tattoos:"):
        performer["tattoos"] = tattoos.strip()

    if skin_color := from_table(soup, "Skin:"):
        performer["ethnicity"] = ethnicity_map.get(skin_color, skin_color)  # type: ignore

    if country := from_table(soup, "From:"):
        performer["country"] = country.split(",")[-1].strip()

    if birth_year := from_table(soup, "Born:"):
        # Unfortunately GEVI only tracks birth years, not full dates
        performer["birthdate"] = f"{birth_year}-01-01"

    if death_year := from_table(soup, "Died:"):
        performer["death_date"] = f"{death_year}-01-01"

    if (bio := soup.find("div", string="Notes:")) and (bio := bio.find_next("div")):
        performer["details"] = bio.get_text(separator="\n")

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
    elif (name := args.get("name")) and (
        candidate := next(iter(performer_search(name)), None)
    ):
        return performer_from_url(candidate["url"])  # type: ignore because we know url will be set
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
    found = [BeautifulSoup(x[1], "html.parser").contents[0] for x in res.json()["data"]]
    return [
        {"name": found.text, "url": base_url._replace(path=found["href"]).geturl()}  # type: ignore
        for found in found
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

    if covers := movie_section.find_all("img", src=lambda x: "Covers" in x):
        movie["front_image"] = abs_url(covers[0]["src"])
        if len(covers) > 1:
            movie["back_image"] = abs_url(covers[1]["src"])

    if (details := soup.find("span", string="Description source:")) and (
        (details := details.parent) and (details := details.find_next("div"))
    ):
        movie["synopsis"] = details.get_text(strip=True)

    if (table := movie_section.find("table")) and isinstance(table, Tag):
        headers = [th.get_text() for th in table.find_all("th")]
        values = table.find_all("td")
        table = dict(zip(headers, values))

        if length := table.get("Length"):
            movie["duration"] = f"{length.get_text(strip=True)}:00"

        if released := table.get("Released"):
            # Unfortunately GEVI only tracks release years, not full dates
            movie["date"] = f"{released.get_text(strip=True)}-01-01"

        if distributor_cell := table.get("Distributor"):
            distributor: ScrapedStudio = name_with_url(distributor_cell.find("a"))  # type: ignore
            if (studio := distributor_cell.find("br")) and (
                studio := studio.next_sibling.get_text(strip=True)
            ):
                movie["studio"] = {"name": studio, "parent": distributor}
            else:
                movie["studio"] = distributor

    if directors := movie_section.find_all("a", href=lambda x: "director" in x):
        movie["director"] = ", ".join(d.get_text(strip=True) for d in directors)

    movie["url"] = url

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
