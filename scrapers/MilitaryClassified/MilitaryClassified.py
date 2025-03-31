import json
import re
import sys
import base64
from datetime import datetime
from py_common.deps import ensure_requirements
ensure_requirements("cloudscraper", "lxml")
try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()

try:
    from lxml import html, etree
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()
try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

# Define a list of special performer names that should preserve their capitalization
SPECIAL_PERFORMER_NAMES = ["TJ", "JJ"]

def extract_performers(title):
    """Extract performer names from the title."""
    if not title:
        return []

    # Skip performer extraction for BUKAKKE scenes
    if "BUKAKKE" in title.upper():
        log.debug(f"BUKAKKE scene detected, skipping performer extraction: {title}")
        return []

    # Special case for single-letter prefixes like "D-Money" or "J-Rodd"
    single_letter_prefix_match = re.match(r'^([A-Z])-([A-Za-z]+)\d*$', title)
    if single_letter_prefix_match:
        prefix = single_letter_prefix_match.group(1)
        name = single_letter_prefix_match.group(2)
        formatted_name = f"{prefix}-{name[0].upper() + name[1:].lower()}"
        return [formatted_name]

    performers = []

    # Split by hyphen to get individual performer names
    parts = title.split('-')

    # Process each part
    for part in parts:
        # Extract the name part without any numbers
        name_match = re.search(r'([A-Za-z]+)\d*', part)
        if name_match and name_match[1]:
            # Get the name
            name = name_match[1]

            # Check if it's a special name that should preserve capitalization
            if name.upper() in SPECIAL_PERFORMER_NAMES:
                formatted_name = name.upper()
            else:
                # Format the name properly (first letter uppercase, rest lowercase)
                formatted_name = name[0].upper() + name[1:].lower()

            performers.append(formatted_name)

    return performers

def extract_title_number(title):
    """Extract the number from the title if present."""
    number_match = re.search(r'([A-Za-z]+)(\d+)', title)
    if number_match and number_match[2]:
        return number_match[2]
    return None

def format_descriptive_part(text):
    """Format the descriptive part of the title."""
    if not text:
        return ""

    # Split by hyphen and format each word
    parts = text.split('-')
    formatted_parts = []

    for part in parts:
        # Format each word (first letter uppercase, rest lowercase)
        formatted_part = part.strip()
        if formatted_part:
            # Split by spaces to handle multi-word parts
            words = formatted_part.split()
            formatted_words = []

            for word in words:
                # Capitalize the first letter of each word
                if word:
                    formatted_word = word[0].upper() + word[1:].lower()
                    formatted_words.append(formatted_word)

            formatted_parts.append(" ".join(formatted_words))

    # Join with spaces
    return " ".join(formatted_parts)

def format_title(search_result_text, performer_names, original_title):
    """Format the title based on search result text and performer names."""
    if not search_result_text:
        return ""
    # Extract the part after the slash (if exists)
    parts = search_result_text.split('/')

    # If there's no slash, use the whole text as the descriptive part
    if len(parts) < 2:
        descriptive_part = search_result_text.strip()
    else:
        descriptive_part = parts[1].strip()

    # Format the descriptive part
    formatted_descriptive_part = format_descriptive_part(descriptive_part)

    # For BUKAKKE scenes or when no performers are extracted, just return the descriptive part
    if not performer_names:
        return formatted_descriptive_part

    # Format performer names as "Name1, Name2 & Name3"
    if len(performer_names) == 1:
        performer_part = performer_names[0]
    elif len(performer_names) == 2:
        performer_part = f"{performer_names[0]} & {performer_names[1]}"
    else:
        # For 3+ performers, use commas and & for the last one
        performer_part = ", ".join(performer_names[:-1]) + f" & {performer_names[-1]}"

    # Extract number from original title if present
    title_number = extract_title_number(original_title)

    # Combine the parts
    if title_number and len(performer_names) == 1:
        formatted_title = f"{performer_part} {title_number}: {formatted_descriptive_part}"
    else:
        formatted_title = f"{performer_part}: {formatted_descriptive_part}"

    return formatted_title

