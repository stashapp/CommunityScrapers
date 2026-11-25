"""Stash scraper for jav-mania.net (uncensored + censored JAV, English) with
avhinban.com (censored JAV, Japanese) for missing fields, fallback and search.

Standard library only. Stash runs it as:
    python JAVMania.py <mode>
with a JSON object on stdin and reads JSON from stdout (UTF-8 both ways).

Modes: sceneByURL, sceneByFragment, sceneByName, sceneByQueryFragment,
       performerByURL, performerByName, performerByFragment
"""

import datetime
import html
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

JM = "https://www.jav-mania.net"
AV = "https://avhinban.com"
ALLOWED_HOSTS = {
    "www.jav-mania.net",
    "jav-mania.net",
    "avhinban.com",
    "www.avhinban.com",
}
UA = "Mozilla/5.0 (compatible; stash-javmania-scraper/1.1; +https://github.com/jav-mania/stash-scraper)"
TIMEOUT = 15  # per request
BUDGET = 60  # seconds for a whole lookup
MAX_BYTES = 3_000_000
START = time.monotonic()
BLOCKED = set()  # hosts that answered 403/429 during this run
FAILED = [0]  # fetches that failed for a reason other than 404

# jav-mania site slug -> (aliases seen in file names, id regex, id normaliser)
D6 = r"(\d{6})"
SEP = r"[-_ .]"
SITES = {
    "caribbeancom": (
        ["caribbeancom", "carib"],
        D6 + SEP + r"(\d{3})",
        lambda m: f"{m[0]}-{m[1]}",
    ),
    "caribbeanpremium": (
        [
            "caribbeancompr",
            "caribbeanpremium",
            "caribpr",
            "carib-pr",
            "carib_pr",
            "carib pr",
        ],
        D6 + SEP + r"(\d{3})",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "1pondo": (["1pondo", "1pon"], D6 + SEP + r"(\d{3})", lambda m: f"{m[0]}_{m[1]}"),
    "pacopacomama": (
        ["pacopacomama", "paco"],
        D6 + SEP + r"(\d{3})",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "10musume": (
        ["10musume", "10mu"],
        D6 + SEP + r"(\d{2})",
        lambda m: f"{m[0]}_{m[1]}",
    ),
    "muramura": (["muramura"], D6 + SEP + r"(\d{3,4})", lambda m: f"{m[0]}_{m[1]}"),
    "heyzo": (["heyzo"], r"(?:hd" + SEP + r"?)?(\d{4})", lambda m: m[0]),
    "kin8": (["kin8tengoku", "kin8"], r"(\d{4})", lambda m: m[0]),
    "nyoshin": (["nyoshin"], r"(n\d{3,5})", lambda m: m[0]),
    "hgmo": (["heydouga", "hgmo"], r"(\d{4})", lambda m: m[0]),
    "h4610": (["h4610"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "c0930": (["c0930"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "h0930": (["h0930"], r"([a-z]{2,6}\d{5,6})", lambda m: m[0]),
    "pikkur": (["pikkur"], r"(\d{5})", lambda m: m[0]),
    "av9898": (["av9898"], r"(\d{4})", lambda m: m[0]),
}
# Longest alias first, so "carib-pr" wins over "carib".
ALIASES = sorted(
    ((alias, slug) for slug, (aliases, _, _) in SITES.items() for alias in aliases),
    key=lambda a: -len(a[0]),
)
# Names without a site alias: every site that uses the bare id shape.
BARE = [
    (re.compile(r"(?<!\d)" + D6 + r"-(\d{3})(?!\d)"), ["caribbeancom"]),
    (
        re.compile(r"(?<!\d)" + D6 + r"_(\d{3})(?!\d)"),
        ["1pondo", "caribbeanpremium", "pacopacomama"],
    ),
    (re.compile(r"(?<!\d)" + D6 + r"_(\d{2})(?!\d)"), ["10musume"]),
]
# Censored codes: "SSIS-001", "ssis 001", "ssis.001" or zero-padded "ssis00001".
CENSORED = re.compile(
    r"(?:(?<![a-z0-9])|(?<=(?<![a-z0-9])\d{3}))([a-z]{2,6})(?:"
    + SEP
    + r"(\d{2,5})|(0\d{2,4}))(?!\d)"
)
NOT_CODES = {
    "hd",
    "fhd",
    "uhd",
    "mp",
    "avi",
    "mkv",
    "wmv",
    "part",
    "cd",
    "disc",
    "dvd",
    "x",
    "h",
    "img",
    "dsc",
    "vid",
    "mov",
    "clip",
    "scene",
    "fc",
    "ppv",
}
EMPTY = {"", "-", "--", "—", "―", "N/A", "n/a"}


def log(msg):
    sys.stderr.write(f"[JAVMania] {msg}\n")


class _SameSiteRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlparse(newurl)
        if (
            u.scheme != "https"
            or u.hostname not in ALLOWED_HOSTS
            or u.hostname in BLOCKED
        ):
            raise urllib.error.HTTPError(newurl, code, "off-site redirect", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(_SameSiteRedirects)


def fetch(url):
    """(final_url, text) or (None, None). Never raises."""
    host = urllib.parse.urlparse(url).hostname
    remaining = BUDGET - (time.monotonic() - START)
    if host in BLOCKED or remaining < 1:
        FAILED[0] += 1
        return None, None
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en"}
    )
    try:
        with OPENER.open(req, timeout=min(TIMEOUT, remaining)) as r:
            body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                log(f"response too large: {url}")
                FAILED[0] += 1
                return None, None
            charset = r.headers.get_content_charset() or "utf-8"
            try:
                page = body.decode(charset, "replace")
            except LookupError:
                page = body.decode("utf-8", "replace")
            return r.geturl(), page
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            BLOCKED.add(urllib.parse.urlparse(e.geturl() or url).hostname)
        if e.code != 404:
            log(f"HTTP {e.code} for {url}")
            FAILED[0] += 1
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
        log(f"{type(e).__name__} for {url}: {e}")
        FAILED[0] += 1
    return None, None


def same_page(requested, final, pattern):
    """True when a redirect stayed on the same work page (only the language
    prefix, host spelling or trailing slash may differ)."""
    a, b = pattern.match(requested or ""), pattern.match(final or "")
    return bool(a and b and a.group(1).lower() == b.group(1).lower())


def text(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment or "")
    return re.sub(
        r"[ \t\r\f\v]+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))
    ).strip()


def value(cell):
    """Plain text of a cell, or None when the site shows a placeholder."""
    v = text(cell)
    return None if v in EMPTY else v


def iso_date(raw):
    """YYYY-MM-DD from '2026-11-25', '2026/11/25' or '2026年11月25日'."""
    m = re.search(r"(\d{4})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})", raw or "")
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return datetime.date(y, mo, d).isoformat()
    except ValueError:  # e.g. 1999-02-29
        return None


def seconds(raw):
    """Duration in seconds from '111分', '479 min' or '01:00:40'."""
    raw = raw or ""
    hms = re.search(r"\b(\d{1,2}):(\d{2}):(\d{2})\b", raw)
    if hms:
        h, m, sec = (int(x) for x in hms.groups())
        return h * 3600 + m * 60 + sec or None
    mins = re.search(r"(\d{1,4})\s*(?:分|min)(?:\s*(\d{1,2})\s*秒)?", raw)
    total = int(mins.group(1)) * 60 + int(mins.group(2) or 0) if mins else 0
    return total or None


def meta(page, prop):
    m = re.search(
        rf'<meta\s+(?:property|name)="{re.escape(prop)}"\s+content="([^"]*)"', page
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


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def detail_rows(page):
    """<table class="detail-table"> rows as {header: inner html}."""
    m = re.search(r'<table class="detail-table">(.*?)</table>', page, re.DOTALL)
    rows = {}
    for th, td in re.findall(
        r"<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>",
        m.group(1) if m else "",
        re.DOTALL,
    ):
        rows[text(th)] = td
    return rows


def strip_ja(cell):
    return re.sub(r'<span lang="ja">.*?</span>', "", cell or "", flags=re.DOTALL)


def performers_from(cell):
    """Names are separated by <br> (one ja alias each) or by "," with the ja
    aliases listed afterwards in the same order. Split before decoding
    entities so an encoded comma stays inside a name."""
    out = []
    for part in re.split(r"<br\s*/?>", cell or ""):
        names = [value(n) for n in strip_ja(part).split(",")]
        names = [n for n in names if n]
        jas = [
            text(j)
            for j in re.findall(r'<span lang="ja">【(.*?)】</span>', part, re.DOTALL)
        ]
        hrefs = [
            re.search(r'href="(/actress/[^"/]+/)"', seg)
            for seg in strip_ja(part).split(",")
        ]
        hrefs = [
            h.group(1) if h else None
            for h, seg in zip(hrefs, strip_ja(part).split(","))
            if value(seg)
        ]
        for i, name in enumerate(names):
            p = {"name": name}
            if len(jas) == len(names) and jas[i]:
                p["aliases"] = jas[i]
            if len(hrefs) == len(names) and hrefs[i]:
                p["urls"] = [JM + hrefs[i]]
            out.append(p)
    return out


def profile_rows(page):
    """[(japanese name or None, profile text)] from the work page's Profile
    rows. With several performers each row starts with the Japanese name."""
    out = []
    for td in re.findall(
        r"<tr>\s*<th>Profile</th>\s*<td>(.*?)</td>\s*</tr>", page, re.DOTALL
    ):
        ja = re.match(
            r'\s*<span lang="ja">(.*?)</span>\s*(?:—|&mdash;|\u2014)?', td, re.DOTALL
        )
        out.append(
            (text(ja.group(1)) if ja else None, text(td[ja.end() :] if ja else td))
        )
    return out


def parse_profile(raw):
    """Stash performer fields from '160cm (5'3") / G-cup / B94 W57 H90 / Born 1986-08-25'."""
    p = {}
    m = re.search(r"(\d{3})\s*cm", raw)
    if m:
        p["height"] = m.group(1)
    cup = re.search(r"\b([A-Z]{1,2})-cup\b", raw)
    bwh = re.search(r"B(\d{2,3})\s*W(\d{2,3})\s*H(\d{2,3})", raw)
    if bwh:
        b, w, h = bwh.groups()
        p["measurements"] = f"{b}{cup.group(1) if cup else ''}-{w}-{h}"
    elif cup:
        p["measurements"] = cup.group(1)
    born = iso_date((re.search(r"Born\s+([0-9/-]+)", raw) or [None, ""])[1])
    if born:
        p["birthdate"] = born
    return p


def attach_profiles(perf, page):
    rows = profile_rows(page)
    for ja, raw in rows:
        target = None
        if ja:
            same = [p for p in perf if p.get("aliases") == ja]
            target = same[0] if len(same) == 1 else None
        elif len(rows) == 1 and len(perf) == 1:
            target = perf[0]
        if target is not None:
            target.update(parse_profile(raw))
    return perf


def clean(scene):
    return {k: v for k, v in scene.items() if v not in (None, "", [], {})}


def scrape_javmania(url, expect=None):
    """Scene from a jav-mania work page, or None if the page is not a work
    page (or not the work `expect` names)."""
    final, page = fetch(url)
    if not page or not same_page(url, final, JM_PAGE):
        return None
    rows = detail_rows(page)
    code = (
        value(rows.get("Content ID"))
        or (value(rows.get("Code")) or "").split(" ")[0]
        or None
    )
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL)
    title = text(h1.group(1)) if h1 else None
    if not code or not title:
        return None  # challenge, landing or error page
    if expect and not same_code(code, expect):
        return None
    video = ld_json(page, "VideoObject")
    title = (
        re.sub(
            rf"(\s*\([^()]*{re.escape(code)}[^()]*\))+$", "", title, flags=re.IGNORECASE
        ).strip()
        or title
    )
    summary = re.search(r'<p class="summary">(.*?)</p>', page, re.DOTALL)
    tag_row = re.search(r'<div class="tag-row">(.*?)</div>', page, re.DOTALL)
    tags = [
        value(t)
        for t in re.findall(
            r'<(?:a|span)\s+class="tag"[^>]*>(.*?)</(?:a|span)>',
            tag_row.group(1) if tag_row else "",
            re.DOTALL,
        )
    ]
    perf = attach_profiles(
        performers_from(rows.get("Performer") or rows.get("Performers")), page
    )
    if not perf:
        perf = [
            {"name": a["name"]}
            for a in as_list(video.get("actor"))
            if isinstance(a, dict) and a.get("name")
        ]
    image = meta(page, "og:image") or next(
        (t for t in as_list(video.get("thumbnailUrl")) if isinstance(t, str)), None
    )
    studio = value(rows.get("Site") or rows.get("Studio"))
    series = value(strip_ja(rows.get("Series")))
    scene = {
        "title": title,
        "code": code,
        "details": text(summary.group(1)) if summary else video.get("description"),
        "date": iso_date(text(rows.get("Release date"))),
        "urls": [final or url],
        "image": urllib.parse.urljoin(final or url, image) if image else None,
        "tags": [{"name": t} for t in tags if t]
        or [{"name": g} for g in as_list(video.get("genre")) if isinstance(g, str)],
        "performers": perf,
        "studio": {"name": studio} if studio else None,
        "groups": [{"name": series}] if series else None,
        "director": value(strip_ja(rows.get("Director"))),
        "duration": seconds(text(rows.get("Runtime"))),
    }
    return clean(scene)


def scrape_avhinban(url, expect=None):
    final, page = fetch(url)
    if not page or not same_page(url, final, AV_PAGE):
        return None
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL)
    code, _, title = (text(h1.group(1)) if h1 else "").partition(" ")
    dl = re.search(r'<dl class="info">(.*?)</dl>', page, re.DOTALL)
    if not code or not dl:
        return None  # not a work page
    if expect and not same_code(code, expect):
        return None
    info = {}
    for dt, dd in re.findall(
        r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", dl.group(1), re.DOTALL
    ):
        if value(dd):  # "-" means unknown
            info[text(dt)] = dd
    img = re.search(r'<div class="pkg">\s*<img\s+src="([^"]+)"', page)
    image = html.unescape(img.group(1)) if img else meta(page, "og:image")
    desc = re.search(
        r"<details>\s*<summary>.*?</summary>\s*<p>(.*?)</p>\s*</details>",
        page,
        re.DOTALL,
    )
    maker = value(info.get("メーカー"))
    label = value(info.get("レーベル"))
    series = value(info.get("シリーズ"))
    if label and maker and label != maker:  # label is a brand of the maker
        studio = {"name": label, "parent": {"name": maker}}
    else:
        studio = {"name": maker or label} if (maker or label) else None
    cast = [
        (value(a), h)
        for h, a in re.findall(
            r'<a\b[^>]*href="(/performers/\d+/)"[^>]*>(.*?)</a>',
            info.get("出演者", ""),
            re.DOTALL,
        )
    ]

    def names(key):
        return [
            value(a)
            for a in re.findall(r"<a\b[^>]*>(.*?)</a>", info.get(key, ""), re.DOTALL)
        ]

    scene = {
        "title": title or code,
        "code": code,
        "details": text(desc.group(1)) if desc else None,
        "date": iso_date(text(info.get("発売日"))),
        "urls": [final or url, *store_urls(page)],
        "image": urllib.parse.urljoin(final or url, image) if image else None,
        "performers": [{"name": n, "urls": [AV + h]} for n, h in cast if n],
        "tags": [{"name": n} for n in names("ジャンル") if n],
        "director": value(info.get("監督")),
        "studio": studio,
        "groups": [{"name": series}] if series else None,
        "duration": seconds(text(info.get("収録時間"))),
    }
    return clean(scene)


def store_url(href):
    """Plain store page for a purchase link (FANZA, MGS, DUGA, Sokmil), with
    affiliate and tracking parameters removed; None for anything else."""
    u = urllib.parse.urlparse(html.unescape(href))
    host = (u.hostname or "").lower()
    if host == "al.fanza.co.jp":  # redirector: real page is in ?lurl=
        target = urllib.parse.parse_qs(u.query).get("lurl", [""])[0]
        t = urllib.parse.urlparse(target)
        cid = urllib.parse.parse_qs(t.query).get("id", [""])[0]
        if t.hostname == "video.dmm.co.jp" and re.fullmatch(r"[a-z0-9_]+", cid):
            return f"https://video.dmm.co.jp/av/content/?id={cid}"
        return None
    if host == "www.mgstage.com":
        m = re.match(r"^/product/product_detail/([A-Za-z0-9_-]+)/?$", u.path)
        return (
            f"https://www.mgstage.com/product/product_detail/{m.group(1)}/"
            if m
            else None
        )
    if host == "click.duga.jp":  # /ppv/<product>/<affiliate>
        m = re.match(r"^/ppv/([A-Za-z0-9_-]+)/", u.path)
        return f"https://duga.jp/ppv/{m.group(1)}/" if m else None
    if host in ("sokmil.com", "www.sokmil.com"):
        m = re.match(r"^/av/_item/(item\d+)\.htm$", u.path)
        return f"https://www.sokmil.com/av/_item/{m.group(1)}.htm" if m else None
    return None


def store_urls(page):
    urls = []
    for href in re.findall(
        r'<a\b[^>]*\bhref="([^"]+)"[^>]*\brel="sponsored[^"]*"', page
    ):
        clean_url = store_url(href)
        if clean_url and clean_url not in urls:
            urls.append(clean_url)
    return urls


JM_PAGE = re.compile(
    r"^https?://(?:www\.)?jav-mania\.net/(?:[a-z]{2}(?:-[a-z]{2,4})?/)?(movies/[^/?#]+/[^/?#]+|jav/[^/?#]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
AV_PAGE = re.compile(
    r"^https?://(?:www\.)?avhinban\.com/works/([^/?#]+)/?(?:[?#].*)?$", re.IGNORECASE
)


def scrape_url(url):
    """Scrape a jav-mania or avhinban work URL. Language prefixes, queries
    and fragments are dropped so the English page is used."""
    url = url.strip() if isinstance(url, str) else ""
    m = JM_PAGE.match(url)
    if m:
        path = m.group(1)
        scene = scrape_javmania(
            f"{JM}/{path}/", expect=path.rstrip("/").rsplit("/", 1)[-1]
        )
        if scene and path.lower().startswith("jav/"):
            enrich_from_avhinban(scene, scene["code"])
        return scene
    m = AV_PAGE.match(url)
    if m:
        return scrape_avhinban(f"{AV}/works/{m.group(1)}/", expect=m.group(1))
    return None


def avhinban_lookup(code):
    _, page = fetch(f"{AV}/search/?q={urllib.parse.quote(code.upper())}")
    for slug in re.findall(r'href="/works/([^"/]+)/"', page or ""):
        if same_code(slug, code):  # the site search is fuzzy
            return f"{AV}/works/{slug}/"
    return None


def enrich_from_avhinban(scene, code):
    """Fill fields the English page lacks (director, series, missing date,
    cover, description, studio) from avhinban and add its URL."""
    av_url = avhinban_lookup(code)
    av = scrape_avhinban(av_url, expect=code) if av_url else None
    if not av:
        return scene
    for key in ("date", "image", "details", "director", "studio", "groups", "duration"):
        if key in av and not scene.get(key):
            scene[key] = av[key]
    for u in av["urls"]:  # avhinban page + plain store pages
        if u not in scene["urls"]:
            scene["urls"].append(u)
    return scene


def avhinban_search(query, limit=20):
    """Result cards for a free-text search (performer name, title words)."""
    _, page = fetch(f"{AV}/search/?q={urllib.parse.quote(query.strip()[:100])}")
    results = []
    for card in re.findall(
        r'<a\b[^>]*class="card"[^>]*>.*?</a>', page or "", re.DOTALL
    ):
        href = re.search(r'href="(/works/[^"]+/)"', card)
        code = re.search(r'<div class="cd">(.*?)</div>', card, re.DOTALL)
        title = re.search(r'<div class="tl">(.*?)</div>', card, re.DOTALL)
        img = re.search(r'<img\b[^>]*\bsrc="([^"]+)"', card)
        if not href or not code:
            continue
        results.append(
            clean(
                {
                    "title": text(title.group(1)) if title else text(code.group(1)),
                    "code": text(code.group(1)),
                    "urls": [AV + href.group(1)],
                    "image": html.unescape(img.group(1)) if img else None,
                }
            )
        )
        if len(results) >= limit:
            break
    return results


def uncensored_candidates(name):
    """[(candidate URL, expected id)] for a file name or title."""
    s = name.lower()
    for alias, slug in ALIASES:
        pos = re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z])", s)
        if not pos:
            continue
        id_re = r"(?<![0-9a-z])" + SITES[slug][1] + r"(?!\d)"
        m = re.search(id_re, s[pos.end() :]) or re.search(id_re, s)
        if m:
            cid = SITES[slug][2](m.groups())
            return [(f"{JM}/movies/{slug}/{cid}/", cid)]
        return []
    for rx, slugs in BARE:
        m = rx.search(s)
        if m:
            return [
                (
                    f"{JM}/movies/{slug}/{SITES[slug][2](m.groups())}/",
                    SITES[slug][2](m.groups()),
                )
                for slug in slugs
            ]
    return []


def censored_codes(name):
    codes = []
    for prefix, num, padded in CENSORED.findall(name.lower()):
        if prefix in NOT_CODES:
            continue
        code = f"{prefix}-{int(num or padded):03d}"
        if code not in codes:
            codes.append(code)
    return codes[:3]


def same_code(a, b):
    def norm(c):
        c = re.sub(r"[^a-z0-9]", "", (c or "").lower())
        c = re.sub(r"^mgs(?=\d*[a-z])", "", c)  # avhinban MGS slugs: mgs-abp-010
        c = re.sub(r"^h\d+(?=[a-z])", "", c)  # FANZA ids: h_1729goji00118
        return re.sub(r"(?<=[a-z])0+(?=\d)", "", c)

    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    # FANZA ids may carry a numeric label prefix: 138sfrd017 == SFRD-017
    return (
        a == b
        or re.fullmatch(r"\d+" + re.escape(b), a) is not None
        or re.fullmatch(r"\d+" + re.escape(a), b) is not None
    )


def lookup_all(name):
    """Every confident match for a free-text name (file name, title, code)."""
    name = (name or "").strip()
    if not name:
        return []
    if re.match(r"https?://", name):
        scene = scrape_url(name)
        return [scene] if scene else []
    found = [
        s
        for s in (
            scrape_javmania(u, expect=cid) for u, cid in uncensored_candidates(name)
        )
        if s
    ]
    if found:
        return found
    for code in censored_codes(name):
        scene = scrape_javmania(f"{JM}/jav/{code}/", expect=code)
        if scene:
            return [enrich_from_avhinban(scene, code)]
        av_url = avhinban_lookup(code)
        scene = scrape_avhinban(av_url, expect=code) if av_url else None
        if scene:
            return [scene]
    return []


def lookup(name):
    """One scene, only when the name is unambiguous."""
    failed_before = FAILED[0]
    found = lookup_all(name)
    if (
        len(found) == 1
        and FAILED[0] > failed_before
        and len(uncensored_candidates(name)) > 1
    ):
        log(f"could not check every studio for {name!r}; not guessing")
        return None
    if len(found) > 1:
        log(
            f"ambiguous id in {name!r}: {[s['urls'][0] for s in found]}; use scene search or add the studio name"
        )
        return None
    return found[0] if found else None


ACTRESS_PAGE = re.compile(
    r"^https?://(?:www\.)?jav-mania\.net/(?:[a-z]{2}(?:-[a-z]{2,4})?/)?actress/([a-z0-9-]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)


def scrape_actress(url):
    """Performer from a jav-mania actress page, including the profile line
    (height, measurements, birthday). Performers without that line on their
    page fall back to the profile printed on up to two uncensored work pages."""
    m = ACTRESS_PAGE.match(url.strip() if isinstance(url, str) else "")
    if not m:
        return None
    page_url = f"{JM}/actress/{m.group(1).lower()}/"
    final, page = fetch(page_url)
    if not page or not same_page(page_url, final, ACTRESS_PAGE):
        return None
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.DOTALL)
    name = value(h1.group(1)) if h1 else None
    if not name:
        return None
    ja = re.search(r'\(<span lang="ja">(.*?)</span>\)\s*also appears', page, re.DOTALL)
    years = re.search(r"active (\d{4})\s*[–-]\s*(\d{4})", page)
    performer = {
        "name": name,
        "aliases": text(ja.group(1)) if ja else None,
        "gender": "Female",
        "career_start": years.group(1) if years else None,
        "career_end": years.group(2) if years else None,
        "urls": [page_url],
    }
    # The actress page prints her profile; older cached copies may not yet.
    own = re.search(r'<p class="actress-profile">(.*?)</p>', page, re.DOTALL)
    if own:
        performer.update(
            parse_profile(text(re.sub(r"<strong>.*?</strong>", "", own.group(1))))
        )
    works = []
    for href in re.findall(r'href="(/movies/[^"/]+/[^"/]+/)"', page):
        if href not in works:
            works.append(href)
    for href in [] if own else works[:2]:
        _, work = fetch(JM + href)
        if not work:
            continue
        rows = detail_rows(work)
        cast = attach_profiles(
            performers_from(rows.get("Performer") or rows.get("Performers")), work
        )
        mine = next((p for p in cast if p.get("urls") == [page_url]), None)
        if not mine:
            continue
        performer["aliases"] = performer["aliases"] or mine.get("aliases")
        for key in ("height", "measurements", "birthdate"):
            if mine.get(key):
                performer[key] = mine[key]
        if any(performer.get(k) for k in ("height", "measurements", "birthdate")):
            break
    return clean(performer)


def actress_candidates(name):
    """[{name, urls}] for a performer name, by the site's slug rule."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    if not slug:
        return []
    url = f"{JM}/actress/{slug}/"
    final, page = fetch(url)
    h1 = re.search(r"<h1>(.*?)</h1>", page or "", re.DOTALL)
    found = value(h1.group(1)) if h1 else None
    if not page or not found or not same_page(url, final, ACTRESS_PAGE):
        return []
    return [{"name": found, "urls": [url]}]


AV_PERFORMER = re.compile(
    r"^https?://(?:www\.)?avhinban\.com/performers/(\d+)/?(?:[?#].*)?$", re.IGNORECASE
)
PROFILE_KEYS = ("height", "measurements", "birthdate")


def scrape_av_performer(url):
    """Performer from an avhinban performer page: Japanese name, other
    spellings, career years and the profile rows; when the page links to the
    English JAV Mania page, its English name is added as an alias."""
    m = AV_PERFORMER.match(url.strip() if isinstance(url, str) else "")
    if not m:
        return None
    page_url = f"{AV}/performers/{m.group(1)}/"
    final, page = fetch(page_url)
    if not page or not same_page(page_url, final, AV_PERFORMER):
        return None
    h1 = re.search(r"<h1>(.*?)の出演作品</h1>", page, re.DOTALL)
    dl = re.search(r'<dl class="info">(.*?)</dl>', page, re.DOTALL)
    name = value(h1.group(1)) if h1 else None
    if not name or not dl:
        return None
    info = {}
    for dt, dd in re.findall(
        r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", dl.group(1), re.DOTALL
    ):
        info[text(dt)] = dd
    span = re.findall(r"(\d{4})-\d{2}-\d{2}", text(info.get("出演作品")))
    sizes = text(info.get("スリーサイズ"))
    bwh = re.search(r"B(\d{2,3})\s*W(\d{2,3})\s*H(\d{2,3})", sizes)
    cup = re.search(r"\(([A-Z]{1,2})カップ\)", sizes)
    height = re.search(r"(\d{3})\s*cm", text(info.get("身長")))
    aliases = [a for a in re.split(r"[、,]", text(info.get("別表記"))) if a.strip()]
    jm = re.search(
        r'href="(https://www\.jav-mania\.net/actress/[a-z0-9-]+/)"',
        info.get("英語ページ", ""),
    )
    urls = [page_url]
    if jm:
        english = scrape_actress(jm.group(1))
        if english:
            aliases.insert(0, english["name"])
            urls.append(english["urls"][0])
    performer = {
        "name": name,
        "aliases": ", ".join(dict.fromkeys(a.strip() for a in aliases)) or None,
        "gender": "Female",
        "career_start": min(span) if span else None,
        "career_end": max(span) if span else None,
        "height": height.group(1) if height else None,
        "measurements": (
            f"{bwh.group(1)}{cup.group(1) if cup else ''}-{bwh.group(2)}-{bwh.group(3)}"
            if bwh
            else (cup.group(1) if cup else None)
        ),
        "birthdate": iso_date(text(info.get("生年月日"))),
        "urls": urls,
    }
    return clean(performer)


def av_performer_candidates(name):
    """[{name, urls}] for a Japanese performer name via the avhinban search."""
    query = (name or "").strip()
    if not query:
        return []
    _, page = fetch(f"{AV}/search/?q={urllib.parse.quote(query[:100])}")
    out = []
    for href, label in re.findall(
        r'href="(/performers/\d+/)"[^>]*>(.*?)</a>', page or "", re.DOTALL
    ):
        label = value(label)
        if (
            label
            and (label == query or query in label)
            and all(o["urls"][0] != AV + href for o in out)
        ):
            out.append({"name": label, "urls": [AV + href]})
    out.sort(key=lambda o: o["name"] != query)  # exact name first
    return out[:10]


def scrape_performer_url(url):
    if isinstance(url, str) and AV_PERFORMER.match(url):
        return scrape_av_performer(url)
    return scrape_actress(url)


def first_url(fragment):
    for u in as_list(fragment.get("urls")) + [fragment.get("url")]:
        if isinstance(u, str) and (JM_PAGE.match(u) or AV_PAGE.match(u)):
            return u
    return None


def file_names(fragment):
    names = []
    for f in as_list(fragment.get("files")):
        path = f.get("path") if isinstance(f, dict) else None
        if isinstance(path, str) and path:
            names.append(os.path.basename(path.replace("\\", "/")))
    return names


def read_input():
    raw = sys.stdin.buffer.read()
    try:
        data = json.loads(raw.decode("utf-8-sig") or "{}")
    except (UnicodeDecodeError, ValueError):
        log("stdin is not valid UTF-8 JSON")
        return {}
    return data if isinstance(data, dict) else {}


def write_output(result):
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    fragment = read_input()
    if mode == "sceneByURL":
        write_output(scrape_url(fragment.get("url")))
    elif mode in ("sceneByFragment", "sceneByQueryFragment"):
        url = first_url(fragment)
        result = scrape_url(url) if url else None
        for key in [fragment.get("code"), fragment.get("title"), *file_names(fragment)]:
            if result is None and isinstance(key, str) and key.strip():
                result = lookup(key)
        write_output(result)
    elif mode == "performerByURL":
        write_output(scrape_performer_url(fragment.get("url")))
    elif mode == "performerByName":
        query = fragment.get("name") if isinstance(fragment.get("name"), str) else ""
        write_output(actress_candidates(query) + av_performer_candidates(query))
    elif mode == "performerByFragment":
        urls = [
            u
            for u in as_list(fragment.get("urls")) + [fragment.get("url")]
            if isinstance(u, str) and (ACTRESS_PAGE.match(u) or AV_PERFORMER.match(u))
        ]
        if not urls and isinstance(fragment.get("name"), str):
            exact = [
                c
                for c in av_performer_candidates(fragment["name"])
                if c["name"] == fragment["name"].strip()
            ]
            found = actress_candidates(fragment["name"]) or (
                exact if len(exact) == 1 else []
            )
            urls = [c["urls"][0] for c in found]
        write_output(scrape_performer_url(urls[0]) if urls else None)
    elif mode == "sceneByName":
        query = fragment.get("name") if isinstance(fragment.get("name"), str) else ""
        write_output(
            lookup_all(query) or (avhinban_search(query) if query.strip() else [])
        )
    else:
        log(f"unknown mode {mode!r}")
        write_output(None)


if __name__ == "__main__":
    main()
