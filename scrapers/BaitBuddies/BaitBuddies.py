import json
import re
import urllib.parse
import urllib.request
from datetime import date as datetype, timedelta

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import feet_to_cm, lb_to_kg, scraper_args

ensure_requirements("lxml", "cloudscraper")
from lxml import html  # noqa: E402
import cloudscraper  # noqa: E402

HAIR_COLORS = {
    "blond": "Blonde",
    "blonde": "Blonde",
    "brown": "Brown",
    "brunette": "Brown",
    "black": "Black",
    "red": "Red",
    "auburn": "Auburn",
    "grey": "Grey",
    "gray": "Grey",
    "bald": "Bald",
}

EYE_COLORS = {
    "blue": "Blue",
    "brown": "Brown",
    "green": "Green",
    "grey": "Grey",
    "gray": "Grey",
    "hazel": "Hazel",
    "red": "Red",
}

# Removing conflict with existing StashDB "Straight" tag, which don't apply
# to these scenes.
TAG_BLACKLIST = {"straight"}

# The age-verification wall checks for this cookie, no session/token needed.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Cookie": "welcome=true",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as res:
            if res.status != 200:
                log.error(f"Request to '{url}' failed with status code {res.status}")
                return None
            return html.fromstring(res.read().decode())
    except urllib.error.URLError as e:
        log.error(f"Request to '{url}' failed: {e}")
        return None


def meta(tree, prop):
    return next(iter(tree.xpath(f'//meta[@property="{prop}"]/@content')), None)


def find_image(tree, video_id):
    """
    og:image is a tiny thumbnail. The custom_thumbs poster (the same
    image used as the player's poster frame) is the cover art for the scene,
    so preferring that; fall back to a gallery still, then to og:image.
    """
    if video_id:
        return f"https://baitbuddies.com/media/thumbs/custom_thumbs/{video_id}.jpg"
    gallery = next(
        iter(
            tree.xpath(
                '//div[@class="video-gallery"]/div[@class="thumb"]'
                '/a[contains(@href,"/media/galleries/")]/@href'
            )
        ),
        None,
    )
    if gallery:
        return gallery
    return meta(tree, "og:image")


def find_date(video_id, model_url):
    """
    The scene page has no release date, but each model's page lists
    every one of their scenes alongside a "Release Date". Walking the involved
    model's scene list (following pagination, if any) looking for the entry that
    links to the requested scene, identified by its numeric id.
    """
    next_url = model_url
    for _ in range(30):
        if not next_url:
            break
        tree = fetch(next_url)
        if tree is None:
            break

        matches = tree.xpath(
            f'//div[contains(@class,"item-col")]'
            f'[.//a[contains(@href, "-{video_id}.html")]]'
        )
        if matches:
            release = matches[0].xpath(
                './/b[normalize-space(text())="Release Date:"]'
                "/following-sibling::text()"
            )
            if not release:
                return None
            m, d, y = release[0].strip().split("/")
            return f"20{y}-{m}-{d}"

        next_href = next(iter(tree.xpath('//a[@rel="next"]/@href')), None)
        next_url = urllib.parse.urljoin(next_url, next_href) if next_href else None

    log.warning(f"Could not find a release date for video id '{video_id}'")
    return None


WAYBIG_STUDIO_URL = "https://www.waybig.com/studios/73/bait-buddies/"
WAYBIG_MONTHS = {
    m: i
    for i, m in enumerate(
        "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1
    )
}


