import json
import re
import sys
import requests
from unicodedata import normalize
from html.parser import HTMLParser

import py_common.log as log
from py_common.types import ScrapedMovie, ScrapedPerformer, ScrapedScene
from py_common.util import dig, scraper_args


studio_map = {
    "2girls1camera.com": "2 Girls 1 Camera",
    "biggulpgirls.com": "Big Gulp Girls",
    "cougarseason.com": "Cougar Season",
    "deepthroatsirens.com": "Deepthroat Sirens",
    "facialsforever.com": "Facials Forever",
    "poundedpetite.com": "Pounded Petite",
    "shesbrandnew.com": "She's Brand New",
    "topwebmodels.com": "Top Web Models",
    "twmclassics.com": "TWM Classics",
    "lucidflix.com": "LucidFlix",
    "inserted.com": "Inserted",
    "rickysroom.com": "Ricky's Room",
    "sidechick.com": "SIDECHICK",
    # Note: look into adding other sites with the same structure, some listed here
    # https://x3guide.com/companies/kb-productions
}


def clean_url(url: str) -> str:
    # remove any query parameters
    return re.sub(r"\?.*", "", url)


def strip_tags(html: str) -> str:
    class ToPlainText(HTMLParser):
        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = []

        def handle_data(self, d):
            self.text.append(d)

        def get_data(self):
            return "".join(self.text)

    s = ToPlainText()
    s.feed(html)
    return normalize("NFKD", s.get_data())


def fetch_page_props(url: str) -> dict | None:
    r = requests.get(url)

    if r.status_code != 200:
        log.error(f"Failed to fetch page HTML: {r.status_code}")
        return None

    matches = re.findall(
        r'(?:<script id="__NEXT_DATA__" type="application\/json">({.+})<\/script>)',
        r.text,
        re.MULTILINE,
    )
    if not matches:
        log.error("Could not find JSON data on page")
        return None

    parsed_json = json.loads(matches[0])

    if not (content := dig(parsed_json, "props", "pageProps")):
        log.error("Could not find page props in JSON data")

    return content


state_map = {
    "AK": "USA",
    "AL": "USA",
    "AR": "USA",
    "AZ": "USA",
    "CA": "USA",
    "CO": "USA",
    "CT": "USA",
    "DC": "USA",
    "DE": "USA",
    "FL": "USA",
    "GA": "USA",
    "HI": "USA",
    "IA": "USA",
    "ID": "USA",
    "IL": "USA",
    "IN": "USA",
    "KS": "USA",
    "KY": "USA",
    "LA": "USA",
    "MA": "USA",
    "MD": "USA",
    "ME": "USA",
    "MI": "USA",
    "MN": "USA",
    "MO": "USA",
    "MS": "USA",
    "MT": "USA",
    "NC": "USA",
    "ND": "USA",
    "NE": "USA",
    "NH": "USA",
    "NJ": "USA",
    "NM": "USA",
    "NV": "USA",
    "NY": "USA",
    "OH": "USA",
    "OK": "USA",
    "OR": "USA",
    "PA": "USA",
    "RI": "USA",
    "SC": "USA",
    "SD": "USA",
    "TN": "USA",
    "TX": "USA",
    "UT": "USA",
    "VA": "USA",
    "VT": "USA",
    "WA": "USA",
    "WI": "USA",
    "WV": "USA",
    "WY": "USA",
    "Alabama": "USA",
    "Alaska": "USA",
    "Arizona": "USA",
    "Arkansas": "USA",
    "California": "USA",
    "Colorado": "USA",
    "Connecticut": "USA",
    "Delaware": "USA",
    "Florida": "USA",
    "Georgia": "USA",
    "Hawaii": "USA",
    "Idaho": "USA",
    "Illinois": "USA",
    "Indiana": "USA",
    "Iowa": "USA",
    "Kansas": "USA",
    "Kentucky": "USA",
    "Louisiana": "USA",
    "Maine": "USA",
    "Maryland": "USA",
    "Massachusetts": "USA",
    "Michigan": "USA",
    "Minnesota": "USA",
    "Mississippi": "USA",
    "Missouri": "USA",
    "Montana": "USA",
    "Nebraska": "USA",
    "Nevada": "USA",
    "New Hampshire": "USA",
    "New Jersey": "USA",
    "New Mexico": "USA",
    "New York": "USA",
    "North Carolina": "USA",
    "North Dakota": "USA",
    "Ohio": "USA",
    "Oklahoma": "USA",
    "Oregon": "USA",
    "Pennsylvania": "USA",
    "Rhode Island": "USA",
    "South Carolina": "USA",
    "South Dakota": "USA",
    "Tennessee": "USA",
    "Texas": "USA",
    "Utah": "USA",
    "Vermont": "USA",
    "Virginia": "USA",
    "Washington": "USA",
    "West Virginia": "USA",
    "Wisconsin": "USA",
    "Wyoming": "USA",
    "United States": "USA",
}


