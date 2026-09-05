import re
from typing import Any
from py_common.util import dig, replace_all


def append_scene_number(
    obj: dict[str, Any],
    api_scene: dict[str, Any],
    separator: str = " - ",
) -> dict[str, Any]:
    """Append the numeric clip-path suffix to a scene title when available."""
    if (
        (title := obj.get("title"))
        and not re.search(r"\bScene \d+\b", title, re.IGNORECASE)
        and (match := re.search(r"_(\d+)$", api_scene.get("clip_path", "")))
    ):
        obj["title"] = f"{title}{separator}Scene {int(match.group(1))}"

    return obj


def append_studio_name(obj: Any, api_object: dict[str, Any], fallback: str) -> Any:
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