def find_waybig_url(date, performer_names):
    """
    WayBig runs its own writeup of most Bait Buddies scenes, on a reverse-
    chronological archive. There's no shared id to match on, so the scene
    is identified by release date, cross-checked against a credited
    performer's first name to guard against same-day collisions. Only the
    matched URL is used - no other WayBig data is pulled in.

    WayBig's own posting date can land a day off from Bait Buddies' own
    release date (timezone/publish-lag differences between the two sites),
    so dates are matched within a +/-1 day tolerance rather than exactly.

    The static pageN.html links advertised on the page are dead (redirect
    back to page 1), but "?page=N" works and paginates correctly.
    """
    first_names = [n.split()[0].lower() for n in performer_names if n]

    target = datetype.fromisoformat(date)
    date_min = (target - timedelta(days=1)).isoformat()
    date_max = (target + timedelta(days=1)).isoformat()

    for page in range(1, 16):  # the archive currently spans ~13 pages
        page_url = WAYBIG_STUDIO_URL if page == 1 else f"{WAYBIG_STUDIO_URL}?page={page}"
        tree = fetch(page_url)
        if tree is None:
            break

        items = tree.xpath('//div[@class="item-col col -video"]')
        if not items:
            break

        for item in items:
            date_text = next(iter(item.xpath('.//span[@class="item-date"]/text()')), "")
            try:
                month, day, year = date_text.replace(",", "").split()
                item_date = f"{year}-{WAYBIG_MONTHS[month[:3]]:02d}-{int(day):02d}"
            except (ValueError, KeyError):
                continue

            # The archive is strictly reverse-chronological, so once an item
            # is older than the tolerance window, the target was never
            # posted - no need to keep paging through even older entries.
            if item_date < date_min:
                return None
            if item_date > date_max:
                continue

            # Not every post is tagged with performer names; only use the
            # cross-check when there's actually something to check against.
            models_text = " ".join(item.xpath('.//span[@class="item-models"]//text()')).lower()
            if models_text and not any(name in models_text for name in first_names):
                continue

            href = next(iter(item.xpath('.//a[contains(@href,"/video/")]/@href')), None)
            if href:
                return href

    return None


GEVI_COMPANY_ID = 7282
GEVI_EPISODES_URL = "https://gayeroticvideoindex.com/coep"


