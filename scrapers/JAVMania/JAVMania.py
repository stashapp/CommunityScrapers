"""Stash scraper for jav-mania.net (uncensored + censored JAV, English) with
avhinban.com (censored JAV, Japanese) as a fallback.

Standard library only. Stash runs it as:
    python JAVMania.py <mode>
with a JSON fragment on stdin and reads JSON from stdout.

Modes: sceneByURL, sceneByFragment, sceneByName, sceneByQueryFragment
"""

import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

JM = "https://www.jav-mania.net"
AV = "https://avhinban.com"
UA = "Mozilla/5.0 (compatible; stash-javmania-scraper/1.0; +https://www.jav-mania.net/)"
TIMEOUT = 20

# jav-mania site slug -> (aliases seen in file names, id regex, id normaliser)
# Ids are matched after the site alias has been found in the name.
D6 = r"(\d{6})"
SITES = {
    "caribbeancom": (
        ["caribbeancom", "carib"],
        D6 + r"[-_ ](\d{3})",
        lambda m: f"{m[0]}-{m[1]}",
    ),
    "caribbeanpremium": (
        ["caribbeancompr", "caribbeanpremium", "caribpr", "carib-pr", "carib_pr"],
        D6 + r"[-_ ](\d{3})",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "1pondo": (["1pondo", "1pon"], D6 + r"[-_ ](\d{3})", lambda m: f"{m[0]}_{m[1]}"),
    "pacopacomama": (
        ["pacopacomama", "paco"],
        D6 + r"[-_ ](\d{3})",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "10musume": (
        ["10musume", "10mu"],
        D6 + r"[-_ ](\d{2})(?!\d)",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "muramura": (["muramura"], D6 + r"[-_ ](\d{3,4})", lambda m: f"{m[0]}_{m[1]}"),
    "heyzo": (["heyzo"], r"(?:hd[-_ ]?)?(\d{4})", lambda m: m[0]),
    "kin8": (["kin8tengoku", "kin8"], r"(\d{4})", lambda m: m[0]),
    "nyoshin": (["nyoshin"], r"(n\d{3,5})", lambda m: m[0]),
    "hgmo": (["heydouga", "hgmo"], r"(\d{4})", lambda m: m[0]),
    "h4610": (["h4610"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "c0930": (["c0930"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "h0930": (["h0930"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "pikkur": (["pikkur"], r"(\d{5})", lambda m: m[0]),
    "av9898": (["av9898"], r"(\d{4})", lambda m: m[0]),
}
# Names without a site alias: try these sites in order for the bare id shape.
BARE = [
    (re.compile(D6 + r"-(\d{3})(?!\d)"), ["caribbeancom"]),
    (
        re.compile(D6 + r"_(\d{3})(?!\d)"),
        ["1pondo", "caribbeanpremium", "pacopacomama"],
    ),
    (re.compile(D6 + r"_(\d{2})(?!\d)"), ["10musume"]),
]
CENSORED = re.compile(r"(?<![a-z0-9])([a-z]{2,6})[-_ ]?0*(\d{2,5})(?![0-9])")


def log(msg):
    sys.stderr.write(f"[JAVMania] {msg}\n")


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            log(f"HTTP {e.code} for {url}")
    except (
        urllib.error.URLError,
        OSError,
        ValueError,
    ) as e:  # network errors must not crash Stash
        log(f"{type(e).__name__} for {url}: {e}")
    return None, None


def text(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment or "")
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def meta(page, prop):
    m = re.search(
        rf'<meta (?:property|name)="{re.escape(prop)}" content="([^"]*)"', page
    )
    return html.unescape(m.group(1)) if m else None


def ld_json(page, kind):
    for raw in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL
    ):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == kind:
            return data
    return {}


def detail_rows(page):
    """<table class="detail-table"> rows as {header: inner html}."""
    m = re.search(r'<table class="detail-table">(.*?)</table>', page, re.DOTALL)
    rows = {}
    for th, td in re.findall(
        r"<tr><th>(.*?)</th><td>(.*?)</td></tr>", m.group(1) if m else "", re.DOTALL
    ):
        rows[text(th)] = td
    return rows


def performers_from(cell):
    """Names are separated by <br> (one ja alias each) or by ", " with the ja
    aliases listed afterwards in the same order."""
    out = []
    for part in re.split(r"<br\s*/?>", cell or ""):
        names = [
            n.strip()
            for n in text(re.sub(r'<span lang="ja">.*?</span>', "", part)).split(",")
        ]
        names = [n for n in names if n]
        jas = [text(j) for j in re.findall(r'<span lang="ja">【(.*?)】</span>', part)]
        for i, name in enumerate(names):
            p = {"name": name}
            if len(jas) == len(names) and jas[i]:
                p["aliases"] = jas[i]
            out.append(p)
    return out


def scrape_javmania(url):
    final, page = fetch(url)
    if not page:
        return None
    video = ld_json(page, "VideoObject")
    rows = detail_rows(page)
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL)
    title = text(h1.group(1)) if h1 else video.get("name")
    code = None
    if "Content ID" in rows:  # uncensored studio page
        code = text(rows["Content ID"])
    elif "Code" in rows:  # censored (FANZA) page
        code = text(rows["Code"]).split()[0]
    if title and code:  # drop the "(CODE)" suffix(es) from the display title
        title = (
            re.sub(
                rf"(\s*\([^()]*{re.escape(code)}[^()]*\))+$",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()
            or title
        )
    summary = re.search(r'<p class="summary">(.*?)</p>', page, re.DOTALL)
    tag_row = re.search(r'<div class="tag-row">(.*?)</div>', page, re.DOTALL)
    tags = [
        text(t)
        for t in re.findall(
            r'<(?:a|span) class="tag"[^>]*>(.*?)</(?:a|span)>',
            tag_row.group(1) if tag_row else "",
        )
    ]
    studio = text(rows.get("Site") or rows.get("Studio") or "")
    perf = performers_from(rows.get("Performer") or rows.get("Performers"))
    if not perf:
        perf = [
            {"name": a.get("name")} for a in video.get("actor", []) if a.get("name")
        ]
    date = text(rows.get("Release date") or "") or (video.get("uploadDate") or "")[:10]
    scene = {
        "title": title,
        "code": code,
        "details": text(summary.group(1)) if summary else video.get("description"),
        "date": date[:10] or None,
        "urls": [final or url],
        "image": meta(page, "og:image") or (video.get("thumbnailUrl") or [None])[0],
        "tags": [{"name": t} for t in tags if t]
        or [{"name": g} for g in video.get("genre", [])],
        "performers": perf,
    }
    if studio:
        scene["studio"] = {"name": studio}
    return clean(scene)


def scrape_avhinban(url):
    final, page = fetch(url)
    if not page:
        return None
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL)
    head = text(h1.group(1)) if h1 else ""
    code, _, title = head.partition(" ")
    info = {}
    dl = re.search(r'<dl class="info">(.*?)</dl>', page, re.DOTALL)
    for dt, dd in re.findall(
        r"<dt>(.*?)</dt><dd>(.*?)</dd>", dl.group(1) if dl else "", re.DOTALL
    ):
        info[text(dt)] = dd
    img = re.search(r'<div class="pkg"><img src="([^"]+)"', page)
    desc = re.search(
        r"<details><summary>.*?</summary><p>(.*?)</p></details>", page, re.DOTALL
    )
    scene = {
        "title": title or head,
        "code": code or None,
        "details": text(desc.group(1)) if desc else None,
        "date": text(info.get("発売日", "")) or None,
        "urls": [final or url],
        "image": html.unescape(img.group(1)) if img else meta(page, "og:image"),
        "performers": [
            {"name": text(a)}
            for a in re.findall(r"<a [^>]*>(.*?)</a>", info.get("出演者", ""))
        ],
        "tags": [
            {"name": text(a)}
            for a in re.findall(r"<a [^>]*>(.*?)</a>", info.get("ジャンル", ""))
        ],
        "director": text(info.get("監督", "")) or None,
    }
    maker = text(info.get("メーカー", ""))
    if maker:
        scene["studio"] = {"name": maker}
    return clean(scene)


def clean(scene):
    return {k: v for k, v in scene.items() if v not in (None, "", [], {})}


def scrape_url(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.endswith("jav-mania.net"):
        return scrape_javmania(url)
    if host.endswith("avhinban.com"):
        return scrape_avhinban(url)
    return None


def uncensored_urls(name):
    """Candidate jav-mania /movies/ URLs for a file name or title."""
    s = name.lower()
    found = []
    for slug, (aliases, id_re, norm) in SITES.items():
        for alias in aliases:
            pos = re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z])", s)
            if not pos:
                continue
            # look for the id anywhere in the name (before or after the alias)
            m = re.search(r"(?<![0-9a-z])" + id_re, s[pos.end() :]) or re.search(
                r"(?<![0-9a-z])" + id_re, s
            )
            if m:
                found.append(f"{JM}/movies/{slug}/{norm(m.groups())}/")
            break
    if not found:
        for rx, slugs in BARE:
            m = rx.search(s)
            if m:
                found += [
                    f"{JM}/movies/{slug}/{SITES[slug][2](m.groups())}/"
                    for slug in slugs
                ]
                break
    return found


def censored_codes(name):
    s = name.lower()
    codes = []
    for prefix, num in CENSORED.findall(s):
        if prefix in ("hd", "fhd", "mp", "avi", "mkv", "part", "cd", "disc", "x", "h"):
            continue
        codes.append(f"{prefix}-{int(num):03d}")
    return codes


def avhinban_lookup(code):
    _, page = fetch(f"{AV}/search/?q={urllib.parse.quote(code.upper())}")
    if not page:
        return None
    for slug in re.findall(r'href="/works/([^"/]+)/"', page):
        if same_code(slug, code):  # the site search is fuzzy
            return f"{AV}/works/{slug}/"
    return None


def lookup(name):
    """Best scene for a free-text name (file name, title or code)."""
    if not name:
        return None
    if re.match(r"https?://", name.strip()):
        return scrape_url(name.strip())
    for url in uncensored_urls(name):
        scene = scrape_javmania(url)
        if scene:
            return scene
    for code in censored_codes(name):
        scene = scrape_javmania(f"{JM}/jav/{code}/")
        if scene:
            av = avhinban_lookup(code)
            if av:
                scene["urls"].append(av)
            return scene
        av = avhinban_lookup(code)
        if av:
            scene = scrape_avhinban(av)
            # the site search is fuzzy: only accept the exact code
            if scene and same_code(scene.get("code"), code):
                return scene
    return None


def same_code(a, b):
    norm = lambda c: re.sub(
        r"(?<=[a-z])0+(?=\d)", "", re.sub(r"[^a-z0-9]", "", (c or "").lower())
    )
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    # FANZA ids may carry a numeric label prefix: 138sfrd017 == SFRD-017
    return (
        a == b
        or re.fullmatch(r"\d+" + re.escape(b), a) is not None
        or re.fullmatch(r"\d+" + re.escape(a), b) is not None
    )


def first_url(fragment):
    for u in (fragment.get("urls") or []) + [fragment.get("url")]:
        if u and urllib.parse.urlparse(u).netloc.lower().endswith(
            ("jav-mania.net", "avhinban.com")
        ):
            return u
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        fragment = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        fragment = {}
    result = None
    if mode == "sceneByURL":
        result = scrape_url(fragment.get("url", ""))
    elif mode in ("sceneByFragment", "sceneByQueryFragment"):
        url = first_url(fragment)
        result = scrape_url(url) if url else None
        for key in ("code", "title"):
            if result is None and fragment.get(key):
                result = lookup(fragment[key])
    elif mode == "sceneByName":
        scene = lookup(fragment.get("name", ""))
        result = [scene] if scene else []
    else:
        log(f"unknown mode {mode!r}")
    print(
        json.dumps(
            result if result is not None else ({} if mode != "sceneByName" else []),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
