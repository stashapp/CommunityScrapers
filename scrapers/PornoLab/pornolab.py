import json
import re
import sys
from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedMovie, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("bs4:beautifulsoup4", "requests")

from bs4 import BeautifulSoup, Tag
import requests


#Headers for Requests
scrape_headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

pornolab_domain = "pornolab.net"


class Parser:

    def __init__(self, text):
        self.soup = BeautifulSoup(text, "html.parser")

        self.data = self.soup.find('div', class_='post-user-message')
        if self.data:
            # Remove spoilers
            for div in self.data.find_all('div', class_='sp-wrap'):
                div.decompose()
            # Remove HRs
            for span in self.data.find_all('span', class_='post-hr'):
                span.decompose()

    def get_field_text(self, tag, titles):
        for title in titles:
            if tag.text == title or tag.text == f"{title}:":
                value_text = ""
                if tag.nextSibling:
                    value_text = tag.nextSibling.text
                for sibling in tag.find_next_siblings():
                    if sibling.name == "span" and 'class' in sibling.attrs and "post-b" in sibling['class']:
                        break
                    if sibling.name == "span" and 'class' in sibling.attrs and "post-br" in sibling['class']:
                        break
                    value_text += sibling.text
                value_text = value_text.strip()
                if len(value_text) > 1 and value_text[0] == ':':
                    return value_text[1:].strip()
                if value_text and tag.text[-1] == ':':
                    return value_text

                if tag.next:
                    if tag.next.next:
                        value_text = tag.next.next.text.strip()
                        if value_text and value_text != ':':
                            return value_text
                        if tag.next.next.next:
                            value_text = tag.next.next.next.text.strip()
                            if value_text:
                                return value_text

        return ""

    def get_title(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            title = self.get_field_text(post_b, ["Название ролика"])
            title = re.sub(r"\[.*?\]", "", title)
            title = re.sub(r"\(.*?\)", "", title)
            title = re.sub(r"/.*", "", title)
            title = title.strip()
            if title:
                return title

        post_aligns = self.data.find_all('div', class_='post-align')
        if post_aligns:
            span = post_aligns[0].find('span')
            if span:
                title = span.text.split('\n')[0]
                title = re.sub(r"\[.*?\]", "", title)
                title = re.sub(r"\(.*?\)", "", title)
                title = re.sub(r"/.*", "", title)
                title = title.strip()
                if title:
                    return title
        else:
            span = self.data.find('span')
            title = span.text.strip()
            title = re.sub(r"\[.*?\]", "", title)
            title = re.sub(r"\(.*?\)", "", title)
            #title = re.sub(r"/.*", "", title)
            title = title.strip()
            if title:
                return title

        header_tag = self.soup.find('h1', class_='maintitle')
        if header_tag:
            title = header_tag.text
            title = re.sub(r"\[.*?\]", "", title)
            title = re.sub(r"\(.*?\)", "", title)
            title = re.sub(r"/.*", "", title)
            title = title.strip()
            if title:
                return title

        return ""

    def get_details(self):
        started = False
        details = ""
        for element in self.data.descendants:
            if isinstance(element, Tag):
                tag = element
                if tag.name == "span" and 'class' in tag.attrs and "post-b" in tag['class']:
                    if tag.text.startswith("Описание"):
                        started = True
                    elif started:
                        break
                if tag.name == "span" and 'class' in tag.attrs and "post-br" in tag['class']:
                    if started:
                        break
            else:
                if started:
                    if element.startswith("Описание"):
                        continue
                    details += element

        details = details.strip()
        if len(details) > 0 and details[0] == ':':
            details = details[1:].strip()
        if details:
            return details

        return ""

    def get_date(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            date = self.get_field_text(post_b, ("Год производства", "Год выпуска", "Охваченный временной промежуток"))
            if date:
                date = date.replace('г.', '').replace('г', '').replace('|', '').strip()
                return date

        return ""

    def get_duration(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            duration = self.get_field_text(post_b, ["Продолжительность"])
            if duration:
                return duration

        return ""

    def get_studio(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            studio = self.get_field_text(post_b, ["Студия"])
            if studio:
                return ScrapedStudio(name=studio)

        return ""

    def get_code(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            code = self.get_field_text(post_b, ["Студийный код фильма"])
            if code:
                return code

        return ""

    def get_director(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            director = self.get_field_text(post_b, ["Режиссер"])
            if director:
                return director

        return ""

    def get_urls(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            url = self.get_field_text(post_b, ["Подсайт и сайт"])
            if url:
                if not url.startswith("http"):
                    url = f"https://{url}"
                return [url,]

        return ""

    def get_tags(self):
        scraped_tags = []
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            tags = self.get_field_text(post_b, ["Жанр"])
            if tags:
                for tag in tags.split(','):
                    tag = tag.strip()
                    if tag:
                        scraped_tags.append(ScrapedTag(name=tag))

        return scraped_tags

    def get_performers(self):
        split_performers_pattern = re.compile(r"[,&](?=[^()]*(?:\(|$))")
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            performers = self.get_field_text(post_b, ["В ролях"])
            if performers:
                performers = re.split(r"[,&](?=[^()]*(?:\(|$))", performers)
                scraped_performers = []
                for performer in performers:
                    aliases = re.search(r"\((.*?)\)", performer)
                    performer = re.sub(r"\(.*?\)", "", performer)
                    if aliases:
                        aliases = aliases.group(1).split(',')
                        aliases = [alias.strip() for alias in aliases]
                        scraped_performers.append(ScrapedPerformer(name=performer.strip(), aliases=aliases))
                    else:
                        scraped_performers.append(ScrapedPerformer(name=performer.strip()))

                return scraped_performers

            performers = self.get_field_text(post_b, ["Имя актрисы"])
            if performers:
                performers = re.split(r"[,&](?=[^()]*(?:\(|$))", performers)
                scraped_performers = []
                for performer in performers:
                    aliases = re.search(r"\((.*?)\)", performer)
                    performer = re.sub(r"\(.*?\)", "", performer)
                    if aliases:
                        aliases = aliases.group(1)
                        scraped_performers.append(ScrapedPerformer(name=performer.strip(), gender="FEMALE", aliases=aliases))
                    else:
                        scraped_performers.append(ScrapedPerformer(name=performer.strip(), gender="FEMALE"))

                return scraped_performers

        return []

    def get_image(self):
        postImg = self.data.find('var', class_='postImg')
        if postImg:
            return postImg['title']

        return ""

    def is_valid(self):
        return bool(self.data)

    def parse_scene(self) -> ScrapedScene:
        scene: ScrapedScene = {}
        
        if title := self.get_title():
            scene["title"] = title

        if details := self.get_details():
            scene["details"] = details

#        if date := self.get_date():
#            scene["date"] = date

        if studio := self.get_studio():
            scene["studio"] = studio

        if code := self.get_code():
            scene["code"] = code

        if director := self.get_director():
            scene["director"] = director

        if urls := self.get_urls():
            scene["urls"] = urls

        if tags := self.get_tags():
            scene["tags"] = tags

        if performers := self.get_performers():
            scene["performers"] = performers

        if image := self.get_image():
            scene["image"] = image

        return scene

    def parse_movie(self) -> ScrapedMovie:
        movie: ScrapedMovie = {}
        
        if name := self.get_title():
            movie["name"] = name

#        if date := self.get_date():
#            movie["date"] = date

#        if duration := self.get_duration():
#            movie["duration"] = duration

        if synopsis := self.get_details():
            movie["synopsis"] = synopsis

        if studio := self.get_studio():
            movie["studio"] = studio

        if director := self.get_director():
            movie["director"] = director

        if front_image := self.get_image():
            movie["front_image"] = front_image

        return movie


def scene_from_url(url: str) -> ScrapedScene | None:
    #Scrape URL
    try:
        scrape = requests.get(url, headers=scrape_headers, timeout=10)
    except requests.RequestException as req_error:
        log.warning(f"Requests failed: {req_error}")
        sys.exit()

    #Check for valid response
    if scrape.status_code == 200:
        #Parse response
        parser = Parser(scrape.text)
        if parser.is_valid():
            scene = parser.parse_scene()
            if scene:
                scene["url"] = url
                movie = parser.parse_movie()
                if movie:
                    movie["url"] = url
                    scene["movies"] = [movie]
            return scene
        else:
            log.warning(f"Page format is invalid. Please check your URL.")
            return None
    else:
        log.warning(f"Response: {scrape.status_code}. Please check your URL.")
        sys.exit()


def scene_from_fragment(args: dict) -> ScrapedScene | None:
    if urls := args.get("urls"):
        for url in urls:
            if pornolab_domain in url:
                return scene_from_url(url)
    log.error("Cannot scrape scene without a URL")


def movie_from_url(url: str) -> ScrapedScene | None:
    #Scrape URL
    try:
        scrape = requests.get(url, headers=scrape_headers, timeout=10)
    except requests.RequestException as req_error:
        log.warning(f"Requests failed: {req_error}")
        sys.exit()

    #Check for valid response
    if scrape.status_code == 200:
        #Parse response
        parser = Parser(scrape.text)
        if parser.is_valid():
            movie = parser.parse_movie()
            movie["url"] = url
            return movie
        else:
            log.warning(f"Page format is invalid. Please check your URL.")
            return None
    else:
        log.warning(f"Response: {scrape.status_code}. Please check your URL.")
        sys.exit()


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-fragment", args:
            result = scene_from_fragment(args)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
