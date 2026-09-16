import configparser
import json
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "..")
from py_common import log
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SHEER_BASE = "https://www.sheer.com"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.ini")

DEFAULT_CONFIG = """[Sheer]
# Paste your cookie string here.
# In Chrome/Firefox: F12 -> Network -> any sheer.com request -> Headers -> Cookie
cookie =
"""


def get_cookies():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            f.write(DEFAULT_CONFIG)
        log.info(f"Created config.ini at {CONFIG_FILE} - add your cookie string to scrape authenticated content")
        return {}

    config = configparser.RawConfigParser()
    config.read(CONFIG_FILE)
    cookie_str = config.get("Sheer", "cookie", fallback="").strip()
    if not cookie_str:
        log.warning("No cookie set in config.ini - scraping logged-out content only")
        return {}

    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookies[name.strip()] = value.strip()
    return cookies


def fetch(url):
    cookies = get_cookies()
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        cookies=cookies,
        timeout=15,
    )
    if r.status_code != 200:
        log.error(f"HTTP {r.status_code} for {url}")
        sys.exit(1)
    return r.text


def parse_relative_date(text):
    text = text.strip().lower()
    now = datetime.now()

    m = re.match(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        deltas = {
            "second": timedelta(seconds=n),
            "minute": timedelta(minutes=n),
            "hour":   timedelta(hours=n),
            "day":    timedelta(days=n),
            "week":   timedelta(weeks=n),
            "month":  timedelta(days=n * 30),
            "year":   timedelta(days=n * 365),
        }
        return (now - deltas.get(unit, timedelta(0))).strftime("%Y-%m-%d")

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%b. %d, %Y",
                "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    for fmt in ("%b %d", "%B %d", "%d %b", "%d %B"):
        try:
            d = datetime.strptime(text, fmt)
            return d.replace(year=now.year).strftime("%Y-%m-%d")
        except ValueError:
            pass

    log.warning(f"Could not parse date: {text!r}")
    return None


def parse_post(html, post_url):
    soup = BeautifulSoup(html, "html.parser")
    scrape = {}

    # Scope to the specific post article
    post_id = post_url.rstrip("/").split("/")[-1]
    article = soup.find("article", {"data-post-id": post_id}) or soup.find("article")

    ctx = article if article else soup

    # Title
    el = ctx.select_one("h3.post__title")
    if el:
        scrape["title"] = el.get_text(strip=True)
    else:
        og = soup.find("meta", property="og:title")
        if og:
            scrape["title"] = og.get("content", "").strip()

    # Date
    time_el = soup.find("time")
    if time_el and time_el.get("datetime"):
        scrape["date"] = time_el["datetime"][:10]
    else:
        date_el = ctx.select_one(".post__date-text")
        if date_el:
            parsed = parse_relative_date(date_el.get_text(strip=True))
            if parsed:
                scrape["date"] = parsed

    # Details
    el = ctx.select_one(".post__text")
    if el:
        scrape["details"] = el.get_text(strip=True)
    else:
        og = soup.find("meta", property="og:description")
        if og:
            scrape["details"] = og.get("content", "").strip()

    # Image — data-poster on video tag (server-rendered)
    video_el = ctx.select_one("video[data-poster]")
    if video_el and video_el.get("data-poster"):
        scrape["image"] = video_el["data-poster"]
    else:
        img_el = ctx.select_one("img.video-poster__img")
        if img_el and img_el.get("src"):
            scrape["image"] = img_el["src"]
        else:
            og_img = soup.find("meta", property="og:image")
            if og_img:
                scrape["image"] = og_img.get("content", "")

    # Tags — inside <template id="post-tags__template">
    tags = []
    template = ctx.find("template", id="post-tags__template")
    if template:
        inner = template.decode_contents()
        tmpl_soup = BeautifulSoup(inner, "html.parser")
        for a in tmpl_soup.select(".post-tags__link"):
            name = a.get_text(strip=True)
            if name:
                tags.append({"name": name})
    if tags:
        scrape["tags"] = tags

    # Performers
    performers = []
    for a in ctx.select(".post__featuring-models__list-item"):
        name = a.get_text(strip=True)
        if name:
            performers.append({"name": name})
    if performers:
        scrape["performers"] = performers

    # Studio
    studio_link_el = ctx.select_one(".post__profile-name--link")
    if studio_link_el:
        studio_name = studio_link_el.get_text(strip=True)
        studio_url  = studio_link_el.get("href", "")
        if studio_url and not studio_url.startswith("http"):
            studio_url = SHEER_BASE + studio_url
        scrape["studio"] = {"name": studio_name, "url": studio_url}
    else:
        studio_url = post_url.rsplit("/post/", 1)[0]
        scrape["studio"] = {"url": studio_url}

    scrape["code"] = post_id
    scrape["urls"] = [post_url]
    return scrape


def by_url(url):
    html = fetch(url)
    return parse_post(html, url)


if __name__ == "__main__":
    fragment = json.loads(sys.stdin.read())

    url = fragment.get("url", "")
    if not url:
        log.error("No URL provided")
        sys.exit(1)

    result = by_url(url)
    print(json.dumps(result))