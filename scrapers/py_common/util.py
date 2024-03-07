from argparse import ArgumentParser
from functools import reduce
from typing import Any, Callable, TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen
import json
import sys


def dig(c: dict | list, *keys: str | int | tuple[str | int, ...], default=None) -> Any:
    """
    Helper function to get a value from a nested dict or list

    If a key is a tuple the items will be tried in order until a value is found

    :param c: dict or list to search
    :param keys: keys to search for
    :param default: default value to return if not found
    :return: value if found, None otherwise

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> dig(obj, "a", "b", 1)
    'd'
    >>> dig(obj, "a", ("e", "f"), "g")
    'h'
    """

    def inner(d: dict | list, key: str | int | tuple):
        if isinstance(d, dict):
            if isinstance(key, tuple):
                for k in key:
                    if k in d:
                        return d[k]
            return d.get(key)
        elif isinstance(d, list) and isinstance(key, int) and key < len(d):
            return d[key]
        else:
            return default

    return reduce(inner, keys, c)  # type: ignore


T = TypeVar("T")


def replace_all(obj: dict, key: str, replacement: Callable[[T], T]) -> dict:
    """
    Helper function to recursively replace values in a nested dict, returning a new dict

    If the key refers to a list the replacement function will be called for each item

    :param obj: dict to search
    :param key: key to search for
    :param replacement: function called on the value to replace it
    :return: new dict

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> replace(obj, "g", lambda x: x.upper()) # Replace a single item
    {'a': {'b': ['c', 'd'], 'f': {'g': 'H'}}}
    >>> replace(obj, "b", lambda x: x.upper()) # Replace all items in a list
    {'a': {'b': ['C', 'D'], 'f': {'g': 'h'}}}
    >>> replace(obj, "z", lambda x: x.upper()) # Do nothing if the key is not found
    {'a': {'b': ['c', 'd'], 'f': {'g': 'h'}}}
    """
    if not isinstance(obj, dict):
        return obj

    new = {}
    for k, v in obj.items():
        if k == key:
            if isinstance(v, list):
                new[k] = [replacement(x) for x in v]
            else:
                new[k] = replacement(v)
        elif isinstance(v, dict):
            new[k] = replace_all(v, key, replacement)
        elif isinstance(v, list):
            new[k] = [replace_all(x, key, replacement) for x in v]
        else:
            new[k] = v
    return new


def replace_at(obj: dict, *path: str, replacement: Callable[[T], T]) -> dict:
    """
    Helper function to replace a value at a given path in a nested dict, returning a new dict

    If the path refers to a list the replacement function will be called for each item

    If the path does not exist, the replacement function will not be called and the dict will be returned as-is

    :param obj: dict to search
    :param path: path to search for
    :param replacement: function called on the value to replace it
    :return: new dict

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> replace_at(obj, "a", "f", "g", replacement=lambda x: x.upper()) # Replace a single item
    {'a': {'b': ['c', 'd'], 'f': {'g': 'H'}}}
    >>> replace_at(obj, "a", "b", replacement=lambda x: x.upper()) # Replace all items in a list
    {'a': {'b': ['C', 'D'], 'f': {'g': 'h'}}}
    >>> replace_at(obj, "a", "z", "g", replacement=lambda x: x.upper()) # Broken path, do nothing
    {'a': {'b': ['c', 'd'], 'f': {'g': 'h'}}}
    """

    def inner(d: dict, *keys: str):
        match keys:
            case [k] if isinstance(d, dict) and k in d:
                if isinstance(d[k], list):
                    return {**d, k: [replacement(x) for x in d[k]]}
                return {**d, k: replacement(d[k])}
            case [k, *ks] if isinstance(d, dict) and k in d:
                return {**d, k: inner(d[k], *ks)}
            case _:
                return d

    return inner(obj, *path)  # type: ignore


