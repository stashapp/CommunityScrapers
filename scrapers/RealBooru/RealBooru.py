#!/usr/bin/env python3
"""
Realbooru.com Scraper for Stashapp
===================================

Scrapes metadata from realbooru.com by matching file md5 hash or post ID.

HOW IT WORKS:
1. Stashapp passes file path via fragment input
2. Extract post ID from filename (e.g., "rb_969688_artist.jpg" -> "969688")
   OR extract md5 from filename (e.g., "323df5c5784c312458abbfa383c46045.jpg")
3. If post ID: Scrape HTML post page directly
   If MD5: Search for post ID via HTML, then scrape post page
4. Parse HTML to extract tags and metadata
5. Map to Stashapp fields and return JSON

NOTE: Realbooru's JSON API is currently offline "indefinitely".

TAG MAPPING:
- Model tags (class="model") -> Performers field
- Character tags (class="character") -> Performers field (for cosplay, e.g., "d.va")
- All other tags (general, copyright, series, metadata) -> Tags field (no prefix)

FILENAME FORMATS SUPPORTED:
- rb_{POST_ID}_optional_name.{ext} (e.g., rb_969688_artist.jpg) - RECOMMENDED (fastest)
- {md5_hash}.{ext} (e.g., 323df5c5784c312458abbfa383c46045.jpg)
"""

import json
import sys
import re
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

def log(message):
    """Log to stderr so it doesn't interfere with JSON output"""
    print(f"[Realbooru.com] {message}", file=sys.stderr)

