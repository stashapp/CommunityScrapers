import base64
import json
import sys
import os
import re
import subprocess
import importlib

# The subdirectory for extra packages that might not be present
deps_dir = os.path.join(os.path.dirname(__file__), 'deps')
os.makedirs(deps_dir, exist_ok=True)

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(parent)  # add parent dir to sys path so that we can import py_common from ther

# dynamic deps
if deps_dir not in sys.path:
    sys.path.insert(0, deps_dir
)

try:
    from py_common import log
except ModuleNotFoundError:
    log.info(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

def ensure_package(requirement_string, import_name=None):
    name = import_name or requirement_string.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].strip()
    try:
        importlib.import_module(name)
    except ImportError:
        log.info(f"Installing {requirement_string} into {deps_dir}...")
        subprocess.check_call(
    [
        sys.executable,
        "-m", "pip", "install",
        requirement_string,
        "--target", deps_dir
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

ensure_package("requests")
ensure_package("bs4")
ensure_package("googletrans==4.0.0rc1")

import requests
from googletrans import Translator
from bs4 import BeautifulSoup


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

def smart_title(s):
    return " ".join(word.capitalize() for word in s.split(" "))

def load_translations_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            if os.path.getsize(cache_file) == 0:
                log.info("Cache file is empty. Starting with empty cache.")
                return {}
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError) as e:
            log.info(f"Cache file invalid: {e}. Starting with empty cache.")
            return {}
    return {}

def translate_text(input_list):
    cache_file = "translation_cache.json"
    cache = load_translations_cache(cache_file)

    translator = Translator()
    output_list = []

    for text in input_list:
        key = str(text)
        if key in cache:
            translated = cache[key]
        else:
            try:
                result = translator.translate(key, src='ja', dest='en')
                translated = result.text
                cache[key] = translated
            except Exception as e:
                log.info(f"Translation error for '{key}': {e}")
                translated = ""
        output_list.append(translated)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    return output_list

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
        scene_title = self.soup.find("div", {"class": "pagetitle"})
        scene_title = smart_title(scene_title.text.strip())
        if self.multipart:
            scene_title = scene_title + f" - Part {self.partnum}"
        
        return scene_title

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
                if perf:
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
            search = re.search(r"(\d{4})/(\d{2})/(\d{2})", dd.text)
            if search:
                date = f"{search[1]}-{search[2]}-{search[3]}"
                return date
        return None

    def get_tags(self):
        potential_tags = self.soup.find("div", {"class": "infowrapper"}).find_all("a")
        tag_tags_raw = [
            a.text for a in potential_tags if "type=tag" in a.get("href")
        ]
        play_tags = [
            a.text for a in potential_tags if "type=play" in a.get("href")
        ]
        translated_tags = translate_text(tag_tags_raw)
        
        combined = play_tags + translated_tags
        formatted = {smart_title(item) for item in combined}

        return [
            {"Name": a} for a in sorted(formatted)
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
        try:
            model_name = self.model_soup.find("div", {"class": "pagetitle mb0"})
            if model_name:
                name = model_name.text.strip()
        except:
            pass
        return name

    def get_height(self):
        height = None
        try:
            info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
            info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
            info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))
    
            if info_dict.get("Height"):
                parse_data = re.search(r"(\d{3})cm\s~\s(\d{3})cm", info_dict.get("Height"))
                if parse_data:
                    data = (int(parse_data[1]) + int(parse_data[2])) / 2
                    return str(data)
        except:
            pass
        return height

    def get_weight(self):
        weight = None
        try:
            info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
            info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
            info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))
            if info_dict.get("Weight"):
                parse_data = re.search(
                    r"(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Weight")
                )
                if parse_data:
                    data = (int(parse_data[1]) + int(parse_data[2])) / 2
                    return str(data)
        except:
            pass
        return weight

    def get_measurements(self):
        measurements = None
        try:
            info_dt = self.model_soup.find("dl", {"class": "info"}).find_all("dt")
            info_dd = self.model_soup.find("dl", {"class": "info"}).find_all("dd")
            info_dict = dict(map(lambda k, v: (k.text, v.text), info_dt, info_dd))
    
            cup = None
            bust = None
            waist = None
            hip = None
    
            if info_dict.get("Cup Size"):
                parse_cup = re.search(r"^(\w)", info_dict.get("Cup Size"))
                if parse_cup:
                    cup = JAP_TO_US_BUST.get(parse_cup[1].strip())
    
            if info_dict.get("Bust Size"):
                parse_bust = re.search(
                    r"(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Bust Size")
                )
                if parse_bust:
                    bust = round(((int(parse_bust[1]) + int(parse_bust[2])) / 2) * 0.393701)
    
            if info_dict.get("Waist Size"):
                parse_waist = re.search(
                    r"(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Waist Size")
                )
                if parse_waist:
                    waist = round(
                        ((int(parse_waist[1]) + int(parse_waist[2])) / 2) * 0.393701
                    )
    
            if info_dict.get("Hip"):
                parse_hip = re.search(r"(\d{2,3})cm\s~\s(\d{2,3})cm", info_dict.get("Hip"))
                if parse_hip:
                    hip = round(((int(parse_hip[1]) + int(parse_hip[2])) / 2) * 0.393701)
    
            if cup and bust and waist and hip:
                return f"{bust}{cup}-{waist}-{hip}"
        except:
            pass
        return measurements

    def get_images(self):
        try:
            model_url = (
                self.model_soup.find("div", {"id": "profile"}).find("img").get("src")
            )
            return [get_image(model_url)]
        except:
            return None

    def get_json(self):
        if self.model_name: 
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
        else:
            return None

def query(fragment, query_type):
    res = None
    media_info = None
    
    file_name = fragment['files'][0]['path'].split('/')[-1]

    log.info("/path/example/file.mp4".split('/')[-1])
    log.info("file.mp4".split('/')[-1])

    if query_type in ("scene"):
        name = re.sub(r"\s", "_", file_name).lower()       
        media_info = _extract_media_id(name)

        if not media_info:
            name = re.sub(r"\s", "_", fragment["code"]).lower()
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
