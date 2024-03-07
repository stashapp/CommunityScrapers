import json
import os
import re
import sys
from typing import Any

CURRENT_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_SCRIPT_DIR)
sys.path.append(PARENT_DIR)

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

try:
    import requests
    from lxml import etree
except ModuleNotFoundError:
    print("You need to install dependencies from requirements.txt")
    sys.exit(1)

XPATHS = {
    "alias": "//section[@class=\"main-column details\"]/h1/text()|//span[text()='別名']/following-sibling::p/text()",
    "birthdate": "//span[text()='生年月日']/../p/a/@href",
    "career": "//span[text()='AV出演期間']/../p/text()",
    "debut": "//span[text()='デビュー作品']/../p/text()",
    "id": '//form[@class="add_favorite"]/@action',
    "image": "//div[@class='act-area']/div[@class=\"thumb\"]/img/@src",
    "instagram": ("//span[text()='ブログ']/../p/a[contains(@href,'instagram.com')]/@href"),
    "measurements": (
        "//span[text()='サイズ']/../p/a/@href|//span[text()='サイズ']/../p/text()"
    ),
    "name_kanji": '//section[@class="main-column details"]/h1/text()',
    "origin": "//span[text()='出身地']/../p/a/text()",
    "name": '//section[@class="main-column details"]/h1/span/text()',
    "search_url": '../h2[@class="ttl"]/a/@href',
    "search": '//p[@class="furi"]',
    "twitter": ("//span[text()='ブログ']/../p/a[contains(@href,'twitter.com')]/@href"),
}

REGEXES = {
    # https://regex101.com/r/9k2GXw/5
    "alias": r"(?P<kanji>[^\x29\uFF09]+?)(?P<studio>[\x28\uFF08\u3010][^\x29\uFF09\u3011]+(?:[\x29\uFF09\u3011]))?\s[\x28\uFF08](?P<katakana>\w+)?\s+/\s(?P<romanized>[a-z-A-Z ]+)?[\x29\uFF09]",
    "id": r"\d+",
    "birthdate": r"[0-9-]+",
    # https://regex101.com/r/FSqv0L/1
    "career": (r"(?P<start>\d{4})年?(?:\d+月)? ?(?:\d+)?日?[-~]? ?(?:(?P<end>\d+)?)?年?"),
    "measurements": (
        r"(?<=T)(?P<height>\d+)? / B(?P<bust>\d+)\([^=]+=(?P<cup>\w+)\) / W(?P<waist>\d+) / H(?P<hip>\d+)"
    ),
    "url": r"https://www.minnano-av.com/actress\d+.html",
}

FORMATS = {
    "image": "https://www.minnano-av.com{IMAGE_URL_FRAGMENT}",
    "url": "https://www.minnano-av.com/actress{PERFORMER_ID}.html",
}


def reverse_first_last_name(performer_name):
    return " ".join(reversed(performer_name.split(" ")))


def convert_to_halfwidth(input: str) -> str:
    """Convert full-width characters to half-width."""
    fullwidth_range = range(0xFF01, 0xFF5E + 1)
    fullwidth_to_halfwidth_dict = {
        chr(fw_char): chr(fw_char - 0xFEE0) for fw_char in fullwidth_range
    }
    halfwidth_str = "".join(
        fullwidth_to_halfwidth_dict.get(char, char) for char in input
    )
    return halfwidth_str


def cm_to_inches(centimeters: int) -> int:
    return int(f"{centimeters / 2.54:.0f}")


