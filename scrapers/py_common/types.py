from typing import Literal, Required, TypedDict

"""
Types for outputs that scrapers can produce and that Stash will accept
"""

# export specific types for eternal inclusion
type Ethnicity = Literal[
    "CAUCASIAN",
    "BLACK",
    "ASIAN",
    "INDIAN",
    "LATIN",
    "MIDDLE_EASTERN",
    "MIXED",
    "OTHER",
]

type EyeColor = Literal["BLUE", "BROWN", "GREEN", "GREY", "HAZEL", "RED"]
type HairColor = Literal[
    "BLONDE",
    "BRUNETTE",
    "BLACK",
    "RED",
    "AUBURN",
    "GREY",
    "BALD",
    "VARIOUS",
    "OTHER",
]


class ScrapedTag(TypedDict, total=False):
    name: Required[str]
    "Name is the only required field"
    stored_id: str
    "Set if tag matched"


class ScrapedPerformer(TypedDict, total=False):
    name: Required[str]
    "Name is the only required field"
    stored_id: str
    "Set if performer matched"
    disambiguation: str
    "This is only added through Tagger view"
    gender: Literal[
        "MALE",
        "FEMALE",
        "TRANSGENDER_MALE",
        "TRANSGENDER_FEMALE",
        "INTERSEX",
        "NON_BINARY",
    ]
    url: str
    "Deprecated: use urls"
    urls: list[str]
    twitter: str
    "Deprecated: use urls"
    instagram: str
    "Deprecated: use urls"
    birthdate: str
    "Must be in the format YYYY-MM-DD"
    death_date: str
    "Must be in the format YYYY-MM-DD"
    ethnicity: Ethnicity
    country: str
    "Not validated"
    eye_color: EyeColor
    hair_color: HairColor
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
    "The 'image' field is deprecated, use 'images' instead"
    images: list[str]
    "Images can be URLs or base64-encoded images"
    details: str


class ScrapedStudio(TypedDict, total=False):
    name: Required[str]
    "Name is the only required field"
    stored_id: str
    "Set if studio matched"
    url: str
    "Deprecated: use urls"
    urls: list[str]
    parent: "ScrapedStudio"
    image: str
    details: str
    aliases: str
    "Aliases must be comma-delimited to be parsed correctly"
    tags: list[ScrapedTag]


class ScrapedGroup(TypedDict, total=False):
    stored_id: str
    name: str
    aliases: str
    duration: str
    "Duration in seconds"
    date: str
    "Must be in the format YYYY-MM-DD"
    rating: str
    director: str
    url: str
    "Deprecated: use urls"
    urls: list[str]
    synopsis: str
    studio: ScrapedStudio
    tags: list[ScrapedTag]
    front_image: str
    "This should be a base64 encoded data URL"
    back_image: str
    "This should be a base64 encoded data URL"


# ScrapedMovie is deprecated in favor of ScrapedGroup
ScrapedMovie = ScrapedGroup


class ScrapedGallery(TypedDict, total=False):
    title: str
    code: str
    details: str
    photographer: str
    url: str
    "Deprecated: use urls"
    urls: list[str]
    date: str
    "Must be in the format YYYY-MM-DD"
    studio: ScrapedStudio
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]


class ScrapedScene(TypedDict, total=False):
    title: str
    code: str
    details: str
    director: str
    url: str
    "Deprecated: use urls"
    urls: list[str]
    date: str
    image: str
    "This should be a base64 encoded data URL"
    studio: ScrapedStudio
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]
    movies: list[ScrapedMovie]
    "Deprecated: use groups"
    groups: list[ScrapedGroup]
    duration: int


class ScrapedImage(TypedDict, total=False):
    title: str
    code: str
    details: str
    photographer: str
    urls: list[str]
    date: str
    studio: ScrapedStudio
    tags: list[ScrapedTag]
    performers: list[ScrapedPerformer]


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
