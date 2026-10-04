import json
import re
import sys
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    Ethnicity,
    HairColor,
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
)
from py_common.util import feet_to_cm, is_valid_url, lb_to_kg, scraper_args

ensure_requirements("lxml", "curl_cffi")

from curl_cffi import requests  # noqa: E402
from lxml import html  # noqa: E402

STUDIO_MAP = {
    "18eighteen": "18 Eighteen",
    "40somethingmag": "40 Something Mag",
    "50plusmilfs": "50 Plus MILFs",
    "60plusmilfs": "60 Plus MILFs",
    "analqts": "Anal QTs",
    "autumn-jade": "Autumn Jade",
    "bigboobalexya": "Big Boob Alexya",
    "bigboobbundle": "Big Boob Bundle",
    "bigboobspov": "Big Boobs POV",
    "bigtitangelawhite": "Big Tit Angela White",
    "bigtitkatiethornton": "Big Tit Katie Thornton",
    "bigtithitomi": "Big Tit Hitomi",
    "bigtithooker": "Big Tit Hooker",
    "bigtitterrynova": "Big Tit Terry Nova",
    "bigtitvenera": "Big Tit Venera",
    "bonedathome": "Boned At Home",
    "bootyliciousmag": "Bootylicious Mag",
    "bustyangelique": "Busty Angelique",
    "bustyarianna": "Busty Arianna",
    "bustydanniashe": "Busty Danni Ashe",
    "bustydustystash": "Busty Dusty Stash",
    "bustyinescudna": "Busty Ines Cudna",
    "bustykellykay": "Busty Kelly Kay",
    "bustykerrymarie": "Busty Kerry Marie",
    "bustylornamorga": "Busty Lorna Morga",
    "bustymerilyn": "Busty Merilyn",
    "bustyoldsluts": "Busty Old Sluts",
    "chicksonblackdicks": "Chicks on Black Dicks",
    "chloesworld": "Chloe's World",
    "christymarks": "Christy Marks",
    "cock4stepmom": "Cock 4 Stepmom",
    "codivorexxx": "Codi Vore XXX",
    "creampieforgranny": "Creampie for Granny",
    "crystalgunnsworld": "Crystal Gunns World",
    "daylenerio": "Daylene Rio",
    "desiraesworld": "Desiraes World",
    "ebonythots": "Ebony Thots",
    "evanottyvideos": "Eva Notty Videos",
    "feedherfuckher": "Feed Her Fuck Her",
    "flatandfuckedmilfs": "Flat and Fucked MILFs",
    "grannygetsafacial": "Granny Gets Facial",
    "grannylovesbbc": "Granny Loves BBC",
    "grannylovesyoungcock": "Granny Loves Young Cock",
    "hairycoochies": "Hairy Coochies",
    "homealonemilfs": "Home Alone MILFs",
    "hornyasianmilfs": "Horny AsisnlM ILFs",
    "ibonedyourmom": "I Boned Your Mom",
    "ifuckedtheboss": "I Fucked The Boss",
    "joanabliss": "Joana Bliss",
    "karinahart": "Karina Hart",
    "latinacoochies": "Latina Coochies",
    "latinmommas": "Latin Mommas",
    "leannecrowvideos": "Leanne Crow Videos",
    "legsex": "Leg Sex",
    "megatitsminka": "Mega Tits Minka",
    "mickybells": "Micky Bells",
    "milfbundle": "MILF Bundle",
    "milfthreesomes": "MILF Threesomes",
    "milftugs": "MILF Tugs",
    "millymarks": "Milly Marks",
    "mommystoytime": "Mommy's Toy Time",
    "nataliefiore": "Natalie Fiore",
    "naughtymag": "Naughty Mag",
    "naughtyfootjobs": "Naughty Foot Jobs",
    "naughtytugs": "Naughty Tugs",
    "nicolepeters": "Nicole Peters",
    "oldhornymilfs": "Old Horny MILFS",
    "pickinguppussy": "Picking Up Pussy",
    "pornloser": "Porn Loser",
    "pornmegaload": "Porn Mega Load",
    "reneerossvideos": "Renee Ross Video",
    "roxired": "Roxi Red",
    "sarennasworld": "Sarenna's World",
    "scoreclassics": "Score Classics",
    "scoreland2": "Scoreland2",
    "scoreland": "Scoreland",
    "scorevideos": "Score Videos",
    "sharizelvideos": "Sha Rizel Videos",
    "silversluts": "Silver Sluts",
    "stacyvandenbergboobs": "Stacy Vandenberg Boobs",
    "tawny-peaks": "Tawny Peaks",
    "tiffany-towers": "Tiffany Towers",
    "titsandtugs": "Tits And Tugs",
    "tnatryouts": "TNA Tryouts",
    "valoryirene": "Valory Irene",
    "xlgirls": "XL Girls",
    "yourmomlovesanal": "Your Mom Loves Anal",
    "yourmomsgotbigtits": "Your Mom's Got Big Tits",
    "yourwifemymeat": "Your Wife My Meat",
}

