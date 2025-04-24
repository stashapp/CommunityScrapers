import argparse
import json
import random
import re
import requests
import sys
import time
from typing import Iterable, Callable, TypeVar
from datetime import datetime

from py_common.util import guess_nationality
import py_common.log as log


try:
    import cloudscraper
except ModuleNotFoundError:
    print(
        "You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper",
        file=sys.stderr,
    )
    sys.exit()

try:
    from lxml import html
except ModuleNotFoundError:
    print(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml",
        file=sys.stderr,
    )
    sys.exit()

stash_date = "%Y-%m-%d"
iafd_date = "%B %d, %Y"
iafd_date_scene = "%b %d, %Y"

T = TypeVar("T")

SHARED_SELECTORS = {
    "title": "//h1/text()",
    "director": '//p[@class="bioheading"][contains(text(),"Director") or contains(text(),"Directors")]/following-sibling::p[@class="biodata"][1]/a/text()',
    "studio": '//p[@class="bioheading"][contains(text(),"Studio")]/following-sibling::p[@class="biodata"][1]//text()',
    "distributor": '//p[@class="bioheading"][contains(text(),"Distributor")]/following-sibling::p[@class="biodata"][1]//text()',
    "date": '//p[@class="bioheading"][contains(text(), "Release Date")]/following-sibling::p[@class="biodata"][1]/text()',
    "synopsis": '//div[@id="synopsis"]/div[@class="padded-panel"]//text()',
}


def maybe(
    values: Iterable[str], f: Callable[[str], (T | None)] = lambda x: x
) -> T | None:
    """
    Returns the first value in values that is not a predefined "empty value" after applying f to it
    """
    empty_values = ["No Data", "No Director", "None", "Unknown"]
    return next(
        (f(x) for x in values if not re.search("|".join(empty_values), x, re.I)),
        None,
    )


def cleandict(d: dict):
    return {k: v for k, v in d.items() if v}


def map_gender(gender: str):
    genders = {
        "Woman": "Female",
        "Man": "Male",
        "Trans woman": "Transgender Female",
        "Trans man": "Transgender Male",
    }
    return genders.get(gender, gender)


def map_haircolor(haircolor: str):
    haircolors = {
        "Blond": "Blonde",
        "Brown": "Brunette",
        "Dark Brown": "Brunette",
        "Red": "Redhead",
        "Grey": "Gray",
    }
    return haircolors.get(haircolor, haircolor)


def clean_date(date: str) -> str | None:
    date = date.strip()
    cleaned = re.sub(r"(\S+\s+\d+,\s+\d+).*", r"\1", date)
    for date_format in [iafd_date, iafd_date_scene]:
        try:
            return datetime.strptime(cleaned, date_format).strftime(stash_date)
        except ValueError:
            pass
    log.warning(f"Unable to parse '{date}' as a date")


def clean_alias(alias: str) -> str | None:
    # Aliases like "X or Y or Z" are indeterminate
    # and should not be included
    if " or " in alias:
        return None
    # We do not want studio disambiguation: "X (studio.com)" -> "X"
    return re.sub(r"\s*\(.*$", "", alias)


def base64_image(url) -> str:
    import base64

    b64img_bytes = base64.b64encode(scraper.get(url).content)
    return f"data:image/jpeg;base64,{b64img_bytes.decode('utf-8')}"


def performer_haircolor(tree):
    return maybe(
        tree.xpath(
            '//div/p[starts-with(.,"Hair Color")]/following-sibling::p[1]//text()'
        ),
        map_haircolor,
    )


def performer_weight(tree):
    return maybe(
        tree.xpath('//div/p[text()="Weight"]/following-sibling::p[1]//text()'),
        lambda w: re.sub(r".*\((\d+)\s+kg.*", r"\1", w),
    )


def performer_height(tree):
    return maybe(
        tree.xpath('//div/p[text()="Height"]/following-sibling::p[1]//text()'),
        lambda h: re.sub(r".*\((\d+)\s+cm.*", r"\1", h),
    )


