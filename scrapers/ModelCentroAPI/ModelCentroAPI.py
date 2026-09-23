import json
import re
import sys
from datetime import date
from urllib.parse import urlencode, urlparse

import requests
from py_common import log
from py_common.cache import cache_to_disk
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import dig, scraper_args

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
)
KEY_TTL = 60 * 60 * 24

# The API answers on two different methods depending on the URL shape:
# /scene/<contentId> is content.load, /product/<productId> is the platform's clip store
# which needs Store.getProductList instead: both return the same objects
STORE_FIELDS = (
    "contentProduct.contentId.title",
    "contentProduct.contentId.description",
    "contentProduct.contentId.tags.alias",
    "contentProduct.contentId.sites.publishDate",
    "contentProduct.contentId._resources.primary.url",
)

studio_map = {
    "amberlilyshow": "Amber Lily Show",
    "amberspanks": "Amber Spanks",
    "americankitten": "American Kitten",
    "amirahadaraxxx": "Amirah Adara XXX",
    "anastasiagree": "Anastasia Gree",
    "anisyia.xxx": "Anisyia XXX",
    "arabellesplayground": "Arabelle's Playground",
    "arinna-cum": "Arinna Cum",
    "aussiexxxhookups": "Aussie XXX HookUps",
    "bhalasada": "Bhala Sada",
    "bigjohnnyxxx": "Big Johnny XXX",
    "blondehexe.net": "BlondeHexe",
    "bohonude.art": "Nude Art Boho",
    "brandonlh": "Brandon Lee Harrington Productions",
    "brianaleecams": "Briana Lee Cams",
    "brookelynnebriar": "Brookelynne Briar",
    "carlhubaygay.xxx": "Carl Hubay Gay",
    "cartoons4grownfolks": "Cartoons 4 Grown Folks",
    "claradeemembers": "Clara Dee Members",
    "clubmaseratixxx": "Club Maserati XXX",
    "cospimps": "CosPimps",
    "danidaniels": "Dani Daniels",
    "darkwetdreemz": "Dark Wet Dreemz",
    "deepsmashmedia": "Deep Smash Media",
    "denudeart": "DenudeArt",
    "dillionation": "Dillio Nation",
    "dirtytina": "Dirty Tina",
    "erinelectra": "Erin Electra",
    "erospiration": "Erospiration",
    "eroticcecelia": "Erotic Cecelia",
    "euroslut.club": "Euro Slut",
    "facialcasting": "Facial Casting",
    "fallinlovia": "Fall In Lovia",
    "fallonfuckingwest": "Fallon Fucking West",
    "francescomalcom": "Francesco Malcom",
    "getyourkneesdirty": "Get Your Knees Dirty",
    "ginagerson.xxx": "Gina Gerson",
    "hentacles": "Hentacles",
    "hollandswing": "Holland Swing",
    "honeybarefeet": "Miss Honey Barefeet",
    "hurricanefury": "Hurricane Fury",
    "immoralfantasy": "Immoral Fantasy",
    "irenerouse": "Irene Rouse",
    "isinxxx": "iSinXXX",
    "jenysmith.net": "Jeny Smith",
    "jerkoffwithme": "Jerkoff With Me",
    "jessieminxxx": "JessieMinxxx.com",
    "kacytgirl": "Sexy Kacy",
    "katie71": "Katie 71",
    "katrinporto": "Katrin Porto",
    "kendrasinclaire": "Kendra Sinclaire",
    "kinkyrubberworld": "Kinky Rubber World",
    "klubkelli": "Klub Kelli",
    "krisskiss": "Kriss Kiss",
    "kyleenash": "Kylee Nash",
    "ladysublime": "Lady Sublime",
    "lasublimexxx": "La Sublime",
    "lilcandy": "LilCandy",
    "lilumoon": "Lilu Moon",
    "lilychey": "Lily Chey",
    "lonelymeow": "LonelyMeow",
    "lornablu.net": "Lorna Blu",
    "lynnasexworld": "Lynna Sex World",
    "masculinejason": "Masculine Jason",
    "melenamariarya": "Melena Maria Rya",
    "miamaffia": "Mia Maffia",
    "monstermalesprod": "MonsterMales",
    "mugursworld": "Mugur Porn",
    "mylifeinmiami": "My Life In Miami",
    "nancyace": "Nancy Ace",
    "nataliek.xxx": "Natalie K",
    "natashanice": "Natasha Nice",
    "naughty-lada": "Naughty Lada",
    "niarossxxx": "Nia Ross XXX",
    "nikkojordan": "Nikko Jordan",
    "niksindian": "Niks Indian",
    "officialelizabethmarxs": "ElizabethMarxs",
    "onedomproductions": "One Dom Productions",
    "openlegsxxx": "Open Legs",
    "peccatriciproduzioni": "Pecca Trici Produzioni",
    "peghim": "Peg Him",
    "platinumpuzzy.net": "Platinum Puzzy",
    "pornojuice": "Porno Juice",
    "porntugal": "Porntugal",
    "psychohenessy": "Henessy",
    "puremolly": "Molly Pills",
    "pvgirls": "Porn Valley Girls",
    "realagent.xxx": "Real Agent",
    "realpeachez": "Sarah Peachez",
    "rebeccalordproductions": "Rebecca Lord Productions",
    "redbottomxxx": "Red Bottom Productions",
    "rexringoxxx.xxx": "Rex Ringo XXX Productions",
    "sabrinasabrokporn": "Sabrina Sabrok Videos",
    "sallydangeloxxx": "City Girlz",
    "sam38g": "Samantha38g",
    "samantalily.xxx": "Samanta Lily",
    "santalatina": "Santalatina",
    "shalinadevine": "Shalina Devine",
    "shootingstar4u.me": "Orgasmic Shooting Star",
    "sirberusssanctum.net": "Sir Berus's Sanctum",
    "sluttywildthing": "Slutty Wild Thing",
    "southerncumsluts": "Southern Cum Sluts",
    "stefolino": "Stefolino",
    "sweetiefox.net": "Sweetie Fox",
    "sylviasucker": "Sylvia Chrystall",
    "tahliaparis": "Tahlia Paris",
    "tanyatate.xxx": "Tanya Tate",
    "theamofficial": "Ass Monkey",
    "theaudreyhollander": "Audrey Hollander Anal Queen",
    "thiccvision": "Thicc Vision",
    "ticklehotness": "Tickle Hotness",
    "trinetyguess": "Trinety Guess",
    "vinaskyxxx": "VinaSkyXXX",
    "womenwhosmoke": "Women Who Smoke",
    "xtcpov": "XTC POV",
    "xtremestudios.studio69swf.live": "Xtreme Studios Media",
    "xxxotikangelzent": "xXxOTIK ANGELZ",
    "yourgoonspace": "Your Goon Space",
}

