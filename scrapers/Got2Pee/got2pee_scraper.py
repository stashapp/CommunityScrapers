import json
import sys
from datetime import datetime
from py_common.deps import ensure_requirements
import py_common.log as log

ensure_requirements("requests", "lxml")

import requests  # noqa: E402
from lxml import html  # noqa: E402


def get_page_content(url):
    """Fetch and parse HTML content from a given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    log.debug(f"Fetching URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return html.fromstring(response.content)
    except requests.exceptions.RequestException:
        return None


def format_date(date_str):
    """Convert date from 'Oct 9, 2017' to 'YYYY-MM-DD' format."""
    try:
        return datetime.strptime(date_str, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None  # Return None if the date can't be parsed


def scrape_video_data(main_url):
    """Extract title, image, details, tags, studio, and date for the given video URL."""
    tree = get_page_content(main_url)
    if tree is None:
        return {}

    scene: dict = {
        "studio": {"name": "Got2Pee", "url": "https://got2pee.com"},
    }

    if title := tree.xpath("//h1"):
        scene["title"] = title[0].text_content()

    if image := tree.xpath("//div[@class='video-trailer']//img/@src"):
        scene["image"] = image[0]

    if details := tree.xpath("//div[@class='movie-description']"):
        scene["details"] = "\n".join(
            part for d in details if (part := d.text_content().strip())
        )

    if tags := tree.xpath("//span[@class='tags-list']//a/text()"):
        # Remove hashtag from tags
        scene["tags"] = [{"name": tag.strip("#")} for tag in tags]

    # Dates are only available from from the list of related videos
    if (raw_date := scrape_video_date(main_url)) and (
        formatted_date := format_date(raw_date)
    ):
        scene["date"] = formatted_date

    return scene


def scrape_video_date(main_url):
    """Find the video URL in related videos and extract the corresponding date."""
    tree = get_page_content(main_url)
    if tree is None:
        return None

    related_video_urls = tree.xpath(
        "/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[1]/a/@href"
    )
    related_video_urls = [
        "https://got2pee.com" + url if not url.startswith("http") else url
        for url in related_video_urls
    ]

    for related_video_url in related_video_urls:
        related_tree = get_page_content(related_video_url)
        if related_tree is None:
            continue

        video_links = related_tree.xpath(
            "/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[1]/a/@href"
        )
        video_dates = related_tree.xpath(
            "/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[2]/span[2]/text()"
        )

        for link, date in zip(video_links, video_dates):
            full_link = (
                "https://got2pee.com" + link if not link.startswith("http") else link
            )
            if full_link == main_url:
                return date.strip()

    return None


if __name__ == "__main__":
    input_data = json.load(sys.stdin)

    if video_url := input_data.get("url"):
        print(json.dumps(scrape_video_data(video_url)))