def convert_bra_jp_to_us(jp_size: str) -> str:
    """
    Converts bra size from Japanese to US size.
    First it looks up the whole size in predefined chart,
    and if that fails:
        1. Band size is calculated manually.
        2. Cup size is looked up in another chart.
            1. If that fails as well, the Japanese cup size is used.
    References:
        * https://www.petitecherry.com/pages/size-guide
        * https://japanrabbit.com/blog/japanese-clothing-size-chart/
    """
    predefined_conversion_chart = {
        "65A": "30AA",
        "65B": "30A",
        "65C": "30B",
        "65D": "30C",
        "65E": "30D",
        "65F": "30E",
        "70A": "32AA",
        "70B": "32A",
        "70C": "32B",
        "70D": "32C",
        "70E": "32D",
        "70F": "32E",
        "70G": "32F",
        "70H": "32F",
        "70I": "32G",
        "75A": "34AA",
        "75B": "34A",
        "75C": "34B",
        "75D": "34C",
        "75E": "34D",
        "75F": "34E",
        "75G": "32E",
        "75H": "34F",
        "75I": "34G",
        "80B": "36A",
        "80C": "36B",
        "80D": "36C",
        "80E": "36D",
        "80F": "36E",
        "80G": "36E",
        "80H": "36F",
        "80I": "36G",
        "85C": "38B",
        "85D": "38C",
        "85E": "38D",
        "85F": "38E",
        "85G": "38E",
        "85H": "38F",
        "90D": "40C",
        "90E": "40D",
        "90F": "40E",
        "90G": "40E",
        "90H": "40F",
        "90I": "40G",
        "95E": "42C",
        "95F": "42E",
        "95G": "42E",
        "95H": "42F",
        "95I": "42G",
        "100E": "44D",
        "100F": "44E",
        "100G": "44E",
        "100H": "44F",
    }
    cup_conversion_chart = {
        "A": "AA",
        "B": "A",
        "C": "B",
        "D": "C",
        "F": "DD",
        "G": "D",
        "H": "F",
        "I": "G",
        "J": "H",
        "K": "I",
    }

    converted_size = None
    converted_size = predefined_conversion_chart.get(jp_size, None)

    if converted_size is None:
        band_size = int(jp_size[:-1])
        cup_size = jp_size[-1]
        converted_size = (
            f"{cm_to_inches(band_size)}{cup_conversion_chart.get(cup_size, cup_size)}"
        )
    return converted_size


def get_xpath_result(tree: Any, xpath_string: str) -> str | list[str] | None:
    _result = tree.xpath(xpath_string)
    if _result == []:
        return None
    elif len(_result) == 1:
        return _result[0]
    else:
        return _result