# Map of studios that don't list performers, but have a fixed set of performers for all scenes.
# Or sites that have a primary performer that is in all scenes but not always listed.
# These are lists in case a future studio has more than one performer in all scenes.
# Use the site name as it shows up in the URL.  Where the TLD is not .com, include the TLD (eg, .xxx)
fixed_performers = {
    "amberlilyshow": ["Amber Lily"],
    "amberspanks": ["Amber Spanks"],
    "amirahadaraxxx": ["Amirah Adara"],
    "anastasiagree": ["Anastasia Gree"],
    "anisyia.xxx": ["Anisyia"],
    "arabellesplayground": ["Arabelle Raphael"],
    "arinnacum": ["Arinna Cum"],
    "blondehexe.net": ["Blonde Hexe"],
    "brianaleecams": ["Briana Lee"],
    "brookelynnebriar": ["Brookelynne Briar"],
    "claradeemembers": ["Clara Dee"],
    "clubmaseratixxx": ["Maserati XXX"],
    "danidaniels": ["Dani's Things"],
    "eroticcecelia": ["Cecelia"],
    "fallinlovia": ["Eva Lovia"],
    "francescomalcom": ["Francesco Malcom"],
    "ginagerson.xxx": ["Gina Gerson"],
    "hollandswing": ["Nikki Holland"],
    "honeybarefeet": ["Miss Honey Barefeet"],
    "hurricanefury": ["Hurricane Fury"],
    "irenerouse": ["Irene Rouse"],
    "jenysmith.net": ["Jeny Smith"],
    "jessieminxxx": ["Jessie Minx"],
    "kacytgirl": ["Kacy"],
    "katie71": ["Katlynn"],
    "kendrasinclaire": ["Kendra Sinclaire"],
    "krisskiss": ["Kriss Kiss"],
    "kyleenash": ["Kylee Nash"],
    "ladysublime": ["Lady Sublime"],
    "lilcandy": ["Lil Candy"],
    "lilumoon": ["Lilu Moon"],
    "lilychey": ["Lily Chey"],
    "lonelymeow": ["LonelyMeow"],
    "lornablu.net": ["Lorna Blu"],
    "lynnasexworld": ["Lynna Nilsson"],
    "masculinejason": ["Jason Collins"],
    "melenamariarya": ["Melena Maria Rya"],
    "nancyace": ["Nancy Ace"],
    "nataliek.xxx": ["Natalie K"],
    "natashanice": ["Natasha Nice"],
    "naughty-lada": ["Naughty Lada"],
    "niarossxxx": ["Nia Ross"],
    "nikkojordan": ["Nikko Jordan"],
    "officialelizabethmarxs": ["Elizabeth Marxs"],
    "psychohenessy": ["Alina Henessy"],
    "puremolly": ["Molly Pills"],
    "realpeachez": ["Sarah Peachez"],
    "rexringoxxx.xxx": ["Rex Ringo"],
    "sabrinasabrokporn": ["Sabrina Sabrok"],
    "sallydangeloxxx": ["Sally D'angelo"],
    "sam38g": ["Samantha 38g"],
    "samantalily.xxx": ["Samanta Lily"],
    "shootingstar4u.me": ["Orgasmic Shooting Star"],
    "sweetiefox.net": ["Sweetie Fox"],
    "sylviasucker": ["Sylvia Chrystall"],
    "tahliaparis": ["Tahlia Paris"],
    "tanyatate.xxx": ["Tanya Tate"],
    "theaudreyhollander": ["Audrey Hollander"],
    "trinetyguess": ["Trinety Guess"],
    "vinaskyxxx": ["Vina Sky"],
}

