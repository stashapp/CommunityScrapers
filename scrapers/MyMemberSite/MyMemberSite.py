import json
import sys
import re
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args, dig
from py_common.types import ScrapedScene, ScrapedGallery

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
    }
)

# Maps public URLs to a API base URLs as well as pretty studio names
_studios = {
    "aeriefans.com": {
        "api": "aerie-saunders.mymember.site",
        "name": "Aerie Saunders",
    },
    "alterpic.com": {
        "api": "alterpic.mymember.site",
        "name": "Alterpic",
    },
    "amieesfetishhouse.com": {
        "api": "amiees-fetish-house.mymember.site",
        "name": "Amiees Fetish House",
    },
    "asianmassagemaster.com": {
        "api": "asianmassagemaster.mymember.site",
        "name": "Asian Massage Master",
    },
    "bbwxxxadventures.com": {
        "api": "bbwxxxadventures.mymember.site",
        "name": "BBW XXX Adventures",
    },
    "bdsmkinkyplay.com": {
        "api": "bdsmkinkyplay.mymember.site",
        "name": "BDSM Kinky Play",
    },
    "beverlybluexxx.com": {
        "api": "beverlybluexxx.mymember.site",
        "name": "BeverlyBlueXxX",
    },
    "bindastimesuk.com": {
        "api": "bindastimesuk.mymember.site",
        "name": "Bindastimesuk",
    },
    "bondageliberation.com": {
        "api": "bondageliberation.mymember.site",
        "name": "Bondage Liberation",
    },
    "brookesballoons.com": {
        "api": "brookesballoons.mymember.site",
        "name": "BrookesBalloons",
    },
    "castersworldwide.com": {
        "api": "castersworldwide.mymember.site",
        "name": "Casters Worldwide",
    },
    "chloestoybox.com": {
        "api": "chloestoybox.mymember.site",
        "name": "Chloe Toy",
    },
    "clubsteffi.fun": {
        "api": "clubsteffi.mymember.site",
        "name": "ClubSteffi",
    },
    "cristalkinky.com": {
        "api": "cristalkinky.mymember.site",
        "name": "Cristal Kinky",
    },
    "curvymary.com": {
        "api": "curvy-mary.mymember.site",
        "name": "Curvy Mary",
    },
    "deemariexxx.com": {
        "api": "deemariexxx.mymember.site",
        "name": "Dee Marie",
    },
    "europornvids.com": {
        "api": "europornvids.mymember.site",
        "name": "Euro Porn Vids",
    },
    "faexcheta.com": {
        "api": "faexcheta.mymember.site",
        "name": "Fae and Cheta",
    },
    "fetiliciousfans.com": {
        "api": "fetilicousfans.mymember.site",
        "name": "Miss Fetilicious",
    },
    "fetishchimera.com": {
        "api": "fetishchimera.mymember.site",
        "name": "Fetish Chimera",
    },
    "friskyfairyk.com": {
        "api": "friskyfairyk.mymember.site",
        "name": "xoXokmarie",
    },
    "girlsofhel.com": {
        "api": "girls-of-hel.mymember.site",
        "name": "Girls of HEL",
    },
    "glass-dp.com": {
        "api": "glassdp.mymember.site",
        "name": "Glassdp",
    },
    "glassdeskproductions.com": {
        "api": "glassdeskproductions.mymember.site",
        "name": "GlassDeskProductions",
    },
    "goddesslesley.com": {
        "api": "goddesslesley.mymember.site",
        "name": "Goddess Lesley",
    },
    "goddessrobin.com": {
        "api": "goddessrobin.mymember.site",
        "name": "Goddess Robin",
    },
    "greatbritishfeet.com": {
        "api": "greatbritishfeet.mymember.site",
        "name": "Great British Feet",
    },
    "greendoorlive.tv": {
        "api": "greendoorlivetv.mymember.site",
        "name": "The World Famous Green Door",
    },
    "heavybondage4life.com": {
        "api": "heavybondage4life.mymember.site",
        "name": "Heavybondage4Life",
    },
    "hornysilver.com": {
        "api": "hornysilver.mymember.site",
        "name": "Hornysilver",
    },
    "josyblack.tv": {
        "api": "josyblack.mymember.site",
        "name": "Josy Black",
    },
    "kingnoirexxx.com": {
        "api": "kingnoirexxx.mymember.site",
        "name": "King Noire",
    },
    "kinkography.com": {
        "api": "kinkography.mymember.site",
        "name": "Kinkography",
    },
    "kinkyponygirl.com": {
        "api": "kinkyponygirl.mymember.site",
        "name": "KinkyPonygirl",
    },
    "kitehkawasaki.com": {
        "api": "kitehkawasaki.mymember.site",
        "name": "Kiteh Kawasaki",
    },
    "lady-asmondena.com": {
        "api": "ladyasmondena.mymember.site",
        "name": "Lady Asmondena",
    },
    "latexlolanoir.com": {
        "api": "latexlolanoir.mymember.site",
        "name": "Lola Noir",
    },
    "latexrapturefans.com": {
        "api": "latexrapturefans.mymember.site",
        "name": "LatexRapture",
    },
    "letseatcakexx.com": {
        "api": "letseatcakexx.mymember.site",
        "name": "LetsEatCakeXx",
    },
    "loonerlanding.com": {
        "api": "loonerlanding.mymember.site",
        "name": "Looner Landing",
    },
    "lukespov.vip": {"api": "lukespov.mymember.site", "name": "Luke's POV"},
    "marvalstudio.com": {
        "api": "marvalstudio.mymember.site",
        "name": "MarValStudio",
    },
    "michaelfittnation.com": {
        "api": "michaelfittnation.mymember.site",
        "name": "Michael Fitt",
    },
    "milenaangel.club": {
        "api": "milenaangel.mymember.site",
        "name": "MilenaAngel",
    },
    "mondofetiche.com": {
        "api": "mondofetiche.mymember.site",
        "name": "Mondo Fetiche",
    },
    "mrhappyendings.com": {
        "api": "mrhappyendings.mymember.site",
        "name": "Mr Happy Endings",
    },
    "nikitzo.com": {
        "api": "nikitzo.mymember.site",
        "name": "NIKITZO",
    },
    "nikkidavisxo.com": {
        "api": "nikkidavisxo.mymember.site",
        "name": "NikkiDavisXO",
    },
    "peacockcouple.com": {
        "api": "peacockcouple.mymember.site",
        "name": "PeacockCouple",
    },
    "pedal-passion.com": {
        "api": "pedal-passion.mymember.site",
        "name": "Pedal Passion",
    },
    "pervfect.net": {
        "api": "pervfect.mymember.site",
        "name": "Pervfect",
    },
    "riggsfilms.vip": {
        "api": "riggsfilms.mymember.site",
        "name": "Riggs Films",
    },
    "royalfetishxxx.com": {
        "api": "royalfetishxxx.mymember.site",
        "name": "RoyalFetishXXX",
    },
    "rubber-pervs.com": {
        "api": "rubberpervs.mymember.site",
        "name": "Rubber-Pervs",
    },
    "rubberdollemmalee.com": {
        "api": "rubberdollemmalee.mymember.site",
        "name": "Rubberdoll Emma Lee",
    },
    "sexyhippies.com": {
        "api": "sexyhippies.mymember.site",
        "name": "Sexy Hippies",
    },
    "shemalevalentina.com": {
        "api": "shemalevalentina.mymember.site",
        "name": "Shemale Valentina",
    },
    "strong-men.com": {
        "api": "strong-men.mymember.site",
        "name": "Strong-Men",
    },
    "tabooseduction.com": {
        "api": "tabooseduction.mymember.site",
        "name": "TabooSeduction",
    },
    "taboosexstories4k.com": {
        "api": "taboosexstories4k.mymember.site",
        "name": "Taboo Sex Stories",
    },
    "the-strapon-site.com": {
        "api": "thestraponsite.mymember.site",
        "name": "The Strapon Site",
    },
    "thegoonhole.com": {
        "api": "thegoonhole.mymember.site",
        "name": "The Goonhole",
    },
    "thekandikjewel.com": {
        "api": "thekandikjewel.mymember.site",
        "name": "The Kandi K Jewel",
    },
    "yourfitcrush.com": {
        "api": "yourfitcrush.mymember.site",
        "name": "Your Fit Crush",
    },
}


