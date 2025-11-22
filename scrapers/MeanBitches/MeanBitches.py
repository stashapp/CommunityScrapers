import json
import sys
import re
import html
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from py_common import log
from py_common.cache import cache_to_disk


# Constants
BASE_URL = "https://megasite.meanworld.com"
DEFAULT_DIRECTOR = "Glenn King"
MAX_PERFORMER_PAGES = 3  # most scenes on first few pages
MAX_SEARCH_PAGES = 5


def fetch_html(url: str, timeout: int = 10) -> str:
    """Fetch HTML content from URL with error handling.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        ValueError: If URL is invalid
        Exception: Network or parsing errors

    Note: High-level caching is provided by search_scenes_by_name() and scrapeSceneURL()
    to avoid decorator overhead with ThreadPoolExecutor.
    """
    if not url or not isinstance(url, str):
        raise ValueError(f"Invalid URL: {url}")

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP Error {e.code}: {str(e)}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {str(e)}")
    except UnicodeDecodeError as e:
        raise Exception(f"Failed to decode response: {str(e)}")


def normalize_url(url: str) -> str:
    """Convert relative URL to absolute URL.

    Args:
        url: URL to normalize (relative or absolute)

    Returns:
        Absolute URL, original if already absolute, or None if invalid

    Raises:
        ValueError: If URL is not a string
    """
    if url is None:
        return None
    if not isinstance(url, str):
        raise ValueError(f"URL must be a string, got {type(url).__name__}")

    url = url.strip()
    if not url:
        return None

    if url.startswith('/'):
        return f"{BASE_URL}{url}"
    return url


def is_valid_url(url: str, required_domain: str = None) -> bool:
    """Validate URL format and optional domain.

    Args:
        url: URL to validate
        required_domain: Optional required domain substring

    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    if not url.startswith("http"):
        return False
    if required_domain and required_domain not in url:
        return False
    return True


def extract_title_from_filename(filename: str) -> str:
    """Extract title from video filename by removing path and extension.

    Args:
        filename: Video filename with path and extension

    Returns:
        Title without path and extension, or None if invalid

    Raises:
        ValueError: If filename is not a string
    """
    if filename is None:
        return None

    if not isinstance(filename, str):
        raise ValueError(f"Filename must be a string, got {type(filename).__name__}")

    filename = filename.strip()
    if not filename:
        return None

    # Remove path separators
    title = filename.split("\\")[-1].split("/")[-1]

    if not title:
        return None

    # Remove common video extensions
    for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"]:
        if title.lower().endswith(ext):
            return title[:-len(ext)]

    return title


def readJSONInput() -> dict:
    """Read and parse JSON input from stdin.

    Returns:
        Parsed JSON data as dict

    Raises:
        SystemExit: On JSON parsing error
    """
    try:
        input_data = sys.stdin.read()
        if not input_data:
            log.error("No input data received")
            sys.exit(69)
        parsed = json.loads(input_data)
        log.debug(f"Input received: {json.dumps(parsed)}")
        return parsed
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON input: {str(e)}")
        sys.exit(69)
    except Exception as e:
        log.error(f"Error reading input: {str(e)}")
        sys.exit(69)


def extract_title(html_content: str) -> str:
    """Extract title from data-title attribute of packageinfo div."""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        packageinfo = soup.find('div', id=re.compile(r'packageinfo_\d+'))
        if packageinfo and packageinfo.get('data-title'):
            return html.unescape(packageinfo['data-title'])
    except Exception as e:
        log.debug(f"Error extracting title: {str(e)}")
    return None


def extract_details(html_content: str) -> str:
    """Extract details from vidImgContent paragraph."""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        vid_content = soup.find('div', class_=re.compile(r'vidImgContent'))
        if vid_content:
            p_tag = vid_content.find('p')
            if p_tag:
                return html.unescape(p_tag.get_text(strip=True))
    except Exception as e:
        log.debug(f"Error extracting details: {str(e)}")
    return None


def extract_studio_name(html_content: str) -> str:
    """Extract studio name from breadcrumb link.

    Find the link_bright link with a relative href (starts with /),
    which points to the studio page, not external links like "Exit Here".
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        # Find all link_bright links and get the one with a relative href
        for link in soup.find_all('a', class_='link_bright'):
            href = link.get('href', '')
            # Studio links have relative hrefs (start with /), not external (start with http)
            if href.startswith('/'):
                return html.unescape(link.get_text(strip=True))
    except Exception as e:
        log.debug(f"Error extracting studio name: {str(e)}")
    return None


