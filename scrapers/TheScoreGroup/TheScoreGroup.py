from datetime import datetime
import json
import re
import sys
from urllib.parse import urlparse, urlunparse

from lxml import html
import requests

from py_common.deps import ensure_requirements
import py_common.log as log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import dig, is_valid_url, scraper_args

ensure_requirements("lxml", "requests")


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

# Shared client because we're making multiple requests
client = requests.Session()


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
    fixed_url = re.sub(r".*?([^/]*(?=/2/0))/2/0/([^?]*)", r"https://www.\1.com/\2", url)
    log.debug(f"url: {url}")
    log.debug(f"fixed_url: {fixed_url}")

    if not is_valid_url(fixed_url):
        log.debug(f"Performer '{name}' has a broken profile link, skipping")
        return None

    return {
        "name": name,
        "urls": [fixed_url],
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
    # url
    clean_url = urlunparse(urlparse(url)._replace(query=""))
    scene: ScrapedScene = {}

    result = client.get(url)
    tree = html.fromstring(result.content)

    if not (
        video_page := tree.xpath(
            '//section[@id="videos_page-page" or @id="mixed_page-page"]'
        )
    ):
        log.error("Page layout has changed, scraper needs updating")
        return scene

    video_page = video_page[0]

    # title
    match video_page.xpath("//h1"):
        case [title] | [title, _]:
            scene["title"] = title.text_content().strip()
        case _:
            log.debug("Could not find title in page, scraper needs updating")

    # date
    if raw_date := video_page.xpath(
        '//div[contains(concat(" ",normalize-space(@class)," ")," mb-3 ")]//span[contains(.,"Date:")]/following-sibling::span'
    ):
        scene["date"] = datetime.strptime(
            re.sub(r"(\d+)[a-z]{2}", r"\1", next(iter(raw_date)).text).replace(
                "..,", ""
            ),
            "%B %d, %Y",
        ).strftime("%Y-%m-%d")

    scene_id = re.sub(r".*\/(\d+)\/?$", r"\1", clean_url)
    scene["code"] = scene_id
    scene["url"] = clean_url

    # Original studio is determinable by looking at the CDN links (<source src="//cdn77.scoreuniverse.com/naughtymag/scenes...)
    # this helps set studio for PornMegaLoad URLs as nothing is released directly by the network
    if video_src := video_page.xpath("//video/source/@src"):
        studio_ref = re.sub(
            r".*\.com/(.+?)\/(video|scene).*", r"\1", next(iter(video_src))
        )
        scene["studio"] = {"name": STUDIO_MAP.get(studio_ref, studio_ref)}

    if description := video_page.xpath(
        '//div[@class="p-desc p-3" or contains(@class, "desc")]/text()'
    ):
        scene["details"] = "\n\n".join(
            [p.strip() for p in description if len(p.strip())]
        )

    if tags := video_page.xpath('//a[contains(@href, "-tag")]'):
        scene["tags"] = [{"name": tag.text} for tag in iter(tags)]

    if performers := video_page.xpath(
        '//span[contains(.,"Featuring:")]/following-sibling::span/a'
    ):
        scene["performers"] = [{"name": p.text} for p in iter(performers)]

    # image
    if image_url := best_quality_scene_image(scene_id):
        scene["image"] = image_url

    return scene


def main():
    op, args = scraper_args()
    log.debug(f"Operation: {op}, arguments: {json.dumps(args)}")
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_query(name)
        case _:
            log.error(f"Operation not implemented: {op}")
            sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
