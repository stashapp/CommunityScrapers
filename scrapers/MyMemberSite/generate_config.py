import requests
import yaml

def fetch_site_urls() -> list[str]:
    """
    Fetches all site URLs from the MyMemberSite API.

    Returns
    -------
    list[str]
        A list of site URLs without the "https://" prefix.
    """
    base_url: str = "https://mymember.site/api/sites-statistics"
    current_page: int = 1
    site_urls: list[str] = [
        'beverlybluexxx.com',
        'deemariexxx.com',
        'mymember.site/androprince-cs-chamber',
        'mymember.site/rubbobjectdoll',
    ]

    while True:
        response = requests.get(base_url, params={"page": current_page})
        if response.status_code != 200:
            print(f"Error fetching '{base_url}': {response.status_code}")
            break

        data = response.json()
        for site in data["data"]:
            site_urls.append(site["site_url"].removeprefix("https://"))
            print(f"Found site URL: {site['site_url']}")

        if current_page >= data["last_page"]:
            break

        current_page += 1

    site_urls.sort()
    # Remove duplicates
    return list(set(site_urls))

if __name__ == "__main__":
    site_urls: list[str] = fetch_site_urls()
    config: dict = {
        "galleryByURL": [
            {
                "action": "script",
                "script": [
                    "python3",
                    "MyMemberSite.py",
                    "gallery-by-url",
                ],
                "url": [f"{url}/photosets/" for url in site_urls if url],
            },
        ],
        "sceneByFragment": {
            "action": "script",
            "script": [
                "python3",
                "MyMemberSite.py",
                "scene-by-url",
            ],
        },
        "sceneByURL": [
            {
                "action": "script",
                "script": [
                    "python3",
                    "MyMemberSite.py",
                    "scene-by-url",
                ],
                "url": [f"{url}/videos/" for url in site_urls if url],
            },
        ],
    }
    print(yaml.dump(config))
