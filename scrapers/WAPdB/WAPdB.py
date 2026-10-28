import json
import re
import sys
from datetime import datetime
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import is_own_url, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")
import requests  # noqa: E402
from bs4 import BeautifulSoup, Tag  # noqa: E402

BASE_URL = "http://warashi-asian-pornstars.fr"


def process_name(name: str) -> str:
    name_map = {"Ô": "ou", "ô": "ou", "û": "uu", "Û": "uu", "î": "ii", "Î": "ii"}
    for k, v in name_map.items():
        name = name.replace(k, v)
    return name.title()


def get_gender(url: str) -> str | None:
    if "female-pornstar" in url:
        return "FEMALE"
    if "male-pornstar" in url:
        return "MALE"
    return None


def scrape_performer(url: str) -> dict[str, Any] | None:
    resp = requests.get(url, timeout=30)
    if not resp.ok:
        log.error(f"HTTP {resp.status_code} for {url}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    if soup.find("div", {"id": "casting-profil-mini-infos"}):
        return scrape_mini_profile(soup, url)
    return scrape_full_profile(soup, url)


def after(soup: Tag, prefix: str) -> str | None:
    "Text following a 'label: ' prefix, None when missing or 'unknown'"
    if node := soup.find(string=lambda t: bool(t) and prefix in t):
        value = node.text.split(prefix)[1].strip()
        return None if value == "unknown" else value
    return None


def scrape_mini_profile(soup: BeautifulSoup, url: str) -> dict[str, Any] | None:
    if soup.find(
        string=lambda t: bool(t) and "pornstar is not yet in our database" in t
    ):
        log.error("Performer not in database")
        return None

    performer: dict[str, Any] = {"urls": [url]}
    if gender := get_gender(url):
        performer["gender"] = gender

    if profile := soup.find("div", {"id": "casting-profil-mini-infos"}):
        if alphabet_name := profile.find("meta", {"itemprop": "name"}):
            performer["name"] = process_name(str(alphabet_name.attrs["content"]))
        if additional_name := profile.find("meta", {"itemprop": "additionalName"}):
            performer["aliases"] = additional_name.attrs["content"]

    if details := soup.find("div", {"id": "casting-profil-mini-infos-details"}):
        if birthdate := after(details, "birthdate: "):
            performer["birthdate"] = datetime.strptime(birthdate, "%B %d, %Y").strftime(
                "%Y-%m-%d"
            )
        if birthplace := after(details, "birthplace: "):
            performer["country"] = birthplace.split(", ")[0]
        if measurements := after(details, "measurements: "):
            performer["measurements"] = measurements
        if height := after(details, "height: "):
            performer["height"] = height.split()[0]

    if (preview := soup.find("div", {"id": "casting-profil-preview"})) and (
        image := preview.find("img", {"itemprop": "image"})
    ):
        image_url = str(image.attrs["src"])
        if "/WAPdB-img/par-defaut/" not in image_url:
            performer["images"] = [f"{BASE_URL}{image_url}"]
    return performer


def scrape_full_profile(soup: BeautifulSoup, url: str) -> dict[str, Any]:
    alphabet_name = ""
    if name_node := soup.find("span", {"itemprop": "name"}):
        alphabet_name = name_node.text

    japanese_name = None
    if additional_name := soup.find("span", {"itemprop": "additionalName"}):
        japanese_name = additional_name.text

    performer: dict[str, Any] = {"name": process_name(alphabet_name), "urls": [url]}
    if gender := get_gender(url):
        performer["gender"] = gender
    if gender_node := soup.find("meta", {"property": "og:gender"}):
        performer["gender"] = str(gender_node.attrs["content"]).upper()
    if (twitter := soup.find(string="official Twitter")) and twitter.parent:
        performer["urls"].append(str(twitter.parent.attrs["href"]))
    if birthday_node := soup.find("time", {"itemprop": "birthDate"}):
        performer["birthdate"] = birthday_node.attrs["content"]
    if (height_node := soup.find("p", {"itemprop": "height"})) and (
        height := height_node.find("span", {"itemprop": "value"})
    ):
        performer["height"] = height.text
    if (weight_node := soup.find("p", {"itemprop": "weight"})) and (
        weight := weight_node.find("span", {"itemprop": "value"})
    ):
        performer["weight"] = weight.text
    if measurements := after(soup, "measurements: "):
        performer["measurements"] = measurements
    # "porn/AV activity: 2016 - 2021", or "2016 - present" while still active
    if activity := after(soup, "porn/AV activity: "):
        years = re.findall(r"\d{4}", activity)
        if years:
            performer["career_start"] = years[0]
        if len(years) > 1:
            performer["career_end"] = years[1]

    if (photos := soup.find("div", {"id": "pornostar-profil-photos-0"})) and (
        image := photos.find("img", {"itemprop": "image"})
    ):
        image_url = str(image.attrs["src"])
        if "/WAPdB-img/par-defaut/" not in image_url:
            performer["images"] = [f"{BASE_URL}{image_url}"]

    if len(country_nodes := soup.find_all("span", {"itemprop": "addressCountry"})) > 1:
        performer["country"] = country_nodes[1].text

    aliases = []
    if japanese_name:
        aliases.append(japanese_name)
    if alias_node := soup.find("div", {"id": "pornostar-profil-noms-alternatifs"}):
        for couple in alias_node.find_all("li"):
            alias = process_name(couple.text)
            if alias in (alphabet_name, str(japanese_name)) or alias in aliases:
                continue
            aliases.append(alias)
    performer["aliases"] = ", ".join(set(aliases))

    if tags_node := soup.find("p", {"class": "implode-tags"}):
        for tag in tags_node.find_all("a"):
            if tag.text == "breast augmentation":
                performer["fake_tits"] = "Y"
            if tag.text == "tatoos":
                performer["tattoos"] = "Y"
            if tag.text == "piercings":
                performer["piercings"] = "Y"

    if traits := soup.find(
        "p", string=lambda t: bool(t) and "distinctive physical characteristics" in t
    ):
        if "breast augmentation" in traits.text:
            performer["fake_tits"] = "Y"
        if "tattoo(s)" in traits.text:
            performer["tattoos"] = "Y"
        if "piercing(s)" in traits.text:
            performer["piercings"] = "Y"

    return performer


def search_performer(name: str) -> list[dict[str, Any]]:
    data = {"recherche_critere": "f", "recherche_valeur": name, "x": "20", "y": "17"}
    resp = requests.post(f"{BASE_URL}/en/s-12/search", data=data, timeout=30)
    if not resp.ok:
        log.error(f"HTTP {resp.status_code} for the search")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    # Exact matches come first
    entries = [
        *soup.find_all("div", {"class": "correspondance_exacte"}, limit=1),
        *soup.find_all("div", {"class": "resultat-pornostar"}),
    ]
    performers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if (match := entry.find("span", {"class": "correspondance-lien"})) and (
            link := match.parent
        ):
            name, href = link.text.strip(), link.attrs["href"]
        elif len(links := entry.find_all("a")) > 1:
            name, href = links[1].text.strip(), links[1].attrs["href"]
        else:
            continue
        if (url := f"{BASE_URL}{href}") not in seen:
            seen.add(url)
            performers.append({"name": process_name(name), "urls": [url]})
    return performers


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-name", {"name": name} if name:
            result = search_performer(name)
        case "performer-by-url", {"url": url} if url:
            result = scrape_performer(url)
        case "performer-by-fragment", args:
            result = next(
                (
                    performer
                    for url in args.get("urls") or []
                    if is_own_url(url) and (performer := scrape_performer(url))
                ),
                None,
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
