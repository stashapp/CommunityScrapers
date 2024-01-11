import argparse
import json
import os
import random
import re
import requests
import sys
import time
from typing import Iterable, Callable, TypeVar
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

# extra modules below need to be installed
try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

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


def maybe(
    values: Iterable[str], f: Callable[[str], (T | None)] = lambda x: x
) -> T | None:
    """
    Returns the first value in values that is not "No data" after applying f to it
    """
    return next(
        (f(x) for x in values if not re.search(r"(?i)no data|director", x)), None
    )


def cleandict(d: dict):
    return {k: v for k, v in d.items() if v}


def map_ethnicity(ethnicity: str):
    ethnicities = {
        "Asian": "asian",
        "Caucasian": "white",
        "Black": "black",
        "Latin": "hispanic",
    }
    return ethnicities.get(ethnicity, ethnicity)


def map_gender(gender: str):
    genders = {
        "f": "Female",
        "m": "Male",
    }
    return genders.get(gender, gender)


def map_country(country: str):
    countries = {
        # https://en.wikipedia.org/wiki/List_of_adjectival_and_demonymic_forms_for_countries_and_nations
        "Abkhaz": "Abkhazia",
        "Abkhazian": "Abkhazia",
        "Afghan": "Afghanistan",
        "Albanian": "Albania",
        "Algerian": "Algeria",
        "American Samoan": "American Samoa",
        "American": "United States of America",
        "Andorran": "Andorra",
        "Angolan": "Angola",
        "Anguillan": "Anguilla",
        "Antarctic": "Antarctica",
        "Antiguan": "Antigua and Barbuda",
        "Argentine": "Argentina",
        "Argentinian": "Argentina",
        "Armenian": "Armenia",
        "Aruban": "Aruba",
        "Australian": "Australia",
        "Austrian": "Austria",
        "Azerbaijani": "Azerbaijan",
        "Azeri": "Azerbaijan",
        "Bahamian": "Bahamas",
        "Bahraini": "Bahrain",
        "Bangladeshi": "Bangladesh",
        "Barbadian": "Barbados",
        "Barbudan": "Antigua and Barbuda",
        "Basotho": "Lesotho",
        "Belarusian": "Belarus",
        "Belgian": "Belgium",
        "Belizean": "Belize",
        "Beninese": "Benin",
        "Beninois": "Benin",
        "Bermudan": "Bermuda",
        "Bermudian": "Bermuda",
        "Bhutanese": "Bhutan",
        "BIOT": "British Indian Ocean Territory",
        "Bissau-Guinean": "Guinea-Bissau",
        "Bolivian": "Bolivia",
        "Bonaire": "Bonaire",
        "Bonairean": "Bonaire",
        "Bosnian": "Bosnia and Herzegovina",
        "Botswanan": "Botswana",
        "Bouvet Island": "Bouvet Island",
        "Brazilian": "Brazil",
        "British Virgin Island": "Virgin Islands, British",
        "British": "United Kingdom",
        "Bruneian": "Brunei",
        "Bulgarian": "Bulgaria",
        "Burkinabé": "Burkina Faso",
        "Burmese": "Burma",
        "Burundian": "Burundi",
        "Cabo Verdean": "Cabo Verde",
        "Cambodian": "Cambodia",
        "Cameroonian": "Cameroon",
        "Canadian": "Canada",
        "Cantonese": "Hong Kong",
        "Caymanian": "Cayman Islands",
        "Central African": "Central African Republic",
        "Chadian": "Chad",
        "Channel Island": "Guernsey",
        "Chilean": "Chile",
        "Chinese": "China",
        "Christmas Island": "Christmas Island",
        "Cocos Island": "Cocos (Keeling) Islands",
        "Colombian": "Colombia",
        "Comoran": "Comoros",
        "Comorian": "Comoros",
        "Congolese": "Congo",
        "Cook Island": "Cook Islands",
        "Costa Rican": "Costa Rica",
        "Croatian": "Croatia",
        "Cuban": "Cuba",
        "Curaçaoan": "Curaçao",
        "Cypriot": "Cyprus",
        "Czech": "Czech Republic",
        "Danish": "Denmark",
        "Djiboutian": "Djibouti",
        "Dominican": "Dominica",
        "Dutch": "Netherlands",
        "Ecuadorian": "Ecuador",
        "Egyptian": "Egypt",
        "Emirati": "United Arab Emirates",
        "Emiri": "United Arab Emirates",
        "Emirian": "United Arab Emirates",
        "English people": "England",
        "English": "England",
        "Equatoguinean": "Equatorial Guinea",
        "Equatorial Guinean": "Equatorial Guinea",
        "Eritrean": "Eritrea",
        "Estonian": "Estonia",
        "Ethiopian": "Ethiopia",
        "European": "European Union",
        "Falkland Island": "Falkland Islands",
        "Faroese": "Faroe Islands",
        "Fijian": "Fiji",
        "Filipino": "Philippines",
        "Finnish": "Finland",
        "Formosan": "Taiwan",
        "French Guianese": "French Guiana",
        "French Polynesian": "French Polynesia",
        "French Southern Territories": "French Southern Territories",
        "French": "France",
        "Futunan": "Wallis and Futuna",
        "Gabonese": "Gabon",
        "Gambian": "Gambia",
        "Georgian": "Georgia",
        "German": "Germany",
        "Ghanaian": "Ghana",
        "Gibraltar": "Gibraltar",
        "Greek": "Greece",
        "Greenlandic": "Greenland",
        "Grenadian": "Grenada",
        "Guadeloupe": "Guadeloupe",
        "Guamanian": "Guam",
        "Guatemalan": "Guatemala",
        "Guinean": "Guinea",
        "Guyanese": "Guyana",
        "Haitian": "Haiti",
        "Heard Island": "Heard Island and McDonald Islands",
        "Hellenic": "Greece",
        "Herzegovinian": "Bosnia and Herzegovina",
        "Honduran": "Honduras",
        "Hong Kong": "Hong Kong",
        "Hong Konger": "Hong Kong",
        "Hungarian": "Hungary",
        "Icelandic": "Iceland",
        "Indian": "India",
        "Indonesian": "Indonesia",
        "Iranian": "Iran",
        "Iraqi": "Iraq",
        "Irish": "Ireland",
        "Israeli": "Israel",
        "Israelite": "Israel",
        "Italian": "Italy",
        "Ivorian": "Ivory Coast",
        "Jamaican": "Jamaica",
        "Jan Mayen": "Jan Mayen",
        "Japanese": "Japan",
        "Jordanian": "Jordan",
        "Kazakh": "Kazakhstan",
        "Kazakhstani": "Kazakhstan",
        "Kenyan": "Kenya",
        "Kirghiz": "Kyrgyzstan",
        "Kirgiz": "Kyrgyzstan",
        "Kiribati": "Kiribati",
        "Korean": "South Korea",
        "Kosovan": "Kosovo",
        "Kosovar": "Kosovo",
        "Kuwaiti": "Kuwait",
        "Kyrgyz": "Kyrgyzstan",
        "Kyrgyzstani": "Kyrgyzstan",
        "Lao": "Lao People's Democratic Republic",
        "Laotian": "Lao People's Democratic Republic",
        "Latvian": "Latvia",
        "Lebanese": "Lebanon",
        "Lettish": "Latvia",
        "Liberian": "Liberia",
        "Libyan": "Libya",
        "Liechtensteiner": "Liechtenstein",
        "Lithuanian": "Lithuania",
        "Luxembourg": "Luxembourg",
        "Luxembourgish": "Luxembourg",
        "Macanese": "Macau",
        "Macedonian": "North Macedonia",
        "Magyar": "Hungary",
        "Mahoran": "Mayotte",
        "Malagasy": "Madagascar",
        "Malawian": "Malawi",
        "Malaysian": "Malaysia",
        "Maldivian": "Maldives",
        "Malian": "Mali",
        "Malinese": "Mali",
        "Maltese": "Malta",
        "Manx": "Isle of Man",
        "Marshallese": "Marshall Islands",
        "Martinican": "Martinique",
        "Martiniquais": "Martinique",
        "Mauritanian": "Mauritania",
        "Mauritian": "Mauritius",
        "McDonald Islands": "Heard Island and McDonald Islands",
        "Mexican": "Mexico",
        "Moldovan": "Moldova",
        "Monacan": "Monaco",
        "Mongolian": "Mongolia",
        "Montenegrin": "Montenegro",
        "Montserratian": "Montserrat",
        "Monégasque": "Monaco",
        "Moroccan": "Morocco",
        "Motswana": "Botswana",
        "Mozambican": "Mozambique",
        "Myanma": "Myanmar",
        "Namibian": "Namibia",
        "Nauruan": "Nauru",
        "Nepalese": "Nepal",
        "Nepali": "Nepal",
        "Netherlandic": "Netherlands",
        "New Caledonian": "New Caledonia",
        "New Zealand": "New Zealand",
        "Ni-Vanuatu": "Vanuatu",
        "Nicaraguan": "Nicaragua",
        "Nigerian": "Nigeria",
        "Nigerien": "Niger",
        "Niuean": "Niue",
        "Norfolk Island": "Norfolk Island",
        "Northern Irish": "Northern Ireland",
        "Northern Marianan": "Northern Mariana Islands",
        "Norwegian": "Norway",
        "Omani": "Oman",
        "Pakistani": "Pakistan",
        "Palauan": "Palau",
        "Palestinian": "Palestine",
        "Panamanian": "Panama",
        "Papua New Guinean": "Papua New Guinea",
        "Papuan": "Papua New Guinea",
        "Paraguayan": "Paraguay",
        "Persian": "Iran",
        "Peruvian": "Peru",
        "Philippine": "Philippines",
        "Pitcairn Island": "Pitcairn Islands",
        "Polish": "Poland",
        "Portuguese": "Portugal",
        "Puerto Rican": "Puerto Rico",
        "Qatari": "Qatar",
        "Romanian": "Romania",
        "Russian": "Russia",
        "Rwandan": "Rwanda",
        "Saba": "Saba",
        "Saban": "Saba",
        "Sahraouian": "Western Sahara",
        "Sahrawi": "Western Sahara",
        "Sahrawian": "Western Sahara",
        "Salvadoran": "El Salvador",
        "Sammarinese": "San Marino",
        "Samoan": "Samoa",
        "Saudi Arabian": "Saudi Arabia",
        "Saudi": "Saudi Arabia",
        "Scottish": "Scotland",
        "Senegalese": "Senegal",
        "Serbian": "Serbia",
        "Seychellois": "Seychelles",
        "Sierra Leonean": "Sierra Leone",
        "Singapore": "Singapore",
        "Singaporean": "Singapore",
        "Slovak": "Slovakia",
        "Slovene": "Slovenia",
        "Slovenian": "Slovenia",
        "Solomon Island": "Solomon Islands",
        "Somali": "Somalia",
        "Somalilander": "Somaliland",
        "South African": "South Africa",
        "South Georgia Island": "South Georgia and the South Sandwich Islands",
        "South Ossetian": "South Ossetia",
        "South Sandwich Island": "South Georgia and the South Sandwich Islands",
        "South Sudanese": "South Sudan",
        "Spanish": "Spain",
        "Sri Lankan": "Sri Lanka",
        "Sudanese": "Sudan",
        "Surinamese": "Suriname",
        "Svalbard resident": "Svalbard",
        "Swati": "Eswatini",
        "Swazi": "Eswatini",
        "Swedish": "Sweden",
        "Swiss": "Switzerland",
        "Syrian": "Syrian Arab Republic",
        "Taiwanese": "Taiwan",
        "Tajikistani": "Tajikistan",
        "Tanzanian": "Tanzania",
        "Thai": "Thailand",
        "Timorese": "Timor-Leste",
        "Tobagonian": "Trinidad and Tobago",
        "Togolese": "Togo",
        "Tokelauan": "Tokelau",
        "Tongan": "Tonga",
        "Trinidadian": "Trinidad and Tobago",
        "Tunisian": "Tunisia",
        "Turkish": "Turkey",
        "Turkmen": "Turkmenistan",
        "Turks and Caicos Island": "Turks and Caicos Islands",
        "Tuvaluan": "Tuvalu",
        "Ugandan": "Uganda",
        "Ukrainian": "Ukraine",
        "Uruguayan": "Uruguay",
        "Uzbek": "Uzbekistan",
        "Uzbekistani": "Uzbekistan",
        "Vanuatuan": "Vanuatu",
        "Vatican": "Vatican City State",
        "Venezuelan": "Venezuela",
        "Vietnamese": "Vietnam",
        "Wallis and Futuna": "Wallis and Futuna",
        "Wallisian": "Wallis and Futuna",
        "Welsh": "Wales",
        "Yemeni": "Yemen",
        "Zambian": "Zambia",
        "Zimbabwean": "Zimbabwe",
        "Åland Island": "Åland Islands",
    }
    return countries.get(country, country)


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


