import json
import re
import urllib.parse
import urllib.request

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import feet_to_cm, lb_to_kg, scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402

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
    if len(names) > 1:
        title = ", ".join(names[:-1]) + " and " + names[-1]
    else:
        title = names[0] if names else ""
    if part_match:
        title += f", Part {part_match}"

    scene = {
        "title": title,
        "code": code_match.group(1).lower() if code_match else None,
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