def performer_country(tree):
    return maybe(
        tree.xpath('//div/p[text()="Nationality"]/following-sibling::p[1]//text()'),
        lambda c: guess_nationality(re.sub(r"^American,.+", "American", c)),
    )


def performer_ethnicity(tree):
    return maybe(
        tree.xpath('//div[p[text()="Ethnicity"]]/p[@class="biodata"][1]//text()')
    )


def performer_deathdate(tree):
    return maybe(
        tree.xpath(
            '(//p[@class="bioheading"][text()="Date of Death"]/following-sibling::p)[1]//text()'
        ),
        clean_date,
    )


def performer_birthdate(tree):
    return maybe(
        tree.xpath(
            '(//p[@class="bioheading"][text()="Birthday"]/following-sibling::p)[1]//text()'
        ),
        clean_date,
    )


def performer_instagram(tree):
    return maybe(
        tree.xpath(
            '//p[@class="biodata"]/a[contains(text(),"http://instagram.com/")]/@href'
        )
    )


def performer_twitter(tree):
    return maybe(
        tree.xpath(
            '//p[@class="biodata"]/a[contains(text(),"http://twitter.com/")]/@href'
        )
    )


def performer_url(tree):
    return maybe(
        tree.xpath('//div[@id="perfwith"]//*[contains(@href,"person.rme")]/@href'),
        lambda u: f"https://www.iafd.com{u}",
    )

def performer_gender_map(tree):
    gender = tree.xpath('//p[@class="bioheading" and contains(text(), "Gender")]/following-sibling::p[1]/text()')
    return map_gender(gender[0])

# unused code
def performer_gender(tree):
    def parse_transgender(gender: str):
        # get trans genders from the short code supplied
        if gender in ['tf', 'tm']:
            return map_gender(gender)

        # next, attempt to get the trans gender from the performer id suffix
        perf_id = next(
            iter(tree.xpath('//form[@id="correct"]/input[@name="PerfID"]/@value')), ""
        )
        trans = (
            "Transgender "
            # IAFD are not consistent with their URLs
            if any(mark in perf_id.lower() for mark in ("_ts", "_ftm", "_mtf"))
            else ""
        )
        return trans + map_gender(gender)

    return maybe(
        tree.xpath('//form[@id="correct"]/input[@name="Gender"]/@value'),
        parse_transgender,
    )
# end unused code


def performer_name(tree):
    return maybe(tree.xpath(SHARED_SELECTORS["title"]), lambda name: name.strip())


def performer_piercings(tree):
    return maybe(
        tree.xpath('//div/p[text()="Piercings"]/following-sibling::p[1]//text()')
    )


def performer_tattoos(tree):
    return maybe(
        tree.xpath('//div/p[text()="Tattoos"]/following-sibling::p[1]//text()')
    )


def performer_eyecolor(tree):
    return maybe(
        tree.xpath('//div/p[text()="Eye Color"]/following-sibling::p[1]//text()')
    )


def performer_aliases(tree):
    aliases = tree.xpath(
        '//div[p[@class="bioheading" and contains(normalize-space(text()),"Performer AKA")'
        'or contains(normalize-space(text()),"AKA")]]'
        '//div[@class="biodata" and not(normalize-space(text())="No known aliases")]/text()'
    )
    return ", ".join([y for x in aliases for y in [clean_alias(x.strip())] if y])


def performer_careerlength(tree):
    return maybe(
        tree.xpath(
            '//div/p[@class="bioheading"][contains(text(), "Active")][1]/following-sibling::p[1]/text()'
        ),
        lambda c: " - ".join(re.sub(r"(\D+\d\d\D+)$", "", c.strip()).split("-")),
    )


def performer_measurements(tree):
    return maybe(
        tree.xpath('//div/p[text()="Measurements"]/following-sibling::p[1]//text()')
    )


def scene_director(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["director"]),
        lambda d: d.strip(),
    )


