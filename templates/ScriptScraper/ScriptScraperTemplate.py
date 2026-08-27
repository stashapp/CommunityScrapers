import json
import sys
from py_common import log
from py_common.util import scraper_args
from py_common.types import (
    ScrapedScene,
    ScrapedGallery,
    ScrapedMovie,
    ScrapedImage,
    ScrapedStudio,
    ScrapedPerformer,
    ScrapedTag,
)


def scene_by_url(_: str) -> ScrapedScene:
    return {
        "title": "Example scraped scene",
        "details": "Great scene, lotta sexy stuff",
        # Technically deprecated, but still used in scene scraper
        "url": "https://example.com",
        "urls": [
            "https://example.com/first",
            "https://example.com/second",
        ],
        "date": "2023-01-02",
        "image": "https://placehold.co/1920x1080/grey/white?text=Example+scraped+scene",
        # Can be created in the scraper interface
        "studio": {
            "name": "Cool Studio",
            "url": "https://coolstudio.com",
            "image": "https://imageholdr.com/660x200/transparent/fa244b?text=Studio+Logo&font-size=125",
            # Can be created if the scraper is used in Tagger view
            "parent": ScrapedStudio(
                {
                    "name": "Cool Network",
                    "url": "https://coolnetwork.com",
                    "image": "https://imageholdr.com/660x130/transparent/e124fa?text=Network+Logo&font-size=115&font-family=impact",
                }
            ),
        },
        # Can be created in the scene scraper modal, not in Tagger view yet
        "movies": [movie_by_url(_)],
        "tags": [
            ScrapedTag(name="First tag"),
            {"name": "Second tag"},
        ],
        "performers": [
            performer_by_url(_),
            {"name": "Second performer"},
        ],
        "code": "any string",
        "director": "same guy as before?",
    }


def movie_by_url(url) -> ScrapedMovie:
    return {
        "name": "Movie Title",
        "aliases": "Movie of the Scene, That Movie You know, The One With The Scene",
        "date": "2023-01-02",
        # in seconds
        "duration": "5400",
        # Not added when a movie is added through a scene scrape
        "director": "Some guy",
        "synopsis": "Even more sexy stuff",
        # The scraper interface will not offer to create this studio so needs
        # to exist already: anything except the Name field here is useless
        "studio": {
            "name": "Cool Network",
            "url": "https://awesomestudio.com",
            "parent": {
                "name": "Awesome Network",
                "url": "https://awesomenetwork.com",
            },
        },
        # 1-5, no fractions: not yet migrated to the new rating100 system
        "rating": "4",
        "front_image": "https://placehold.co/800x1200/brown/white?text=Front+cover+image",
        "back_image": "https://placehold.co/800x1200/slategrey/white?text=Back+cover+image",
        "url": "https://awesomestudio.com/movie-title",
    }


def performer_by_url(_: str) -> ScrapedPerformer:
    return {
        "name": "Example Performer",
        # This is only added when a performer added through Tagger view
        "disambiguation": "CoolSite.com",
        # has to be one of "MALE", "FEMALE", "TRANSGENDER_MALE", "TRANSGENDER_FEMALE", "INTERSEX", "NON_BINARY"
        "gender": "FEMALE",
        "urls": ["https://bunny-fun-times.com"],
        "twitter": "https://twitter.com/bad_bunny",
        "instagram": "https://instagram.com/bunny4lyfe",
        "birthdate": "1990-01-01",
        # Has to be one of "CAUCASIAN", "BLACK", "ASIAN", "INDIAN", "LATIN", "MIDDLE_EASTERN", "MIXED", "OTHER"
        "ethnicity": "MIXED",
        # Non-existent country will work
        # but Stash will recognize most countries and show their flag in the UI
        "country": "USA",
        # Has to be one of "BLUE", "BROWN", "GREEN", "GREY", "HAZEL", "RED"
        "eye_color": "RED",
        # has to be one of "BLONDE", "BRUNETTE", "BLACK", "RED", "AUBURN", "GREY", "BALD", "VARIOUS", "OTHER"
        "hair_color": "VARIOUS",
        # in centimeters
        "height": "175",
        "measurements": "No validation for this field",
        "fake_tits": "no",
        "penis_length": "15",
        "circumcised": "N/A",
        "career_length": "2005-2015",
        "tattoos": "Left arm, Right bicep, Forehead",
        "piercings": "Right nostril, Philtrum",
        # Stash will split these on commas: ["Any", "Number", "Of", "Aliases"]
        "aliases": "Any, Number, Of, Aliases",
        "tags": [
            {"name": "Redhead"},
            {"name": "MILF"},
        ],
        # This image will be used when a performer is added in a single scene scrape
        "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC",  # deprecated
        # if the performer is added through a direct performer scrape or as a part
        # of a scene in Tagger view you will get to browse these images and choose the one you'd like to use
        "images": [
            "https://placehold.co/800x1200/green/white?text=Performer+first+image",
            "https://placehold.co/800x1200/blue/white?text=Performer+second+image",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAAhKDveksOjmAAAAAElFTkSuQmCC",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNkYPhfz0AEYBxVSF+FAP5FDvcfRYWgAAAAAElFTkSuQmCC",
        ],
        "details": "A little blurb about the performer",
        "death_date": "2020-12-31",
        # in kilograms
        "weight": "64",
    }