def performer_by_url(url):
    request = requests.get(url)
    log.debug(request.status_code)

    tree = etree.HTML(request.text)

    scrape = {}
    aliases = set()

    JAPANESE = True

    if origin_result := get_xpath_result(tree, XPATHS["origin"]):
        if origin_result == "海外":
            JAPANESE = False

    if name_xpath_result := get_xpath_result(tree, XPATHS["name"]):
        _, romanized_name = name_xpath_result.split(" / ")
        performer_name = romanized_name
        if JAPANESE:
            performer_name = reverse_first_last_name(performer_name)
        scrape["name"] = performer_name
        aliases.add(romanized_name)

    if kanji_xpath_result := get_xpath_result(tree, XPATHS["name_kanji"]):
        # \u3010 is 【
        if "\u3010" in kanji_xpath_result:
            kanji_name, _ = kanji_xpath_result.split("\u3010")
        else:
            kanji_name = kanji_xpath_result
        if kanji_name != "":
            aliases.add(kanji_name)
        else:
            log.debug("Kanji name XPath matched, but no value found.")

    if aliases_xpath_result := get_xpath_result(tree, XPATHS["alias"]):
        for alias in aliases_xpath_result:
            if match := re.match(REGEXES["alias"], alias):
                aliases.add(match.group("kanji"))
                try:
                    aliases.add(match.group("romanized"))
                except:
                    pass

    if favorite_form_url := get_xpath_result(tree, XPATHS["id"]):
        if match := re.search(REGEXES["id"], favorite_form_url):
            scrape["url"] = FORMATS["url"].format(PERFORMER_ID=match[0])
        else:
            log.debug("URL XPath matched, but no value found.")

    if twitter_url_result := get_xpath_result(tree, XPATHS["twitter"]):
        if twitter_url_result != None:
            scrape["twitter"] = twitter_url_result
        else:
            log.debug("Twitter XPath matched, but no value found.")

    if instagram_url_result := get_xpath_result(tree, XPATHS["instagram"]):
        if instagram_url_result != None:
            scrape["instagram"] = instagram_url_result
        else:
            log.debug("Instagram XPath matched, but no value found.")

    if birthdate_result := get_xpath_result(tree, XPATHS["birthdate"]):
        if match := re.search(
            REGEXES["birthdate"], convert_to_halfwidth(birthdate_result)
        ):
            scrape["birthdate"] = match[0]
        else:
            log.debug("Birthday XPath matched, but no value found.")

    if measurements_result := get_xpath_result(tree, XPATHS["measurements"]):
        combined = "".join(measurements_result)
        if match := re.search(REGEXES["measurements"], convert_to_halfwidth(combined)):
            waist_in_inches, hip_in_inches = [
                cm_to_inches(int(measurement))
                for measurement in [match["waist"], match["hip"]]
            ]

            bra_size = convert_bra_jp_to_us(f'{match["bust"]}{match["cup"]}')

            scrape["measurements"] = f"{bra_size}-{waist_in_inches}-{hip_in_inches}"
            if match["height"] != None:
                scrape["height"] = match["height"]
        else:
            log.debug("Measurements XPath matched, but no value found.")

    if career_result := get_xpath_result(tree, XPATHS["career"]):
        clean_career_result = convert_to_halfwidth(career_result).replace(" ", "")
        if match := re.match(REGEXES["career"], clean_career_result):
            groups = match.groups()
            start = match["start"] + "-" if groups[0] != None else ""
            end = match["end"] if groups[1] != None else ""
            scrape["career_length"] = start + end
        else:
            log.debug("Career debut XPath matched, but no value found.")

    elif debut_result := get_xpath_result(tree, XPATHS["debut"]):
        if match := re.search(REGEXES["career"], convert_to_halfwidth(debut_result)):
            groups = match.groups()
            scrape[
                "career_length"
            ] = f'{match["start"] if groups[0] != None else ""}-{match["end"] if groups[1] != None else ""}'
        else:
            log.debug("Career debut XPath matched, but no value found.")

    if image_result := get_xpath_result(tree, XPATHS["image"]):
        clean_url_fragment = str.replace(image_result, "?new", "")
        if clean_url_fragment != "":
            scrape["image"] = str.format(
                FORMATS["image"], IMAGE_URL_FRAGMENT=clean_url_fragment
            )
        else:
            log.debug("Image XPath matched, but no value found.")

    aliases.discard(None)
    sorted_aliases = sorted(aliases)
    scrape["aliases"] = ", ".join(sorted_aliases)
    if JAPANESE:
        scrape["country"] = "Japan"
        scrape["ethnicity"] = "Asian"
        scrape["hair_color"] = "Black"
        scrape["eye_color"] = "Brown"
    scrape["gender"] = "Female"
    print(json.dumps(scrape))


def performer_by_name(name: str, retry=True) -> None:
    queryURL = f"https://www.minnano-av.com/search_result.php?search_scope=actress&search_word={name}"

    result = requests.get(queryURL)
    tree = etree.HTML(result.text)

    performer_list = []

    if re.search(REGEXES["url"], result.url):
        performer_list.append({"name": name, "url": result.url})
    elif search_result := get_xpath_result(tree, XPATHS["search"]):
        for node in search_result:
            performer = {}
            node_value = node.text
            if "/" not in node_value:
                continue
            _, romanized_name = node_value.split(" / ")
            performer["name"] = romanized_name
            if url_result := get_xpath_result(node, XPATHS["search_url"]):
                url = ""
                if match := re.search(REGEXES["id"], url_result):
                    url = str.format(FORMATS["url"], PERFORMER_ID=match[0])
                performer["url"] = url
            performer_list.append(performer)
    elif retry:
        modified_name = reverse_first_last_name(name)
        performer_by_name(modified_name, retry=False)
    else:
        performer_list.append({"name": "No performer found"})

    print(json.dumps(performer_list))


def main():
    if len(sys.argv) == 1:
        log.error("No arguments")
        sys.exit(1)

    stdin = sys.stdin.read()

    inputJSON = json.loads(stdin)
    url = inputJSON.get("url", None)
    name = inputJSON.get("name", None)

    if "performer_by_url" in sys.argv:
        log.debug("Processing performer by URL")
        log.debug(stdin)
        if url:
            performer_by_url(url)
        else:
            log.error("Missing URL")
    elif "performer_by_name" in sys.argv:
        log.debug("Processing performer by name")
        log.debug(stdin)
        if name:
            performer_by_name(name)
        else:
            log.error("Missing name")
    else:
        log.error("No argument processed")
        log.debug(stdin)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(e)
