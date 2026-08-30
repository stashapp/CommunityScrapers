import sys
import json
import requests
import re
from bs4 import BeautifulSoup as bs
import io
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def read_json_input():
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    return json.loads(sys.stdin.read())

def clean_details(html_node):
    if not html_node:
        return ""
    
    # 移除 "Description" 标题
    header = html_node.find('h2')
    if header:
        header.decompose()

    # 将 <br> 替换为换行符
    for br in html_node.find_all("br"):
        br.replace_with("\n")

    # 获取文本
    text = html_node.get_text()

    # 格式化处理：确保段落之间有空行，并清理多余空格
    lines = [line.strip() for line in text.split('\n')]
    # 过滤掉空的列表元素，但保留段落感
    result = ""
    for line in lines:
        if line:
            result += line + "\n\n"
    final_text = result.strip()
    return re.sub(r"Enjoy,\s*\n+", "Enjoy,\n", final_text)

STUDIO_WORDS = ("cockyboys",)


def normalize_query(query):
    """Fold typographic characters to ASCII and drop a file extension.

    The site's search only matches straight quotes, and queries frequently
    arrive as filenames or as tagger strings.
    """
    for fancy, plain in (('\u2019', "'"), ('\u2018', "'"),
                         ('\u201c', '"'), ('\u201d', '"'),
                         ('\u2013', '-'), ('\u2014', '-')):
        query = query.replace(fancy, plain)
    query = re.sub(r'\.(mp4|mkv|avi|mov|wmv|m4v|flv|webm)$', '', query, flags=re.I)
    return re.sub(r'\s+', ' ', query).strip()


def query_candidates(query):
    """Build search terms to try, longest first.

    The tagger sends "<date> <studio> <performers> <title> <performers>",
    which matches nothing verbatim, so strip the parts the site never
    indexes and fall back to shorter fragments.
    """
    query = normalize_query(query)
    query = re.sub(r'^\s*\d{4}[-/]\d{2}[-/]\d{2}\s*', '', query)
    for word in STUDIO_WORDS:
        query = re.sub(r'^\s*' + word + r'\s*', '', query, flags=re.I)
    query = query.strip()

    candidates = [query]
    if " - " in query:
        candidates.append(query.split(" - ")[0].strip())

    words = query.split()
    if len(words) > 2:
        candidates.append(" ".join(words[:2]))   # usually the leading performer
        candidates.append(" ".join(words[-2:]))  # or the trailing one

    seen, ordered = set(), []
    for c in candidates:
        if c and c.lower() not in seen:
            seen.add(c.lower())
            ordered.append(c)
    return ordered


def score(title, query):
    """Rank by how many query words the result title accounts for."""
    words = set(re.findall(r"[a-z0-9']+", query.lower()))
    hits = set(re.findall(r"[a-z0-9']+", (title or '').lower()))
    return len(words & hits)


# The site returns 24 results per page; a common performer runs to several
MAX_SEARCH_PAGES = 5


def run_search(query):
    results, seen = [], set()
    for page in range(1, MAX_SEARCH_PAGES + 1):
        params = {"query": query}
        if page > 1:
            params["page"] = page

        response = requests.get("https://cockyboys.com/search.php",
                                params=params, headers=headers)
        if response.status_code != 200:
            break

        found = 0
        for sec in bs(response.content, 'html.parser').select('section.previewThumb'):
            link = sec.select_one('a.abso')
            if not link or not link.get('href'):
                continue

            found += 1
            url = "https://cockyboys.com" + link['href']
            if url in seen:
                continue

            seen.add(url)
            thumb = sec.select_one('a.thumbCover img')
            results.append({
                "Title": (link.get('title') or link.get_text()).strip(),
                "URL": url,
                "Image": thumb['src'] if thumb and thumb.get('src') else "",
            })

        if found < 24:
            break
    return results


def search_scenes(query):
    for candidate in query_candidates(query):
        results = run_search(candidate)
        if results:
            # Best overlap with the full query first, so tagger strings that
            # only match on a performer still surface the right scene.
            return sorted(results, key=lambda r: -score(r["Title"], query))
    return []


def upgrade_image(url):
    """og:image is a 475x350 thumbnail. The CDN also serves a "-full" variant
    which is 1800x1200 for most scenes and identical for the rest, so it is
    never worse. Fall back to the thumbnail if it is not there."""
    if not url or "-full." in url:
        return url

    full = re.sub(r'(\.[a-z]+)$', r'-full\1', url, flags=re.I)
    try:
        if requests.head(full, headers=headers, timeout=15).status_code == 200:
            return full
    except Exception:
        pass
    return url


def scrape_scene(url):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None

    soup = bs(response.content, 'html.parser')
    
    # 提取标题 (og:title)
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title["content"]

    # 提取日期并转换格式 (01/02/2006 -> 2006-01-02)
    date_str = ""
    date_label = soup.find("strong", string=re.compile("Released:"))
    if date_label:
        raw_date = date_label.next_sibling.strip()
        try:
            date_str = datetime.strptime(raw_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        except:
            date_str = raw_date

    # 提取 Details (按预期保留换行)
    details_node = soup.find("div", class_="movieDesc")
    details = clean_details(details_node)

    # 提取演员
    performers = []
    perf_nodes = soup.select('div.movieModels span a.name')
    for p in perf_nodes:
        performers.append({
            "Name": p.get('title', '').replace('“', '').replace('”', '').strip(),
            "URLs": [f"https://cockyboys.com{p['href']}"]
        })

    # 提取标签
    tags = []
    tag_label = soup.find("strong", string=re.compile("Categorized Under:"))
    if tag_label:
        tag_links = tag_label.find_next_siblings("a")
        tags = [{"name": t.get_text().strip()} for t in tag_links]

    # 提取工作室
    studio_name = ""
    og_site = soup.find("meta", property="og:site_name")
    if og_site:
        studio_name = og_site["content"]

    img = ""
    og_img = soup.find("meta", property="og:image")
    if og_img:
        img = og_img["content"]
        img = upgrade_image(img)

    code = ""
    setid = re.search(r'setid\s*:\s*"(\d+)"', response.text)
    if setid:
        code = setid.group(1)

    return {
        "Title": title,
        "Code": code,
        "Date": date_str,
        "Details": details,
        "Studio": {"Name": studio_name},
        "Performers": performers,
        "Tags": tags,
        "Image": img,
        "URL": url
    }

if __name__ == '__main__':
    args = sys.argv
    if len(args) > 1 and args[1] == 'sceneByURL':
        input_data = read_json_input()
        scene_url = input_data.get('url')
        result = scrape_scene(scene_url)
        print(json.dumps(result))
    elif len(args) > 1 and args[1] == 'sceneByName':
        input_data = read_json_input()
        print(json.dumps(search_scenes(input_data.get('name', ''))))
    elif len(args) > 1 and args[1] == 'sceneByFragment':
        input_data = read_json_input()
        scene_url = input_data.get('url')
        if not scene_url:
            matches = search_scenes(input_data.get('title') or '')
            if matches:
                scene_url = matches[0]['URL']
        print(json.dumps(scrape_scene(scene_url) if scene_url else None))
    elif len(args) > 1 and args[1] == 'sceneByQueryFragment':
        input_data = read_json_input()
        scene_url = input_data.get('url')
        print(json.dumps(scrape_scene(scene_url) if scene_url else None))