def get_formatted_title(scraper, original_title):
    """Get the formatted title from the search results."""
    search_url = f"https://militaryclassified.com/dt/classic/ClassicSearch.pl?search={original_title}"

    try:
        search_response = scraper.get(search_url, timeout=10)
        search_response.raise_for_status()

        # Parse the search results
        search_tree = html.fromstring(search_response.content)

        # Extract all titles from search results
        search_title_xpath = "//div[contains(@class, 'RecruitBox')]/div[contains(@class, 'RecruitBoxText')]/text()"
        search_titles = search_tree.xpath(search_title_xpath)

        if search_titles and len(search_titles) > 0:
            # Look for an exact match first
            exact_match = None
            for title in search_titles:
                title_text = title.strip()
                # Extract the part before the slash
                title_parts = title_text.split('/')
                title_name = title_parts[0].strip()

                # Check if this is an exact match for the original title
                if title_name.upper() == original_title.upper():
                    exact_match = title_text
                    log.debug(f"Found exact match: {exact_match}")
                    break

            # If no exact match, use the first result
            search_result_text = exact_match if exact_match else search_titles[0].strip()
            log.debug(f"Using search result: {search_result_text}")

            # Extract performer names from the original title
            performer_names = extract_performers(original_title)

            # Format the title
            formatted_title = format_title(search_result_text, performer_names, original_title)
            log.debug(f"Formatted title: {formatted_title}")

            return formatted_title
        else:
            log.warning(f"No search results found for: {original_title}")
            return original_title
    except Exception as e:
        log.error(f"Error fetching search results: {e}")
        return original_title

def extract_date(tree):
    """Extract the date from the page."""
    # Try different XPaths for the date
    date_xpaths = [
        "//div[@id=\"VideoPlayerWrapper\"]/div[@class=\"MovieBlurb\"]/div[@class=\"Right\"]/text()",
        "//div[@class=\"MovieBlurb\"]/div[@class=\"Right\"]/text()"
    ]

    for xpath in date_xpaths:
        try:
            date_elements = tree.xpath(xpath)
            if date_elements:
                for date_str in date_elements:
                    date_str = date_str.strip()
                    # Try different date formats
                    date_patterns = [
                        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                        r'(\d{2}/\d{2}/\d{4})'   # MM/DD/YYYY
                    ]

                    for pattern in date_patterns:
                        date_match = re.search(pattern, date_str)
                        if date_match:
                            date_text = date_match.group(1)
                            try:
                                # Try to parse the date
                                if '-' in date_text:
                                    date_obj = datetime.strptime(date_text, "%Y-%m-%d")
                                else:
                                    date_obj = datetime.strptime(date_text, "%m/%d/%Y")

                                return date_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                log.error(f"Could not parse date: {date_text}")
        except Exception as e:
            log.error(f"Error extracting date with XPath {xpath}: {e}")

    # If we couldn't find a date, look for it in the page content
    try:
        content_xpath = "//div[@id='BodyContainer']//text()"
        content_elements = tree.xpath(content_xpath)
        if content_elements:
            content_text = ' '.join([e.strip() for e in content_elements if e.strip()])

            # Look for dates in the content
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{2}/\d{2}/\d{4})'   # MM/DD/YYYY
            ]

            for pattern in date_patterns:
                date_matches = re.findall(pattern, content_text)
                if date_matches:
                    for date_text in date_matches:
                        try:
                            # Try to parse the date
                            if '-' in date_text:
                                date_obj = datetime.strptime(date_text, "%Y-%m-%d")
                            else:
                                date_obj = datetime.strptime(date_text, "%m/%d/%Y")

                            return date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
    except Exception as e:
        log.error(f"Error extracting date from content: {e}")

    return None