# Map of studios that don't list tags, but have a fixed set of tags for all scenes.
# Or sites that have tags, but don't include the obvious ones since it applies to every scene
# Use the site name as it shows up in the URL.  Where the TLD is not .com, include the TLD (eg, .xxx)

default_tags = {
    "amirahadaraxxx": [
        "Brown Hair (Female)",
        "Hungarian",
        "Natural Tits",
        "Small Tits",
        "White Woman",
    ],
    "anastasiagree": ["BBW", "Brown Hair (Female)", "Solo Female", "White Woman"],
    "anisyia.xxx": ["Fake Tits", "Brown Hair (Female)", "Long Hair", "White Woman"],
    "arabellesplayground": ["Big Tits", "Natural Tits", "White Woman"],
    "arinna-cum": ["Blonde Hair (Female)", "White Woman"],
    "blondehexe.net": [
        "Blonde Hair (Female)",
        "Solo Female",
        "White Woman",
        "Natural Tits",
    ],
    "bohonude.art": ["Softcore", "Solo Female"],
    "brookelynnebriar.net": ["Brown Hair (Female)", "Natural Tits", "White Woman"],
    "brianaleecams": [
        "Brown Hair (Female)",
        "Natural Tits",
        "White Woman",
        "Long Hair",
        "Natural Tits",
    ],
    "carlhubaygay.net": ["Mature", "Gay", "White Man"],
    "cartoons4grownfolks": ["Animated"],
    "claradeemembers": ["Brown Hair (Female)", "Natural Tits", "White Woman"],
    "clubmaseratixxx": [
        "Brown Hair (Female)",
        "Natural Tits",
        "Big Tits",
        "Black Woman",
    ],
    "danidaniels": ["Brown Hair (Female)", "Natural Tits", "White Woman"],
    "darkwetdreemz": ["Natural Tits", "Black Woman"],
    "erinelectra": ["Natural Tits", "White Woman", "White Man", "Twosome (Straight)"],
    "eroticcecelia": ["Solo Female", "Softcore"],
    "facialcasting": ["Facial", "Cumshot"],
    "getyourkneesdirty": ["Small Dick", "Cumshot", "White Man", "Blowjob"],
    "ginagerson.xxx": ["Blonde Hair (Female)", "White Woman", "Natural Tits"],
    "hollandswing": ["White Woman", "Natural Tits"],
    "irenerouse": [
        "Brown Hair (Female)",
        "Long Hair",
        "White Woman",
        "Natural Tits",
        "Solo Female",
    ],
    "jenysmith.net": [
        "Brown Hair (Female)",
        "Long Hair",
        "White Woman",
        "Natural Tits",
    ],
    "kacytgirl": ["Blonde Hair (Female)", "Trans Woman", "White Woman"],
    "katie71": ["Brown Hair (Female)", "Long Hair", "White Woman"],
    "kendrasinclaire": [
        "Trans Woman",
        "White Woman",
        "Brown Hair (Female)",
        "Long Hair",
    ],
    "klubkelli": ["Redistribution"],
    "krisskiss": ["White Woman", "Brown Hair (Female)", "Long Hair"],
    "kyleenash": ["Fake Tits", "Solo Female", "MILF", "White Woman"],
    "ladysublime": [
        "BBW",
        "Brown Hair (Female)",
        "Solo Female",
        "White Woman",
        "Long Hair",
    ],
    "lilcandy": ["White Woman", "Natural Tits"],
    "lilumoon": ["White Woman", "Natural Tits", "Brown Hair (Female)", "Long Hair"],
    "lilychey": ["White Woman", "Natural Tits", "Brown Hair (Female)", "Long Hair"],
    "lonelymeow": ["Asian Woman", "Natural Tits", "Black Hair (Female)", "Long Hair"],
    "lornablu.net": ["Mature", "Blonde Hair (Female)", "White Woman", "Natural Tits"],
    "lynnasexworld": ["Blonde Hair (Female)", "White Woman", "Fake Tits"],
    "masculinejason": ["Bald", "White Man", "Gay", "Tattoos"],
    "melenamariarya": [
        "White Woman",
        "Natural Tits",
        "Brown Hair (Female)",
        "Long Hair",
    ],
    "miamaffia.xxx": ["Trans Woman", "White Woman", "Tattoos", "Long Hair"],
    "nancyace": ["White Woman", "Blonde Hair (Female)", "Long Hair", "Natural Tits"],
    "nataliek.xxx": [
        "White Woman",
        "Blonde Hair (Female)",
        "Long Hair",
        "MILF",
        "Natural Tits",
    ],
    "natashanice": ["White Woman", "Brown Hair (Female)", "Long Hair", "Natural Tits"],
    "naughty-lada": [
        "White Woman",
        "Brown Hair (Female)",
        "MILF",
        "Big Tits",
        "Natural Tits",
    ],
    "niarossxxx": ["Black Woman", "Black Hair (Female)", "Natural Tits"],
    "niksindian": ["South Asian Woman"],
    "officialelizabethmarxs": ["White Woman", "Natural Tits", "Red Hair"],
    "peccatriciproduzioni": [
        "Mature",
        "Brown Hair (Female)",
        "White Woman",
        "Natural Tits",
    ],
    "peghim": ["Pegging", "Toys", "Anal Toys", "Strap-on"],
    "platinumpuzzy.net": ["BBW"],
    "psychohenessy": [
        "White Woman",
        "Brown Hair (Female)",
        "Long Hair",
        "Natural Tits",
    ],
    "puremolly": ["White Woman", "Blonde Hair (Female)", "Long Hair", "Natural Tits"],
    "realpeachez": ["White Woman", "Blonde Hair (Female)", "Long Hair", "Natural Tits"],
    "rexringoxxx.xxx": ["Black Male"],
    "sabrinasabrokporn": [
        "White Woman",
        "Blonde Hair (Female)",
        "Long Hair",
        "Fake Tits",
    ],
    "sallydangeloxxx": [
        "White Woman",
        "Blonde Hair (Female)",
        "Long Hair",
        "Fake Tits",
        "Mature",
    ],
    "sam38g": [
        "White Woman",
        "Red Head",
        "Long Hair",
        "Natural Tits",
        "Big Tits",
        "Solo Female",
    ],
    "samantalily.xxx": ["White Woman", "Big Tits", "Natural Tits"],
    "santalatina": ["Latina Woman", "Black Hair (Female)", "Long Hair", "Natural Tits"],
    "shalinadevine": ["White Woman", "Blonde Hair (Female)", "Long Hair", "Fake Tits"],
    "shootingstar4u.me": ["White Woman", "Blonde Hair (Female)", "Natural Tits"],
    "sirberusssanctum.net": ["Black Man", "Black Hair (Male)"],
    "sluttywildthing": [
        "White Woman",
        "Brown Hair (Female)",
        "Long Hair",
        "Natural Tits",
    ],
    "sweetiefox.net": ["White Woman", "Fake Tits"],
    "sylviasucker": ["White Woman", "Brown Hair (Female)", "Blowjob", "Natural Tits"],
    "tahliaparis": ["White Woman", "Fake Tits", "Blonde Hair (Female)"],
    "tanyatate.xxx": ["White Woman", "Fake Tits", "Blonde Hair (Female)"],
    "theaudreyhollander": ["White Woman", "Natural Tits", "Red Hair"],
    "ticklehotness": ["Tickling"],
    "trinetyguess": ["BBW", "Solo Female", "White Woman"],
    "vinaskyxxx": ["Asian Woman", "Natural Tits", "Black Hair (Female)", "Long Hair"],
    "womenwhosmoke": ["Smoking"],
    "xtcpov": ["POV"],
}