ETHNICITY_MAP: dict[str, Ethnicity] = {
    "Asian": "Asian",
    "Black": "Black",
    "Latina": "Latin",
    "Other": "Other",
    "White": "Caucasian",
}

HAIR_COLOR_MAP: dict[str, HairColor] = {
    "Black": "Black",
    "Blonde": "Blonde",
    "Brunette": "Brunette",
    "Redhead": "Red",
}

# Shared client because we're making multiple requests.
# The sites reject non-browser TLS fingerprints: the handshake succeeds and the
# connection is then reset at the first HTTP byte, so impersonation is required.
client = requests.Session(impersonate="chrome")
# Search serves a "Verifying Browser" interstitial whose JS only sets this cookie
client.cookies.set("tsg_verified", "true", domain=".scoreland.com")


# Example element:
# <div class="li-item model h-100 ">
#   <div class="box pos-rel d-flex flex-column h-100">
#     <div class="item-img pos-rel">
#       <a href="https://www.scoreland.com/big-boob-models/no-model/0/?nats=MTAwNC4yLjIuMi41NDUuMC4wLjAuMA"
#          class="d-block"
#          title=" Scoreland Profile">
#         <img src="https://cdn77.scoreuniverse.com/shared-bits/images/male-model-placeholder-photo.jpg" />
#       </a>
#     </div>
#     <div class="info t-c p-2">
#       <div class="t-trunc t-uc">
#         <a href="https://www.scoreland.com/big-boob-models/no-model/0/?nats=MTAwNC4yLjIuMi41NDUuMC4wLjAuMA"
#            title=""
#            aria-label=" Scoreland Profile"
#            class="i-model accent-text">
#         </a>
#       </div>
#     </div>
#   </div>
# </div>
def map_performer(el) -> ScrapedPerformer | None:
    "Converts performer search result into scraped performer"
    url = el.xpath(".//a/@href")[0]
    if "no-model" in url:
        return None
    name = el.xpath(".//a/@title")[1]
    image = el.xpath(".//img/@src")[0]
    # https://join.{domain}/strack/{nats}/{site}/2/1/{path} -> https://www.{domain}/{path}
    if not (
        m := re.match(r"https://join\.([^/]+)/strack/[^/]+/[^/]+/2/\d+/([^?]+)", url)
    ):
        log.debug(f"Performer '{name}' has no profile link, skipping")
        return None

    return {
        "name": name,
        "urls": [f"https://www.{m[1]}/{m[2]}"],
        "image": image,
    }


def performer_query(query: str):
    "Search performer by name"
    # Form data to be sent as the POST request body
    payload = {
        "ci_csrf_token": "",
        "keywords": query,
        "s_filters[site]": "all",
        "s_filters[type]": "models",
        "m_filters[sort]": "top_rated",
        "m_filters[gender]": "any",
        "m_filters[body_type]": "any",
        "m_filters[race]": "any",
        "m_filters[hair_color]": "any",
    }
    result = client.post("https://www.scoreland.com/search-es/", data=payload)
    tree = html.fromstring(result.content)
    performers = [p for x in tree.find_class("model") if (p := map_performer(x))]
    # The site offers no relevance sort, so float exact and partial name matches to the top
    needle = query.casefold()
    performers.sort(
        key=lambda p: (
            p["name"].casefold() != needle,
            needle not in p["name"].casefold(),
        )
    )

    if not performers:
        log.warning(f"No performers found for '{query}'")
    return performers


def best_quality_scene_image(code: str) -> str | None:
    "Finds the highest resolution scene image for a scene ID"
    no_qual_path = (
        "https://cdn77.scoreuniverse.com/modeldir/data/posting/"
        f"{code[0 : len(code) - 3]}/{code[-3:]}/posting_{code}"
    )
    for quality in ["_1920", "_1600", "_1280", "_800", "_xl", "_lg", "_med", ""]:
        image_url = f"{no_qual_path}{quality}.jpg"
        if is_valid_url(image_url):
            return image_url
    return None


def scene_from_url(url: str) -> ScrapedScene:
    "Scrape scene URL from HTML"
    scene = page_metadata(url)
    if not scene:
        return scene

    scene_id = re.sub(r".*\/(\d+)\/?$", r"\1", urlparse(url).path)
    scene["code"] = scene_id
    if image_url := best_quality_scene_image(scene_id):
        scene["image"] = image_url
    return scene


def gallery_from_url(url: str) -> ScrapedGallery:
    "Photo sets share the scene page layout and id, so the scene fields carry over"
    scene = page_metadata(url)
    gallery: ScrapedGallery = {}
    for key in ("title", "date", "details", "urls", "studio", "tags", "performers"):
        if value := scene.get(key):
            gallery[key] = value
    return gallery