def to_scraped_performer(raw_performer: dict) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": raw_performer["name"],
        "gender": raw_performer["gender"],
    }

    if image := raw_performer.get("thumb"):
        performer["image"] = image

    if bio := raw_performer.get("Bio"):
        performer["details"] = strip_tags(bio)

    if (birthdate := raw_performer.get("Birthdate")) and birthdate != "1969-12-31":
        performer["birthdate"] = birthdate

    if measurements := raw_performer.get("Measurements"):
        performer["measurements"] = measurements

    if eye_color := raw_performer.get("Eyes"):
        performer["eye_color"] = eye_color

    if ethnicity := raw_performer.get("Ethnicity"):
        performer["ethnicity"] = ethnicity

    if (height_ft := raw_performer.get("Height")) and (
        h := re.match(r"(\d+)\D+(\d+).+", height_ft)
    ):
        height_cm = round((float(h.group(1)) * 12 + float(h.group(2))) * 2.54)
        performer["height"] = str(height_cm)

    if (weight_lb := raw_performer.get("Weight")) and (
        w := re.match(r"(\d+)\slbs", weight_lb)
    ):
        weight_kg = round(float(w.group(1)) / 2.2046)
        performer["weight"] = str(weight_kg)

    if hair_color := raw_performer.get("Hair"):
        performer["hair_color"] = hair_color

    if country := raw_performer.get("Born"):
        country = country.split(",")[-1].strip()
        performer["country"] = state_map.get(country, country)

    return performer


def to_scraped_scene(raw_scene: dict) -> ScrapedScene:
    scene: ScrapedScene = {}

    if title := raw_scene.get("title"):
        scene["title"] = title
    if date := raw_scene.get("publish_date"):
        scene["date"] = date[:10].replace("/", "-")
    if details := raw_scene.get("description"):
        scene["details"] = strip_tags(details)
    if scene_id := raw_scene.get("id"):
        scene["code"] = str(scene_id)
    if models := raw_scene.get("models"):
        scene["performers"] = [{"name": x} for x in models]
    if tags := raw_scene.get("tags"):
        scene["tags"] = [{"name": x} for x in tags]

    if site := dig(raw_scene, "site_domain"):
        studio_name = studio_map.get(site, site)
        scene["studio"] = {"name": studio_name}

    # extra_thumbnails has the best sizes and in most cases the first one is the same as thumb
    # thumb is a good fallback if extra_thumbnails is not available
    # final fallback is special_thumbnails
    cover_candidates = filter(
        None,
        (
            dig(raw_scene, "extra_thumbnails", 0),
            dig(raw_scene, "thumb"),
            dig(raw_scene, "special_thumbnails", 0),
        ),
    )
    # No animated scene covers
    img_exts = (".jpg", ".jpeg", ".png")

    if scene_cover := next((x for x in cover_candidates if x.endswith(img_exts)), None):
        scene["image"] = scene_cover

    return scene


def to_scraped_movie(raw_movie: dict) -> ScrapedMovie:
    movie: ScrapedMovie = {
        "name": raw_movie["title"],
    }

    if date := raw_movie.get("publish_date"):
        movie["date"] = date[:10].replace("/", "-")

    if duration := raw_movie.get("videos_duration"):
        movie["duration"] = duration

    if cover := raw_movie.get("trailer_screencap"):
        movie["front_image"] = cover

    if site := dig(raw_movie, "site_domain"):
        studio_name = studio_map.get(site, site)
        movie["studio"] = {"name": studio_name}

    return movie


def scrape_scene(url: str) -> ScrapedScene | None:
    if not (props := fetch_page_props(url)):
        return None

    scene = to_scraped_scene(props["content"])
    scene["url"] = url

    if playlist := dig(props, "playlist", "data", 0):
        scene["movies"] = [to_scraped_movie(playlist)]

    return scene


def scrape_performer(url: str) -> ScrapedPerformer | None:
    if not (props := fetch_page_props(url)):
        return None

    performer = to_scraped_performer(props["model"])
    performer["url"] = url

    return performer


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scrape_scene(clean_url(url))
        case "performer-by-url", {"url": url} if url:
            result = scrape_performer(clean_url(url))
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)
    print(json.dumps(result))