def scene_studio(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["studio"]),
        lambda s: {"name": s},
    ) or maybe(
        tree.xpath(SHARED_SELECTORS["distributor"]),
        lambda s: {"name": s},
    )


def scene_details(tree):
    return maybe(tree.xpath(SHARED_SELECTORS["synopsis"]))


def scene_date(tree):
    # If there's no release date we will use the year from the title for an approximate date
    title_pattern = re.compile(r".*\(([0-9]{4})\).*")
    return maybe(
        tree.xpath(SHARED_SELECTORS["date"]),
        clean_date,
    ) or maybe(
        tree.xpath(SHARED_SELECTORS["title"]),
        lambda t: re.sub(title_pattern, r"\1-01-01", t).strip()
        if re.match(title_pattern, t)
        else None,
    )


def scene_title(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["title"]),
        lambda t: re.sub(r"\s*\(\d{4}\)$", "", t.strip()),
    )


def movie_studio(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["studio"]),
        lambda s: {"name": s},
    ) or maybe(
        tree.xpath(SHARED_SELECTORS["distributor"]),
        lambda s: {"name": s},
    )


def movie_date(tree):
    # If there's no release date we will use the year from the title for an approximate date
    title_pattern = re.compile(r".*\(([0-9]{4})\).*")
    return maybe(
        tree.xpath(SHARED_SELECTORS["date"]),
        lambda d: clean_date(d.strip()),
    ) or maybe(
        tree.xpath(SHARED_SELECTORS["title"]),
        lambda t: re.sub(title_pattern, r"\1-01-01", t).strip()
        if re.match(title_pattern, t)
        else None,
    )


def movie_duration(tree):
    # Convert duration from minutes to seconds, but keep it a string because that's what stash expects
    return maybe(
        tree.xpath(
            '//p[@class="bioheading"][contains(text(), "Minutes")]/following-sibling::p[@class="biodata"][1]/text()'
        ),
        lambda d: str(int(d) * 60),
    )


def movie_synopsis(tree):
    return maybe(tree.xpath(SHARED_SELECTORS["synopsis"]))


def movie_director(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["director"]),
        lambda d: d.strip(),
    )


def movie_title(tree):
    return maybe(
        tree.xpath(SHARED_SELECTORS["title"]),
        lambda t: re.sub(r"\s*\(\d+\)$", "", t.strip()),
    )


def video_url(tree):
    return maybe(
        tree.xpath('//div/p[contains(., "should be linked to")]/text()[2]'),
        lambda t: re.sub(r".*http", "http", t.strip()),
    )


# Only create a single scraper: this saves time when scraping multiple pages
# because it doesn't need to get past Cloudflare each time
scraper = cloudscraper.create_scraper()


def scrape(url: str, retries=0):
    global iafd_uuid_url
    try:
        scraped = scraper.get(url, timeout=(3, 7))
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return scrape(url, retries + 1)
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    if scraped.status_code >= 400:
        if retries < 10:
            wait_time = random.randint(1, 4)
            log.debug(f"HTTP Error: {scraped.status_code}, waiting {wait_time} seconds")
            time.sleep(wait_time)
            return scrape(url, retries + 1)
        log.error(f"HTTP Error: {scraped.status_code}, giving up")
        sys.exit(1)
    iafd_uuid_url = scraped.url
    return html.fromstring(scraped.content)


def performer_query(query):
    tree = scrape(
        f"https://www.iafd.com/results.asp?searchtype=comprehensive&searchstring={query}"
    )
    performer_names = tree.xpath(
        '//table[@id="tblFem" or @id="tblMal"]//td[a[img]]/following-sibling::td[1]/a/text()'
    )
    performer_urls = tree.xpath(
        '//table[@id="tblFem" or @id="tblMal"]//td[a[img]]/following-sibling::td[1]/a/@href'
    )
    performers = [
        {
            "name": name,
            "urls": [f"https://www.iafd.com{url}"],
        }
        for name, url in zip(performer_names, performer_urls)
    ]
    if not performers:
        log.warning(f"No performers found for '{query}'")
    return performers