def find_gevi_url(date, performer_names):
    """
    GEVI's episode list for this company is loaded from a small JSON API
    rather than static HTML. Matched the same way as WayBig: exact release
    date, cross-checked against a credited performer's first name to guard
    against same-day collisions. Only the matched URL is used - no other
    GEVI data (title, description, images) is pulled in.
    """
    if not performer_names:
        return None

    first_names = [n.split()[0].lower() for n in performer_names if n]

    params = urllib.parse.urlencode(
        {
            "CompanyID": GEVI_COMPANY_ID,
            "draw": 1,
            "start": 0,
            "length": 100,
            "search[value]": performer_names[0],
        }
    )
    req = urllib.request.Request(f"{GEVI_EPISODES_URL}?{params}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as res:
            if res.status != 200:
                return None
            payload = json.loads(res.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError):
        return None

    for row in payload.get("data", []):
        if len(row) < 4 or row[1] != date:
            continue

        performers_html = row[3].lower()
        if not any(name in performers_html for name in first_names):
            continue

        m = re.search(r"episode/(\d+)", row[2])
        if m:
            return f"https://gayeroticvideoindex.com/episode/{m.group(1)}"

    return None


IAFD_STUDIO_URL = "https://www.iafd.com/studio.rme/studio=6657/baitbuddies.com.htm"

_iafd_scraper = None


def iafd_sequel_number(title):
    m = re.search(r"\((?:round|part)\s*(\d+)\)\s*$", title, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(?<!\d)(\d+)\s*$", title)
    if m:
        return int(m.group(1))
    return None


def find_iafd_url(date, part_match, performer_names):
    """
    IAFD catalogs every Bait Buddies release in one big alphabetical table
    (title, label, year - no exact date, and no pagination to worry about).
    There's no shared id, so matching relies on every credited performer's
    first name appearing in the title (IAFD formats these the same way
    this scraper builds Title: "X and Y"), cross-checked against the
    release year and any "Part N"/"(Round N)" sequel suffix to disambiguate
    scenes with the same cast. Cloudflare blocks plain requests here, hence
    `cloudscraper`. Only the matched URL is used - no other IAFD data
    (label, year, etc.) is pulled in.
    """
    global _iafd_scraper
    if not performer_names:
        return None

    first_names = [n.split()[0].lower() for n in performer_names if n]

    if _iafd_scraper is None:
        _iafd_scraper = cloudscraper.create_scraper()
    try:
        res = _iafd_scraper.get(IAFD_STUDIO_URL, timeout=(5, 20))
    except Exception as e:
        log.warning(f"IAFD request failed: {e}")
        return None
    if res.status_code != 200:
        return None

    tree = html.fromstring(res.content)
    target_year = date.split("-")[0] if date else None
    target_number = int(part_match) if part_match else None

    candidates = []
    for row in tree.xpath('//table[@id="studio"]/tbody/tr'):
        title_text = next(iter(row.xpath("./td[1]/a/text()")), "")
        href = next(iter(row.xpath("./td[1]/a/@href")), None)
        year = next(iter(row.xpath("./td[3]/text()")), "").strip()
        if not title_text or not href:
            continue

        if not all(name in title_text.lower() for name in first_names):
            continue

        candidates.append((title_text, year, href))

    if target_year:
        by_year = [c for c in candidates if c[1] == target_year]
        if by_year:
            candidates = by_year

    if len(candidates) == 1:
        return f"https://www.iafd.com{candidates[0][2]}"

    by_number = [c for c in candidates if iafd_sequel_number(c[0]) == target_number]
    if len(by_number) == 1:
        return f"https://www.iafd.com{by_number[0][2]}"

    return None


def order_performers_by_filename(og_title, performers):
    """
    The video's internal filename lists performers in a specific order
    (e.g. "BB1018_M_Duke_Riley" goes Duke, then Riley Mitchel).
    """
    stem = re.sub(r"\.\w+$", "", og_title)
    tokens = stem.split("_")[1:]  # drop the leading release code token

    remaining = list(performers)
    ordered = []
    for token in tokens:
        for p in remaining:
            if p["name"].split()[0].lower() == token.lower():
                ordered.append(p)
                remaining.remove(p)
                break

    if not ordered:
        return performers

    ordered.extend(remaining)
    return ordered


def scene_from_url(url):
    tree = fetch(url)
    if tree is None:
        return None

    # Each role group for performers is split into "Straight:", "Bait:" as
    # its own div. Using that only as a fallback base order (Straight before Bait).
    role_groups = []
    for group in tree.xpath('//div[@class="new-video-models"]/div[@class="new-video-model"]'):
        role = next(iter(group.xpath('.//div[@class="sub-label"]/text()')), "").strip().rstrip(":")
        people = [
            {"name": a.text_content().strip(), "urls": [a.get("href")] if a.get("href") else []}
            for a in group.xpath('.//a[@class="desc"]')
            if a.text_content().strip()
        ]
        role_groups.append((role, people))

    role_groups.sort(key=lambda rg: 0 if rg[0].lower() == "straight" else 1)
    performers = [p for _, people in role_groups for p in people]

    og_title = meta(tree, "og:title") or ""
    code_match = re.match(r"^([A-Za-z0-9]+)_", og_title)
    performers = order_performers_by_filename(og_title, performers)

    paragraphs = [
        text.replace("\xa0", " ").strip()
        for text in tree.xpath('//div[@id="description"]//text()')
        if text.strip()
    ]
    details = "\n\n".join(paragraphs)

    # Sequel scenes with the same cast call this out right up top, either
    # tacked onto the greeting ("Welcome back to BaitBuddies.com!  PART 2")
    # or as its own line ("Part 2 of Perf A and Perf B", "Round 2 of Perf A
    # and Perf B"), so it's enough to check just the first couple of
    # paragraphs. "Round" is treated the same as "Part" for a consistent
    # title suffix.
    part_match = None
    for paragraph in paragraphs[:2]:
        m = re.search(r"\b(?:part|round)\s*(\d+)\b", paragraph, re.IGNORECASE)
        if m:
            part_match = m.group(1)
            break

    tags = [
        text.strip()
        for text in tree.xpath('//div[@class="tags-box"]/a/text()')
        if text.strip() and text.strip().lower() not in TAG_BLACKLIST
    ]

    video_id_match = re.search(r"-(\d+)\.html", url)
    video_id = video_id_match.group(1) if video_id_match else None

    names = [p["name"] for p in performers]
    if len(names) > 2:
        title = ", ".join(names[:-1]) + ", and " + names[-1]
    elif len(names) == 2:
        title = names[0] + " and " + names[1]
    else:
        title = names[0] if names else ""
    if part_match:
        title += f", Part {part_match}"

    code = code_match.group(1).lower() if code_match else None
    # Older releases were coded without the "bb" prefix (e.g. "337" instead
    # of "bb337"), so add it back in for a consistent code namespace.
    if code and not code.startswith("bb"):
        code = f"bb{code}"

    scene = {
        "title": title,
        "code": code,
        "details": details,
        "urls": [url],
        "image": find_image(tree, video_id),
        "studio": {"name": "Bait Buddies", "urls": ["https://www.baitbuddies.com/"]},
        "tags": [{"name": t} for t in tags],
        "performers": performers,
    }

    if video_id and performers and performers[0]["urls"]:
        date = find_date(video_id, performers[0]["urls"][0])
        if date:
            scene["date"] = date
            waybig_url = find_waybig_url(date, [p["name"] for p in performers])
            if waybig_url:
                scene["urls"].append(waybig_url)
            gevi_url = find_gevi_url(date, [p["name"] for p in performers])
            if gevi_url:
                scene["urls"].append(gevi_url)
            iafd_url = find_iafd_url(date, part_match, [p["name"] for p in performers])
            if iafd_url:
                scene["urls"].append(iafd_url)

    return {k: v for k, v in scene.items() if v not in (None, "", [])}


def performer_from_url(url):
    tree = fetch(url)
    if tree is None:
        return None

    name = next(
        iter(tree.xpath('//div[@class="profile-disc"]/h2/text()')), ""
    ).strip()

    # The Body stats block is a flat run of "Label: " text nodes each
    # immediately followed by a <b> value, e.g. "Height: <b>5`10``</b>".
    stats = {}
    for b in tree.xpath(
        '//div[contains(@class,"profile-stats")][.//span[text()="BODY"]]//b'
    ):
        label = b.xpath("preceding-sibling::text()[1]")
        if label:
            stats[label[0].strip().rstrip(":").strip()] = (b.text or "").strip()

    performer = {
        "name": name,
        "gender": "Male",
        "urls": [url],
        "image": next(
            iter(tree.xpath('//img[@class="img-thumbnail"]/@src')), None
        ),
        "height": feet_to_cm(stats.get("Height", "")),
        "weight": lb_to_kg(stats.get("Weight", "")),
        "hair_color": HAIR_COLORS.get(stats.get("Hair", "").lower()),
        "eye_color": EYE_COLORS.get(stats.get("Eyes", "").lower()),
        "circumcised": stats.get("Cock Type", "").lower() or None,
    }

    cock_size = stats.get("Cock Size", "").replace("`", "").strip()
    if cock_size:
        try:
            performer["penis_length"] = str(round(float(cock_size) * 2.54, 1))
        except ValueError:
            pass

    return {k: v for k, v in performer.items() if v not in (None, "", [])}


if __name__ == "__main__":
    op, args = scraper_args()

    match op:
        case "scene-by-url":
            result = scene_from_url(args["url"]) if args.get("url") else None
        case "performer-by-url":
            result = performer_from_url(args["url"]) if args.get("url") else None
        case _:
            log.error(f"Unsupported operation: {op}")
            exit(1)

    print(json.dumps(result))
