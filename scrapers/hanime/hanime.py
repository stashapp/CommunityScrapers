import sys
import json
import requests
import io
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


HANIME_SEARCH_URL = "https://search.htv-services.com/"

def search_hanime(query):
    params = {
        "search_text": query,
        "tags": [],
        "tags_mode": "AND",
        "brands": [],
        "blacklist": [],
        "order_by": "title_sortable",
        "ordering": "asc",
        "page": 0
    }

    try:
        response = requests.post(HANIME_SEARCH_URL, json=params)
        data = response.json()
        hits = json.loads(data.get("hits", "[]"))
    except Exception as e:
        print("Failed to fetch or parse JSON response", e, file=sys.stderr)
        return []

    return [
        {
            "Title": hit["name"],
            "URL": f'https://hanime.tv/videos/hentai/{hit["slug"]}',
            "Image": hit.get("cover_url", "")
        }
        for hit in hits
    ]

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print("No input from stdin", file=sys.stderr)
            sys.exit(1)

        raw = json.loads(raw_input)
    except Exception as e:
        print("Invalid JSON input:", e, file=sys.stderr)
        sys.exit(1)

    # CASE 1: Search mode (scene-by-name)
    if "name" in raw:
        results = search_hanime(raw["name"])
        print(json.dumps(results, ensure_ascii=False))
        return
    # CASE 2: User selected a result – return URL and Title
    else:
        print(json.dumps({
            "URL": raw["url"],
            "Title": raw.get("title", "")
        }, ensure_ascii=False))
        return

    # DEFAULT: Invalid input
    print("Missing 'name' or 'url' in input", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
