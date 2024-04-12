import json
import re
import requests
import sys
from unicodedata import normalize
from html.parser import HTMLParser

import py_common.log as log
from py_common.types import ScrapedMovie, ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import dig, guess_nationality, replace_all, scraper_args

# Maps the `site_domain` key from the API
# to studio names currently used on StashDB
studio_map = {
    "2girls1camera.com": "2 Girls 1 Camera",
    "allanal.com": "All Anal",
    "alterotic.com": "Alt Erotic",
    "amazingfilms.com": "Amazing Films",
    "analonly.com": "Anal Only",
    "analjesse.com": "Anal Jesse",
    "benefitmonkey.com": "Benefit Monkey",
    "biggulpgirls.com": "Big Gulp Girls",
    "bjraw.com": "BJ Raw",
    "blackbullchallenge.com": "Black Bull Challenge",
    "cougarseason.com": "Cougar Season",
    "creampiethais.com": "Creampie Thais",
    "deepthroatsirens.com": "Deepthroat Sirens",
    "dirtyauditions.com": "Dirty Auditions",
    "divine-dd.com": "Divine-DD",
    "facialsforever.com": "Facials Forever",
    "freakmobmedia.com": "FreakMob Media",
    "gogobarauditions.com": "Gogo Bar Auditions",
    "gotfilled.com": "Got Filled",
    "hobybuchanon.com": "Hoby Buchanon",
    "inkedpov.com": "Inked POV",
    "inserted.com": "Inserted",
    "jav888.com": "JAV888",
    "lady-sonia.com": "Lady Sonia",
    "lezkey.com": "LezKey",
    "lucidflix.com": "LucidFlix",
    "meanfeetfetish.com": "Mean Feet Fetish",
    "members.hobybuchanon.com": "Hoby Buchanon",
    "mongerinasia.com": "Monger In Asia",
    "nylonperv.com": "Nylon Perv",
    "nympho.com": "Nympho",
    "poundedpetite.com": "Pounded Petite",
    "premium-nickmarxx.com": "Nick Marxx",
    "red-xxx.com": "Red-XXX",
    "rickysroom.com": "Ricky's Room",
    "s3xus.com": "S3XUS",
    "seska.com": "Seska",
    "sexymodernbull.com": "Sexy Modern Bull",
    "shesbrandnew.com": "She's Brand New",
    "sidechick.com": "SIDECHICK",
    "suckthisdick.com": "Suck This Dick",
    "swallowed.com": "Swallowed",
    "thaigirlswild.com": "Thai Girls Wild",
    "topwebmodels.com": "Top Web Models",
    "trueanal.com": "True Anal",
    "twmclassics.com": "TWM Classics",
    "xful.com": "Xful",
    "yesgirlz.com": "Yes Girlz",
    "yummycouple.com": "Yummy Couple",
    "z-filmz-originals.com": "Z-Filmz",
}


def clean_url(url: str) -> str:
    # remove any query parameters
    return re.sub(r"\?.*", "", url)


# Some sites only work with the `tour.` subdomain
def fix_url(url: str) -> str:
    url = url.replace("twmclassics.com", "topwebmodels.com")
    url = url.replace("suckthisdick.com", "hobybuchanon.com")
    url = url.replace("premium-nickmarxx.com", "nickmarxx.com")
    tour_domain = (
        "nympho",
        "allanal",
        "analonly",
        "2girls1camera",
        "biggulpgirls",
        "deepthroatsirens",
        "facialsforever",
        "poundedpetite",
        "seska",
        "swallowed",
        "shesbrandnew",
        "topwebmodels",
        "trueanal",
        "twmclassics",
    )
    return re.sub(rf"//(?<!tour\.)({'|'.join(tour_domain)})", r"//tour.\1", url)


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


def make_performer_url(slug: str, site: str) -> str:
    return f"https://{site}/models/{slug}"


def get_studio(site: str) -> ScrapedStudio:
    name = studio_map.get(site, site)
    studio: ScrapedStudio = {
        "name": name,
        "url": f"https://{site}",
    }
    if name == "Suck This Dick":
        studio["parent"] = get_studio("hobybuchanon.com")
    return studio


def to_scraped_performer(raw_performer: dict) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": raw_performer["name"],
        "gender": raw_performer["gender"],
        "url": make_performer_url(raw_performer["slug"], raw_performer["site_domain"]),
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
        performer["country"] = guess_nationality(country)

    if twitter := raw_performer.get("Twitter", "").removeprefix("@"):
        performer["twitter"] = f"https://twitter.com/{twitter}"

    if instagram := raw_performer.get("Instagram", "").removeprefix("@"):
        performer["instagram"] = f"https://www.instagram.com/{instagram}"

    return performer


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

    site = raw_movie["site_domain"]
    movie["studio"] = get_studio(site)

    # There is no reliable way to construct a movie URL from the data

    return movie


def to_scraped_scene(raw_scene: dict) -> ScrapedScene:
    site = raw_scene["site_domain"]
    scene: ScrapedScene = {}

    if title := raw_scene.get("title"):
        scene["title"] = title
    if date := raw_scene.get("publish_date"):
        scene["date"] = date[:10].replace("/", "-")
    if details := raw_scene.get("description"):
        scene["details"] = strip_tags(details)
    if scene_id := raw_scene.get("id"):
        scene["code"] = str(scene_id)
    if models := raw_scene.get("models_thumbs"):
        scene["performers"] = [
            {
                "name": x["name"],
                "image": x["thumb"],
                "url": make_performer_url(x["slug"], site),
            }
            for x in models
        ]
    if tags := raw_scene.get("tags"):
        scene["tags"] = [{"name": x} for x in tags]

    scene["studio"] = get_studio(site)

    # trailer_screencap is what's shown on most sites
    # extra_thumbnails has the best sizes and in most cases the first one is the same as thumb
    # thumb is a good fallback if extra_thumbnails is not available
    # final fallback is special_thumbnails
    cover_candidates = filter(
        None,
        (
            dig(raw_scene, "poster_url"),            
            dig(raw_scene, "trailer_screencap"),
            dig(raw_scene, "extra_thumbnails", 0),
            dig(raw_scene, "thumb"),
            dig(raw_scene, "special_thumbnails", 0),
        ),
    )
    # No animated scene covers
    img_exts = (".jpg", ".jpeg", ".png")

    if scene_cover := next((x for x in cover_candidates if x.endswith(img_exts)), None):
        scene["image"] = scene_cover

    # There is no reliable way to construct a scene URL from the data

    return scene


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

    return to_scraped_performer(props["model"])


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

    result = replace_all(result, "url", fix_url)  # type: ignore
    print(json.dumps(result))
