import sys
import json
import re
import os
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup as bs

# =============== CONFIG / AUTH ===============
# If the members site requires login, you can paste your cookie string here.
# Example from browser's dev tools "Request Headers" -> Cookie:
#   "lbgauth=...; PHPSESSID=...; other=..."
AUTH_COOKIE = ""  # <-- fill this if needed, otherwise leave empty

# You can also add other headers if you like
BASE_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}
if AUTH_COOKIE:
    BASE_HEADERS["Cookie"] = AUTH_COOKIE


# =============== HELPERS ===============

def debug(msg: str) -> None:
    """Write debug messages to stderr so Stash can show them in logs."""
    sys.stderr.write(f"[LadyboyGold] {msg}\n")


def read_json_input() -> Dict[str, Any]:
    """Read the JSON Stash sends on stdin."""
    raw = sys.stdin.read() or ""
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        debug(f"Failed to decode JSON input: {e} | raw={raw!r}")
        return {}


def fetch_page(url: str) -> Optional[str]:
    """Fetch the HTML for the given URL."""
    try:
        debug(f"Fetching URL: {url}")
        res = requests.get(url, headers=BASE_HEADERS, timeout=15)
        debug(f"HTTP status: {res.status_code}")
        if res.status_code != 200:
            debug(f"Non-200 response: {res.status_code}")
            return None
        return res.text
    except Exception as e:
        debug(f"Error fetching URL {url}: {e}")
        return None

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug")

