import requests
from lxml import html
import json
from datetime import datetime

def get_page_content(url):
    """Fetch and parse HTML content from a given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
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

    # Extract details
    title = tree.xpath("//h1/text()")
    image = tree.xpath("//div[@class='video-trailer']//img/@src")

    # 🔥 Fix: Ensure description is correctly extracted
    details = tree.xpath("//div[@class='movie-description']/strong/following-sibling::text()")
    details = " ".join([d.strip() for d in details if d.strip()])  # Clean up text and join if needed

    # Extract tags
    tags = tree.xpath("//span[@class='tags-list']//a/text()")
    tags = [tag.strip("#") for tag in tags]  # Remove hashtag from tags

    # Extract and format date
    raw_date = scrape_video_date(main_url)
    formatted_date = format_date(raw_date) if raw_date else None

    return {
        "title": title[0] if title else None,
        "image": image[0] if image else None,
        "details": details if details else None,  # 🔥 Now properly extracted
        "tags": [{"Name": tag} for tag in tags],
        "studio": {"Name": "Got2Pee"},
        "date": formatted_date  # Now in 'YYYY-MM-DD' format
    }

def scrape_video_date(main_url):
    """Find the video URL in related videos and extract the corresponding date."""
    tree = get_page_content(main_url)
    if tree is None:
        return None

    related_video_urls = tree.xpath("/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[1]/a/@href")
    related_video_urls = ["https://got2pee.com" + url if not url.startswith("http") else url for url in related_video_urls]

    for related_video_url in related_video_urls:
        related_tree = get_page_content(related_video_url)
        if related_tree is None:
            continue

        video_links = related_tree.xpath("/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[1]/a/@href")
        video_dates = related_tree.xpath("/html/body/div[3]/div/div[2]/div[12]/section/div/div[1]/div/div/div[2]/span[2]/text()")

        for link, date in zip(video_links, video_dates):
            full_link = "https://got2pee.com" + link if not link.startswith("http") else link
            if full_link == main_url:
                return date.strip()

    return None

if __name__ == "__main__":
    import sys
    input_data = json.loads(sys.stdin.read())
    video_url = input_data.get("url")
    if video_url:
        print(json.dumps(scrape_video_data(video_url), indent=4))