def is_valid_url(url):
    """
    Checks if an URL is valid by making a HEAD request and ensuring the response code is 2xx
    """
    try:
        req = Request(url, method="HEAD")
        with urlopen(req) as response:
            return 200 <= response.getcode() < 300
    except URLError:
        return False


def __default_parser(**kwargs):
    parser = ArgumentParser(**kwargs)
    # Some scrapers can take extra arguments so we can
    # do rudimentary configuration in the YAML file
    parser.add_argument("extra", nargs="*")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    # "Scrape with..." and the subsequent search box
    subparsers.add_parser(
        "performer-by-name", help="Search for performers"
    ).add_argument("--name", help="Performer name to search for")

    # The results of performer-by-name will be passed to this
    pbf = subparsers.add_parser("performer-by-fragment", help="Scrape a performer")
    # Technically there's more information in this fragment,
    # but in 99.9% of cases we only need the URL or the name
    pbf.add_argument("--url", help="Scene URL")
    pbf.add_argument("--name", help="Performer name to search for")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "performer-by-url", help="Scrape a performer by their URL"
    ).add_argument("--url")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "movie-by-url", help="Scrape a movie by its URL"
    ).add_argument("--url")

    # The looking glass search icon
    # name field is guaranteed to be filled by Stash
    subparsers.add_parser("scene-by-name", help="Scrape a scene by name").add_argument(
        "--name", help="Name to search for"
    )

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "scene-by-url", help="Scrape a scene by its URL"
    ).add_argument("--url")

    # "Scrape with..."
    sbf = subparsers.add_parser("scene-by-fragment", help="Scrape a scene")
    sbf.add_argument("-u", "--url")
    sbf.add_argument("--id")
    sbf.add_argument("--title")  # Title will be filename if not set in Stash
    sbf.add_argument("--date")
    sbf.add_argument("--details")
    sbf.add_argument("--urls", nargs="+")

    # Tagger view or search box
    sbqf = subparsers.add_parser("scene-by-query-fragment", help="Scrape a scene")
    sbqf.add_argument("-u", "--url")
    sbqf.add_argument("--id")
    sbqf.add_argument("--title")  # Title will be filename if not set in Stash
    sbqf.add_argument("--code")
    sbqf.add_argument("--details")
    sbqf.add_argument("--director")
    sbqf.add_argument("--date")
    sbqf.add_argument("--urls", nargs="+")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "gallery-by-url", help="Scrape a gallery by its URL"
    ).add_argument("--url", help="Gallery URL")

    # "Scrape with..."
    gbf = subparsers.add_parser("gallery-by-fragment", help="Scrape a gallery")
    gbf.add_argument("-u", "--url")
    gbf.add_argument("--id")
    gbf.add_argument("--title")
    gbf.add_argument("--date")
    gbf.add_argument("--details")
    gbf.add_argument("--urls", nargs="+")

    return parser


def scraper_args(**kwargs):
    """
    Helper function to parse arguments for a scraper

    This allows scrapers to be called from the command line without
    piping JSON to stdin but also from Stash

    Returns a tuple of the operation and the parsed arguments: operation is one of
    - performer-by-name
    - performer-by-fragment
    - performer-by-url
    - movie-by-url
    - scene-by-name
    - scene-by-url
    - scene-by-fragment
    - scene-by-query-fragment
    - gallery-by-url
    - gallery-by-fragment

    A scraper can be configured to take extra arguments by adding them to the YAML file:
    ```yaml
    sceneByName:
      action: script
      script:
        - python
        - my-scraper.py
        - extra
        - args
        - scene-by-name
    ```

    When called from Stash through the above configuration this function would return:
    ```python
    ("scene-by-name", {"extra": ["extra", "args"], "name": "scene name"})
    ```
    """

    parser = __default_parser(**kwargs)
    args = vars(parser.parse_args())

    # If stdin is not connected to a TTY the script is being executed by Stash
    if not sys.stdin.isatty():
        try:
            stash_fragment = json.load(sys.stdin)
            args.update(stash_fragment)
        except json.decoder.JSONDecodeError:
            # This would only happen if Stash passed invalid JSON
            sys.exit(69)

    return args.pop("operation"), args


