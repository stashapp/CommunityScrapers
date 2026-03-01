import json
import sys

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import dig, scraper_args

# AlgoliaAPI is a shared utility in the CommunityScrapers repo
# that handles Algolia auth, caching, and common scraping logic
from AlgoliaAPI.AlgoliaAPI import scene_from_url as algolia_scene_from_url

SITE = "playboytv"


def _build_title(api_scene: dict) -> str | None:
    """
    Construct title as "Serie Name - Season X, Episode Y".
    Uses the site's own language from serie_name, movie_title, and title fields.
    Falls back gracefully if any field is missing.
    """
    serie_name = api_scene.get("serie_name", "").strip()
    movie_title = api_scene.get("movie_title", "").strip()  # e.g. "Season 1"
    episode_title = api_scene.get("title", "").strip()       # e.g. "Episode 1"

    if serie_name and movie_title and episode_title:
        return f"{serie_name} - {movie_title}, {episode_title}"
    if serie_name and episode_title:
        return f"{serie_name} - {episode_title}"
    return episode_title or serie_name or None


def _build_urls(api_scene: dict) -> list[str]:
    """
    Build all known URL variants for a PlayboyTV episode:
    both www and members subdomains, both /view/ and /playboytv/ path formats.
    """
    url_title = api_scene.get("url_title", "")
    clip_id = api_scene.get("clip_id", "")
    return [
        f"https://www.playboytv.com/en/episode/view/{url_title}/{clip_id}",
        f"https://members.playboytv.com/en/episode/view/{url_title}/{clip_id}",
        f"https://www.playboytv.com/en/episode/playboytv/{url_title}/{clip_id}",
        f"https://members.playboytv.com/en/episode/playboytv/{url_title}/{clip_id}",
    ]


def _postprocess(scene: ScrapedScene, api_scene: dict) -> ScrapedScene:
    """
    PlayboyTV-specific overrides applied after AlgoliaAPI's generic scraping:
    1. Title: constructed from serie_name + movie_title + title
    2. URLs: four variants (www/members x view/playboytv paths)
    3. Image: PlayboyTV uses multicontent_data.nsfw, not pictures.nsfw.top
    """
    if title := _build_title(api_scene):
        scene["title"] = title

    scene["urls"] = _build_urls(api_scene)

    # Override image: PlayboyTV uses multicontent_data.nsfw instead of pictures
    if nsfw := dig(api_scene, "multicontent_data", "nsfw"):
        img_file = next(
            (e["file"] for e in nsfw if e.get("name") == "contentHero"), None
        ) or next(
            (e["file"] for e in nsfw if e.get("name") == "thumbnail"), None
        )
        if img_file:
            scene["image"] = f"https://transform.gammacdn.com/media/{img_file}"

    return scene


def main_scraper():
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = algolia_scene_from_url(url, [SITE], postprocess=_postprocess)
        case _:
            log.error(f"Unsupported operation: {op}, args: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main_scraper()