def performer_haircolor(tree):
    return maybe(
        tree.xpath(
            '//div/p[starts-with(.,"Hair Color")]/following-sibling::p[1]//text()'
        )
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
        lambda c: map_country(re.sub(r"^American,.+", "American", c)),
    )


def performer_ethnicity(tree):
    return maybe(
        tree.xpath('//div[p[text()="Ethnicity"]]/p[@class="biodata"][1]//text()'),
        map_ethnicity,
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


def performer_gender(tree):
    def prepend_transgender(gender: str):
        perf_id = next(
            iter(tree.xpath('//form[@id="correct"]/input[@name="PerfID"]/@value')), ""
        )
        trans = (
            "Transgender "
            # IAFD are not consistent with their
            if any(mark in perf_id for mark in ("_ts", "_ftm", "_mtf"))
            else ""
        )
        return trans + map_gender(gender)

    return maybe(
        tree.xpath('//form[@id="correct"]/input[@name="Gender"]/@value'),
        prepend_transgender,
    )


def performer_name(tree):
    return maybe(tree.xpath("//h1/text()"), lambda name: name.strip())


def performer_piercings(tree):
    return maybe(
        tree.xpath('//div/p[text()="Piercings"]/following-sibling::p[1]//text()')
    )


def performer_tattoos(tree):
    return maybe(
        tree.xpath('//div/p[text()="Tattoos"]/following-sibling::p[1]//text()')
    )


def performer_aliases(tree):
    return maybe(
        tree.xpath(
            '//div[p[@class="bioheading" and contains(normalize-space(text()),"Performer AKA")]]//div[@class="biodata" and not(text()="No known aliases")]/text()'
        ),
        lambda aliases: ", ".join(
            filter(None, (clean_alias(alias) for alias in aliases.split(", ")))
        ),
    )


def performer_careerlength(tree):
    return maybe(
        tree.xpath(
            '//div/p[@class="biodata"][contains(text(),"Started around")]/text()'
        ),
        lambda c: re.sub(r"(\D+\d\d\D+)$", "", c),
    )


def performer_measurements(tree):
    return maybe(
        tree.xpath('//div/p[text()="Measurements"]/following-sibling::p[1]//text()')
    )


def scene_director(tree):
    return maybe(
        tree.xpath(
            '//p[@class="bioheading"][text()="Director" or text()="Directors"]/following-sibling::p[1]//text()'
        ),
        lambda d: d.strip(),
    )


def scene_studio(tree):
    return maybe(
        tree.xpath(
            '//div[@class="col-xs-12 col-sm-3"]//p[text() = "Studio"]/following-sibling::p[1]//text()'
        ),
        lambda s: {"name": s},
    )


def scene_details(tree):
    return maybe(tree.xpath('//div[@id="synopsis"]/div[@class="padded-panel"]//text()'))


def scene_date(tree):
    return maybe(
        tree.xpath(
            '//div[@class="col-xs-12 col-sm-3"]//p[text() = "Release Date"]/following-sibling::p[1]//text()'
        ),
        clean_date,
    )


def scene_title(tree):
    return maybe(
        tree.xpath("//h1/text()"), lambda t: re.sub(r"\s*\(\d{4}\)$", "", t.strip())
    )


def movie_studio(tree):
    return maybe(
        tree.xpath(
            '//p[@class="bioheading"][contains(text(),"Studio" or contains(text(),"Distributor"))]/following-sibling::p[@class="biodata"][1]//text()'
        ),
        lambda s: {"name": s},
    )


def movie_date(tree):
    # If there's no release date we will use the year from the title for an approximate date
    return maybe(
        tree.xpath(
            '//p[@class="bioheading"][contains(text(), "Release Date")]/following-sibling::p[@class="biodata"][1]/text()'
        ),
        lambda d: clean_date(d.strip()),
    ) or maybe(
        tree.xpath("//h1/text()"),
        lambda t: re.sub(r".*\(([0-9]+)\).*$", r"\1-01-01", t),
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
    return maybe(tree.xpath('//div[@id="synopsis"]/div[@class="padded-panel"]//text()'))


def movie_director(tree):
    return maybe(
        tree.xpath(
            '//p[@class="bioheading"][contains(text(), "Directors")]/following-sibling::p[@class="biodata"][1]/a/text()'
        ),
        lambda d: d.strip(),
    )


def movie_title(tree):
    return maybe(
        tree.xpath("//h1/text()"), lambda t: re.sub(r"\s*\(\d+\)$", "", t.strip())
    )


# Only create a single scraper: this saves time when scraping multiple pages
# because it doesn't need to get past Cloudflare each time
scraper = cloudscraper.create_scraper()


def scrape(url: str, retries=0):
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
            "Name": name,
            "URL": f"https://www.iafd.com{url}",
        }
        for name, url in zip(performer_names, performer_urls)
    ]
    if not performers:
        log.warning(f"No performers found for '{query}'")
    return performers


def performer_from_tree(tree):
    return {
        "name": performer_name(tree),
        "gender": performer_gender(tree),
        "url": performer_url(tree),
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
        "images": tree.xpath('//div[@id="headshot"]//img/@src'),
    }


def scene_from_tree(tree):
    return {
        "title": scene_title(tree),
        "date": scene_date(tree),
        "details": scene_details(tree),
        "director": scene_director(tree),
        "studio": scene_studio(tree),
        "performers": [
            {"name": name} for name in tree.xpath('//div[@class="castbox"]/p/a/text()')
        ],
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
    elif args.operation == "movie":
        result = movie_from_tree(scraped)
    elif args.operation == "scene":
        result = scene_from_tree(scraped)

    print(json.dumps(cleandict(result)))


if __name__ == "__main__":
    main()
