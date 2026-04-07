import sys
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Constants
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
STUDIO_NAME = 'ThatFetishGirl'
REQUEST_TIMEOUT = 10
MIN_DESCRIPTION_LENGTH = 20


def log(message, level='info'):
    """Log message to stderr. Only logs warnings and errors by default."""
    if level in ['warning', 'error']:
        print(message, file=sys.stderr)


def extract_title(soup):
    """Extract scene title from page."""
    title_elem = soup.find('h4')
    if title_elem:
        return title_elem.get_text(strip=True)
    return None


def extract_performers(soup, title_elem):
    """Extract performer names from first paragraph after title."""
    if not title_elem:
        return None
    
    next_p = title_elem.find_next_sibling('p')
    if not next_p:
        return None
    
    performers = []
    performer_links = next_p.find_all('a', href=lambda x: x and '/models/' in x)
    
    for link in performer_links:
        name = link.get_text(strip=True)
        if name:
            performers.append({'name': name})
    
    return performers if performers else None


def extract_date(soup):
    """Extract release date from list items."""
    list_items = soup.find_all('li')
    
    for li in list_items:
        text = li.get_text(strip=True)
        if '/' in text and len(text.split('/')) == 3:
            try:
                date_obj = datetime.strptime(text, '%m/%d/%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    return None


def extract_duration(soup):
    """Extract video duration in seconds."""
    list_items = soup.find_all('li')
    
    for li in list_items:
        text = li.get_text(strip=True)
        if 'min' in text.lower():
            duration = ''.join(filter(str.isdigit, text))
            if duration:
                return int(duration) * 60
    
    return None


def extract_tags(soup):
    """Extract category tags."""
    tags = []
    excluded_tags = {'Movies', 'Categories'}
    tag_links = soup.find_all('a', href=lambda x: x and '/categories/' in x)
    
    for link in tag_links:
        tag_name = link.get_text(strip=True)
        if tag_name and tag_name not in excluded_tags:
            tags.append({'name': tag_name})
    
    return tags if tags else None


def extract_description(soup):
    """Extract scene description using multiple fallback methods."""
    # Method 1: Look for div with class "vidImgContent"
    desc_div = soup.find('div', class_='vidImgContent')
    if desc_div:
        desc_p = desc_div.find('p')
        if desc_p:
            desc = desc_p.get_text(strip=True)
            if desc and len(desc) > MIN_DESCRIPTION_LENGTH:
                return desc
    
    # Method 2: Try og:description meta tag
    meta_desc = soup.find('meta', property='og:description')
    if meta_desc and meta_desc.get('content'):
        desc = meta_desc['content'].strip().rstrip('...')
        if len(desc) > MIN_DESCRIPTION_LENGTH:
            return desc
    
    # Method 3: Try standard description meta tag
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc = meta_desc['content'].strip().rstrip('...')
        if len(desc) > MIN_DESCRIPTION_LENGTH:
            return desc
    
    log("WARNING: No description found!", 'warning')
    return None


def extract_image(soup):
    """Extract scene thumbnail image URL."""
    image_elem = soup.find('meta', property='og:image')
    if image_elem and image_elem.get('content'):
        return image_elem['content']
    return None


def scrape_scene(url):
    """
    Scrape a scene from thatfetishgirl.com.
    
    Args:
        url: The URL of the scene to scrape
        
    Returns:
        dict: Scraped scene data or None if scraping failed
    """
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        result = {}
        
        # Extract all data
        title = extract_title(soup)
        if title:
            result['title'] = title
        
        title_elem = soup.find('h4')
        performers = extract_performers(soup, title_elem)
        if performers:
            result['performers'] = performers
        
        date = extract_date(soup)
        if date:
            result['date'] = date
        
        duration = extract_duration(soup)
        if duration:
            result['duration'] = duration
        
        tags = extract_tags(soup)
        if tags:
            result['tags'] = tags
        
        description = extract_description(soup)
        if description:
            result['details'] = description
        
        # Studio is always the same
        result['studio'] = {'name': STUDIO_NAME}
        
        image = extract_image(soup)
        if image:
            result['image'] = image
        
        return result
        
    except requests.RequestException as e:
        log(f"Error fetching URL: {e}", 'error')
        return None
    except Exception as e:
        log(f"Error parsing page: {e}", 'error')
        import traceback
        log(traceback.format_exc(), 'error')
        return None


def main():
    """Main entry point for the scraper."""
    try:
        input_data = sys.stdin.read()
        fragment = json.loads(input_data)
        
        url = fragment.get('url')
        if not url:
            log("No URL provided in input", 'error')
            sys.exit(1)
        
        result = scrape_scene(url)
        
        if result:
            print(json.dumps(result))
        else:
            log("Failed to scrape scene", 'error')
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        log(f"Invalid JSON input: {e}", 'error')
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}", 'error')
        import traceback
        log(traceback.format_exc(), 'error')
        sys.exit(1)


if __name__ == '__main__':
    main()