def extract_performers(html_content: str) -> list:
    """Extract all performer names from infolink class."""
    performers = []
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        for link in soup.find_all('a', class_=re.compile(r'link_bright.*infolink')):
            name = link.get_text(strip=True)
            if name:
                performers.append({"name": html.unescape(name)})
    except Exception as e:
        log.debug(f"Error extracting performers: {str(e)}")
    return performers


def extract_performer_links(html_content: str) -> list:
    """Extract performer profile links from the scene page."""
    performer_links = []
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        for link in soup.find_all('a', class_=re.compile(r'link_bright.*infolink')):
            href = link.get('href')
            if href:
                performer_links.append(href)
    except Exception as e:
        log.debug(f"Error extracting performer links: {str(e)}")
    return performer_links


def extract_setid(html_content: str) -> str:
    """Extract the setid from packageinfo div."""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        packageinfo = soup.find('div', id=re.compile(r'packageinfo_(\d+)'))
        if packageinfo:
            setid_match = re.search(r'packageinfo_(\d+)', packageinfo.get('id', ''))
            if setid_match:
                return setid_match.group(1)
    except Exception as e:
        log.debug(f"Error extracting setid: {str(e)}")
    return None


def fetch_performer_thumbnail(performer_url: str, setid: str) -> str:
    """Fetch performer page(s) and extract thumbnail for the given setid, handling pagination."""
    # Guard against None or invalid URLs
    if not performer_url or not isinstance(performer_url, str):
        return None

    try:
        page = 1

        while page <= MAX_PERFORMER_PAGES:
            # Build URL for current page
            if page == 1:
                url = performer_url
            else:
                # Add page parameter
                separator = '&' if '?' in performer_url else '?'
                url = f"{performer_url}{separator}page={page}"

            try:
                perf_html = fetch_html(url)
            except Exception as e:
                log.error(f"Error fetching performer page {page}: {str(e)}")
                break

            try:
                soup = BeautifulSoup(perf_html, 'lxml')

                # Look for img with id="set-target-{setid}"
                set_img = soup.find('img', id=f'set-target-{setid}')
                if set_img:
                    thumb_path = set_img.get('src', '').strip()
                    if thumb_path and thumb_path.endswith('.jpg'):
                        # Convert to full URL
                        return normalize_url(thumb_path) or thumb_path

                # Check if there's a next page by looking for pagination links
                # Look for href with page={page + 1}
                next_page_found = False
                for link in soup.find_all('a', href=re.compile(f'page={page + 1}')):
                    next_page_found = True
                    break

                if not next_page_found:
                    # No next page found, stop pagination
                    break

            except Exception as e:
                log.error(f"Error parsing performer page {page}: {str(e)}")
                break

            page += 1

    except Exception as e:
        log.error(f"Error in fetch_performer_thumbnail: {str(e)}")

    return None


def extract_image(html_content: str) -> str:
    """Extract image URL from og:image meta tag, preview thumb, performer page, or JavaScript."""
    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # First try og:image meta tag
        og_image = soup.find('meta', property='og:image')
        if og_image:
            url = og_image.get('content', '').strip()
            # Skip empty URLs or URLs that are just the base path
            if url and not url.endswith('contentthumbs/'):
                # Upgrade to 4x quality: convert any version (1x, 2x, 3x) to 4x
                url = re.sub(r'/meanbitches/content/contentthumbs/(.*)-[1234]x\.jpg$', r'/content//contentthumbs/\1-4x.jpg', url)
                if url:
                    return url

        # Fallback 1: Extract preview image from dvd_preview_thumb class
        preview_img = soup.find('img', class_=re.compile(r'dvd_preview_thumb'))
        if preview_img:
            thumb_url = preview_img.get('src', '').strip()
            if thumb_url:
                return normalize_url(thumb_url) or thumb_url

        # Fallback 2: fetch performer page to get higher quality thumbnail
        setid = extract_setid(html_content)
        if setid:
            performer_links = extract_performer_links(html_content)
            for perf_link in performer_links:
                thumb_url = fetch_performer_thumbnail(perf_link, setid)
                if thumb_url:
                    return thumb_url

        # Fallback 3: try to extract movie thumbnail from JavaScript
        thumb_match = re.search(r'thumbnail:\s*"([^"]*\.jpg)"', html_content)
        if thumb_match:
            thumb_url = thumb_match.group(1).strip()
            if thumb_url:
                return normalize_url(thumb_url) or thumb_url

    except Exception as e:
        log.debug(f"Error extracting image: {str(e)}")

    return None


