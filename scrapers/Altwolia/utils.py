import re
from typing import Any, TypeVar

from py_common.types import ScrapedGallery, ScrapedMovie, ScrapedScene
from py_common.util import dig, replace_all

Scraped = TypeVar("Scraped", ScrapedScene, ScrapedGallery, ScrapedMovie)

# clip_path is always "{movie_id}_{position}", but the position is only a
# meaningful scene number when the clip is part of its original multi-scene release
_clip_position = re.compile(r"_(\d+)$")
_numbered_title = re.compile(r"\bScene\s*#?\s*\d+\b", re.IGNORECASE)


def _normalized(title: str) -> str:
    "Title comparison insensitive to case, punctuation and zero-padding"
    title = re.sub(r"[^a-z0-9]+", " ", title.casefold())
    return re.sub(r"\b0+(\d)", r"\1", title).strip()


def append_scene_number(
    scene: ScrapedScene,
    api_scene: dict[str, Any],
    separator: str = ", ",
) -> ScrapedScene:
    """
    Disambiguates scenes that reuse their movie's title, as is common on
    DVD-first sites, by appending the clip's position within the movie:
    "Turn It Up" -> "Turn It Up, Scene 3"

    Scenes whose titles already contain a scene number or differ from their
    movie's title are left untouched. Pass a scene postprocess function only:
    galleries also have titles but their hits don't describe original releases
    """
    if (
        (title := scene.get("title"))
        and not _numbered_title.search(title)
        and _normalized(title) == _normalized(api_scene.get("movie_title") or "")
        and (position := _clip_position.search(api_scene.get("clip_path") or ""))
    ):
        scene["title"] = f"{title}{separator}Scene {int(position.group(1))}"
    return scene


def append_studio_name(
    obj: Scraped, api_object: dict[str, Any], fallback: str
) -> Scraped:
    "Sets the studio to the API's main channel, parented under the fallback"
    if studio_name := dig(api_object, "mainChannel", "name"):
        return replace_all(
            obj,
            "studio",
            lambda s: {
                **s,
                "name": studio_name,
                "parent": {"name": fallback},
            },
        )
    return replace_all(obj, "studio", lambda s: {**s, "name": fallback})