## At least one studio has seriously managed to mess up their tags by not splitting them properly.
## Do what we can to break the mess of a single tag they return with spaces.  It might not be
## perfect but it's better than what's returned by the API.
tags_need_splitting = [
    "rexringoxxx.xxx",
]


def api_call(domain: str, keys: list[str], method: str, params: dict) -> dict | None:
    """One /sapi/ call. Returns the `response` object, or None if anything failed."""
    url = f"https://{domain}/sapi/{keys[0]}/{keys[1]}/{method}?" + urlencode(
        {"_method": method, "tz": "1", **params}
    )
    headers = {"User-Agent": USER_AGENT, "Referer": f"https://{domain}/"}
    try:
        response = requests.get(url, headers=headers, timeout=(3, 10))
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        log.error(f"{method} request failed: {exc}")
        return None
    if not payload.get("status"):
        log.error(f"{method} refused the request: {payload.get('reason') or payload}")
        return None
    return payload.get("response")


def extract_api_keys(page_url: str) -> list[str] | None:
    try:
        page = requests.get(
            page_url, headers={"User-Agent": USER_AGENT}, timeout=(3, 10)
        ).text
    except requests.RequestException as exc:
        log.warning(f"Could not fetch {page_url}: {exc}")
        return None

    init = re.search(r"_fox_init(.+?)</script>", page, re.DOTALL)
    key1 = re.search(r'ah":"([a-zA-Z0-9_-]+)"', init.group(1)) if init else None
    key2 = re.search(r'aet":(\d+),"', init.group(1)) if init else None
    if not (key1 and key2):
        log.warning(f"No API identification in {page_url}")
        return None
    return [key1.group(1)[::-1], key2.group(1)]  # the first key is stored reversed


