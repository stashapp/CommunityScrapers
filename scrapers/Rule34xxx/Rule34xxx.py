#!/usr/bin/env python3
"""
Rule34.xxx HTML Scraper for Stashapp
=====================================

Approach:
1. Extract post ID from filename (r34_{POST_ID} format) or md5 hash
2. For md5 hashes, use public search page to find post ID
3. Fetch HTML page to extract categorized tags

Tag categorization:
- Characters → Performers
- Artists → Studio (first non-voice artist) (Stash only supports one)
- Voice actors → Performers
- Copyright → Tags
- General → Tags
- Meta → Tags
"""

import json
import sys
import re
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
import time

def log(message):
    """Log to stderr so it doesn't interfere with JSON output"""
    print(f"[Rule34.xxx HTML] {message}", file=sys.stderr)

def is_voice_actor(artist_name):
    """
    Detect if an artist name indicates they are a voice actor.

    Patterns detected:
    - Contains "audio" (e.g., "evilaudio")
    - Contains "voice" (e.g., "voiceactor", "voice_actor")

    Args:
        artist_name: Artist name to check

    Returns: True if appears to be a voice actor
    """
    name_lower = artist_name.lower()

    # Check for audio in name
    if 'audio' in name_lower:
        return True

    # Check for voice-related terms
    if 'voice' in name_lower:
        return True

    return False

def separate_voice_actors(artists):
    """
    Separate voice actors from regular artists.

    Args:
        artists: List of artist names

    Returns: Tuple of (non_va_artists, va_artists)
    """
    if not artists:
        return [], []

    non_va = []
    va = []

    for artist in artists:
        if is_voice_actor(artist):
            va.append(artist)
        else:
            non_va.append(artist)

    if va:
        log(f"Separated {len(va)} voice actor(s) from {len(non_va)} artist(s)")

    return non_va, va

def extract_post_id_from_filename(file_path):
    """
    Extract post ID from filename if it follows r34_{POST_ID}_* format.

    Supports formats like:
    - r34_12345_artist.jpg
    - r34_12345_01.png
    - r34_12345.mp4

    Returns: post_id (string) or None
    """
    filename = Path(file_path).stem

    # Match r34_{digits}_{anything} or r34_{digits}
    match = re.match(r'^r34_(\d+)', filename)
    if match:
        post_id = match.group(1)
        log(f"Extracted post ID from filename: {post_id}")
        return post_id

    return None

def extract_md5_from_path(file_path):
    """
    Extract md5 hash from filename.
    
    Looks for 32 hex character sequences in the filename.
    Examples:
        /path/to/abc123def456...32chars.jpg -> abc123def456...
        0c0cd2945f33f59ba0f91b86a26387ff.mp4 -> 0c0cd2945f33f59ba0f91b86a26387ff
    
    Returns: md5 hash string (lowercase) or None
    """
    filename = Path(file_path).stem
    
    # First try: entire filename is exactly 32 hex characters
    cleaned = re.sub(r'[^a-fA-F0-9]', '', filename)
    if len(cleaned) == 32:
        return cleaned.lower()
    
    # Second try: find 32 consecutive hex characters anywhere in filename
    match = re.search(r'([a-fA-F0-9]{32})', filename)
    if match:
        return match.group(1).lower()
    
    return None

