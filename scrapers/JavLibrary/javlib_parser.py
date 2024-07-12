from typing import Any
from bs4 import BeautifulSoup  # noqa: E402
import logging


log = logging.getLogger()


def parse_duration(duration: str) -> str:
    "Parses durations like '247 min(s)' into something Stash can use like '04:07:00'"
    minutes = int(duration.split()[0])
    hours = minutes // 60
    minutes = minutes % 60

    return f"{hours:02}:{minutes:02}:00"


def scrape_movie(html: str) -> dict[str, Any]:
    """
    Scrapes all of the information about a movie from the raw HTML

    Returns a dictionary that can be used to create a ScrapedScene or ScrapedMovie
    """
    scraped = {}

    soup = BeautifulSoup(html, "html.parser")
    if not (css := soup.css):
        log.error("Unable to use CSS selectors with BeautifulSoup")
        return scraped

    if title := css.select_one("#video_title a"):
        scraped["title"] = title.get_text().strip()
    else:
        log.warning("Unable to find title")

    if code := css.select_one("#video_id td.text"):
        scraped["code"] = code.get_text().strip()
    else:
        log.warning("Unable to find code")

    if date := css.select_one("#video_date td.text"):
        scraped["date"] = date.get_text().strip()
    else:
        log.warning("Unable to find date")

    if (image := css.select_one("#video_jacket_img")) and (src := image.get("src")):
        if isinstance(src, list):
            src = src[0]
        scraped["cover"] = src
    else:
        log.warning("Unable to find image")

    # Duration is approximate but still useful
    if duration := css.select_one("#video_length .text"):
        scraped["duration"] = parse_duration(duration.get_text())
    else:
        log.warning("Unable to find duration")

    # Instead of an empty field they use `----` when the director is not known/credited
    if (director := css.select_one("#video_director td.text")) and not all(
        c == "-" for c in director.get_text()
    ):
        scraped["director"] = director.get_text().strip()
    else:
        log.warning("No director found")

    if maker := css.select_one("#video_maker a"):
        scraped["maker"] = maker.get_text()

    if label := css.select_one("#video_label a"):
        scraped["label"] = label.get_text()

    scraped["cast"] = []
    for cast in css.select(".cast"):
        performer = {}
        if name := cast.select_one(".star"):
            performer["name"] = name.get_text()
        if aliases := cast.select(".alias"):
            performer["aliases"] = ", ".join(a.get_text() for a in aliases)
        scraped["cast"].append(performer)

    scraped["categories"] = [cat.get_text() for cat in css.select(".genre")]

    return scraped


if __name__ == "__main__":
    import sys
    import pathlib
    import json

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <html file>")
        exit(1)

    file = pathlib.Path(sys.argv[1])
    if not file.exists():
        print(f"{file} is not a valid file")
        exit()

    html = file.read_text(encoding="utf-8")
    print(json.dumps(scrape_movie(html)))