def extract_date(html_content: str) -> str:
    """Extract date from text_med class (first occurrence)."""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        # Find the first li with text_med class
        for li in soup.find_all('li', class_=re.compile(r'text_med')):
            text = li.get_text(strip=True)
            # Look for date pattern MM/DD/YYYY
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
            if date_match:
                date_str = date_match.group(1).strip()
                try:
                    parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    return date_str
    except Exception as e:
        log.debug(f"Error extracting date: {str(e)}")
    return None


def extract_tags(html_content: str) -> list:
    """Extract all tag names from blogTags using BeautifulSoup."""
    tags = []
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        # Find blogTags div
        blogtags_div = soup.find('div', class_=re.compile(r'blogTags'))
        if blogtags_div:
            # Find all border_btn links within blogTags
            for link in blogtags_div.find_all('a', class_=re.compile(r'border_btn')):
                tag_name = link.get_text(strip=True)
                if tag_name:
                    tags.append({"name": html.unescape(tag_name)})
    except Exception as e:
        log.debug(f"Error extracting tags: {str(e)}")
    return tags


def extract_studio_code(html_content: str) -> str:
    """Extract studio code from upload path in HTML."""
    try:
        match = re.search(r'/content//upload/([^/]+)/', html_content)
        if match:
            return match.group(1)
    except Exception as e:
        log.debug(f"Error extracting studio code: {str(e)}")
    return None


def extract_search_result_data(container, scene_url: str, title: str) -> dict:
    """Extract scene data from search results HTML without scraping individual pages.

    Takes a BeautifulSoup container element and extracts data directly from it.
    Extracts: title, url, image, performer, studio, date
    Skips: description, tags, code (available on full page but not needed for search)
    """
    result = {
        "title": html.unescape(title.strip()),
        "url": scene_url
    }

    try:
        # container is already a BeautifulSoup element, use it directly
        soup = container

        # Extract image from img or video tag (try src0_2x/poster_2x, src0_1x/poster_1x, then src/poster)
        img_tag = soup.find('img', class_='update_thumb')
        video_tag = soup.find('video', class_='update_thumb')

        if img_tag:
            # IMG tag: try src0_2x, src0_1x, then src
            img_url = img_tag.get('src0_2x') or img_tag.get('src0_1x') or img_tag.get('src')
            if img_url:
                img_url = img_url.strip()
                img_url = normalize_url(img_url) or img_url
                result["image"] = img_url
        elif video_tag:
            # VIDEO tag: try poster_2x, poster_1x, then poster (poster attribute uses poster_Nx naming)
            img_url = video_tag.get('poster_2x') or video_tag.get('poster_1x') or video_tag.get('poster')
            if img_url:
                img_url = img_url.strip()
                img_url = normalize_url(img_url) or img_url
                result["image"] = img_url

        # Extract performer from /models/ link
        perf_link = soup.find('a', href=re.compile(r'https://megasite\.meanworld\.com/models/'))
        if perf_link:
            perf_name = perf_link.get_text(strip=True)
            result["performers"] = [{"name": perf_name}]

        # Extract studio from site link (href="/sitename/")
        studio_link = soup.find('a', href=re.compile(r'^/[^/]+/$'))
        if studio_link:
            studio_name = studio_link.get_text(strip=True)
            result["studio"] = {"name": studio_name}

        # Extract date from list item with calendar icon
        for li in soup.find_all('li', class_='text_med'):
            date_text = li.get_text(strip=True)
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_text):
                try:
                    parsed_date = datetime.strptime(date_text, "%m/%d/%Y")
                    result["date"] = parsed_date.strftime("%Y-%m-%d")
                    break
                except (ValueError, AttributeError):
                    # Invalid date format, continue to next date candidate
                    pass

    except Exception as e:
        log.debug(f"Error parsing search result: {str(e)}")

    return result