def guess_nationality(country: str) -> str:
    """
    Tries to guess the country from a string

    Returns the original string if no match is found
    """
    for c in country.split(","):
        c = c.strip().lower()
        if c in demonyms:
            return demonyms[c]
    return country


US_states = [
    "AK",
    "AL",
    "AR",
    "AZ",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MI",
    "MN",
    "MO",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VA",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
]

demonyms = {
    # https://en.wikipedia.org/wiki/List_of_adjectival_and_demonymic_forms_for_countries_and_nations
    "abkhaz": "Abkhazia",
    "abkhazian": "Abkhazia",
    "afghan": "Afghanistan",
    "african american": "USA",
    "albanian": "Albania",
    "algerian": "Algeria",
    "american samoan": "American Samoa",
    "american": "USA",
    "andorran": "Andorra",
    "angolan": "Angola",
    "anguillan": "Anguilla",
    "antarctic": "Antarctica",
    "antiguan": "Antigua and Barbuda",
    "argentine": "Argentina",
    "argentinian": "Argentina",
    "armenian": "Armenia",
    "aruban": "Aruba",
    "australian": "Australia",
    "austrian": "Austria",
    "azerbaijani": "Azerbaijan",
    "azeri": "Azerbaijan",
    "bahamian": "Bahamas",
    "bahraini": "Bahrain",
    "bangladeshi": "Bangladesh",
    "barbadian": "Barbados",
    "barbudan": "Antigua and Barbuda",
    "basotho": "Lesotho",
    "belarusian": "Belarus",
    "belgian": "Belgium",
    "belizean": "Belize",
    "beninese": "Benin",
    "beninois": "Benin",
    "bermudan": "Bermuda",
    "bermudian": "Bermuda",
    "bhutanese": "Bhutan",
    "biot": "British Indian Ocean Territory",
    "bissau-guinean": "Guinea-Bissau",
    "bolivian": "Bolivia",
    "bonaire": "Bonaire",
    "bonairean": "Bonaire",
    "bosnian": "Bosnia and Herzegovina",
    "botswanan": "Botswana",
    "bouvet island": "Bouvet Island",
    "brazilian": "Brazil",
    "british virgin island": "Virgin Islands, British",
    "british": "United Kingdom",
    "bruneian": "Brunei",
    "bulgarian": "Bulgaria",
    "burkinabé": "Burkina Faso",
    "burmese": "Burma",
    "burundian": "Burundi",
    "cabo verdean": "Cabo Verde",
    "cambodian": "Cambodia",
    "cameroonian": "Cameroon",
    "canadian": "Canada",
    "cantonese": "Hong Kong",
    "caymanian": "Cayman Islands",
    "central african": "Central African Republic",
    "chadian": "Chad",
    "channel island": "Guernsey",
    "chilean": "Chile",
    "chinese": "China",
    "christmas island": "Christmas Island",
    "cocos island": "Cocos (Keeling) Islands",
    "colombian": "Colombia",
    "comoran": "Comoros",
    "comorian": "Comoros",
    "congolese": "Congo",
    "cook island": "Cook Islands",
    "costa rican": "Costa Rica",
    "croatian": "Croatia",
    "cuban": "Cuba",
    "curaçaoan": "Curaçao",
    "cypriot": "Cyprus",
    "czech": "Czech Republic",
    "danish": "Denmark",
    "djiboutian": "Djibouti",
    "dominican": "Dominica",
    "dutch": "Netherlands",
    "ecuadorian": "Ecuador",
    "egyptian": "Egypt",
    "emirati": "United Arab Emirates",
    "emiri": "United Arab Emirates",
    "emirian": "United Arab Emirates",
    "english people": "England",
    "english": "England",
    "equatoguinean": "Equatorial Guinea",
    "equatorial guinean": "Equatorial Guinea",
    "eritrean": "Eritrea",
    "estonian": "Estonia",
    "ethiopian": "Ethiopia",
    "european": "European Union",
    "falkland island": "Falkland Islands",
    "faroese": "Faroe Islands",
    "fijian": "Fiji",
    "filipino": "Philippines",
    "finnish": "Finland",
    "formosan": "Taiwan",
    "french guianese": "French Guiana",
    "french polynesian": "French Polynesia",
    "french southern territories": "French Southern Territories",
    "french": "France",
    "futunan": "Wallis and Futuna",
    "gabonese": "Gabon",
    "gambian": "Gambia",
    "georgian": "Georgia",
    "german": "Germany",
    "ghanaian": "Ghana",
    "gibraltar": "Gibraltar",
    "greek": "Greece",
    "greenlandic": "Greenland",
    "grenadian": "Grenada",
    "guadeloupe": "Guadeloupe",
    "guamanian": "Guam",
    "guatemalan": "Guatemala",
    "guinean": "Guinea",
    "guyanese": "Guyana",
    "haitian": "Haiti",
    "heard island": "Heard Island and McDonald Islands",
    "hellenic": "Greece",
    "herzegovinian": "Bosnia and Herzegovina",
    "honduran": "Honduras",
    "hong kong": "Hong Kong",
    "hong konger": "Hong Kong",
    "hungarian": "Hungary",
    "icelandic": "Iceland",
    "indian": "India",
    "indonesian": "Indonesia",
    "iranian": "Iran",
    "iraqi": "Iraq",
    "irish": "Ireland",
    "israeli": "Israel",
    "israelite": "Israel",
    "italian": "Italy",
    "ivorian": "Ivory Coast",
    "jamaican": "Jamaica",
    "jan mayen": "Jan Mayen",
    "japanese": "Japan",
    "jordanian": "Jordan",
    "kazakh": "Kazakhstan",
    "kazakhstani": "Kazakhstan",
    "kenyan": "Kenya",
    "kirghiz": "Kyrgyzstan",
    "kirgiz": "Kyrgyzstan",
    "kiribati": "Kiribati",
    "korean": "South Korea",
    "kosovan": "Kosovo",
    "kosovar": "Kosovo",
    "kuwaiti": "Kuwait",
    "kyrgyz": "Kyrgyzstan",
    "kyrgyzstani": "Kyrgyzstan",
    "lao": "Lao People's Democratic Republic",
    "laotian": "Lao People's Democratic Republic",
    "latvian": "Latvia",
    "lebanese": "Lebanon",
    "lettish": "Latvia",
    "liberian": "Liberia",
    "libyan": "Libya",
    "liechtensteiner": "Liechtenstein",
    "lithuanian": "Lithuania",
    "luxembourg": "Luxembourg",
    "luxembourgish": "Luxembourg",
    "macanese": "Macau",
    "macedonian": "North Macedonia",
    "magyar": "Hungary",
    "mahoran": "Mayotte",
    "malagasy": "Madagascar",
    "malawian": "Malawi",
    "malaysian": "Malaysia",
    "maldivian": "Maldives",
    "malian": "Mali",
    "malinese": "Mali",
    "maltese": "Malta",
    "manx": "Isle of Man",
    "marshallese": "Marshall Islands",
    "martinican": "Martinique",
    "martiniquais": "Martinique",
    "mauritanian": "Mauritania",
    "mauritian": "Mauritius",
    "mcdonald islands": "Heard Island and McDonald Islands",
    "mexican": "Mexico",
    "moldovan": "Moldova",
    "monacan": "Monaco",
    "mongolian": "Mongolia",
    "montenegrin": "Montenegro",
    "montserratian": "Montserrat",
    "monégasque": "Monaco",
    "moroccan": "Morocco",
    "motswana": "Botswana",
    "mozambican": "Mozambique",
    "myanma": "Myanmar",
    "namibian": "Namibia",
    "nauruan": "Nauru",
    "nepalese": "Nepal",
    "nepali": "Nepal",
    "netherlandic": "Netherlands",
    "new caledonian": "New Caledonia",
    "new zealand": "New Zealand",
    "ni-vanuatu": "Vanuatu",
    "nicaraguan": "Nicaragua",
    "nigerian": "Nigeria",
    "nigerien": "Niger",
    "niuean": "Niue",
    "norfolk island": "Norfolk Island",
    "northern irish": "Northern Ireland",
    "northern marianan": "Northern Mariana Islands",
    "norwegian": "Norway",
    "omani": "Oman",
    "pakistani": "Pakistan",
    "palauan": "Palau",
    "palestinian": "Palestine",
    "panamanian": "Panama",
    "papua new guinean": "Papua New Guinea",
    "papuan": "Papua New Guinea",
    "paraguayan": "Paraguay",
    "persian": "Iran",
    "peruvian": "Peru",
    "philippine": "Philippines",
    "pitcairn island": "Pitcairn Islands",
    "polish": "Poland",
    "portuguese": "Portugal",
    "puerto rican": "Puerto Rico",
    "qatari": "Qatar",
    "romanian": "Romania",
    "russian": "Russia",
    "rwandan": "Rwanda",
    "saba": "Saba",
    "saban": "Saba",
    "sahraouian": "Western Sahara",
    "sahrawi": "Western Sahara",
    "sahrawian": "Western Sahara",
    "salvadoran": "El Salvador",
    "sammarinese": "San Marino",
    "samoan": "Samoa",
    "saudi arabian": "Saudi Arabia",
    "saudi": "Saudi Arabia",
    "scottish": "Scotland",
    "senegalese": "Senegal",
    "serbian": "Serbia",
    "seychellois": "Seychelles",
    "sierra leonean": "Sierra Leone",
    "singapore": "Singapore",
    "singaporean": "Singapore",
    "slovak": "Slovakia",
    "slovene": "Slovenia",
    "slovenian": "Slovenia",
    "solomon island": "Solomon Islands",
    "somali": "Somalia",
    "somalilander": "Somaliland",
    "south african": "South Africa",
    "south georgia island": "South Georgia and the South Sandwich Islands",
    "south ossetian": "South Ossetia",
    "south sandwich island": "South Georgia and the South Sandwich Islands",
    "south sudanese": "South Sudan",
    "spanish": "Spain",
    "sri lankan": "Sri Lanka",
    "sudanese": "Sudan",
    "surinamese": "Suriname",
    "svalbard resident": "Svalbard",
    "swati": "Eswatini",
    "swazi": "Eswatini",
    "swedish": "Sweden",
    "swiss": "Switzerland",
    "syrian": "Syrian Arab Republic",
    "taiwanese": "Taiwan",
    "tajikistani": "Tajikistan",
    "tanzanian": "Tanzania",
    "thai": "Thailand",
    "timorese": "Timor-Leste",
    "tobagonian": "Trinidad and Tobago",
    "togolese": "Togo",
    "tokelauan": "Tokelau",
    "tongan": "Tonga",
    "trinidadian": "Trinidad and Tobago",
    "tunisian": "Tunisia",
    "turkish": "Turkey",
    "turkmen": "Turkmenistan",
    "turks and caicos island": "Turks and Caicos Islands",
    "tuvaluan": "Tuvalu",
    "ugandan": "Uganda",
    "ukrainian": "Ukraine",
    "uruguayan": "Uruguay",
    "uzbek": "Uzbekistan",
    "uzbekistani": "Uzbekistan",
    "vanuatuan": "Vanuatu",
    "vatican": "Vatican City State",
    "venezuelan": "Venezuela",
    "vietnamese": "Vietnam",
    "wallis and futuna": "Wallis and Futuna",
    "wallisian": "Wallis and Futuna",
    "welsh": "Wales",
    "yemeni": "Yemen",
    "zambian": "Zambia",
    "zimbabwean": "Zimbabwe",
    "åland island": "Åland Islands",
    **{s.lower(): "USA" for s in US_states},
}