def performer_from_url(url: str) -> ScrapedPerformer | None:
    "Scrape performer profile page"
    tree = html.fromstring(client.get(url).content)

    if not (name := re.sub(r"'s? Profile$", "", tree.xpath("string(//h1)").strip())):
        log.error("Could not find performer name, scraper needs updating")
        return None

    def stat(label: str) -> str:
        return tree.xpath(
            f'string(//span[@class="label" and text()="{label}:"]/following-sibling::span)'
        ).strip()

    performer: ScrapedPerformer = {
        "name": name,
        "gender": "FEMALE",
        "urls": [urlunparse(urlparse(url)._replace(query=""))],
    }
    if ethnicity := stat("Ethnicity"):
        if mapped_ethnicity := ETHNICITY_MAP.get(ethnicity):
            performer["ethnicity"] = mapped_ethnicity
        else:
            log.warning(f"Unmapped ethnicity '{ethnicity}'")
    if hair_color := stat("Hair Color"):
        if mapped_hair := HAIR_COLOR_MAP.get(hair_color):
            performer["hair_color"] = mapped_hair
        else:
            log.warning(f"Unmapped hair color '{hair_color}'")
    if height := feet_to_cm(stat("Height")):
        performer["height"] = height
    if weight := lb_to_kg(stat("Weight")):
        performer["weight"] = weight
    # The bra size replaces the bust figure: 34H + 44-28-38 -> 34H-28-38
    bra_size, measurements = stat("Bra Size"), stat("Measurements")
    if bra_size and (m := re.match(r"\d+(-\d+-\d+)$", measurements)):
        performer["measurements"] = bra_size + m[1]
    elif bra_size or measurements:
        performer["measurements"] = bra_size or measurements
    if image := tree.xpath(
        'string(//img[contains(@src, "/modeldir/data/photos/")]/@src)'
    ):
        performer["images"] = [image]
    return performer


def page_metadata(url: str) -> ScrapedScene:
    "Fields shared by the video and photo pages"
    clean_url = urlunparse(urlparse(url)._replace(query=""))
    scene: ScrapedScene = {}

    result = client.get(url)
    tree = html.fromstring(result.content)

    if not (
        page := tree.xpath(
            '//article[@id="videos_page-page" or @id="mixed_page-page" or @id="photos_page-page"]'
        )
    ):
        log.error("Page layout has changed, scraper needs updating")
        return scene

    page = page[0]

    # title
    match page.xpath("//h1"):
        case [title] | [title, _]:
            # Unreleased sets prefix the title with a "coming soon:" badge
            scene["title"] = "".join(
                title.xpath('text()|*[not(contains(@class, "accent-text"))]//text()')
            ).strip()
        case _:
            log.debug("Could not find title in page, scraper needs updating")

    # date
    if raw_date := page.xpath(
        '//span[@class="label" and contains(.,"Date:")]/following-sibling::span'
    ):
        scene["date"] = (
            datetime.strptime(  # noqa: DTZ007
                re.sub(r"(\d+)[a-z]{2}", r"\1", next(iter(raw_date)).text).replace(
                    "..,", ""
                ),
                "%B %d, %Y",
            )
            .date()
            .isoformat()
        )

    scene["urls"] = [clean_url]

    # Original studio is determinable by looking at the CDN links (<source src="//cdn77.scoreuniverse.com/naughtymag/scenes...)
    # this helps set studio for PornMegaLoad URLs as nothing is released directly by the network
    # Photo pages have no video, but their thumbnails follow the same scheme (.../naughtymag/gallys/...)
    if cdn_src := page.xpath("//video/source/@src") or page.xpath(
        '//img[contains(@src, "/gallys/")]/@src'
    ):
        studio_ref = re.sub(
            r".*\.com/(.+?)\/(video|scene|gallys).*", r"\1", next(iter(cdn_src))
        )
        scene["studio"] = {"name": STUDIO_MAP.get(studio_ref, studio_ref)}

    if description := page.xpath(
        '//div[@class="p-desc p-3" or contains(@class, "desc")]/text()'
    ):
        scene["details"] = "\n\n".join(
            [p.strip() for p in description if len(p.strip())]
        )

    if tags := page.xpath('//a[contains(@href, "-tag")]'):
        scene["tags"] = [{"name": tag.text} for tag in iter(tags)]

    if performers := page.xpath(
        '//span[contains(.,"Featuring:")]/following-sibling::span/a'
    ):
        scene["performers"] = [{"name": p.text} for p in iter(performers)]

    return scene


def main():
    op, args = scraper_args()
    log.debug(f"Operation: {op}, arguments: {json.dumps(args)}")
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_query(name)
        case _:
            log.error(f"Operation not implemented: {op}")
            sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