def _fetch_and_parse_search_page(encoded_query: str, page: int, search_name: str) -> tuple:
    """Fetch and parse a single search results page.

    Args:
        encoded_query: URL-encoded search query
        page: Page number to fetch
        search_name: Original search name (for exact match checking)

    Returns:
        Tuple of (results_list, has_exact_match)
    """
    page_results = []
    has_exact_match = False

    try:
        # Build search URL
        if page == 1:
            search_url = f"https://megasite.meanworld.com/search.php?query={encoded_query}"
        else:
            search_url = f"https://megasite.meanworld.com/search.php?query={encoded_query}&page={page}"

        # Fetch page
        try:
            html_content = fetch_html(search_url)
        except Exception as e:
            log.error(f"Error fetching search page {page}: {str(e)}")
            return page_results, has_exact_match

        # Parse results
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            all_containers = soup.find_all('div', class_=re.compile(r'latestUpdateB'))

            if not all_containers:
                return page_results, has_exact_match

            for container in all_containers:
                try:
                    # Skip latestUpdateBinfo containers
                    if 'latestUpdateBinfo' in container.get('class', []):
                        continue

                    # Find the scene link
                    scene_link = None
                    for link in container.find_all('a', href=re.compile(r'https://megasite\.meanworld\.com/scenes/.*_vids\.html')):
                        title = link.get_text(strip=True)
                        if title:
                            scene_link = link
                            break

                    if not scene_link:
                        continue

                    scene_url = scene_link.get('href')
                    title = scene_link.get_text(strip=True)

                    if not scene_url or not title:
                        continue

                    # Check for exact match
                    if html.unescape(title).lower() == search_name.lower():
                        has_exact_match = True

                    # Extract data
                    result = extract_search_result_data(container, scene_url, title)
                    page_results.append(result)

                except Exception as e:
                    log.error(f"Error processing scene container on page {page}: {str(e)}")
                    continue

        except Exception as e:
            log.error(f"Error parsing search page {page}: {str(e)}")

    except Exception as e:
        log.error(f"Error in _fetch_and_parse_search_page: {str(e)}")

    return page_results, has_exact_match


def _search_sequential(encoded_query: str, name: str, max_pages: int) -> list:
    """Fetch search results sequentially (one page at a time).

    Used for generic searches where we need to stop early anyway.
    """
    results = []
    exact_match_found = False

    for page in range(1, max_pages + 1):
        if exact_match_found:
            break

        page_results, has_exact_match = _fetch_and_parse_search_page(encoded_query, page, name)
        results.extend(page_results)

        if has_exact_match:
            exact_match_found = True
            log.debug(f"Exact match found on page {page}, stopping search")
            break

        # Stop if no results on this page
        if not page_results:
            break

    return results


def _search_parallel(encoded_query: str, name: str, max_pages: int) -> list:
    """Fetch search results in parallel (multiple pages concurrently).

    Used for specific searches where we want to find exact matches faster.
    """
    results = []

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all page fetch tasks
            future_to_page = {
                executor.submit(_fetch_and_parse_search_page, encoded_query, page, name): page
                for page in range(1, max_pages + 1)
            }

            # Collect results as they complete, stop early if exact match found
            exact_match_found = False
            for future in as_completed(future_to_page):
                if exact_match_found:
                    continue

                page = future_to_page[future]
                try:
                    page_results, has_exact_match = future.result(timeout=15)
                    if page_results:
                        results.extend(page_results)

                    if has_exact_match:
                        exact_match_found = True
                        log.debug(f"Exact match found on page {page}, stopping search")

                except TimeoutError:
                    log.error(f"Timeout waiting for search page {page} results")
                except BaseException as e:
                    # Catch BaseException to handle any threading-related issues
                    log.error(f"Exception in search page {page}: {type(e).__name__}: {str(e)}")

    except BaseException as e:
        log.error(f"Error in parallel search: {type(e).__name__}: {str(e)}")

    return results


