#!/usr/bin/env python3
import sys
import json
import requests
import re
import os
from bs4 import BeautifulSoup
from bs4 import NavigableString
from datetime import datetime
from urllib.parse import quote, urlparse

def resolve_url(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        if r.status_code >= 400:
            r = requests.get(url, allow_redirects=True, timeout=10)
        return r.url
    except requests.RequestException as e:
        print(f"Failed to resolve URL: {e}", file=sys.stderr)
        return ""

def get_oldest_wayback_date(url: str) -> str:
    # Simple estimation of when a page was first published, as studio doesn't list
    if urlparse(url).scheme == "":
        url = "https://" + url
    encoded_url = quote(url)
    cdx_api_url = (
        f"https://web.archive.org/cdx/search/cdx?output=json&limit=1&collapse=digest&url={encoded_url}"
    )

    try:
        response = requests.get(cdx_api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if len(data) > 1:
            timestamp_index = data[0].index("timestamp") 
            raw_timestamp = data[1][timestamp_index]
            date_object = datetime.strptime(raw_timestamp, "%Y%m%d%H%M%S")
            return date_object.strftime("%Y-%m-%d")
        else:
            return "No archive found for this URL."
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Error parsing API response.", file=sys.stderr)
        return None
    except (ValueError, IndexError) as e:
        print(f"Error processing date format or list index: {e}", file=sys.stderr)
        return None

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch(url):
    r = requests.get(url, timeout=10, headers=HEADERS)
    r.raise_for_status()
    return r.text

def filtered_descendants(tag):
    if tag is None:
        return []
    return [x for x in tag.descendants if x is not None]

def extract_description(soup):
    desc_el = soup.select_one("body > table div[style*='text-align: justify']")

    if not desc_el:
        print("Warning: description element not found", file=sys.stderr)
        return None

    # Remove source-formatting newlines from text nodes
    for node in filtered_descendants(desc_el):
        if node is None:
            continue 
        if isinstance(node, NavigableString):
            node.replace_with(node.replace("\n", " "))

    for br in desc_el.find_all("br"):
        br.replace_with("\n")

    # Iterate over each 'li' tag and insert the dash at the beginning
    for li in desc_el.find_all("li"):
        dash_string = NavigableString("\n- ")
        li.insert(0, dash_string)

    # Text cleanup 
    text = desc_el.get_text()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    lines = text.splitlines(keepends=True)
    text = "".join(
        line.lstrip(" ") if line.strip() else line
        for line in lines
    )
    text = re.sub(r'(?m)^(?=\S)[ ]+|^[ ]+$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip out extra blanks in bullet point list
    lines = text.splitlines(keepends=True)
    result = []
    after_phrase = False
    for line in lines:
        if "Key highlights of " in line and "include" in line:
            after_phrase = True
            result.append(line)
            continue
        if after_phrase and line.strip() == "":
            continue
        result.append(line)
    text = "".join(result)
    
    text = re.sub(r'(Full\s+(?:Video|Download)\s+Details).*?Key highlights of video include','Key highlights of video include',text,flags=re.DOTALL)
    text = re.sub(r'(Key highlights of video include[^\n]*\n)(?:^[ \t]*\n)+',r'\1',text,flags=re.MULTILINE)

    text = re.split(r"available\s+in\s*:", text, flags=re.I)[0].strip()

    return text if text else None

def studio_name(url):
    studio_map = {
        "girlsgonehypnotized": "Girls Gone Hypnotized",
        "girlsgettingsleepy": "Girls Getting Sleepy",
        "girlspoppingballoons": "Girls Popping Balloons",
        "girlsbarefoot": "Girls Barefoot",
    }

    studioName = None
    for key, value in studio_map.items():
        if key in url.lower():
            studioName = value
            break
    return studioName

def scrape_scene(url):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("body > table > tbody > tr:nth-child(2) > td > table > tbody > tr:nth-child(1) > td:nth-child(1) > span")
    title = re.sub(r"\s+", " ", title_el.get_text()).strip() if title_el else None

    desc=extract_description(soup)

    code = os.path.splitext(os.path.basename(urlparse(url).path))[0]

    urls = []
    for a in soup.find_all("a"):
        img = a.find("img")
        if img and "buynow" in img.get("src", ""):
            urls.append(a.get("href"))

    date = get_oldest_wayback_date(url)
    
    checked_urls = [url]
    for test_url in urls:
        test_url=resolve_url(test_url)
        if test_url!="" and test_url!="https://www.clips4sale.com/studio/48957/gg-fetish-media":
            checked_urls.append(test_url)
    
    studioName = studio_name(url)
    
    return {
        "title": title,
        "details": desc,
        "date": date,
        "urls": checked_urls,
        "code": code,
        "studio": {"name": studioName}
    }

def main():
    try:
        raw = sys.stdin.read().strip()

        if not raw:
            print(json.dumps({"scenes": []}))
            return

        data = json.loads(raw)
        url = data.get("url") or data.get("query")

        scene = scrape_scene(url)

        print(json.dumps(scene))

    except Exception as e:
        print(f"Scraper error: {e}", file=sys.stderr)
        print(json.dumps({"scenes": []}))

if __name__ == "__main__":
    main()