def extract_post_id_from_filename(file_path):
    """
    Extract post ID from filename with format: rb_{POST_ID}_optional_name.{ext}

    Examples:
        rb_969688_artist.jpg -> 969688
        rb_969688.png -> 969688
        rb_14681636_01.mp4 -> 14681636

    Returns: post ID string or None if no match
    """
    filename = Path(file_path).name
    # Match rb_{digits}_anything or rb_{digits}.ext
    match = re.match(r'rb[_-](\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def extract_md5_from_path(file_path):
    """
    Extract md5 hash from filename.

    Assumes filename IS the md5 hash (with or without extension).
    Examples:
        /path/to/323df5c5784c312458abbfa383c46045.jpg -> 323df5c5784c312458abbfa383c46045
        abc123def456.mp4 -> abc123def456

    Returns: md5 hash string (lowercase, 32 hex chars) or None if invalid
    """
    filename = Path(file_path).stem  # Gets filename without extension
    # MD5 hashes are exactly 32 hexadecimal characters
    md5_hash = re.sub(r'[^a-fA-F0-9]', '', filename)
    if len(md5_hash) == 32:
        return md5_hash.lower()
    return None

class RealbooruHTMLParser(HTMLParser):
    """Parse Realbooru post page HTML to extract tags and metadata with types"""

    def __init__(self):
        super().__init__()
        self.categorized_tags = {
            "models": [],     # Performers (includes both model and character tags for cosplay)
            "general": []     # All other tags (copyright, series, metadata, general, etc.)
        }
        self.score = None
        self.current_tag_class = None
        self.in_tag_link = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Detect tag links with class indicating type
        if tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            if 'page=post' in href and 's=list' in href and 'tags=' in href:
                self.in_tag_link = True
                # Extract tag type from CSS class
                tag_class = attrs_dict.get('class', '').lower()

                # Models/performers get special treatment
                # Note: 'character' is used for cosplay (e.g., "d.va" when someone cosplays D.Va)
                if 'model' in tag_class or 'character' in tag_class:
                    self.current_tag_class = 'model'
                # Everything else goes to general tags
                # This includes: copyright, series, metadata, general, and any future classes
                else:
                    self.current_tag_class = 'general'

    def handle_data(self, data):
        if self.in_tag_link and self.current_tag_class:
            # Extract tag name from link text
            tag_name = data.strip()
            if tag_name:
                # Convert underscores to spaces
                tag_name = tag_name.replace("_", " ")

                # Add to appropriate category (deduplicate)
                if self.current_tag_class == 'model':
                    if tag_name not in self.categorized_tags["models"]:
                        self.categorized_tags["models"].append(tag_name)
                else:  # Everything else (general, copyright, series, metadata, etc.)
                    if tag_name not in self.categorized_tags["general"]:
                        self.categorized_tags["general"].append(tag_name)

        # Extract score: "Score: 4"
        if 'Score:' in data or 'Current Score:' in data:
            match = re.search(r'Score:\s*\*?\*?(\d+)', data)
            if match:
                self.score = match.group(1)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_tag_link = False
            self.current_tag_class = None

def scrape_html_post(post_id):
    """
    Scrape post page HTML for metadata when API is unavailable.

    Args:
        post_id: Post ID to scrape

    Returns: dict with categorized_tags and score, or None on failure
    """
    url = f"https://realbooru.com/index.php?page=post&s=view&id={post_id}"
    log(f"Scraping HTML page: {url}")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "stashapp/stash scraper (realbooru.com)"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # Parse HTML
        parser = RealbooruHTMLParser()
        parser.feed(html)

        total_tags = sum(len(tags) for tags in parser.categorized_tags.values())
        if total_tags == 0:
            log("No tags found in HTML")
            return None

        log(f"Scraped {total_tags} tags from HTML: {len(parser.categorized_tags['models'])} models, {len(parser.categorized_tags['general'])} general")

        return {
            "id": post_id,
            "categorized_tags": parser.categorized_tags,
            "score": parser.score or "",
            "rating": "",  # Not easily available in HTML
            "width": "",
            "height": "",
            "file_url": "",
            "md5": ""
        }

    except Exception as e:
        log(f"HTML scraping failed: {e}")
        return None

def search_by_md5_html(md5_hash):
    """
    Search for post by MD5 via HTML search page.

    Args:
        md5_hash: MD5 hash to search for

    Returns: post ID if found, None otherwise
    """
    url = f"https://realbooru.com/index.php?page=post&s=list&tags=md5:{md5_hash}"
    log(f"Searching for MD5 via HTML: md5:{md5_hash}")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "stashapp/stash scraper (realbooru.com)"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # Look for post ID in various patterns
        # Pattern 1: s=view&id=123456 (most common)
        match = re.search(r's=view&(?:amp;)?id=(\d+)', html)
        if match:
            post_id = match.group(1)
            log(f"Found post ID from MD5 search: {post_id}")
            return post_id

        # Pattern 2: Any id= parameter
        match = re.search(r'[?&](?:amp;)?id=(\d+)', html)
        if match:
            post_id = match.group(1)
            log(f"Found post ID from MD5 search: {post_id}")
            return post_id

        # Pattern 3: Image alt text "Image: 123456"
        match = re.search(r'Image:\s*(\d+)', html)
        if match:
            post_id = match.group(1)
            log(f"Found post ID from alt text: {post_id}")
            return post_id

        log("No post found for MD5 in HTML search")
        log(f"HTML preview (first 500 chars): {html[:500]}")
        return None

    except Exception as e:
        log(f"HTML MD5 search failed: {e}")
        return None

def map_to_stashapp(post_data, categorized_tags):
    """
    Map realbooru.com post data to Stashapp scraper output format.

    Stashapp expects JSON with fields:
        - urls: [string] (array of links)
        - performers: [{"name": string}] (models/characters for cosplay)
        - tags: [{"name": string}] (all other tags - no prefix)
        - details: string

    Args:
        post_data: Post metadata dict
        categorized_tags: Dict with keys: models, general

    Returns: dict in Stashapp format
    """
    result = {}

    # URLs - link to post page
    if post_data.get("id"):
        result["urls"] = [f"https://realbooru.com/index.php?page=post&s=view&id={post_data['id']}"]

    # Performers from model tags (includes both models and character cosplay)
    if categorized_tags.get("models"):
        result["performers"] = [{"name": performer} for performer in categorized_tags["models"]]
        log(f"Mapped {len(categorized_tags['models'])} performers")

    # Tags - all general tags (includes copyright, series, metadata, general, etc.)
    all_tags = []
    for tag in categorized_tags.get("general", []):
        all_tags.append({"name": tag})

    # NOTE: optional behavior that I personally like.
    #       disabling this for upstream.
    # Add "scraped" marker tag if we have any tags/performers
    # (indicates successful scraping)
    # has_content = (
    #     all_tags or
    #     categorized_tags.get("models")
    # )
    # if has_content:
    #     all_tags.append({"name": "[scraped]"})

    if all_tags:
        result["tags"] = all_tags

    # Details - include score and dimensions
    details = []
    if post_data.get("score"):
        details.append(f"Score: {post_data['score']}")
    if post_data.get("width") and post_data.get("height"):
        details.append(f"Dimensions: {post_data['width']}x{post_data['height']}")

    # Add rating as detail
    if post_data.get("rating"):
        rating_map = {"s": "Safe", "q": "Questionable", "e": "Explicit"}
        rating = rating_map.get(post_data["rating"], post_data["rating"])
        details.append(f"Rating: {rating}")

    if details:
        result["details"] = " | ".join(details)

    return result

def main():
    """
    Main scraper entry point.

    Stashapp passes JSON input via stdin with structure:
    {
        "path": "/path/to/file.jpg",  # For fragment scraping
        "files": [{"path": "..."}],   # Alternative format
        "url": "https://..."           # For URL scraping
    }

    Returns: JSON output to stdout with scraped metadata
    """
    try:
        # Read input from Stashapp
        input_data = json.load(sys.stdin)
        log(f"Received input: {input_data}")

        # Extract file path from different input formats
        file_path = None

        # Try different input fields in order of preference
        if input_data.get("files") and len(input_data["files"]) > 0:
            file_path = input_data["files"][0].get("path")
        if not file_path:
            file_path = input_data.get("path")
        if not file_path:
            file_path = input_data.get("url")
        if not file_path:
            file_path = input_data.get("title")

        if not file_path:
            log("No filename/path/url/title in input")
            print(json.dumps({}))
            return

        log(f"Processing file: {file_path}")

        # Try to extract post ID first (faster than MD5 lookup)
        post_id = extract_post_id_from_filename(file_path)
        post_data = None

        if post_id:
            log(f"Extracted post ID: {post_id}")
            # Use HTML scraping directly (API is currently broken)
            post_data = scrape_html_post(post_id)
        else:
            # Fall back to MD5 extraction
            md5_hash = extract_md5_from_path(file_path)
            if md5_hash:
                log(f"Extracted md5: {md5_hash}")
                # Search for post ID via HTML, then scrape
                found_post_id = search_by_md5_html(md5_hash)
                if found_post_id:
                    post_data = scrape_html_post(found_post_id)
                else:
                    log("No post found for MD5")
            else:
                log("Could not extract post ID or md5 from filename")
                print(json.dumps({}))
                return

        if not post_data:
            log("No matching post found")
            print(json.dumps({}))
            return

        # Get categorized tags from HTML scraper
        categorized_tags = post_data.get("categorized_tags")
        if not categorized_tags:
            log("Post found but no tags")
            print(json.dumps({}))
            return

        # Map to Stashapp format with proper field mapping
        result = map_to_stashapp(post_data, categorized_tags)

        # Output JSON to stdout
        print(json.dumps(result))
        log("Scrape successful!")

    except Exception as e:
        log(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Return empty dict on error
        print(json.dumps({}))

if __name__ == "__main__":
    main()