@cache_to_disk(ttl=3600)  # Cache for 1 hour (3600 seconds)
def search_scenes_by_name(name: str) -> list:
    """Search for scenes by name - returns array of enriched scene fragments, sorted by relevance.

    Results are cached for 1 hour. Uses parallel page fetching for specific searches (3+ words),
    and sequential fetching for generic searches to minimize overhead.
    Search results are extracted from the search page directly without scraping individual
    scene pages.
    """
    results = []

    if not name or not isinstance(name, str):
        log.error(f"Invalid search name: {name}")
        return results

    try:
        name = name.strip()
        if not name:
            return results

        encoded_query = urllib.parse.quote(name)
        max_pages = 5

        # Decide between parallel and sequential based on query specificity
        # If search has 3+ words, it's likely specific (e.g. "Victoria June POV Slave Orders 5")
        # Use parallel to find exact match faster. Otherwise use sequential for simplicity.
        word_count = len(name.split())
        use_parallel = word_count >= 3

        if use_parallel:
            log.debug(f"Search query '{name}' has {word_count} words, using parallel fetching")
            results = _search_parallel(encoded_query, name, max_pages)
        else:
            log.debug(f"Search query '{name}' has {word_count} word(s), using sequential fetching")
            results = _search_sequential(encoded_query, name, max_pages)

        # Sort results by relevance to the search query
        def relevance_score(scene):
            title = scene.get("title", "").lower()
            query = name.lower()

            # Exact match (highest priority)
            if title == query:
                return 1000

            # Starts with query (very relevant)
            if title.startswith(query):
                return 900

            # Query is substring (relevant)
            if query in title:
                return 800

            # Levenshtein-like: count matching words in order
            query_words = query.split()
            title_words = title.split()
            matching_words = sum(1 for w in query_words if any(w in tw for tw in title_words))
            word_match_score = 700 * (matching_words / max(len(query_words), 1))

            return word_match_score

        results.sort(key=relevance_score, reverse=True)

        # Log sample of first result
        if results:
            first = results[0]
            first_fields = ", ".join(first.keys())
            log.debug(f"Search returning {len(results)} results. First result fields: {first_fields}")

    except Exception as e:
        log.error(f"Error searching scenes by name: {str(e)}")

    return results


def _resolve_scene_fragment(scene_fragment: dict, require_megasite_domain: bool = False, prefer_exact_match: bool = False):
    """Resolve a scene fragment by attempting to scrape URL or search by title.

    Common logic for query_scene_fragment and enrich_scene_fragment.

    Args:
        scene_fragment: Scene fragment dict with optional 'url', 'title', 'file_name', 'urls'
        require_megasite_domain: If True, only scrape megasite.meanworld.com URLs
        prefer_exact_match: If True, search results prefer exact title match

    Returns:
        Enriched scene dict or original fragment if resolution fails
    """
    # Attempt to scrape URL(s) if present
    # Try URLs in order: urls array first (if available), then main url field
    urls_to_try = []

    # Add urls from array if available
    if "urls" in scene_fragment and isinstance(scene_fragment.get("urls"), list):
        urls_to_try.extend(scene_fragment.get("urls", []))

    # Add main url if not already in array
    if "url" in scene_fragment:
        main_url = scene_fragment.get("url")
        if main_url and main_url not in urls_to_try:
            urls_to_try.append(main_url)

    # Try each URL in order
    for url in urls_to_try:
        if url and isinstance(url, str) and url.startswith("http"):
            # Check domain requirement if specified
            if require_megasite_domain and "megasite.meanworld.com" not in url:
                # Skip non-megasite URLs and continue to next URL
                continue

            try:
                result = scrapeSceneURL(url)
                # Only return result if it has meaningful data (at least a title)
                # Gallery pages might scrape "successfully" but only get studio/director
                if result.get("title"):
                    return result
                else:
                    log.debug(f"URL {url} returned incomplete data (no title), trying next URL")
            except Exception as e:
                # If URL fails, try next URL or fall through to search by title
                log.debug(f"Failed to scrape URL {url}, trying next URL: {str(e)}")

    # Extract title from fragment or filename
    title = scene_fragment.get("title")
    if not title and "file_name" in scene_fragment:
        title = extract_title_from_filename(scene_fragment.get("file_name", ""))

    # Search by title if available
    if title:
        log.debug(f"All URLs failed, falling back to search by title: '{title}'")
        search_results = search_scenes_by_name(title)
        if search_results:
            if prefer_exact_match:
                # Find the best match: prefer exact title match, otherwise use first result
                best_match = search_results[0]
                for result in search_results:
                    if result["title"].lower() == title.lower():
                        best_match = result
                        break
                log.debug(f"Found {len(search_results)} search results, using best match: {best_match.get('url')}")
                return scrapeSceneURL(best_match["url"])
            else:
                # Return the first (best) match
                log.debug(f"Found {len(search_results)} search results, using first: {search_results[0].get('url')}")
                return scrapeSceneURL(search_results[0]["url"])
        else:
            log.debug(f"No search results found for title: '{title}'")
    else:
        log.debug(f"No title available for fallback search")

    # If we can't find it, return the fragment as-is
    log.debug(f"Returning original fragment with {len(scene_fragment)} fields")
    return scene_fragment


