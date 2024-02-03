from typing import Literal, Required, TypedDict

"""
Types for outputs that scrapers can produce and that Stash will accept
"""

class ScrapedTag(TypedDict):
    name: str
    "Name is the only required field"

class ScrapedPerformer(TypedDict, total=False):
    name: Required[str]
    "Name is the only required field"
    disambiguation: str
    "This is only added through Tagger view"
    gender: Literal["MALE", "FEMALE", "TRANSGENDER_MALE", "TRANSGENDER_FEMALE", "INTERSEX", "NON_BINARY"]
    url: str
    twitter: str
    instagram: str
    birthdate: str
    "Must be in the format YYYY-MM-DD"
    death_date: str
    "Must be in the format YYYY-MM-DD"
    ethnicity: Literal["CAUCASIAN", "BLACK", "ASIAN", "INDIAN", "LATIN", "MIDDLE_EASTERN", "MIXED", "OTHER"]
    country: str
    "Not validated"
    eye_color: Literal["BLUE", "BROWN", "GREEN", "GREY", "HAZEL", "RED"]
    hair_color: Literal["BLONDE", "BRUNETTE", "BLACK", "RED", "AUBURN", "GREY", "BALD", "VARIOUS", "OTHER"]
    "Hair color, can be 'VARIOUS' or 'OTHER' if the performer has multiple hair colors"
    height: str
    "Height in centimeters"
    weight: str
    "Weight in kilograms"
    measurements: str
    "bust-waist-hip measurements in centimeters, with optional cupsize for bust (e.g. 90-60-90, 90C-60-90)"
    fake_tits: str
    penis_length: str
    circumcised: str
    career_length: str
    tattoos: str
    piercings: str
    aliases: str
    "Must be comma-delimited in order to be parsed correctly"
    tags: list[ScrapedTag]
    image: str
    images: list[str]
    "Images can be URLs or base64-encoded images"
    details: str

class ScrapedStudio(TypedDict, total=False):
    name: Required[str]
    "Name is the only required field"
    url: str
    parent: 'ScrapedStudio'
    image: str

class ScrapedMovie(TypedDict, total=False):
    name: str
    date: str
    "Must be in the format YYYY-MM-DD"
    duration: str
    "Duration in seconds"
    director: str
    synopsis: str
    studio: ScrapedStudio
    rating: str
    front_image: str
    back_image: str
    url: str
    aliases: str

class ScrapedGallery(TypedDict, total=False):
    title: str
    details: str
    url: str
    urls: list[str]
    date: str
    "Must be in the format YYYY-MM-DD"
    studio: ScrapedStudio
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]
    code: str
    photographer: str

class ScrapedScene(TypedDict, total=False):
    title: str
    details: str
    url: str
    urls: list[str]
    date: str
    image: str
    studio: ScrapedStudio
    movies: list[ScrapedMovie]
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]
    code: str
    director: str

# Technically we can return a full ScrapedPerformer but the current UI only
# shows the name. The URL is absolutely necesserary for the result to be used
# in the next step: actually scraping the performer
class PerformerSearchResult(TypedDict):
    name: str
    url: str

# Technically we can return a full ScrapedScene but the current UI only
# shows the name, image, studio, tags and performers. The URL is absolutely
# necesserary for the result to be used in the next step: actually scraping the scene
class SceneSearchResult(TypedDict, total=False):
    title: Required[str]
    url: Required[str]
    date: str
    "Must be in the format YYYY-MM-DD"
    image: str
    "Image can be a URL or base64-encoded image"
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]
    studio: ScrapedStudio