def extract_details(tree):
    """Extract the details from the page."""
    try:
        details_xpaths = [
            "//h4[text()='HOW IT WENT DOWN']/following-sibling::p/text()",
            "//h4[contains(text(), 'HOW IT WENT DOWN')]/following-sibling::p/text()",
            "//div[@id='BodyContainer']//p/text()"
        ]

        for xpath in details_xpaths:
            details_elements = tree.xpath(xpath)
            if details_elements:
                # Filter out empty strings and join with newlines
                details = "\n\n".join([d.strip() for d in details_elements if d.strip()])
                if details:
                    return details
    except Exception as e:
        log.error(f"Error extracting details: {e}")

    return None

def scrape_scene(url):
    scene_data = {}
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=10)
        response.raise_for_status()

        # Try different encodings if UTF-8 fails
        content = None
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                content = response.content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            # If all encodings fail, use latin-1 as a fallback (it can decode any byte)
            content = response.content.decode('latin-1')

        # Parse the HTML
        tree = html.fromstring(content)
    except Exception as e:
        log.error(f"Error fetching or parsing URL: {e}")
        return {}

    # Extract common elements
    try:
        original_title_xpath = "//div[@id=\"BodyContainer\"]//h4/text()"
        original_title_elements = tree.xpath(original_title_xpath)
        original_title = ""
        if original_title_elements:
            original_title = original_title_elements[0].strip()

            # Get the formatted title from search results
            formatted_title = get_formatted_title(scraper, original_title)
            scene_data["title"] = formatted_title

        # Extract code (lowercase original title)
        if original_title:
            scene_data["code"] = original_title.lower()
    except Exception as e:
        log.error(f"Error extracting title: {e}")

    # Extract date
    try:
        date = extract_date(tree)
        if date:
            scene_data["date"] = date
    except Exception as e:
        log.error(f"Error extracting date: {e}")

    # Extract details
    try:
        details = extract_details(tree)
        if details:
            scene_data["details"] = details
    except Exception as e:
        log.error(f"Error extracting details: {e}")

    # Extract image and convert to base64
    try:
        image_xpath = "//video/@poster"
        image_elements = tree.xpath(image_xpath)
        if image_elements:
            img_url = f"https://militaryclassified.com{image_elements[0]}"
            try:
                # Fetch the image using cloudscraper
                img_response = scraper.get(img_url, timeout=10)
                img_response.raise_for_status()

                # Convert to base64
                img_b64 = base64.b64encode(img_response.content).decode('utf-8')
                scene_data["image"] = f"data:image/jpeg;base64,{img_b64}"

                log.debug(f"Successfully fetched and encoded image from {img_url}")
            except Exception as e:
                log.error(f"Error fetching image: {e}")
                # Fallback to just the URL if we can't fetch the image
                scene_data["image"] = img_url
    except Exception as e:
        log.error(f"Error extracting image: {e}")

    # Set Studio
    scene_data["studio"] = {"name": "Military Classified"}
    # Set Director
    scene_data["director"] = "Rob Navarro"

    # Extract performers
    try:
        if original_title:
            # Skip performer extraction for BUKAKKE scenes
            if "BUKAKKE" in original_title.upper():
                log.debug(f"BUKAKKE scene detected, skipping performer extraction: {original_title}")
            else:
                performer_names = extract_performers(original_title)
                if performer_names:
                    scene_data["performers"] = [{"name": name} for name in performer_names]
                    log.debug(f"Extracted performers: {performer_names}")
                else:
                    log.warning(f"No performers extracted from title: {original_title}")
    except Exception as e:
        log.error(f"Error extracting performers: {e}")

    return scene_data

def main():
    try:
        input_json = json.loads(sys.stdin.read())
        url = input_json.get("url", "")
        if not url:
            log.error("No URL provided")
            sys.exit(1)

        scene_data = scrape_scene(url)
        output_json = {**input_json, **scene_data}
        print(json.dumps(output_json))
    except Exception as e:
        log.error(f"Unhandled exception: {e}")
        sys.exit(69)  # Use a specific exit code for unhandled exceptions

if __name__ == "__main__":
    main()