def __api_request(url) -> dict:
    log.debug(f"Fetching '{url}'")
    try:
        response = session.get(url, timeout=(3, 6))
    except requests.exceptions.RequestException as req_ex:
        log.error(f"Error fetching '{url}': {req_ex}")
        sys.exit(-1)

    if response.status_code != 200:
        log.error(f"Fetching '{url}' resulted in error status: {response.status_code}")
        sys.exit(-1)

    data = response.json()
    log.trace(f"Raw data from API: {data}")
    return data


def __parse_url(url: str) -> tuple[str, str]:
    """
    Returns the studio name and the API URL corresponding to the given URL.

    Exits if the domain is not known or if the path does not conform to the expected format
    """
    parsed = urlparse(url)

    domain = re.sub(r"^www\.", "", parsed.netloc)
    if not (studio := _studios.get(domain)):
        log.error(f"Domain {domain} not supported, URL: '{url}'")
        sys.exit(-1)

    if not (
        match := re.match(
            r"^/(?P<type>videos|photosets)/(?P<id>\d+)(?:-(?P<name>.+))?$", parsed.path
        )
    ):
        log.error(f"Unable to parse URL '{url}'")
        sys.exit(-1)

    _type, _id, slug = match.groups()

    _type = {"photosets": "photo-collections"}.get(_type, _type)

    return studio["name"], f"https://{studio['api']}/api/{_type}/{_id}"


def gallery_from_url(url: str) -> ScrapedGallery:
    studio, api_url = __parse_url(url)
    raw_gallery = __api_request(api_url)

    scraped: ScrapedGallery = {}

    if title := raw_gallery.get("title"):
        scraped["title"] = title

    if _id := raw_gallery.get("id"):
        scraped["code"] = str(_id)

    if date := raw_gallery.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_gallery.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_gallery.get("tags"):
        scraped["tags"] = [{"name": t["name"]} for t in tags]

    if cast := raw_gallery.get("casts"):
        scraped["performers"] = [{"name": p["screen_name"]} for p in cast]

    scraped["studio"] = {"name": studio}

    return scraped


def scene_from_url(url: str) -> ScrapedScene:
    studio, api_url = __parse_url(url)
    raw_scene = __api_request(api_url)

    scraped: ScrapedScene = {}

    if title := raw_scene.get("title"):
        scraped["title"] = title

    if _id := raw_scene.get("id"):
        scraped["code"] = str(_id)

    if date := raw_scene.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_scene.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_scene.get("tags"):
        scraped["tags"] = [{"name": t["name"]} for t in tags]

    if cast := raw_scene.get("casts"):
        scraped["performers"] = [{"name": p["screen_name"]} for p in cast]

    if image := dig(raw_scene, ("poster_src", "cover_photo")):
        scraped["image"] = image

    scraped["studio"] = {"name": studio}

    return scraped


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
