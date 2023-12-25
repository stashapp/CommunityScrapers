import json
import os
import re
import sys
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()
    
try:
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

#  --------------------------------------

# This is a scraper for: animecharactersdatabase.com
#
# AnimeCharactersDatabase includes characters from:
# Anime, Hentai, (Mobile) Games, Eroge, Virtual Idols/YouTubers, Vocaloid
#
# These fields will be populated if available:
# Name, Gender, Birthdate, Country, Hair Color, Eye Color, Height, Measurements, URL, Details, Tags, Image
#
# A number of additional tags can be configured below.

# ---------------------------------------
# ---------- Tag Configuration ----------
# ---------------------------------------

# Maximum number of search results (between 1 and 30).
# Search by name includes the franchise for each result to make it easier to choose the correct one.
# Some (non ascii, very short) names require querying the API individually to get the franchise for each result.
# This might get you banned, since the API is rate limited.
# See: http://wiki.animecharactersdatabase.com/index.php?title=API_Access
limit = 15

# Prefix for performer tags.
prefix = "performer:"

# List of additional tags.
additional_tags = [{"name": "fictional"}]  # []

# Tags mostly include appearance indicators like: ahoge, dress, hat, twintails, etc.
include_tag = True
tag_prefix = prefix

# Scrape the source material as tag (name of anime/game): Kantai Collection, Idolmaster: Cinderella Girls, etc.
include_parody = True
parody_prefix = "parody:"

# Scrape Zodiac Sign as tag: Libra ♎, Sagittarius ♐, etc.
include_sign = True
sign_prefix = prefix + "sign:"

# Scrape race of non-human characters as tag: Orc, Elf, etc.
include_race = True
race_prefix = prefix + "race:"

# Scrape ship class of ship girls as tag (kancolle, etc.): Destroyer, etc.
include_ship_class = True
ship_class_prefix = prefix + "ship:"

# Scrape blood type as tag: A, B, etc.
include_blood_type = True
blood_type_prefix = prefix + "Blood Type "

# Scrape apparent age as tag: Adult, Teen, etc.
# Might differ from canonical age.
# Canonical age will be ignored, since it would result in too many tags.
# Birthdate is sometimes available, but the resulting calculated age represents neither canonical age nor apparent age.
include_apparent_age = True
apparent_age_prefix = prefix + "Apparent "

# Scrape Hair Length as tag: To Shoulders, To Neck, Past Waist, etc.
include_hair_length = True
hair_length_prefix = prefix + "Hair "


# ---------------------------------------
# ---------------------------------------
# ---------------------------------------

def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)


def scrapeURL(url):
    return html.fromstring(scrapeUrlToString(url))


def scrapeUrlToString(url):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url)
    except:
        log.error("scrape error")
        sys.exit(1)

    if scraped.status_code >= 400:
        log.error('HTTP Error: %s' % scraped.status_code)
        sys.exit(1)

    return scraped.content


def performerByName(query):
    cleanedQuery = requests.utils.quote(query)
    url = f"https://www.animecharactersdatabase.com/searchall.php?in=characters&sq={cleanedQuery}"
    tree = scrapeURL(url)
    names = tree.xpath("//li/div[@class='tile3top']/a/text()")
    ids = tree.xpath("//li/div[@class='tile3top']/a/@href")

    results = []
    for name, id in zip(names, ids):
        results.append({
            "name": name,
            "id": id.replace("characters.php?id=", ""),
            "url": "https://www.animecharactersdatabase.com/" + id
        })
    log.info(f"scraped {len(results)} results on: {url}")
    return results


def addFranchise(query, results):
    cleanedQuery = requests.utils.quote(query)
    url = f"https://www.animecharactersdatabase.com/api_series_characters.php?character_q={cleanedQuery}"
    data = json.loads(scrapeUrlToString(url))
    count1 = 0
    count2 = 0
    for result in results:
        try:
            # Try to find the franchise in API search results.
            # These results are ordered by alphabet and limited to 100,
            # so short queries might not include the correct result.
            # The API query also does not seem to support any Kanji.
            franchise = next(e["anime_name"] for e in data["search_results"] if str(e["id"]) == result["id"])
            count1 += 1
        except:
            # Use separate API calls as a backup.
            # This might get you banned, since the API is rate limited.
            franchise = apiGetCharacter(result["id"])["origin"]
            count2 += 1
        # Append franchise to character name for easier differentiation.
        result["name"] = f"{result['name']} ({franchise})"
        result.pop("id")
    log.debug(f"scraped {count1} franchises by single API call")
    log.debug(f"scraped {count2} franchises by separate API calls")
    return results