def query_scene_fragment(scene_fragment: dict) -> dict:
    """Query for scenes matching a fragment - returns single enriched scene.

    This is used by sceneByQueryFragment to find a scene matching a fragment.
    Returns a single enriched scene (the best match).
    """
    return _resolve_scene_fragment(scene_fragment, require_megasite_domain=False, prefer_exact_match=False)


def enrich_scene_fragment(scene_fragment: dict) -> dict:
    """Enrich a scene fragment (from URL or partial data) by scraping full details.

    This is used by sceneByFragment to enrich scenes from library.
    Only scrapes megasite.meanworld.com URLs (skips meanbitches.com which return 404).
    Prefers exact title matches when searching.
    """
    return _resolve_scene_fragment(scene_fragment, require_megasite_domain=True, prefer_exact_match=True)


def scrapeSceneURL(url: str) -> dict:
    """Scrape scene data from MeanBitches page by URL.

    Raises an exception on 404 or network errors so that calling code
    (e.g. _resolve_scene_fragment) can fall back to searching by title.
    """
    ret = {'url': url}  # Include the URL in the response

    try:
        # Fetch the HTML content
        html_content = fetch_html(url)

        # Extract all fields
        if title := extract_title(html_content):
            ret['title'] = title

        if details := extract_details(html_content):
            ret['details'] = details

        # Studio
        studio = {}
        if studio_name := extract_studio_name(html_content):
            studio['name'] = studio_name
        studio['url'] = "https://www.meanbitches.com/"
        if studio:
            ret['studio'] = studio

        # Performers
        if performers := extract_performers(html_content):
            ret['performers'] = performers

        # Image
        if image := extract_image(html_content):
            ret['image'] = image

        # Date
        if date := extract_date(html_content):
            ret['date'] = date

        # Tags
        if tags := extract_tags(html_content):
            ret['tags'] = tags

        # Studio code
        if code := extract_studio_code(html_content):
            ret['code'] = code

        # Director
        ret['director'] = "Glenn King"

    except Exception as e:
        # Don't swallow exceptions - let calling code handle them
        # This allows _resolve_scene_fragment to fall back to search by title on 404
        raise

    return ret


def scrapeGalleryURL(url: str) -> dict:
    """Scrape gallery data from MeanBitches page by URL."""
    # For galleries, use the same extraction as scenes but with photographer instead of director
    ret = scrapeSceneURL(url)

    # Replace director with photographer for galleries
    if 'director' in ret:
        del ret['director']
    ret['photographer'] = "Glenn King"

    return ret


# Read the input
input_data = readJSONInput()
operation = sys.argv[1] if len(sys.argv) > 1 else "unknown"
log.debug(f"=== OPERATION START: {operation} ===")

if operation == "scrapeSceneURL":
    url = input_data.get('url')
    ret = scrapeSceneURL(url)
    print(json.dumps(ret))
elif operation == "scrapeGalleryURL":
    url = input_data.get('url')
    ret = scrapeGalleryURL(url)
    print(json.dumps(ret))
elif operation == "searchScenes":
    name = input_data.get('name')
    ret = search_scenes_by_name(name)
    print(json.dumps(ret))
elif operation == "queryScene":
    ret = query_scene_fragment(input_data)
    print(json.dumps(ret))
elif operation == "enrichScene":
    ret = enrich_scene_fragment(input_data)
    print(json.dumps(ret))
else:
    log.error(f"Unknown operation: {operation}")
    sys.exit(69)
