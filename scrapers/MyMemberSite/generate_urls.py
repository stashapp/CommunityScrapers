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
        'mymember.site',
    ]

    while True:
        response = requests.get(base_url, params={"page": current_page})
        if response.status_code != 200:
            print(f"Error fetching '{base_url}': {response.status_code}")
            break

        data = response.json()
        for site in data["data"]:
            site_url: str = site["site_url"].removeprefix("https://")
            if site_url.startswith('mymember.site'):
                continue

            site_urls.append(f"{site_url}/")
            print(f"Found site URL: {site['site_url']}")

        if current_page >= data["last_page"]:
            break

        current_page += 1

    # Remove duplicates
    site_urls = list(set(site_urls))
    site_urls.sort()

    return site_urls

if __name__ == "__main__":
    site_urls: list[str] = fetch_site_urls()
    print(yaml.dump(site_urls))
