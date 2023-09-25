import argparse
import json
import sys
import time
import re
import random
import requests
from typing import Iterable, Callable
from datetime import datetime

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


def maybe(values: Iterable[str], f: Callable[[str], str] = lambda x: x):
    """
    Returns the first value in values that is not "No data" after applying f to it
    """
    return next((f(x) for x in values if not re.search(r"(?i)no data", x)), None)


def cleandict(d: dict):
    return {k: v for k, v in d.items() if v}


def map_ethnicity(ethnicity):
    ethnicities = {
        "Asian": "asian",
        "Caucasian": "white",
        "Black": "black",
        "Latin": "hispanic",
    }
    return ethnicities.get(ethnicity, ethnicity)


def map_gender(gender):
    genders = {
        "f": "Female",
        "m": "Male",
    }
    return genders.get(gender, gender)


def map_country(value):
    country = {
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
    return country.get(value, value)


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


def clean_date(date: str) -> datetime | None:
    date = date.strip()
    cleaned = re.sub(r"(\S+\s+\d+,\s+\d+).*", r"\1", date)
    for date_format in [iafd_date, iafd_date_scene]:
        try:
            return datetime.strptime(cleaned, date_format).strftime(stash_date)
        except ValueError:
            pass
    log.warning(f"Unable to parse '{date}' as a date")


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
    print(json.dumps(performers))
    if not performers:
        log.warning(f"No performers found for '{query}'")


def performer_from_tree(tree):
    scraped = {}

    name = tree.xpath("//h1/text()")
    scraped["name"] = maybe(name, lambda name: name.strip())

    gender = tree.xpath('//form[@id="correct"]/input[@name="Gender"]/@value')
    scraped["gender"] = maybe(gender, map_gender)

    url = tree.xpath('//div[@id="perfwith"]//*[contains(@href,"person.rme")]/@href')
    scraped["url"] = maybe(url, lambda u: f"https://www.iafd.com{u}")

    twitter = tree.xpath(
        '//p[@class="biodata"]/a[contains(text(),"http://twitter.com/")]/@href'
    )
    scraped["twitter"] = maybe(twitter)

    instagram = tree.xpath(
        '//p[@class="biodata"]/a[contains(text(),"http://instagram.com/")]/@href'
    )
    scraped["instagram"] = maybe(instagram)

    birthdate = tree.xpath(
        '(//p[@class="bioheading"][text()="Birthday"]/following-sibling::p)[1]//text()'
    )
    scraped["birthdate"] = maybe(birthdate, clean_date)

    deathdate = tree.xpath(
        '(//p[@class="bioheading"][text()="Date of Death"]/following-sibling::p)[1]//text()'
    )
    scraped["death_date"] = maybe(deathdate, clean_date)

    ethnicity = tree.xpath(
        '//div[p[text()="Ethnicity"]]/p[@class="biodata"][1]//text()'
    )
    scraped["ethnicity"] = maybe(ethnicity, map_ethnicity)

    country = tree.xpath(
        '//div/p[text()="Nationality"]/following-sibling::p[1]//text()'
    )
    scraped["country"] = maybe(
        country, lambda c: map_country(re.sub(r"^American,.+", "American", c))
    )

    height = tree.xpath('//div/p[text()="Height"]/following-sibling::p[1]//text()')
    scraped["height"] = maybe(height, lambda h: re.sub(r".*\((\d+)\s+cm.*", r"\1", h))

    weight = tree.xpath('//div/p[text()="Weight"]/following-sibling::p[1]//text()')
    scraped["weight"] = maybe(weight, lambda w: re.sub(r".*\((\d+)\s+kg.*", r"\1", w))

    hair_color = tree.xpath(
        '//div/p[starts-with(.,"Hair Color")]/following-sibling::p[1]//text()'
    )
    scraped["hair_color"] = maybe(hair_color)

    measurements = tree.xpath(
        '//div/p[text()="Measurements"]/following-sibling::p[1]//text()'
    )
    scraped["measurements"] = maybe(measurements)

    career_length = tree.xpath(
        '//div/p[@class="biodata"][contains(text(),"Started around")]/text()'
    )
    scraped["career_length"] = maybe(
        career_length, lambda c: re.sub(r"(\D+\d\d\D+)$", "", c)
    )

    aliases = tree.xpath(
        '//div[p[@class="bioheading" and contains(normalize-space(text()),"Performer AKA")]]//div[@class="biodata" and not(text()="No known aliases")]/text()'
    )
    scraped["aliases"] = maybe(aliases)

    tattoos = tree.xpath('//div/p[text()="Tattoos"]/following-sibling::p[1]//text()')
    scraped["tattoos"] = maybe(tattoos)

    piercings = tree.xpath(
        '//div/p[text()="Piercings"]/following-sibling::p[1]//text()'
    )
    scraped["piercings"] = maybe(piercings)

    image_url = tree.xpath('//div[@id="headshot"]//img/@src')
    scraped["images"] = image_url

    print(json.dumps(cleandict(scraped)))
    sys.exit(0)


def scene_from_tree(tree):
    scraped = {}
    title = tree.xpath("//h1/text()")
    scraped["title"] = maybe(title, lambda t: t.strip())

    date = tree.xpath(
        '//div[@class="col-xs-12 col-sm-3"]//p[text() = "Release Date"]/following-sibling::p[1]//text()'
    )
    scraped["date"] = maybe(date, clean_date)

    details = tree.xpath('//div[@id="synopsis"]/div[@class="padded-panel"]//text()')
    scraped["details"] = maybe(details)

    studio = tree.xpath(
        '//div[@class="col-xs-12 col-sm-3"]//p[text() = "Studio"]/following-sibling::p[1]//text()'
    )
    scraped["studio"] = maybe(studio, lambda s: {"name": s})

    performers = tree.xpath('//div[@class="castbox"]/p/a/text()')
    scraped["performers"] = [{"name": name} for name in performers]

    print(json.dumps(cleandict(scraped)))
    sys.exit(0)


def movie_from_tree(tree):
    scraped = {}

    title = tree.xpath("//h1/text()")
    scraped["name"] = maybe(title, lambda t: re.sub(r"\s*\([0-9]+\)$", "", t.strip()))

    directors = tree.xpath(
        '//p[@class="bioheading"][contains(text(), "Directors")]/following-sibling::p[@class="biodata"][1]/a/text()'
    )
    scraped["director"] = maybe(directors, lambda d: d.strip())

    movie_synopsis = tree.xpath(
        '//div[@id="synopsis"]/div[@class="padded-panel"]//text()'
    )
    scraped["synopsis"] = maybe(movie_synopsis)

    duration = tree.xpath(
        '//p[@class="bioheading"][contains(text(), "Minutes")]/following-sibling::p[@class="biodata"][1]/text()'
    )
    # Convert duration from minutes to seconds,
    # but keep it a string because that's what stash expects
    scraped["duration"] = maybe(duration, lambda d: str(int(d) * 60))

    date = tree.xpath(
        '//p[@class="bioheading"][contains(text(), "Release Date")]/following-sibling::p[@class="biodata"][1]/text()'
    )
    # If there's no release date, use the year from the title for an approximate date
    scraped["date"] = maybe(date, lambda d: clean_date(d.strip())) or maybe(
        title, lambda t: re.sub(r".*\(([0-9]+)\).*$", r"\1-01-01", t)
    )

    aliases = tree.xpath('//div[@class="col-sm-12"]/dl/dd//text()')
    scraped["aliases"] = ", ".join(aliases)

    studio = tree.xpath(
        '//p[@class="bioheading"][contains(text(),"Studio")]/following-sibling::p[@class="biodata"][1]//text()'
    )
    distributor = tree.xpath(
        '//p[@class="bioheading"][contains(text(),"Distributor")]/following-sibling::p[@class="biodata"][1]//text()'
    )
    scraped["studio"] = maybe(studio, lambda s: {"name": s}) or maybe(
        distributor, lambda s: {"name": s}
    )

    print(json.dumps(cleandict(scraped)))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser("IAFD Scraper")
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")

    search_parser = subparsers.add_parser("search", help="Search for performers")
    search_parser.add_argument("name", nargs="*", help="Name to search for", default="")

    performer_parser = subparsers.add_parser("performer", help="Scrape a performer")
    performer_parser.add_argument("url", nargs="?", help="Performer URL", default="")

    movie_scraper = subparsers.add_parser("movie", help="Scrape a movie")
    movie_scraper.add_argument("url", nargs="?", help="Movie URL", default="")

    scene_scraper = subparsers.add_parser("scene", help="Scrape a scene")
    scene_scraper.add_argument("url", nargs="?", help="Scene URL", default="")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    name = url = None
    # Script is being piped into, probably by Stash
    if not sys.stdin.isatty():
        try:
            frag = json.load(sys.stdin)
            url = frag.get("url")
            name = frag.get("name")
        except json.decoder.JSONDecodeError:
            log.error("Invalid JSON")
            sys.exit(1)

    if args.operation == "search":
        name = name or " ".join(args.name)
        if not name:
            log.error("No query provided")
            sys.exit(1)
        log.debug(f"Searching for '{name}'")
        performer_query(name)
        sys.exit(0)

    url = url or args.url
    if not url:
        log.error("No URL provided")
        sys.exit(1)

    log.debug(f"{args.operation} scraping '{url}'")
    scraped = scrape(url)
    if args.operation == "performer":
        performer_from_tree(scraped)
    elif args.operation == "movie":
        movie_from_tree(scraped)
    elif args.operation == "scene":
        scene_from_tree(scraped)


if __name__ == "__main__":
    main()
