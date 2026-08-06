import json, re, sys, urllib.request, ssl
ctx = ssl.create_default_context()
H = {"User-Agent": "Mozilla/5.0","Accept-Language": "zh-CN","Cookie": "over18=18; existmag=mag"}
D = "https://www.javbus.com"

def fetch(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=15, context=ctx).read().decode("utf-8", errors="replace")
    except:
        return None

def ec(t):
    t = re.sub(r"(?i)\b(CD|DVD|DISC|PART|JAV)[-_ ]?\d{1,3}\b", " ", t or "")
    m = re.search(r"^.*?([A-Za-z][A-Za-z0-9]*?[A-Za-z])[-_ ]*(\d{2,5}).*$", t)
    return f"{m.group(1).upper()}-{m.group(2)}" if m else None

def ps(h):
    p = '<a class="movie-box" href="(https?://www\\.javbus\\.com/[^"]+)"[^>]*>(.*?)<div class="photo-info">\\s*<span>(.*?)</span>'
    r = []
    for u, b, i in re.findall(p, h, re.DOTALL):
        mt = re.search(r'^([^<]+)(?:<br|<div)', i, re.DOTALL)
        title = mt.group(1).strip() if mt else ""
        cd = re.findall(r'<date>(.*?)</date>', i)
        code = cd[0] if len(cd) > 0 else ""
        date = cd[1] if len(cd) > 1 else ""
        if title:
            display = f"{code} - {title}" if code else title
            result = {"title": display, "url": u}
            if code:
                result["code"] = code
            if date:
                result["date"] = date
            mi = re.search(r'<img[^>]*src="([^"]+)"', b)
            if mi:
                img = mi.group(1)
                result["image"] = f"https://www.javbus.com{img}" if img.startswith("/") else img
            r.append(result)
    return r

def search(c):
    for p in [f"{D}/search/{c}", f"{D}/uncensored/search/{c}"]:
        h = fetch(p)
        if h:
            r = ps(h)
            if r:
                return r
    return []

def ss(u):
    h = fetch(u)
    if not h:
        return {}
    r = {}
    m = re.search(r"<h3>(.*?)</h3>", h)
    raw = m.group(1).strip() if m else ""
    r["title"] = re.sub(r'^[A-Za-z0-9]+-[A-Za-z0-9]+\s+', '', raw)
    m = re.search("識別碼[\\s:]*</span>\\s*<span[^>]*>([^<]+)", h)
    r["code"] = m.group(1).strip() if m else ""
    m = re.search("發行日期[^<]*</span>\\s*([^<\\n]+)", h)
    r["date"] = m.group(1).strip() if m else ""
    m = re.search("長度[^<]*</span>\\s*([^<\\n]+)", h)
    dv = re.search(r"\d+", m.group(1)) if m else None
    if dv:
        r["duration"] = int(dv.group()) * 60
    m = re.search("導演[^<]*</span>[^>]*<a[^>]*>([^<]+)", h)
    r["director"] = m.group(1).strip() if m else ""
    m = re.search("發行商[^<]*</span>\\s*<a[^>]*>([^<]+)", h)
    if not m:
        m = re.search("製作商[^<]*</span>\\s*<a[^>]*>([^<]+)", h)
    r["studio"] = {"name": m.group(1).strip()} if m else {}
    r["tags"] = [{"name": t} for t in re.findall('class="genre"><label>.*?<a[^>]*>([^<]+)', h, re.DOTALL)]
    r["performers"] = [{"name": p} for p in re.findall('class="star-name"[^>]*><a[^>]*>([^<]+)', h, re.DOTALL)]
    m = re.search('class="bigImage"[^>]*><img[^>]*src="([^"]+)"', h)
    if m:
        s = m.group(1)
        r["image"] = f"{D}{s}" if s.startswith("/") else s
    return r

f = json.loads(sys.stdin.read())
mode = sys.argv[1] if len(sys.argv) > 1 else ""
u = f.get("url") or (f.get("urls") or [""])[0]
n = f.get("name") or f.get("title") or ""
c = ec(f.get("code") or n or u)

if mode == "searchName":
    print(json.dumps(search(c) if c else []))   # sceneByName → list
elif u:
    print(json.dumps(ss(u)))                    # object
elif c:
    hits = search(c)                            # fragment 路径 → 单个对象
    hit = next((x for x in hits if x.get("code", "").upper() == c.upper()), hits[0] if hits else None)
    print(json.dumps(ss(hit["url"]) if hit else {}))
else:
    print(json.dumps([] if mode == "searchName" else {}))