def apiGetCharacter(id):
    url = f"https://www.animecharactersdatabase.com/api_series_characters.php?character_id={id}"
    return json.loads(scrapeUrlToString(url))


def performerByURL(url, result={}):
    log.debug("performerByURL: " + url)
    tree = scrapeURL(url)
    result["url"] = url
    result["name"] = next(iter(tree.xpath(
        "//h3[@id='section001_summary']/following-sibling::p/a[contains(@href,'character')]/text()")), "").strip()
    result["details"] = "\n".join([s.strip() for s in tree.xpath(
        "//div[@style='padding: 0 15px 15px 15px; text-align: left;']/text()")])
    if not result["details"]:
        result["details"] = re.sub(" .$", ".", " ".join([s.strip() for s in tree.xpath(
            "//h3[@id='section001_summary']/following-sibling::p[contains(a/@href,'character')]//text()") if
                                                         s.strip()]))
    result["image"] = next(iter(tree.xpath("//meta[@property='og:image']/@content")), "")

    # left table, works for link and plain text fields, return result list
    def parse_left(field):
        template = "//table//th[text()='{0}' or a/text()='{0}']/following-sibling::td/a/text()"
        return tree.xpath(template.format(field))

    result["tags"] = additional_tags
    if include_tag:
        result["tags"] += [{"name": tag_prefix + tag.strip()} for tag in parse_left("Tags ")]
    if include_parody:
        result["tags"] += [{"name": parody_prefix + tag.strip()} for tag in parse_left("From")]
    if include_blood_type:
        result["tags"] += [{"name": blood_type_prefix + tag.strip()} for tag in parse_left("Blood Type")]
    if include_race:
        result["tags"] += [{"name": race_prefix + tag.strip()} for tag in parse_left("Race")]
    if include_sign:
        result["tags"] += [{"name": sign_prefix + tag.strip()} for tag in parse_left("Sign")]
    if include_ship_class:
        result["tags"] += [{"name": ship_class_prefix + tag.strip()} for tag in parse_left("Ship Class")]
    result["country"] = next(iter(parse_left("Nationality")), "")
    birthday = parse_left("Birthday")
    birthyear = parse_left("Birthyear")
    if birthday and birthyear:
        birthdate = datetime.strptime(birthday[0].strip(), "%B %d").replace(year=int(birthyear[0].strip()))
        result["birthdate"] = birthdate.strftime("%Y-%m-%d")
    bust = parse_left("Bust")
    waist = parse_left("Waist")
    hip = parse_left("Hip")
    if bust and waist and hip:
        bust = bust[0].strip().replace("cm", "")
        waist = waist[0].strip().replace("cm", "")
        hip = hip[0].strip().replace("cm", "")
        result["measurements"] = "{}-{}-{}".format(bust, waist, hip)
    result["height"] = next(iter(parse_left("Height")), "").strip().replace("cm", "")

    # middle/right table, reverse result list to prefer official appearance, return result or empty string
    def parse_right(field):
        template = "//table//th[text()='{}']/following-sibling::td/text()"
        return next(reversed(tree.xpath(template.format(field))), "").strip().replace("Unknown", "")

    # should be tagged anyway if yes
    # if parse_right("Animal Ears") == "Yes":
    #     result["tags"] += [{"name": "performer:animal ears"}]
    hair_length = parse_right("Hair Length")
    if include_hair_length and hair_length:
        result["tags"] += [{"name": hair_length_prefix + hair_length}]
    apparent_age = parse_right("Apparent Age")
    if include_apparent_age and apparent_age:
        result["tags"] += [{"name": apparent_age_prefix + apparent_age}]
    result["gender"] = parse_right("Gender")
    result["eye_color"] = parse_right("Eye Color")
    result["hair_color"] = parse_right("Hair Color")

    return result


# read the input
i = readJSONInput()

if sys.argv[1] == "performerByURL":
    url = i["url"]
    result = performerByURL(url)
    print(json.dumps(result))
elif sys.argv[1] == "performerByName":
    name = i["name"]
    log.info(f"Searching for name: {name}")
    results = performerByName(name)[:limit]
    results = addFranchise(name, results)
    print(json.dumps(results))