def get_post_id_from_md5_search(md5_hash):
    """
    Scrape search page to find post ID from md5 hash (no API key needed).
    
    Uses the public search interface: https://rule34.xxx/index.php?page=post&s=list&tags=md5:HASH
    Scrapes the search results to extract the post ID.
    
    Returns: post_id (string) or None
    """
    search_url = f"https://rule34.xxx/index.php?page=post&s=list&tags=md5:{md5_hash}"
    log(f"Searching for post by md5 (no auth): {search_url}")
    
    try:
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "stashapp/stash scraper",
            "Accept": "text/html"
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
        
        # Look for post ID in the search results
        # Format: <a id="p12345" or href with id=12345
        patterns = [
            r'id="p(\d+)"',  # Direct post ID in anchor
            r'[?&]id=(\d+)',  # ID in URL parameter
            r'\/index\.php\?page=post&s=view&id=(\d+)'  # Full URL pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                post_id = match.group(1)
                log(f"Found post ID from search: {post_id}")
                return post_id
        
        log(f"No post found in search results for md5:{md5_hash}")
        return None
        
    except Exception as e:
        log(f"Search page scraping failed: {e}")
        return None

class Rule34TagParser(HTMLParser):
    """Parse rule34.xxx HTML to extract categorized tags"""

    def __init__(self):
        super().__init__()
        self.tags = {
            "characters": [],
            "artists": [],
            "copyrights": [],
            "general": [],
            "meta": []
        }
        self.current_tag_type = None
        self.current_tag_link = False
        self.current_tag_name = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Look for tag list items with class indicating type
        if tag == "li":
            class_name = attrs_dict.get("class", "")

            # Map class names to tag types
            if "tag-type-character" in class_name or "character" in class_name:
                self.current_tag_type = "characters"
            elif "tag-type-artist" in class_name or "artist" in class_name:
                self.current_tag_type = "artists"
            elif "tag-type-copyright" in class_name or "copyright" in class_name or "series" in class_name:
                self.current_tag_type = "copyrights"
            elif "tag-type-metadata" in class_name or "meta" in class_name:
                self.current_tag_type = "meta"
            elif "tag-type-general" in class_name or "tag" in class_name:
                self.current_tag_type = "general"

        # Track when we're inside a tag link
        if tag == "a" and self.current_tag_type:
            self.current_tag_link = True
            self.current_tag_name = ""

    def handle_data(self, data):
        # Capture tag name from link text
        if self.current_tag_link:
            self.current_tag_name += data.strip()

    def handle_endtag(self, tag):
        # When link ends, save the tag
        if tag == "a" and self.current_tag_link and self.current_tag_name:
            tag_name = self.current_tag_name.replace("_", " ").strip()
            # Filter out empty, "?", and invalid tags
            if tag_name and tag_name != "?" and len(tag_name) > 1 and self.current_tag_type:
                # Avoid duplicates
                if tag_name not in self.tags[self.current_tag_type]:
                    self.tags[self.current_tag_type].append(tag_name)
            self.current_tag_link = False
            self.current_tag_name = ""

        # Reset tag type when list item ends
        if tag == "li":
            self.current_tag_type = None

def scrape_html_tags(post_id, retry_count=3):
    """
    Fetch HTML page and extract categorized tags with retry logic.

    Returns:
        - dict with tags if successful
        - None if temporary failure (rate limit, timeout, server error)
        - False if permanent failure (404, post doesn't exist)
    """
    url = f"https://rule34.xxx/index.php?page=post&s=view&id={post_id}"
    log(f"Fetching HTML from {url}")

    for attempt in range(retry_count):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "stashapp/stash scraper",
                "Accept": "text/html"
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')

            # Check if post actually exists (404 page might return 200)
            if "Nobody here but us chickens" in html or "Post not found" in html:
                log(f"Post {post_id} does not exist (404)")
                return False  # Permanent failure

            parser = Rule34TagParser()
            parser.feed(html)

            # Verify we got some tags (sanity check)
            total_tags = sum(len(tags) for tags in parser.tags.values())
            if total_tags == 0:
                log(f"Warning: No tags extracted, might be parsing issue")

            log(f"Extracted tags: {len(parser.tags['characters'])} characters, "
                f"{len(parser.tags['artists'])} artists, "
                f"{len(parser.tags['copyrights'])} copyrights, "
                f"{len(parser.tags['general'])} general, "
                f"{len(parser.tags['meta'])} meta")

            return parser.tags

        except urllib.error.HTTPError as e:
            if e.code == 404:
                log(f"Post {post_id} not found (404)")
                return False  # Permanent failure
            elif e.code == 429:
                log(f"Rate limited (429), attempt {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    # NOTE: this could honestly be higher. in my experience, rule34 only allows ~60rpm
                    time.sleep(2 ** attempt)
                    continue
                else:
                    log("Rate limit exceeded, giving up")
                    return None  # Temporary failure - don't tag
            elif e.code >= 500:
                log(f"Server error ({e.code}), attempt {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    time.sleep(1)
                    continue
                else:
                    log("Server errors persist, giving up")
                    return None  # Temporary failure
            else:
                log(f"HTTP error {e.code}: {e}")
                return None  # Other HTTP error - temporary failure

        except urllib.error.URLError as e:
            log(f"Network error, attempt {attempt + 1}/{retry_count}: {e}")
            if attempt < retry_count - 1:
                time.sleep(1)
                continue
            else:
                log("Network errors persist, giving up")
                return None  # Temporary failure

        except Exception as e:
            log(f"Unexpected error: {e}")
            return None  # Temporary failure

    return None  # All retries failed

def map_to_stashapp(post_id, categorized_tags, md5_hash=None):
    """Map scraped data to Stashapp format"""
    result = {}

    # URLs - link to specific post or md5 search
    if post_id:
        result["urls"] = [f"https://rule34.xxx/index.php?page=post&s=view&id={post_id}"]
    elif md5_hash:
        result["urls"] = [f"https://rule34.xxx/index.php?page=post&s=list&tags=md5:{md5_hash}"]

    # Separate voice actors from regular artists
    regular_artists, voice_actors = separate_voice_actors(categorized_tags["artists"])

    # Performers from characters + voice actors
    all_performers = []
    if categorized_tags["characters"]:
        all_performers.extend(categorized_tags["characters"])
    if voice_actors:
        all_performers.extend(voice_actors)

    if all_performers:
        result["performers"] = [{"name": str(performer)} for performer in all_performers]
        log(f"Mapped {len(all_performers)} performers")

    # Studio from first regular (non-VA) artist
    if regular_artists:
        result["studio"] = {"name": str(regular_artists[0])}
        log(f"Mapped studio: {regular_artists[0]}")

    # Tags
    all_tags = []

    # General tags
    for tag in categorized_tags["general"]:
        all_tags.append({"name": str(tag)})

    # Copyright/series tags
    for series in categorized_tags["copyrights"]:
        all_tags.append({"name": str(series)})

    # Meta tags
    for meta in categorized_tags["meta"]:
        all_tags.append({"name": str(meta)})

    # NOTE: optional behavior that I personally like.
    #       disabling this for upstream.
    # Add "scraped" marker tag if we have any content
    # (indicates successful scraping)
    # has_content = (
    #     all_tags or
    #     all_performers or
    #     regular_artists
    # )
    # if has_content:
    #   all_tags.append({"name": "[scraped]"})

    if all_tags:
        result["tags"] = all_tags
        log(f"Mapped {len(all_tags)} total tags")

    return result

def main():
    """Main scraper entry point"""
    try:
        # Read input
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
            log("No filename/path/url/title in input - returning empty")
            print(json.dumps({}))
            return

        # Try to extract post ID from filename first (r34_* format)
        post_id = extract_post_id_from_filename(file_path)
        md5_hash = None

        if post_id:
            # Direct scraping from post ID
            log(f"Using post ID from filename: {post_id}")
        else:
            # Try md5 hash extraction
            md5_hash = extract_md5_from_path(file_path)
            
            if md5_hash:
                log(f"Extracted md5: {md5_hash}")

                # Try scraping search page (no API needed!)
                log("Trying md5 lookup via search page")
                post_id = get_post_id_from_md5_search(md5_hash)

                if not post_id:
                    log("Could not find post by md5 hash - will return search URL")
                    # Don't return early - we'll provide a search URL instead
            else:
                log("Could not extract post ID or md5 from filename")
                print(json.dumps({}))
                return

        # If we have a post_id, scrape HTML for categorized tags
        if post_id:
            categorized_tags = scrape_html_tags(post_id)

            if categorized_tags is None:
                # Temporary failure (rate limit, timeout, server error)
                # Return empty result - don't pollute library with error tags
                log("Temporary failure (rate limit or server error) - returning empty")
                print(json.dumps({}))
                return
            elif categorized_tags is False:
                # Permanent failure (404, post doesn't exist)
                log("Post does not exist (404) - returning empty")
                print(json.dumps({}))
                return
            elif not categorized_tags:
                # Empty dict or other falsy value
                log("No tags extracted - returning empty")
                print(json.dumps({}))
                return

            # Check if we actually got any meaningful tags
            has_tags = any([
                categorized_tags.get("characters"),
                categorized_tags.get("artists"),
                categorized_tags.get("copyrights"),
                categorized_tags.get("general"),
                categorized_tags.get("meta")
            ])

            if not has_tags:
                log("Post found but no tags successfully extracted - returning empty to avoid md5 filename pollution")
                print(json.dumps({}))
                return

            # Map to Stashapp format with full data
            result = map_to_stashapp(post_id, categorized_tags, md5_hash)
        else:
            # No post found - return empty instead of search URL
            # This prevents tagging files with md5 filenames from other boorus
            log("No post found for md5 hash - returning empty to avoid pollution from md5 filenames")
            print(json.dumps({}))
            return

        print(json.dumps(result))
        log("Scrape successful!")

    except Exception as e:
        log(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Don't tag with error - return empty to avoid polluting library
        print(json.dumps({}))

if __name__ == "__main__":
    main()
