import re
from typing import Any

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