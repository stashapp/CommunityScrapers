import base64
import json
import sys
import os
import re


# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

BASE_QUERY_MEDIA_SEARCH = "https://my.tokyo-hot.com/product/?q="
BASE_DETAIL_URL = "https://my.tokyo-hot.com"

JAP_TO_US_BUST = {
    "A": "AA",
    "B": "A",
    "C": "B",
    "D": "C",
    "E": "D",
    "F": "DD",
    "G": "DDD",
    "H": "F",
    "I": "G",
    "J": "H",
    "K": "I",
}

MEDIA_CONFIGURATIONS = [
    ## must contain either 1 or 2 capture groups
    ## group 1 = the code
    ## group 2 (optional) = the part number if it's a multi-part (split) scene
    r"(n\d{4})\D*_\D{2}(\d)\S*",  # "mult-part N series"
    r"(n\d{4})\S*",  # "single part N series"
    r"(k\d{4})\S*",  # "single part K series"
    r"(kb\d{4})\S*",  # "single part KB series"
]

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
        file=sys.stderr,
    )
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print(
        "You need to install the Beautiful Soup module. (https://pypi.org/project/beautifulsoup4/)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4",
        file=sys.stderr,
    )
    sys.exit()


class ScenePage:
    def __init__(self, scene_id, multipart, partnum, url):
        self.url = url
        self.soup = _soup_maker(self.url)
        self.scene_id = scene_id
        self.multipart = multipart
        self.partnum = partnum
        self.title = self.get_title()
        self.studio = self.get_studio()
        self.image = self.get_image()
        self.details = self.get_details()
        self.performers = self.get_performers()
        self.date = self.get_date()
        self.tags = self.get_tags()

    def get_title(self):
        title = self.scene_id
        if self.multipart:
            title = title + f" - Part {self.partnum}"
        scene_title = self.soup.find("div", {"class": "pagetitle"})
        if scene_title:
            title = title + " - " + scene_title.text.strip()
        return title

    def get_studio(self):
        info = self.soup.find("div", {"class": "infowrapper"})
        info_links = info.find_all("a")
        for link in info_links:
            if "vendor" in link.get("href"):
                return link.text
        return None

    def get_image(self):
        info = self.soup.find("video")
        if info:
            return get_image(info.get("poster"))
        return None

    def get_performers(self):
        performers = []
        info = self.soup.find("div", {"class": "infowrapper"})
        info_links = info.find_all("a")
        for link in info_links:
            if "cast" in link.get("href"):
                perf = TokyoHotModel(
                    model_url=BASE_DETAIL_URL + link.get("href")
                ).get_json()
                performers.append(perf)
        return performers

    def get_details(self):
        details = None
        scene_details = self.soup.find("div", {"class": "sentence"})
        if scene_details:
            details = scene_details.text.strip()
        return details

    def get_date(self):
        log.info("Invoking self date")
        info_dd = self.soup.find("div", {"class": "infowrapper"}).find_all("dd")
        for dd in info_dd:
            search = re.search("(\d{4})/(\d{2})/(\d{2})", dd.text)
            if search:
                date = f"{search[1]}-{search[2]}-{search[3]}"
                return date
        return None

    def get_tags(self):
        potential_tags = self.soup.find("div", {"class": "infowrapper"}).find_all("a")
        return [
            {"Name": a.text} for a in potential_tags if "type=play" in a.get("href")
        ]

    def get_json(self):
        return {
            "Title": self.title,
            "Details": self.details,
            "URL": self.url,
            "Date": self.date,
            "Performers": self.performers,
            "Studio": {"Name": self.studio},
            "Code": self.scene_id,
            "Image": self.image,
            "Tags": self.tags,
        }