def performer_from_tree(tree):
    return {
        "name": performer_name(tree),
        "gender": performer_gender_map(tree),
        "urls": [performer_url(tree)],
        "twitter": performer_twitter(tree),
        "instagram": performer_instagram(tree),
        "birthdate": performer_birthdate(tree),
        "death_date": performer_deathdate(tree),
        "ethnicity": performer_ethnicity(tree),
        "country": performer_country(tree),
        "height": performer_height(tree),
        "weight": performer_weight(tree),
        "hair_color": performer_haircolor(tree),
        "measurements": performer_measurements(tree),
        "career_length": performer_careerlength(tree),
        "aliases": performer_aliases(tree),
        "tattoos": performer_tattoos(tree),
        "piercings": performer_piercings(tree),
        "eye_color": performer_eyecolor(tree),
        "images": [
            base64_image(url) for url in tree.xpath('//div[@id="headshot"]//img/@src')
        ],
    }


def scene_from_tree(tree):
    return {
        "title": scene_title(tree),
        "date": scene_date(tree),
        "details": scene_details(tree),
        "director": scene_director(tree),
        "studio": scene_studio(tree),
        "performers": [
            {
                "name": p.text_content(),
                "urls": [f"https://www.iafd.com{p.get('href')}"],
                "images": [base64_image(url) for url in p.xpath("img/@src")],
            }
            for p in tree.xpath('//div[@class="castbox"]/p/a')
        ],
        "urls": [video_url(tree)],
    }


def movie_from_tree(tree):
    return {
        "name": movie_title(tree),
        "director": movie_director(tree),
        "synopsis": movie_synopsis(tree),
        "duration": movie_duration(tree),
        "date": movie_date(tree),
        "aliases": ", ".join(tree.xpath('//div[@class="col-sm-12"]/dl/dd//text()')),
        "studio": movie_studio(tree),
        "url": video_url(tree),
    }


def main():
    parser = argparse.ArgumentParser("IAFD Scraper", argument_default="")
    subparsers = parser.add_subparsers(
        dest="operation", help="Operation to perform", required=True
    )

    subparsers.add_parser("search", help="Search for performers").add_argument(
        "name", nargs="?", help="Name to search for"
    )
    subparsers.add_parser("performer", help="Scrape a performer").add_argument(
        "url", nargs="?", help="Performer URL"
    )
    subparsers.add_parser("movie", help="Scrape a movie").add_argument(
        "url", nargs="?", help="Movie URL"
    )
    subparsers.add_parser("scene", help="Scrape a scene").add_argument(
        "url", nargs="?", help="Scene URL"
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    log.debug(f"Arguments from commandline: {args}")
    # Script is being piped into, probably by Stash
    if not sys.stdin.isatty():
        try:
            frag = json.load(sys.stdin)
            args.__dict__.update(frag)
            log.debug(f"With arguments from stdin: {args}")
        except json.decoder.JSONDecodeError:
            log.error("Received invalid JSON from stdin")
            sys.exit(1)

    if args.operation == "search":
        name = args.name
        if not name:
            log.error("No query provided")
            sys.exit(1)
        log.debug(f"Searching for '{name}'")
        matches = performer_query(name)
        print(json.dumps(matches))
        sys.exit(0)

    url = args.url
    if not url:
        log.error("No URL provided")
        sys.exit(1)

    log.debug(f"{args.operation} scraping '{url}'")
    scraped = scrape(url)
    result = {}
    if args.operation == "performer":
        result = performer_from_tree(scraped)
        result["urls"] = [iafd_uuid_url]
    elif args.operation == "movie":
        result = movie_from_tree(scraped)
    elif args.operation == "scene":
        result = scene_from_tree(scraped)

    print(json.dumps(cleandict(result)))


if __name__ == "__main__":
    main()