@cache_to_disk(ttl=KEY_TTL)
def api_keys(domain: str) -> list[str] | None:
    return extract_api_keys(f"https://{domain}/")


def keys_for(domain: str, page_url: str) -> list[str] | None:
    return api_keys(domain) or extract_api_keys(page_url)


def load_scene(domain: str, keys: list[str], scene_id: str) -> dict | None:
    response = api_call(
        domain,
        keys,
        "content.load",
        {
            "filter[id][fields][0]": "id",
            "filter[id][values][0]": scene_id,
            "transitParameters[v1]": "ykYa8ALmUD",
            "transitParameters[preset]": "scene",
        },
    )
    return dig(response or {}, "collection", 0)


def load_store_product(
    domain: str, keys: list[str], product_id: str
) -> tuple[dict, str] | None:
    response = api_call(
        domain,
        keys,
        "Store.getProductList",
        {
            "limit": "1",
            "filter[id][fields][0]": "id",
            "filter[id][values][0]": product_id,
            "metaFields[contentProduct][contentId][resources][primary]": "primary..origin",
            **{f"fields[{i}]": f for i, f in enumerate(STORE_FIELDS)},
        },
    )
    wrapped = dig(response or {}, "collection", 0, "contentProduct", "collection") or {}
    contents = dig(next(iter(wrapped.values()), {}), "contentId", "collection") or {}
    if not contents:
        log.error(f"No content behind store product {product_id}")
        return None
    content_id, content = next(iter(contents.items()))
    return content, content_id


