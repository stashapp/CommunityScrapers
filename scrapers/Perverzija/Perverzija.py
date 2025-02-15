import requests
from lxml import html
import json
import re

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

def scrape_video_data(main_url):
    """Extract title, image, details, tags, studio, and performers for the given video URL."""
    tree = get_page_content(main_url)
    if tree is None:
        return {}

    # Extract details
    raw_title = tree.xpath('//*[@id="content"]/div[1]/div[3]/div[1]/h1/text()')
    image = tree.xpath('//*[@id="featured-img-id"]/img/@src')
    
    # Extract all <p> tags inside the bialty-container class for the description
    description_elements = tree.xpath('//*[@class="bialty-container"]//p')
    
    # Combine all <p> tag text content into a single string
    details = " ".join([p.text_content().strip() for p in description_elements if p.text_content().strip()])
    
    # Clean up extra spaces or newlines in the description
    details = re.sub(r'\s+', ' ', details).strip()  # Replace multiple spaces/newlines with a single space
    
    tags = tree.xpath('//*[@id="content"]/div[1]/div[4]/div[3]/a/text()')
    performers = tree.xpath('//*[@id="content"]/div[1]/div[4]/div[2]/a/text()')
    
    # Process title
    studio, actual_title = None, None
    if raw_title:
        title_parts = raw_title[0].split(' – ')
        if len(title_parts) >= 2:
            studio = title_parts[0].strip()
            actual_title = title_parts[-1].strip()
        else:
            actual_title = raw_title[0].strip()
    
    return {
        "title": actual_title,
        "image": image[0] if image else None,
        "details": details,  # The cleaned description text
        "tags": [{"Name": tag} for tag in tags],
        "studio": {"Name": studio} if studio else None,
        "performers": [{"Name": performer} for performer in performers]
    }

if __name__ == "__main__":
    import sys
    input_data = json.loads(sys.stdin.read())
    video_url = input_data.get("url")
    if video_url:
        print(json.dumps(scrape_video_data(video_url), indent=4))