class TokyoHotModel:
    def __init__(self, model_url):
        self.url = model_url
        self.model_soup = _soup_maker(self.url)
        self.model_name = self.get_name()
        self.height = self.get_height()
        self.weight = self.get_weight()
        self.measurements = self.get_measurements()
        self.images = self.get_images()
        self.gender = "Female"
        self.ethnicity = "Asian"
        self.country = "JP"

    def get_name(self):
        name = None
        model_name = self.model_soup.find("div", {"class": "pagetitle mb0"})
        if model_name:
            name = model_name.text.strip()
        return name

    def get_height(self):
        info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
        info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
        info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))

        if info_dict.get("Height"):
            parse_data = re.search("(\d{3})cm\s~\s(\d{3})cm", info_dict.get("Height"))
            if parse_data:
                data = (int(parse_data[1]) + int(parse_data[2])) / 2
                return str(data)
        return None

    def get_weight(self):
        info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
        info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
        info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))
        if info_dict.get("Weight"):
            parse_data = re.search(
                "(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Weight")
            )
            if parse_data:
                data = (int(parse_data[1]) + int(parse_data[2])) / 2
                return str(data)
        return None

    def get_measurements(self):
        info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
        info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
        info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))

        cup = None
        bust = None
        waist = None
        hip = None

        if info_dict.get("Cup Size"):
            parse_cup = re.search("^(\w)", info_dict.get("Cup Size"))
            if parse_cup:
                cup = JAP_TO_US_BUST.get(parse_cup[1].strip())

        if info_dict.get("Bust Size"):
            parse_bust = re.search(
                "(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Bust Size")
            )
            if parse_bust:
                bust = round(((int(parse_bust[1]) + int(parse_bust[2])) / 2) * 0.393701)

        if info_dict.get("Waist Size"):
            parse_waist = re.search(
                "(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Waist Size")
            )
            if parse_waist:
                waist = round(
                    ((int(parse_waist[1]) + int(parse_waist[2])) / 2) * 0.393701
                )

        if info_dict.get("Hip"):
            parse_hip = re.search("(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Hip"))
            if parse_hip:
                hip = round(((int(parse_hip[1]) + int(parse_hip[2])) / 2) * 0.393701)

        if cup and bust and waist and hip:
            return f"{bust}{cup}-{waist}-{hip}"

        return None

    def get_images(self):
        try:
            model_url = (
                self.model_soup.find("div", {"id": "profile"}).find("img").get("src")
            )
            return [get_image(model_url)]
        except:
            return None

    def get_json(self):
        return {
            "Name": self.model_name,
            "Gender": self.gender,
            "URL": self.url,
            "Ethnicity": self.ethnicity,
            "Country": self.country,
            "Height": self.height,
            "Weight": self.weight,
            "Measurements": self.measurements,
            "Images": self.images,
        }


def query(fragment, query_type):
    res = None
    media_info = None

    if query_type in ("scene"):
        name = re.sub(r"\s", "_", fragment["title"]).lower()
        media_info = _extract_media_id(name)

    if media_info:
        res = scrape_scene(
            name=media_info["code"],
            multipart=media_info["multipart"],
            partnum=media_info["partnum"],
        )

    return res


def _soup_maker(url: str):
    requests.packages.urllib3.disable_warnings()
    try:
        html = requests.get(url, verify=False)
        soup = BeautifulSoup(html.text, "html.parser")
    except Exception as e:
        log.error("Error retrieving specified URL")
        raise e
    return soup


def _parse_media_search(soup):
    detail_page_url = None
    detail_object = soup.find("a", {"class": "rm"})
    if detail_object:
        detail_page_url = BASE_DETAIL_URL + detail_object.get("href")
        log.info(f"Scene URL found: {detail_page_url}")
    return detail_page_url


def _extract_media_id(media_title: str, configuration: dict = MEDIA_CONFIGURATIONS):
    log.info(f"Extracting Media ID for {media_title}")

    def _extract_multi_part(search_results):
        if len(search_results.groups()) > 1:
            return (True, search_results[2])
        return (False, False)

    for config in configuration:
        search = re.search(pattern=config, string=media_title)
        if search:
            scene_info = {
                "code": search[1],
                "multipart": _extract_multi_part(search)[0],
                "partnum": _extract_multi_part(search)[1],
            }
            log.info(f"Regex matched. Details {scene_info}")
            return scene_info
    return None


def scrape_scene(name, multipart, partnum):
    search_soup = _soup_maker(BASE_QUERY_MEDIA_SEARCH + name)
    scene_url = _parse_media_search(soup=search_soup)
    if scene_url is None:
        log.info(f"Scene not found: {name}. Try another server region, e.g. Hong Kong")
        return None
    scene_page = ScenePage(
        scene_id=name, multipart=multipart, partnum=partnum, url=scene_url
    )
    response = scene_page.get_json()
    return response


def get_image(image_url):
    try:
        response = requests.get(image_url, verify=False, timeout=(3, 6))
    except requests.exceptions.RequestException:
        log.error(f"Error fetching URL {image_url}")

    if response.status_code < 400:
        mime = "image/jpeg"
        encoded = base64.b64encode(response.content).decode("utf-8")
        return f"data:{mime};base64,{encoded}"

    log.info(f"Fetching {image_url} resulted in error: {response.status_code}")
    return None


def main():
    scraper_input = sys.stdin.read()
    i = json.loads(scraper_input)
    ret = {}
    if sys.argv[1] == "query":
        ret = query(i, sys.argv[2])
    output = json.dumps(ret)
    print(output)


main()