def scraped_performers(
    domain: str, keys: list[str], content_id: str, site: str
) -> list[ScrapedPerformer]:
    response = api_call(
        domain,
        keys,
        "model.getModelContent",
        {"fields[0]": "modelId.stageName", "transitParameters[contentId]": content_id},
    )
    performers: list[ScrapedPerformer] = [
        {"name": name.strip()}
        for entry in (dig(response or {}, "collection") or {}).values()
        for model in (dig(entry, "modelId", "collection") or {}).values()
        if (name := model.get("stageName"))
    ]
    seen = {p["name"].casefold() for p in performers}
    performers.extend(
        {"name": name}
        for name in fixed_performers.get(site, [])
        if name.casefold() not in seen
    )
    return performers


def scraped_tags(content: dict, site: str) -> list[ScrapedTag]:
    aliases = [
        alias
        for tag in (dig(content, "tags", "collection") or {}).values()
        if (alias := tag.get("alias"))
    ]
    # One studio returns every tag as a single space-separated blob
    if site in tags_need_splitting:
        aliases = [word for alias in aliases for word in alias.split(" ")]

    tags: list[ScrapedTag] = []
    seen: set[str] = set()
    for name in [*aliases, *default_tags.get(site, [])]:
        if (name := name.strip()) and name.casefold() not in seen:
            seen.add(name.casefold())
            tags.append({"name": name})
    return tags


def to_scene(content: dict, content_id: str, site: str) -> ScrapedScene:
    studio: ScrapedStudio = {"name": studio_map.get(site, site)}
    scene: ScrapedScene = {
        "title": (content.get("title") or "").strip(),
        "details": (content.get("description") or "").strip(),
        "studio": studio,
        "tags": scraped_tags(content, site),
    }
    if image := dig(content, "_resources", "primary", 0, "url"):
        scene["image"] = image
    published = dig(content, "sites", "collection", content_id, "publishDate")
    try:
        scene["date"] = date.fromisoformat(published[:10]).isoformat()
    except (TypeError, ValueError):
        log.debug(f"No usable publishDate for content {content_id}: {published!r}")
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    domain = urlparse(url).netloc
    # The lookup tables are keyed on the site name as it appears in the URL,
    # with the TLD kept for anything that is not .com
    site = re.sub(r"www\.|\.com", "", domain)

    if not (match := re.search(r"/(\d+)/*", url)):
        log.error(f"Error with the ID ({url}): are you sure that your URL is correct?")
        return None
    if not (keys := keys_for(domain, url)):
        log.error("There is a problem with getting API identification")
        return None

    object_id = match.group(1)
    if "/product/" in url:
        if not (resolved := load_store_product(domain, keys, object_id)):
            return None
        content, content_id = resolved
    elif content := load_scene(domain, keys, object_id):
        content_id = object_id
    else:
        return None

    scene = to_scene(content, content_id, site)
    if performers := scraped_performers(domain, keys, content_id, site):
        scene["performers"] = performers
    return scene


def main() -> None:
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
