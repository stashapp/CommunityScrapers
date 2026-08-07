import json
import re
import random
import sys
from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedMovie, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("bs4:beautifulsoup4", "requests")

from bs4 import BeautifulSoup, Tag, NavigableString
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
                # Начально захватываем текст сразу после тега
                if tag.next_sibling:
                    node = tag.next_sibling
                    value_text = node.get_text() if isinstance(node, Tag) else str(node)
                else:
                    value_text = ""
                # Собираем текст от следующих siblings, пока не встретим маркер нового поля
                for sibling in tag.find_next_siblings():
                    if sibling.name == "span" and 'class' in sibling.attrs:
                        classes = sibling['class']
                        # останавливаемся на следующем поле (post-b), на переносе (post-br) или на других разделительных блоках (post-u)
                        if any(c in classes for c in ("post-b", "post-br", "post-u")):
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
        # Первый приоритет: <title>…</title>
        if self.soup.title and self.soup.title.string:
            raw = self.soup.title.string
            # отрезаем суффикс сайта
            raw = re.sub(r"::.*$", "", raw)
            # чистим от [..], (..) и всего после '/' или '|'
            title = re.sub(r"\[.*?\]", "", raw)
            title = re.sub(r"\(.*?\)", "", title)
            title = re.sub(r"[/|].*", "", title)
            title = title.strip()
            if title:
                return title