def gallery_by_url(_: str) -> ScrapedGallery:
    return {
        "title": "Example gallery",
        "details": "Great gallery, lotta sexy stuff",
        "url": "https://example.com",
        "urls": [
            "https://example.com/first",
            "https://example.com/second",
        ],
        "date": "2023-01-02",
        "code": "test",
        "studio": {
            "name": "Cool Studio",
            "url": "https://coolstudio.com",
            "image": "https://imageholdr.com/660x200/transparent/fa244b?text=Studio+Logo&font-size=125",
            "parent": {
                "name": "Cool Network",
                "url": "https://coolnetwork.com",
                "image": "https://imageholdr.com/660x130/transparent/e124fa?text=Network+Logo&font-size=115&font-family=impact",
            },
        },
        "tags": [
            {
                "name": "Example tag",
            },
            {"name": "Second tag"},
        ],
        "performers": [
            performer_by_url(_),
            {"name": "Second performer"},
        ],
    }


def image_by_url(_: str) -> ScrapedImage:
    return {
        "title": "Example image",
        "code": "image code",
        "date": "2024-01-02",
        "details": "Details are not required but can be a nice place for extra information",
        "studio": {
            "name": "Cool Studio",
            "url": "https://coolstudio.com",
            "image": "https://imageholdr.com/660x200/transparent/fa244b?text=Studio+Logo&font-size=125",
            "parent": {
                "name": "Cool Network",
                "url": "https://coolnetwork.com",
                "image": "https://imageholdr.com/660x130/transparent/e124fa?text=Network+Logo&font-size=115&font-family=impact",
            },
        },
        "tags": [
            {"name": "Example tag"},
            {"name": "Second tag"},
        ],
        "performers": [
            performer_by_url(_),
            {"name": "Second performer"},
        ],
        "photographer": "Camera Guy",
        "urls": [
            "https://example.com/image-of-thing",
            "https://example.com/image-but-bigger",
        ],
    }


if __name__ == "__main__":
    op, args = scraper_args(prog="Test Scraper")
    result = None
    log.debug(f"{op}: {json.dumps(args)}")
    match op, args:
        case "gallery-by-fragment", args:
            result = gallery_by_url("dummy-url")
        case "gallery-by-url" | "gallery-by-fragment", {"url": url}:
            result = gallery_by_url(url)
        case "movie-by-url", {"url": url}:
            result = movie_by_url(url)
        case "scene-by-url", {"url": url}:
            result = scene_by_url(url)
        case "scene-by-name", {"name": name}:
            result = [scene_by_url(name)]
        case "scene-by-fragment", args:
            result = scene_by_url("dummy-url")
        case "scene-by-query-fragment", args:
            result = scene_by_url("dummy-url")
        case "performer-by-url", {"url": url}:
            result = performer_by_url(url)
        case "performer-by-name", {"name": name}:
            result = [performer_by_url(name)]
        case "performer-by-fragment", {"url": url}:
            result = performer_by_url(url)
        case "image-by-url", {"url": url}:
            result = image_by_url(url)
        case "image-by-fragment", args:
            result = image_by_url("dummy-url")
        case _:
            log.error(f"Unknown operation {op}")
            sys.exit(1)

    print(json.dumps(result))