def save_debug_html(html: str, url: str, kind: str = "performer") -> str:
    """
    Save raw HTML to a debug/*.html file so you can inspect what the site returned.
    Returns the full path, or '' on failure.
    """
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        # Make a filesystem-safe version of the URL for the filename
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", url)
        filename = f"{kind}_{ts}_{safe[:80]}.html"
        path = os.path.join(DEBUG_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    except Exception as e:
        debug(f"Failed to save debug HTML: {e}")
        return ""

def is_login_page(html: str) -> bool:
    """Return True if this HTML is clearly the login page, not a performer page."""
    if not html:
        return False
    # Look for auth.form and login form markers
    if 'form action="/auth.form"' in html:
        return True
    if 'id="loginForm"' in html:
        return True
    if "LadyboyGold Network Members Area" in html:
        return True
    return False

def extract_image_from_style(style: str) -> Optional[str]:
    """
    Extract image URL from a CSS style like:
      background: url('/path/to/img.jpg') center center / cover no-repeat;
    """
    if not style:
        return None
    m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
    if not m:
        return None
    path = m.group(1)
    if path.startswith("http://") or path.startswith("https://"):
        return path
    # LadyboyGold tour/members images are usually relative to https://ladyboygold.com/
    return f"https://ladyboygold.com/{path.lstrip('/')}"


def parse_scene_from_html(url: str, html: str) -> Dict[str, Any]:
    """
    Parse the LadyboyGold scene HTML into a Stash-compatible scene dict.
    Supports the members layout with #nowPlayingDetails and falls back
    to older/tour-style selectors where needed.
    """
    soup = bs(html, "html.parser")

    now = soup.select_one("#nowPlayingDetails")

    # ========== TITLE ==========
    title = ""

    # 1) Members layout: direct text of <h2> in #nowPlayingDetails
    if now:
        h2_now = now.select_one("h2")
        debug(f"nowPlayingDetails h2 found: {bool(h2_now)}")
        if h2_now:
            direct = h2_now.find(string=True, recursive=False)
            if direct:
                candidate = direct.strip()
                debug(f"nowPlayingDetails candidate title: {repr(candidate)}")
                if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
                    title = candidate

    # 2) Original tour layout: <div class="show_video"><h2>...</h2></div>
    if not title:
        title_elem = soup.select_one("div.show_video h2")
        if title_elem:
            candidate = title_elem.get_text(strip=True)
            debug(f"show_video h2 candidate title: {repr(candidate)}")
            if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
                title = candidate

    # 3) Generic fallbacks: h1 / h2
    if not title:
        h1 = soup.select_one("h1")
        if h1:
            candidate = h1.get_text(strip=True)
            debug(f"h1 candidate title: {repr(candidate)}")
            if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
                title = candidate

    if not title:
        h2_any = soup.select_one("h2")
        if h2_any:
            candidate = h2_any.get_text(strip=True)
            debug(f"generic h2 candidate title: {repr(candidate)}")
            if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
                title = candidate

    # 4) og:title
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            candidate = og["content"].strip()
            debug(f"og:title candidate: {repr(candidate)}")
            if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
                title = candidate

    # 5) <title> tag, cleaned
    if not title and soup.title and soup.title.string:
        candidate = soup.title.string.strip()
        debug(f"<title> candidate: {repr(candidate)}")
        candidate = re.sub(r"\s*[\|\-–]\s*Ladyboy\s*Gold.*$", "", candidate, flags=re.I)
        if candidate and not re.match(r"^Watch\s+Video\s+from", candidate, flags=re.I):
            title = candidate

    # Final cleanup: strip trailing " 4K"
    if title:
        title = re.sub(r"\s+4[Kk]$", "", title).strip()

    # ========== DESCRIPTION ==========
    details = ""

    # Members layout: story inside #nowPlayingDetails
    if now:
        set_story = now.select_one("div.setStory")
        if set_story:
            details = set_story.get_text(" ", strip=True)

    # Fallback: older tour layout (hidden description paragraphs)
    if not details:
        detail_elems = soup.select("div.setDescription p.d-none")
        details_parts: List[str] = []
        for p in detail_elems:
            text = p.get_text(" ", strip=True)
            if text:
                details_parts.append(text)
        if details_parts:
            details = "\n\n".join(details_parts).strip()

    # ========== TAGS ==========
    tag_elems = soup.select("div.tags a")
    tags: List[Dict[str, str]] = []
    for a in tag_elems:
        t = a.get_text(strip=True)
        if t:
            tags.append({"name": t})

    # ========== PERFORMERS / DATE / STUDIO ==========
    performers: List[Dict[str, str]] = []
    date_iso: Optional[str] = None
    studio_name = "LadyboyGold"  # default network name

    if now:
        detail = now.select_one("div.setDetail")
        if detail:
            # Performers: span.setActor a
            perf_links = detail.select("span.setActor a")
            for a in perf_links:
                name = a.get_text(strip=True)
                # strip trailing rating digits like "Ning 4"
                name = re.sub(r"\s*\d+$", "", name).strip()
                if name:
                    performers.append({"name": name})

            # Date: last span.setUpload, like "September 12, 2020 to"
            upload_spans = detail.select("span.setUpload")
            if upload_spans:
                date_text = upload_spans[-1].get_text(" ", strip=True)
                # remove trailing "to"
                date_text = re.sub(r"\s+to$", "", date_text).strip()
                debug(f"upload date text: {repr(date_text)}")
                try:
                    dt = datetime.strptime(date_text, "%B %d, %Y")
                    date_iso = dt.strftime("%Y-%m-%d")
                except ValueError:
                    debug(f"Could not parse date: {repr(date_text)}")

            # Studio / channel: span.setChannel (e.g. "Ladyboy Obsession")
            channel_span = detail.select_one("span.setChannel")
            if channel_span:
                chan = channel_span.get_text(" ", strip=True)
                if chan:
                    studio_name = chan

    # Old performer fallback (tour layout)
    if not performers:
        performer_elems = soup.select("div.show_video h3")
        for h3 in performer_elems:
            name = h3.get_text(strip=True)
            if not name:
                continue
            name = re.sub(r"^Ladyboy\s+", "", name).strip()
            parts = [n.strip() for n in name.split(",") if n.strip()]
            for part in parts:
                performers.append({"name": part})

    # ========== IMAGE (POSTER) + CODE ==========
    image_url = None
    code = None

    # 1) Prefer the <video> poster attribute in the Now Playing block
    video = None
    if now:
        video = now.select_one("video")
    if not video:
        # fallback: any video tag on the page
        video = soup.select_one("video")

    if video and video.get("poster"):
        image_url = video.get("poster").strip()
        debug(f"Found video poster: {image_url}")

    # 2) Try to get a code from the URL (?galid=...)
    m_code = re.search(r"[?&]galid=(\d+)", url)
    if m_code:
        code = m_code.group(1)

    # 3) Fallback: old style-based thumbnail (tour layout)
    if not image_url:
        img_elem = soup.select_one("div.show_video img[style]")
        if img_elem:
            style_attr = img_elem.get("style", "")
            image_url = extract_image_from_style(style_attr)
            debug(f"Fallback style image: {image_url}")
            m = re.search(r"[?&]gal=([^&]+)", style_attr)
            if m and not code:
                code = m.group(1)


    # ========== BUILD FINAL SCENE DICT ==========
    scene: Dict[str, Any] = {}

    scene["title"] = title or url
    scene["url"] = url

    if details:
        scene["details"] = details

    # Date if we could parse it
    if date_iso:
        scene["date"] = date_iso

    # Studio (channel if available, else LadyboyGold)
    scene["studio"] = {"name": studio_name}

    if tags:
        scene["tags"] = tags
    if performers:
        scene["performers"] = performers
    if image_url:
        scene["image"] = image_url
    if code:
        scene["code"] = code

    return scene

def parse_performer_from_html(url: str, html: str) -> Dict[str, Any]:
    """
    Parse a LadyboyGold members performer profile page into a Stash performer dict.
    Uses the layout seen on pages like:
      https://members.ladyboygold.com/index.php?&section=1516&actorid=2351

    Example stats block:

      Age: 24
      Birthday: February 7
      Height: 5'7" (175cm)
      Weight: 116.6 lbs (53kg)
      Shoe: 41
      Measurements: 32A-26-31
      Cock: 7" inches (17.8cm)
      Email: N/A
      Phone: N/A
      Location: Pattaya

      <bio paragraph...>
    """
    soup = bs(html, "html.parser")

    performer: Dict[str, Any] = {
        "url": url,
        "gender": "transgender_female",
    }

    # ---------- NAME ----------
    name = None

    # Best source: <span class="titleName">Lita 2</span>
    name_elem = soup.select_one("span.titleName")
    if name_elem:
        name = name_elem.get_text(strip=True)

    # Fallback: h2 with "Model Profile: Name"
    if not name:
        for h2 in soup.find_all("h2"):
            text = h2.get_text(strip=True)
            if text.startswith("Model Profile"):
                parts = text.split(":", 1)
                if len(parts) > 1:
                    name = parts[1].strip()
                break

    if not name:
        debug("Could not find performer name, falling back to URL")
        name = url

    performer["name"] = name

    # ---------- IMAGE ----------
    # Performer image: <img src="/cms_actors/2351.jpg" ...>
    img_elem = soup.select_one('img[src*="/cms_actors/"]')
    if img_elem and img_elem.get("src"):
        src = img_elem["src"].strip()

        if src.startswith("//"):
            image_url = "https:" + src
        elif src.startswith("http://") or src.startswith("https://"):
            image_url = src
        else:
            # Use PUBLIC site, not members, so Stash can fetch without auth
            image_url = "https://www.ladyboygold.com" + src

        performer["image"] = image_url

    # ---------- STATS + BIO ----------
    # First div.story = stats; last div.story = bio paragraph
    story_divs = soup.select("div.story")
    stats_text = ""
    bio_text = ""

    if story_divs:
        stats_text = story_divs[0].get_text("\n", strip=True)
        if len(story_divs) > 1:
            bio_text = story_divs[-1].get_text(" ", strip=True)

    # ========== PARSE STATS LINES ==========
    age_val = None
    birthday_text = None
    height_cm = None
    weight_kg = None
    measurements = None
    cock_cm = None

    for line in stats_text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith("age:"):
            m = re.search(r"Age:\s*(\d+)", line, flags=re.I)
            if m:
                try:
                    age_val = int(m.group(1))
                except ValueError:
                    pass

        elif line.lower().startswith("birthday:"):
            # e.g. "Birthday: February 7"
            m = re.search(r"Birthday:\s*(.*)", line, flags=re.I)
            if m:
                birthday_text = m.group(1).strip()

        elif line.lower().startswith("height:"):
            # e.g. Height: 5'7" (175cm)
            m = re.search(r"\(([0-9]+)cm\)", line)
            if m:
                height_cm = m.group(1)

        elif line.lower().startswith("weight:"):
            # e.g. Weight: 116.6 lbs (53kg)
            m = re.search(r"\(([0-9.]+)kg\)", line)
            if m:
                weight_kg = m.group(1)

        elif line.lower().startswith("measurements:"):
            m = re.search(r"Measurements:\s*(.*)", line, flags=re.I)
            if m:
                measurements = m.group(1).strip()

        elif line.lower().startswith("cock:"):
            # e.g. Cock: 7" inches (17.8cm)
            m = re.search(r"\(([0-9.]+)cm\)", line)
            if m:
                cock_cm = m.group(1)

        # We ignore Location / Email / Phone for now, at your request

    # ---------- SET PARSED FIELDS ----------
    if height_cm:
        performer["height"] = height_cm  # cm
    if weight_kg:
        performer["weight"] = weight_kg  # kg
    if measurements:
        performer["measurements"] = measurements
    if cock_cm:
        # Stash core doesn't have an official penis field,
        # but adding this is still useful if tools read it.
        performer["penis_size"] = cock_cm  # cm

    # ---------- BIRTHDATE from Age + Birthday ----------
    birthdate_iso = None
    if age_val is not None and birthday_text:
        try:
            # Birthday text like "February 7"
            parts = birthday_text.split()
            if len(parts) >= 2:
                month_name = parts[0]
                day_num = int(re.sub(r"\D", "", parts[1]))

                months = [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ]
                if month_name in months:
                    month_index = months.index(month_name) + 1
                    now = datetime.now()
                    current_year = now.year

                    this_year_bday = datetime(current_year, month_index, day_num)
                    extra_year = 1 if this_year_bday > now else 0
                    birth_year = current_year - age_val - extra_year
                    birth_dt = datetime(birth_year, month_index, day_num)
                    birthdate_iso = birth_dt.strftime("%Y-%m-%d")
        except Exception as e:
            debug(f"Error parsing birthdate from age/birthday: {e}")

    if birthdate_iso:
        performer["birthdate"] = birthdate_iso

    # ---------- DESCRIPTION (BIO ONLY) ----------
    # Per your request: REMOVE stats + location from description,
    # and only keep the actual bio/narrative paragraph.
    if bio_text:
        performer["details"] = bio_text

    debug(f"Parsed performer dict: {performer}")
    return performer


def handle_scene_by_url() -> None:
    """Entry point for op = scene-by-url."""
    data = read_json_input()
    url = data.get("url")
    if not url:
        debug("No 'url' provided in JSON input")
        print(json.dumps({}))
        return

    # Ensure tpl=show_video8 is present for proper scene layout
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # if no tpl param, add tpl=show_video8
    if qs.get("tpl", [None])[0] is None:
        qs["tpl"] = ["show_video8"]
        new_query = urlencode(qs, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))
        debug(f"Adjusted URL to include tpl=show_video8: {url}")

    html = fetch_page(url)
    if not html:
        debug("Failed to fetch HTML, returning empty scene")
        print(json.dumps({}))
        return

    scene = parse_scene_from_html(url, html)

    # Log exactly what we send back to Stash
    debug("JSON sent to Stash:\n" + json.dumps(scene, indent=2))

    # This is what Stash actually parses
    print(json.dumps(scene))

def handle_performer_by_url() -> None:
    """Entry point for op = performer-by-url."""
    data = read_json_input()
    url = data.get("url")
    if not url:
        debug("No 'url' provided in JSON input (performer-by-url)")
        print(json.dumps({}))
        return

    html = fetch_page(url)
    if not html:
        debug("Failed to fetch performer HTML, returning empty object")
        print(json.dumps({}))
        return

    performer = parse_performer_from_html(url, html)

    debug("Performer JSON sent to Stash:")
    debug(json.dumps(performer, ensure_ascii=False, indent=2))

    print(json.dumps(performer))


# =============== MAIN ===============

def main() -> None:
    if len(sys.argv) < 2:
        debug("No operation specified (expected e.g. 'scene-by-url' or 'performer-by-url')")
        print(json.dumps({}))
        return

    op = sys.argv[1]

    if op == "scene-by-url":
        handle_scene_by_url()
    elif op == "performer-by-url":
        handle_performer_by_url()
    else:
        debug(f"Unsupported operation: {op}")
        print(json.dumps({}))

if __name__ == "__main__":
    main()