#        # Второй приоритет: <span class="post-b">
#        for post_b in self.data.find_all('span', class_='post-b'):
#            title = self.get_field_text(post_b, ["Название ролика"])
#            # Очищаем от [..], (..), и всего после /
#            title = re.sub(r"\[.*?\]", "", title)
#            title = re.sub(r"\(.*?\)", "", title)
#            title = re.sub(r"[/|].*", "", title)
#            title = title.strip()
#            if title:
#                return title
#
#        # Второй приоритет: <div class="post-align">
#        post_aligns = self.data.find_all('div', class_='post-align')
#        if post_aligns:
#            span = post_aligns[0].find('span')
#            if span:
#                title = span.text.split('\n')[0]
#                title = re.sub(r"\[.*?\]", "", title)
#                title = re.sub(r"\(.*?\)", "", title)
#                title = re.sub(r"[/|].*", "", title)
#                title = title.strip()
#                if title:
#                    return title
#        else:
#            # Фолбэк: первый попавшийся <span>
#            span = self.data.find('span')
#            if span:
#                title = span.get_text(strip=True)
#                title = re.sub(r"\[.*?\]", "", title)
#                title = re.sub(r"\(.*?\)", "", title)
#                title = re.sub(r"[/|].*", "", title)
#                title = title.strip()
#                if title:
#                    return title
#
#        # Третий приоритет: <h1 class="maintitle">
#        header_tag = self.soup.find('h1', class_='maintitle')
#        if header_tag:
#            title = header_tag.text
#            title = re.sub(r"\[.*?\]", "", title)
#            title = re.sub(r"\(.*?\)", "", title)
#            title = re.sub(r"[/|].*", "", title)
#            title = title.strip()
#            if title:
#                return title
#                
#        # Четвёртый фолбэк: <title>Assent Of A Woman / … :: PornoLab.Net</title>
#        if self.soup.title and self.soup.title.string:
#            title = self.soup.title.string
#            # убираем суффикс сайта
#            title = re.sub(r"::.*$", "", title)
#            # чистим от [..], (..) и всего после '/' или '|'
#            title = re.sub(r"\[.*?\]", "", title)
#            title = re.sub(r"\(.*?\)", "", title)
#            title = re.sub(r"[/|].*", "", title)
#            title = title.strip()
#            if title:
#                return title
#
        return ""

    def get_details(self):
       started = False
       details = ""
       for element in self.data.descendants:
           if isinstance(element, Tag):
               tag = element
               # нашли маркер начала описания
               if tag.name == "span" and 'class' in tag.attrs and "post-b" in tag['class']:
                   if tag.text.startswith("Описание"):
                       started = True
                       continue
                   # при встрече любого другого post-b после старта — выходим
                   elif started:
                       break
               # игнорируем post-br (можно вставлять "\n" вместо них)
               if tag.name == "span" and 'class' in tag.attrs and "post-br" in tag['class']:
                   if started:
                       details += "\n"
                   continue
           else:
               if started:
                   # пропускаем сам лейбл «Описание»
                   if element.startswith("Описание"):
                       continue
                   details += element

       details = details.strip()
       if details.startswith(':'):
           details = details[1:].strip()
       return details if details else ""

    def get_date(self):
        # 1) Основной способ: через get_field_text по span.post-b
        titles = ("Год производства", "Год выпуска", "Охваченный временной промежуток")
        for post_b in self.data.find_all('span', class_='post-b'):
            raw = self.get_field_text(post_b, titles)
            if raw:
                # убираем «г.», «г» и «|»
                clean = raw.replace('г.', '').replace('г', '').replace('|', '').strip()
                m = re.search(r"(\d{4})", clean)
                if m:
                    return f"{m.group(1)}-01-01"

        # 2) Фолбэк для структуры:
        #    <span class="post-color-text"><span class="post-b">Год выпуска</span>:</span>
        #    … 
        #    <span class="post-color-text">2012</span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if nested and nested.text in titles:
                # ищем следующий span.post-color-text с цифрами
                for sib in wrapper.find_next_siblings():
                    if isinstance(sib, Tag) and 'post-color-text' in sib.get('class', []):
                        raw2 = sib.get_text(strip=True)
                        clean2 = raw2.replace('г.', '').replace('г', '').replace('|', '').strip()
                        m2 = re.search(r"(\d{4})", clean2)
                        if m2:
                            return f"{m2.group(1)}-01-01"
                break

        # Если год так и не найден — возвращаем пустую строку
        return ""

    def get_duration(self):
        # 1) Стандартный способ: через get_field_text
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            duration = self.get_field_text(post_b, ["Продолжительность"])
            if duration:
                return duration.strip().rstrip('.')

        # 2) Фолбэк: структура вида
        #    <span class="post-color-text"><span class="post-b">Продолжительность</span>:</span>
        #    <span class="post-color-text">02:31:16.</span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if nested and nested.text.strip() == "Продолжительность":
                for sib in wrapper.find_next_siblings():
                    if isinstance(sib, Tag) and 'post-color-text' in sib.get('class', []):
                        dur = sib.get_text(strip=True)
                        # убираем финальную точку, если есть
                        return dur.rstrip('.')
                break

        # если не нашли ни одним способом — возвращаем пустую строку
        return ""

    def get_studio(self):
        # 1) Стандартный способ: через get_field_text по <span class="post-b">
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            studio = self.get_field_text(post_b, ["Студия"]).lstrip(':').strip()
            if studio:
                return ScrapedStudio(name=studio.strip().rstrip('.'))

        # 2) Фолбэк: структура вида
        #    <span class="post-color-text"><span class="post-b">Студия</span>:</span>
        #    <span class="post-color-text">Sweet Sinner.</span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if nested and nested.text.strip().startswith("Студия"):
                # ищем следующий <span class="post-color-text"> с именем студии
                for sib in wrapper.find_next_siblings():
                    if isinstance(sib, Tag) and 'post-color-text' in sib.get('class', []):
                        raw = sib.get_text().lstrip(':').strip()
                        name = raw.rstrip('.')
                        if name:
                            return ScrapedStudio(name=name)
                break

        # ничего не найдено
        return ""

    def get_code(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            code = self.get_field_text(post_b, ["Студийный код фильма"])
            if code:
                return code

        return ""

    def get_director(self):
        # 1) Стандартный способ: через get_field_text по <span class="post-b">Режиссер</span>
        for post_b in self.data.find_all('span', class_='post-b'):
            director = self.get_field_text(post_b, ["Режиссер"]).lstrip(':').strip()
            if director:
                return director.rstrip('.')

        # 2) Фолбэк: ищем после <span class="post-color-text"><span class="post-b">Режиссер</span></span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if nested and nested.text.strip() == "Режиссер":
                for sib in wrapper.find_next_siblings():
                    # пропускаем всё, что не post-color-text
                    if not (isinstance(sib, Tag) and 'post-color-text' in sib.get('class', [])):
                        continue
                    # если это новый лейбл — значит информации нет, выходим
                    if sib.find('span', class_='post-b'):
                        return ""
                    # иначе это значение режиссёра
                    raw = sib.get_text().lstrip(':').strip()
                    return raw.rstrip('.')
                # после метки не нашлось ни одного значения — сразу пусто
                return ""

        # ничего не нашли — возвращаем пустую строку
        return ""

    def get_urls(self):
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            url_raw = self.get_field_text(post_b, ["Подсайт и сайт"])
            if not url_raw:
                continue
            # разбиваем по слешу (учитываем возможные пробелы вокруг)
            parts = re.split(r"\s*/\s*", url_raw)
            urls = []
            for part in parts:
                u = part.strip()
                if not u:
                    continue
                # если нет протокола, добавляем https://
                if not re.match(r"^https?://", u, re.IGNORECASE):
                    u = f"https://{u}"
                urls.append(u)
            if urls:
                return urls
        # если не нашли ни одной — возвращаем пустой список
        return []

    def get_tags(self):
        scraped_tags = []
        # 1) Стандартный способ через get_field_text
        post_bs = self.data.find_all('span', class_='post-b')
        for post_b in post_bs:
            tags = self.get_field_text(post_b, ["Жанр"])
            if tags:
                for tag in tags.split(','):
                    t = tag.strip().rstrip('.')
                    if t:
                        scraped_tags.append(ScrapedTag(name=t))
        if scraped_tags:
            return scraped_tags

        # 2) Фолбэк: структура вида
        #    <span class="post-color-text"><span class="post-b">Жанр</span>:</span>
        #    <span class="post-color-text">Feature, All Sex, M.I.L.F.s.</span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if nested and nested.text.strip().startswith("Жанр"):
                # следующий span.post-color-text содержит сами жанры
                for sib in wrapper.find_next_siblings():
                    if isinstance(sib, Tag) and 'post-color-text' in sib.get('class', []):
                        raw = sib.get_text(strip=True)
                        for tag in raw.rstrip('.').split(','):
                            t = tag.strip()
                            if t:
                                scraped_tags.append(ScrapedTag(name=t))
                        return scraped_tags
                break

        return scraped_tags

    def get_performers(self):
        split_pattern = re.compile(r"[,&](?=[^()]*(?:\(|$))")

        # 1) Стандартный способ: через get_field_text по «В ролях» и «Имя актрисы»
        for post_b in self.data.find_all('span', class_='post-b'):
            # ветка «В ролях»
            raw = self.get_field_text(post_b, ["В ролях"])
            if raw:
                parts = split_pattern.split(raw)
                scraped = []
                for part in parts:
                    m = re.search(r"\((.*?)\)", part)
                    name = re.sub(r"\(.*?\)", "", part).strip().rstrip('.')
                    if m:
                        aliases = [a.strip() for a in m.group(1).split(',')]
                        scraped.append(ScrapedPerformer(name=name, aliases=", ".join(aliases)))
                    else:
                        scraped.append(ScrapedPerformer(name=name))
                return scraped

            # ветка «Имя актрисы»
            raw = self.get_field_text(post_b, ["Имя актрисы"])
            if raw:
                parts = split_pattern.split(raw)
                scraped = []
                for part in parts:
                    m = re.search(r"\((.*?)\)", part)
                    name = re.sub(r"\(.*?\)", "", part).strip().rstrip('.')
                    if m:
                        aliases = [a.strip() for a in m.group(1).split(',')]
                        scraped.append(ScrapedPerformer(name=name, gender="FEMALE", aliases=", ".join(aliases)))
                    else:
                        scraped.append(ScrapedPerformer(name=name, gender="FEMALE"))
                return scraped

        # 2) Фолбэк: после <span.post-color-text><span.post-b>В ролях</span></span>
        for wrapper in self.data.find_all('span', class_='post-color-text'):
            nested = wrapper.find('span', class_='post-b')
            if not (nested and nested.text.strip() == "В ролях"):
                continue
            # проходим все следующие узлы
            for sib in wrapper.next_siblings:
                # пропускаем тег <br>
                if isinstance(sib, Tag) and sib.name == 'br':
                    continue
                # пропускаем одиночный «:»
                if isinstance(sib, NavigableString):
                    text = sib.strip()
                    if not text or text == ':':
                        continue
                    raw = text
                # если список в <span class="post-color-text">
                elif isinstance(sib, Tag) and 'post-color-text' in sib.get('class', []):
                    raw = sib.get_text(strip=True)
                    if not raw or raw == ':':
                        continue
                else:
                    continue
                # мы получили строку актёров — разбираем
                parts = split_pattern.split(raw.rstrip('.'))
                scraped = []
                for part in parts:
                    m = re.search(r"\((.*?)\)", part)
                    name = re.sub(r"\(.*?\)", "", part).strip()
                    if m:
                        aliases = [a.strip() for a in m.group(1).split(',')]
                        scraped.append(ScrapedPerformer(name=name, aliases=", ".join(aliases)))
                    else:
                        scraped.append(ScrapedPerformer(name=name))
                return scraped
            # если после «В ролях» не нашлось ничего кроме «:» и <br> — возвращаем пустой список
            return []

    def get_image(self):
        # Собираем три группы кандидатов
        left_imgs = self.data.find_all(
            'var', class_=lambda c: c and 'postImg' in c and 'img-left' in c
        )
        right_imgs = [
            v for v in self.data.find_all(
                'var', class_=lambda c: c and 'postImg' in c and 'img-right' in c
            ) if v not in left_imgs
        ]
        generic_imgs = [
            v for v in self.data.find_all(
                'var', class_=lambda c: c and 'postImg' in c
            ) if v not in left_imgs + right_imgs
        ]

        # Если нет ни img-left, ни img-right — перемешиваем generic и берём их в случайном порядке
        if not left_imgs and not right_imgs and generic_imgs:
            random.shuffle(generic_imgs)

        candidates = left_imgs + right_imgs + generic_imgs
        
        # Если на странице есть блок года — фильтруем изображения, оставляя только те, что идут выше него
        marker = None
        for post_b in self.data.find_all('span', class_='post-b'):
            if post_b.text.strip() in ("Год производства", "Год выпуска"):
                marker = post_b
                break
        if marker:
            # все <var class="postImg">, идущие ДО этого маркера
            prev_imgs = marker.find_all_previous(
                'var',
                class_=lambda c: c and 'postImg' in c
            )
            if prev_imgs:
                candidates = [v for v in candidates if v in prev_imgs]

        # Перебираем кандидатов и возвращаем первую «живую» картинку
        for postImg in candidates:
            url = postImg.get('title', '').strip()
            
         # Пропускаем GIF-файлы
            if url.lower().endswith('.gif'):
                continue
            
            if not url:
                continue

            try:
                resp = requests.head(
                    url,
                    headers=scrape_headers,
                    timeout=3,
                    allow_redirects=True
                )
            except requests.exceptions.Timeout:
                # Считаем таймаут не признаком мёртвой ссылки
                return url
            except requests.RequestException as e:
                log.warning(f"Cannot reach image {url}: {e}, skipping to next.")
                continue

            if resp.status_code == 200:
                return url
            else:
                log.warning(f"Image URL returned {resp.status_code}, skipping to next.")
                continue

        # Если ни один кандидат не годится
        return ""

    def is_valid(self):
        return bool(self.data)

    def parse_scene(self) -> ScrapedScene:
        scene: ScrapedScene = {}
        
        if title := self.get_title():
            scene["title"] = title

        if details := self.get_details():
            scene["details"] = details

        if date := self.get_date():
            scene["date"] = date

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

        if date := self.get_date():
            movie["date"] = date

        if duration := self.get_duration():
            movie["duration"] = duration

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
