import base64
import json
import posixpath
import re
import sys
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from itertools import chain
from pathlib import Path, PureWindowsPath
from typing import Any, cast

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedGallery,
    ScrapedGroup,
    ScrapedImage,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, scraper_args

ensure_requirements("lxml")
from lxml import etree


@dataclass(frozen=True)
class Dialect:
    name: str
    title: tuple[str, ...] = ()
    details: tuple[str, ...] = ()
    date: tuple[str, ...] = ()
    studio: tuple[str, ...] = ()
    "Also used as the `photographer` of a gallery or image, which have no director"
    director: tuple[str, ...] = ()
    "Elements holding a real URL, not an id we would have to guess a URL from"
    urls: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    "Ordered best-first: a poster beats a backdrop"
    images: tuple[str, ...] = ()
    "Kodi movie sets, which map onto Stash groups"
    sets: tuple[str, ...] = ()
    "Elements wrapping one performer each, with <name>/<role>/<thumb> children"
    performers: tuple[str, ...] = ()
    "Elements holding every performer in one delimited string"
    performer_lists: tuple[str, ...] = ()
    performer_separator: str = " / "
    "Tag elements holding a delimited list rather than a single tag"
    joined_tags: tuple[str, ...] = ()
    tag_separator: str = " / "
    'Whether <title> is the *arrs\' "{site} - {season}x{date} - {title}" format'
    composite_title: bool = False


# Kodi's <movie>, and everything that has ever imitated it: Jellyfin, Emby,
# TinyMediaManager, MediaPortal, Radarr, Whisparr-Eros and Namer all write this
KODI = Dialect(
    name="Kodi",
    title=("title", "originaltitle", "sorttitle", "localtitle"),
    details=("plot", "outline", "tagline"),
    # <year> last: it is a bare year, and Stash accepts that as a partial date
    date=("premiered", "releasedate", "aired", "dateadded", "year"),
    studio=("studio", "showtitle"),
    director=("director", "photographer"),
    # <sourceid> is Namer's "where this scene came from"; <url> is hand-written
    urls=("sourceid", "url"),
    tags=("tag", "genre", "style"),
    images=(
        "thumb[@aspect='poster']",
        "art/poster",
        "thumb",
        "art/background",
        "fanart/thumb",
        "art/fanart",
    ),
    sets=("set",),
    performers=("actor",),
)

# Sonarr and Whisparr v2 are Sonarr forks: a "series" is the site and an
# "episode" is the scene, so <episodedetails> is a scene and <tvshow> is a studio
KODI_EPISODE = Dialect(
    name="Kodi episode",
    title=("title",),
    details=("plot", "outline"),
    date=("aired", "premiered", "releasedate", "year"),
    studio=("studio", "showtitle"),
    director=("director", "photographer"),
    urls=("sourceid", "url"),
    tags=("tag", "genre", "style"),
    images=("thumb[@aspect='poster']", "thumb", "art/poster"),
    performers=("actor",),
)

# A series/show is a site rather than a scene, so it only contributes a studio
KODI_SERIES = Dialect(
    name="Kodi series",
    studio=("title", "originaltitle", "sorttitle", "studio"),
    tags=("tag", "genre", "style"),
    urls=("url",),
)

# Roksbox, from Sonarr/Radarr/Whisparr. <length> is the *site's* runtime rather
# than this scene's, and <year> holds a full air date, hence the odd mapping
ROKSBOX = Dialect(
    name="Roksbox",
    title=("title",),
    details=("description",),
    date=("year",),
    director=("director", "photographer"),
    performer_lists=("actors",),
    performer_separator=" , ",
    joined_tags=("genre",),
    composite_title=True,
)

# WDTV, from Sonarr/Radarr/Whisparr. Shares the .xml extension with Roksbox and
# is told apart only by its root element, which is why dispatch is on the root
WDTV = Dialect(
    name="WDTV",
    title=("episode_name", "title"),
    details=("overview",),
    date=("firstaired",),
    studio=("series_name",),
    director=("director", "photographer"),
    performer_lists=("actor",),
    joined_tags=("genre",),
)

# Legacy MediaBrowser/Emby XML, still written by Radarr's MediaBrowser consumer
EMBY = Dialect(
    name="Emby legacy",
    title=("LocalTitle", "OriginalTitle", "SortTitle", "Name"),
    details=("Overview", "Description", "Tagline"),
    date=("PremiereDate", "ReleaseDate", "FirstAired", "ProductionYear"),
    studio=("Studios/Studio", "Studio", "Network"),
    director=("Director", "Photographer", "Persons/Person[Type='Director']/Name"),
    urls=("Trailer",),
    tags=("Genres/Genre", "Genre", "Tags/Tag", "Tag"),
    performers=("Persons/Person",),
    performer_lists=("Actors",),
    performer_separator="|",
)

EMBY_SERIES = Dialect(
    name="Emby legacy series",
    studio=("LocalTitle", "OriginalTitle", "SortTitle", "Name"),
    tags=("Genres/Genre", "Genre", "Tags/Tag", "Tag"),
)

DIALECTS: dict[str, Dialect] = {
    "movie": KODI,
    "musicvideo": KODI,
    "episodedetails": KODI_EPISODE,
    "tvshow": KODI_SERIES,
    "video": ROKSBOX,
    "details": WDTV,
    "Movie": EMBY,
    "Item": EMBY,
    "Series": EMBY_SERIES,
}

# Sidecars named after their media file, most specific first
OWN_SIDECARS = (
    "{stem}.nfo",
    ".nfo/{stem}.nfo",
    "{stem}.xml",
    "{stem}.info.json",
    "{stem}.json",
    "{name}.json",
)

# gallery-dl names a file's metadata after the file as downloaded, so a .png
# re-encoded to .jpg afterwards still has its metadata under the .png name
REENCODED_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".avif",
    ".jxl",
    ".mp4",
    ".webm",
    ".mkv",
)

# Stash addresses a file inside an archive as "<archive path>/<path in archive>"
ARCHIVE_SUFFIXES = (".zip", ".cbz")

# Sidecars describing the whole folder. Lower priority than the file's own, and
# used as defaults: a studio set here applies to every scene in the folder
FOLDER_SIDECARS = (
    "movie.nfo",
    "movie.xml",
    "folder.nfo",
    "tvshow.nfo",
    "series.xml",
    ".plexmatch",
    "info.json",
)

# Cover-image keywords, best first:
# `-thumb` is what the *arrs write for a scene; `.metathumb` is WDTV's JPEG-with-an-odd-extension
OWN_IMAGES = ("thumb", "poster", "cover")
"Keywords qualified by the video's own name, which outrank the folder's artwork"
LATE_OWN_IMAGES = ("fanart", "landscape")
"""
Backdrops, ranked under the cover-style keywords but still over anything
folder-wide: a file named after this video is about this video, while a
folder's `cover.jpg` belongs to whatever else is in the folder too.
"""
FOLDER_IMAGES = (
    "screenshot",
    "poster",
    "cover",
    "folder",
    "thumb",
    "fanart",
    "landscape",
    "banner",
)
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".metathumb")

# What can sit between a video's name and a cover keyword: "Scene-cover.jpg",
# "Scene cover.jpg", "Scene.cover.jpg". The empty one catches "Scenecover.jpg",
# which nobody would write by hand but some exporters produce.
COVER_DELIMITERS = ("-", "_", ".", " ", "")

# Kodi allows an .nfo holding nothing but a URL, and Whisparr-Eros appends its
# TMDB/StashDB links after </movie>, which makes the file invalid XML
# Both put the URL alone on its own line, so anchoring to the line avoids dragging in URLs that appear inside a plot
BARE_URL = re.compile(rb"^[ \t]*(https?://\S+?)[ \t]*$", re.MULTILINE)

MAX_IMAGE_BYTES = 20 * 1024 * 1024

# Namer writes str(None) into <theporndbid> when it has no id, and every writer
# here emits ids for providers whose URL layout we would only be guessing at, so
# a synthesised URL is only offered when the id really is one of these UUIDs
UUID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.IGNORECASE)

# Only providers whose URL layout is stable and public are rebuilt from an id:
# a bare numeric id could belong to anything, so it is left alone rather than turned into a plausible-looking 404
ID_URLS = {
    "tpdb": "https://theporndb.net/scenes/{}",
    "theporndb": "https://theporndb.net/scenes/{}",
    "theporndbid": "https://theporndb.net/scenes/{}",
    "stashdb": "https://stashdb.org/scenes/{}",
}

# Everyone in an <actor> is a performer, but Emby files people like the
# director through the same <Persons> list, tagged by <Type>
NON_PERFORMER_ROLES = {"director", "writer", "producer", "composer"}

# Roksbox has no studio element: Sonarr, Radarr and Whisparr build its <title>
# out of "{site} - {season}x{air date} - {episode title}", so the site and the
# scene's real title are only recoverable by taking that format string apart
COMPOSITE_TITLE = re.compile(r"^(?P<studio>.+?) - \d+x\S+ - (?P<title>.+)$")

# lxml's recovery drops a stray "&" along with the word after it, so ampersands
# that do not begin an entity are escaped before parsing rather than lost
STRAY_AMPERSAND = re.compile(rb"&(?![a-zA-Z][a-zA-Z0-9]*;|#[0-9]+;|#[xX][0-9a-fA-F]+;)")


@dataclass(frozen=True)
class Member:
    "A sidecar stored inside a zip archive rather than beside the media"

    archive: Path
    path: str

    @property
    def name(self) -> str:
        return posixpath.basename(self.path)

    def read_bytes(self) -> bytes:
        with zipfile.ZipFile(self.archive) as archive:
            return archive.read(self.path)

    def __str__(self) -> str:
        return f"{self.archive}/{self.path}"


Source = Path | Member


def own_sidecar_names(stem: str, name: str) -> list[str]:
    return [t.format(stem=stem, name=name) for t in OWN_SIDECARS] + [
        f"{stem}{suffix}.json" for suffix in REENCODED_SUFFIXES
    ]


def archive_member(media: Path) -> Member | None:
    "The archive and path inside it, when `media` is a file Stash found in an archive"
    for parent in media.parents:
        if parent.suffix.casefold() in ARCHIVE_SUFFIXES and parent.is_file():
            return Member(parent, media.relative_to(parent).as_posix())
    return None


def archive_names(archive: Path) -> set[str]:
    try:
        with zipfile.ZipFile(archive) as opened:
            return set(opened.namelist())
    except (OSError, zipfile.BadZipFile) as exc:
        log.debug(f"Could not open {archive}: {exc}")
        return set()


def sidecars_in_archive(member: Member) -> Iterator[tuple[Source, bool]]:
    "Sidecars beside a file inside an archive, which are in the archive too"
    names = archive_names(member.archive)
    directory = posixpath.dirname(member.path)
    name = posixpath.basename(member.path)
    stem = posixpath.splitext(name)[0]
    folder = [(posixpath.join(directory, n), True) for n in FOLDER_SIDECARS]
    own = [(posixpath.join(directory, n), False) for n in own_sidecar_names(stem, name)]
    for path, is_folder_level in dict.fromkeys(folder + own):
        if path in names:
            yield Member(member.archive, path), is_folder_level


def archive_folder_sidecars(archive: Path) -> Iterator[tuple[Source, bool]]:
    "A zipped gallery's own folder-level sidecars: the shallowest of each name"
    names = archive_names(archive)
    for wanted in FOLDER_SIDECARS:
        matches = [n for n in names if posixpath.basename(n) == wanted]
        if matches:
            yield Member(archive, min(matches, key=lambda n: n.count("/"))), True


def candidate_sidecars(media: Path) -> Iterator[tuple[Source, bool]]:
    """
    Yield every sidecar that could describe `media`, least specific first, paired
    with whether it describes the whole folder rather than this file

    Yielding in this order lets the caller merge by overwriting:
    a title in the file's own .nfo lands on top of one from the folder's
    """
    if member := archive_member(media):
        yield from sidecars_in_archive(member)
        return

    # A gallery can be a folder of loose images rather than a single file
    directory = media if media.is_dir() else media.parent
    stem = media.name if media.is_dir() else media.stem

    if media.is_file() and media.suffix.casefold() in ARCHIVE_SUFFIXES:
        yield from archive_folder_sidecars(media)

    folder = [(directory / name, True) for name in FOLDER_SIDECARS]
    own = [(directory / name, False) for name in own_sidecar_names(stem, media.name)]

    seen: set[Path] = set()
    for path, is_folder_level in folder + own:
        if path not in seen and path.is_file():
            seen.add(path)
            yield path, is_folder_level


def candidate_images(media: Path) -> Iterator[Path]:
    """
    Yield conventional cover images sitting next to `media`, best first.

    The directory is listed once and matched case-insensitively rather than
    stat-ed for each of the ~100 name/delimiter/extension combinations, which
    also means "Cover.JPG" is found on a case-sensitive filesystem.
    """
    directory = media if media.is_dir() else media.parent
    stem = (media.name if media.is_dir() else media.stem).casefold()

    try:
        entries = [
            path
            for path in sorted(directory.iterdir())
            if path.suffix.casefold() in IMAGE_SUFFIXES and path.is_file()
        ]
    except OSError as exc:
        log.debug(f"Could not list {directory}: {exc}")
        return

    def qualified(keyword: str) -> set[str]:
        return {f"{stem}{delimiter}{keyword}" for delimiter in COVER_DELIMITERS}

    wanted = [qualified(keyword) for keyword in OWN_IMAGES]
    wanted += [{stem}]  # the Roksbox convention: the video's own name, verbatim
    wanted += [qualified(keyword) for keyword in LATE_OWN_IMAGES]
    wanted += [{keyword} for keyword in FOLDER_IMAGES]

    for names in wanted:
        for path in entries:
            if path.stem.casefold() in names:
                yield path


def parse_xml(raw: bytes) -> etree._Element | None:
    parser = etree.XMLParser(
        recover=True, resolve_entities=False, no_network=True, load_dtd=False
    )
    cleaned = STRAY_AMPERSAND.sub(b"&amp;", raw.lstrip(b"\xef\xbb\xbf").lstrip())
    try:
        return etree.fromstring(cleaned, parser=parser)
    except etree.XMLSyntaxError as exc:
        log.debug(f"Not XML: {exc}")
        return None


def text(element: etree._Element | None) -> str | None:
    if element is None or not (value := (element.text or "").strip()):
        return None
    return unescape(value).strip() or None


def first_text(root: etree._Element, paths: Iterable[str]) -> str | None:
    return next(
        (value for path in paths for e in root.findall(path) if (value := text(e))),
        None,
    )


def all_text(root: etree._Element, paths: Iterable[str]) -> list[str]:
    return [value for path in paths for e in root.findall(path) if (value := text(e))]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    match value.strip():
        case str(v) if m := re.match(r"^(\d{4})-(\d{2})-(\d{2})", v):
            return "-".join(m.groups())
        case str(v) if m := re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", v):
            month, day, year = m.groups()
            return f"{year}-{month:0>2}-{day:0>2}"
        case str(v) if m := re.match(r"^(\d{4})$", v):
            return m.group(1)
    log.debug(f"Unrecognised date: {value}")
    return None


IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF8", "image/gif"),
)


def is_remote(reference: str) -> bool:
    return reference.startswith(("http://", "https://"))


def image_mime(data: bytes) -> str | None:
    """
    Sniff the format from the bytes rather than the extension.

    WDTV writes JPEGs as `.metathumb`, and tools mislabel PNGs as `.jpg` often
    enough that trusting the suffix puts a wrong MIME type in the data URI
    """
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return next((m for sig, m in IMAGE_SIGNATURES if data.startswith(sig)), None)


def data_uri(path: Path) -> str | None:
    """Base64 a local image so Stash can take it without filesystem access"""
    if (size := path.stat().st_size) > MAX_IMAGE_BYTES:
        log.warning(f"Skipping {path}: {size // 1024 // 1024}MB is too large to embed")
        return None

    data = path.read_bytes()
    if not (mime := image_mime(data)):
        log.warning(f"Skipping {path}: not a recognised image format")
        return None

    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def resolve_image(reference: str, directory: Path) -> str | None:
    """
    Turn an image reference from a sidecar into something Stash can fetch.

    Remote URLs pass straight through. Local references are resolved against the
    media's own folder before being trusted as absolute paths, because the
    absolute path in the file is whoever-wrote-it's filesystem, not ours: a
    Windows `Z:\\Videos\\x.jpg` is meaningless to Stash in a container, while the
    `x.jpg` sitting beside the video is exactly the same picture
    """
    if is_remote(reference):
        return reference

    basename = PureWindowsPath(reference.replace("\\", "/")).name
    for candidate in (directory / reference, directory / basename, Path(reference)):
        try:
            if candidate.is_file():
                return data_uri(candidate)
        except OSError:
            continue

    log.debug(f"Could not resolve image reference: {reference}")
    return None


def extract_performers(
    root: etree._Element, dialect: Dialect, directory: Path
) -> list[ScrapedPerformer]:
    performers: dict[str, ScrapedPerformer] = {}

    for path in dialect.performers:
        for node in root.findall(path):
            kind = (first_text(node, ("type", "Type")) or "actor").lower()
            if kind in NON_PERFORMER_ROLES:
                continue
            if not (name := first_text(node, ("name", "Name"))):
                continue

            performer: ScrapedPerformer = {"name": name}
            if alias := first_text(node, ("alias", "Alias")):
                performer["aliases"] = alias
            headshot = first_text(node, ("thumb", "image", "Thumb", "Image"))
            if headshot and (resolved := resolve_image(headshot, directory)):
                performer["images"] = [resolved]
            performers.setdefault(name.casefold(), performer)

    for path in dialect.performer_lists:
        for value in all_text(root, (path,)):
            for entry in value.split(dialect.performer_separator):
                # These lists are written as "Name - Character", and the
                # character half is a TV concept with no scene equivalent
                if name := entry.split(" - ")[0].strip():
                    performers.setdefault(name.casefold(), {"name": name})

    return list(performers.values())


def extract_tags(root: etree._Element, dialect: Dialect) -> list[ScrapedTag]:
    values = all_text(root, dialect.tags)
    for joined in all_text(root, dialect.joined_tags):
        values.extend(part.strip() for part in joined.split(dialect.tag_separator))

    tags: dict[str, ScrapedTag] = {}
    for value in values:
        if value:
            tags.setdefault(value.casefold(), {"name": value})
    return list(tags.values())


def extract_groups(root: etree._Element, dialect: Dialect) -> list[ScrapedGroup]:
    """Kodi movie sets, which are the closest thing a sidecar has to a Stash group"""
    groups: list[ScrapedGroup] = []
    for path in dialect.sets:
        for node in root.findall(path):
            # Kodi wrote <set>Name</set> before v17 and <set><name/></set> after
            if not (name := first_text(node, ("name",)) or text(node)):
                continue
            group: ScrapedGroup = {"name": name}
            if synopsis := first_text(node, ("overview", "plot")):
                group["synopsis"] = synopsis
            groups.append(group)
    return groups


def extract_urls(root: etree._Element, dialect: Dialect) -> list[str]:
    urls = [value for value in all_text(root, dialect.urls) if is_remote(value)]

    ids = [(n.get("type", "").lower(), text(n)) for n in root.findall("uniqueid")]
    ids += [("theporndbid", first_text(root, ("theporndbid",)))]

    urls += [
        template.format(value)
        for provider, value in ids
        if value and UUID.match(value) and (template := ID_URLS.get(provider))
    ]

    return urls


def extract_image(root: etree._Element, dialect: Dialect, media: Path) -> str | None:
    """
    The first image we can actually deliver

    A local file beats a remote URL even when the sidecar named the URL first:
    the artwork the *arrs download sits right there beside the video,
    but the URL it came from is a third-party CDN that may well have moved on
    """
    directory = media if media.is_dir() else media.parent
    references = all_text(root, dialect.images)

    candidates = chain(
        (resolve_image(r, directory) for r in references if not is_remote(r)),
        (data_uri(path) for path in candidate_images(media)),
        (r for r in references if is_remote(r)),
    )
    return next((image for image in candidates if image), None)


def parse_plexmatch(raw: bytes) -> ScrapedScene:
    lines = (
        line.partition(":") for line in raw.decode("utf-8", "replace").splitlines()
    )
    fields = {key.strip(): value.strip() for key, sep, value in lines if sep}

    if not (title := fields.get("Title")):
        return {}

    # `Episode:` lines mean a Sonarr layout, where the series is the site and
    # `Year` is when that site started rather than when this scene came out
    if "Episode" in fields:
        return {"studio": ScrapedStudio(name=title)}

    scraped: ScrapedScene = {"title": title}
    if date := parse_date(fields.get("Year")):
        scraped["date"] = date
    return scraped


def yt_dlp_date(yyyymmdd: Any) -> str | None:
    if isinstance(yyyymmdd, str) and re.fullmatch(r"\d{8}", yyyymmdd):
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return None


def parse_json(raw: bytes, media: Path) -> ScrapedScene:
    "JSON sidecars are told apart by content, any other JSON beside the media is ignored"
    try:
        info = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(info, dict):
        return {}
    if "extractor" in info and "webpage_url" in info:
        return parse_yt_dlp(info, media)
    if "category" in info and "subcategory" in info:
        return parse_gallery_dl(info)
    return {}


# Namespaces that are part of the tag's meaning rather than just a heading
GALLERY_DL_KEPT_NAMESPACES = {"male", "language"}
GALLERY_DL_PERFORMER_NAMESPACES = {"character", "cosplayer", "model"}


def gallery_dl_values(value: Any, *, tag_string: bool = False) -> list[str]:
    match value:
        case list():
            return [text for item in value if (text := str(item).strip())]
        case str() if tag_string and "," in value:
            return [text for part in value.split(",") if (text := part.strip())]
        # booru tag strings: space-separated, with underscores for spaces
        case str() if tag_string:
            return [part.replace("_", " ") for part in value.split()]
        case str() if value.strip():
            return [value.strip()]
        case _:
            return []


def gallery_dl_date(value: Any) -> str | None:
    match value:
        case bool():
            return None
        case int() | float():
            # Millisecond timestamps are ten times past anything 32-bit seconds can hold
            seconds = value / 1000 if value > 2147483647 * 10 else value
            return datetime.fromtimestamp(seconds, UTC).date().isoformat()
        case str():
            try:
                return datetime.fromisoformat(value.strip()).date().isoformat()
            except ValueError:
                return parse_date(value)
        case _:
            return None


def parse_gallery_dl(info: dict[str, Any]) -> ScrapedScene:
    "gallery-dl's --write-info-json (info.json) and --write-metadata (<file>.json)"
    keys = {key.casefold(): value for key, value in info.items()}
    artists = gallery_dl_values(keys.get("artist")) + gallery_dl_values(
        keys.get("artists")
    )
    groups = [
        group
        for key in ("group", "groups", "circle", "studio", "studios")
        for group in gallery_dl_values(keys.get(key))
    ]
    performers = [
        name
        for key in ("characters", "models", "performers")
        for name in gallery_dl_values(keys.get(key))
    ]
    tags: list[str] = []
    for key in ("tags", "categories", "parody"):
        for tag in gallery_dl_values(keys.get(key), tag_string=key == "tags"):
            namespace, separator, value = tag.partition(":")
            if not separator:
                tags.append(tag)
            elif namespace == "artist":
                artists.append(value)
            elif namespace == "group":
                groups.append(value)
            elif namespace in GALLERY_DL_PERFORMER_NAMESPACES:
                performers.append(value)
            elif namespace in GALLERY_DL_KEPT_NAMESPACES:
                tags.append(tag)
            else:
                tags.append(value)

    scraped: ScrapedScene = {}
    titles = [keys.get("title")] + [
        v for k, v in keys.items() if k.startswith("title_")
    ]
    if title := next(
        (t.strip() for t in titles if isinstance(t, str) and t.strip()), None
    ):
        scraped["title"] = title
    if isinstance(details := keys.get("description"), str) and details.strip():
        scraped["details"] = details.strip()
    if date := gallery_dl_date(keys.get("date")):
        scraped["date"] = date
    # The artist made the work; a group or circle only published it
    if studio := next(iter(artists + groups), None):
        scraped["studio"] = ScrapedStudio(name=studio)
    if performers:
        scraped["performers"] = [ScrapedPerformer(name=name) for name in performers]
    if tags:
        scraped["tags"] = [ScrapedTag(name=tag) for tag in tags]
    return scraped


def parse_yt_dlp(info: dict[str, Any], media: Path) -> ScrapedScene:
    "yt-dlp's --write-info-json output"
    scraped: ScrapedScene = {}
    if title := info.get("title"):
        scraped["title"] = title
    if details := (info.get("description") or "").strip():
        scraped["details"] = details
    scraped["urls"] = [info["webpage_url"]]
    # release_date is the original release when the site states one, upload_date the posting
    if date := yt_dlp_date(info.get("release_date")) or yt_dlp_date(
        info.get("upload_date")
    ):
        scraped["date"] = date
    if (duration := info.get("duration")) and duration >= 10:
        scraped["duration"] = int(duration)
    if cast_list := info.get("cast"):
        scraped["performers"] = [
            ScrapedPerformer(name=name) for name in cast_list if name
        ]

    # Categories first: where both exist they're the site's curated spelling of the tags
    tags: dict[str, str] = {}
    for tag in (info.get("categories") or []) + (info.get("tags") or []):
        if tag:
            tags.setdefault(tag.casefold(), tag)
    if tags:
        scraped["tags"] = [ScrapedTag(name=tag) for tag in tags.values()]

    # --write-thumbnail saves the cover beside the video, and the JSON's own
    # thumbnail URL is often a signed CDN link that expires
    if image := next(
        (uri for path in candidate_images(media) if (uri := data_uri(path))),
        info.get("thumbnail"),
    ):
        scraped["image"] = image
    return scraped


def read_sidecar(path: Source, media: Path) -> ScrapedScene:
    try:
        raw = path.read_bytes()
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        log.warning(f"Could not read {path}: {exc}")
        return {}

    if path.name == ".plexmatch":
        return parse_plexmatch(raw)

    if path.name.endswith(".json"):
        return parse_json(raw, media)

    scraped: ScrapedScene = {}
    if urls := [m.decode("utf-8", "replace") for m in BARE_URL.findall(raw)]:
        scraped["urls"] = urls

    if (root := parse_xml(raw)) is None:
        return scraped

    if not (dialect := DIALECTS.get(str(root.tag))):
        log.debug(f"{path.name}: unsupported root element <{root.tag}>")
        return scraped

    log.debug(f"{path.name}: reading as {dialect.name}")
    directory = media if media.is_dir() else media.parent

    if title := first_text(root, dialect.title):
        if dialect.composite_title and (parts := COMPOSITE_TITLE.match(title)):
            title = parts["title"]
            scraped["studio"] = ScrapedStudio(name=parts["studio"])
        scraped["title"] = title
    if details := first_text(root, dialect.details):
        scraped["details"] = details
    if date := parse_date(first_text(root, dialect.date)):
        scraped["date"] = date
    if studio := first_text(root, dialect.studio):
        scraped["studio"] = ScrapedStudio(name=studio)
    if director := first_text(root, dialect.director):
        scraped["director"] = director
    if tags := extract_tags(root, dialect):
        scraped["tags"] = tags
    if performers := extract_performers(root, dialect, directory):
        scraped["performers"] = performers
    if groups := extract_groups(root, dialect):
        scraped["groups"] = groups
    if urls := extract_urls(root, dialect):
        scraped["urls"] = scraped.get("urls", []) + urls
    if image := extract_image(root, dialect, media):
        scraped["image"] = image

    return scraped


LIST_FIELDS = ("urls", "tags", "performers", "groups")


def merge(base: ScrapedScene, overlay: ScrapedScene) -> ScrapedScene:
    """
    Fold a more specific sidecar over a less specific one

    Scalars are replaced, so a scene's own .nfo wins over the folder's; lists
    accumulate, so a folder-wide genre list and a per-scene one both survive
    """
    merged: ScrapedScene = {**base, **overlay}
    for key in LIST_FIELDS:
        combined = list(base.get(key, [])) + list(overlay.get(key, []))  # type: ignore[arg-type]
        if not combined:
            merged.pop(key, None)  # type: ignore[misc]
            continue
        seen: dict[str, Any] = {}
        for entry in combined:
            identity = entry if isinstance(entry, str) else entry.get("name", "")
            seen.setdefault(identity.casefold(), entry)
        merged[key] = list(seen.values())  # type: ignore[literal-required]
    return merged


def scrape_media(paths: list[Path]) -> ScrapedScene | None:
    """Read every sidecar belonging to every file behind one Stash object"""
    if not paths:
        log.error("Nothing to scrape: Stash gave us no readable files")
        return None

    found = [
        (is_folder_level, path, media)
        for media in paths
        for path, is_folder_level in candidate_sidecars(media)
    ]
    found.sort(key=lambda entry: not entry[0])

    scraped: ScrapedScene = {}
    for is_folder_level, path, media in found:
        log.debug(
            f"Found {'folder' if is_folder_level else 'file'}-level sidecar: {path}"
        )
        if partial := read_sidecar(path, media):
            scraped = merge(scraped, partial)

    # A cover sitting beside the media is worth having even with no sidecar
    covers = (image for media in paths for image in candidate_images(media))
    cover = None if "image" in scraped else next(covers, None)
    if cover and (uri := data_uri(cover)):
        log.debug(f"Using cover image: {cover}")
        scraped["image"] = uri

    if not scraped:
        log.info(f"No sidecar files found for: {', '.join(str(p) for p in paths)}")
        return None

    return scraped


def media_paths(args: dict[str, Any]) -> list[Path]:
    """Every file behind the object being scraped, skipping ones we cannot see"""
    paths = [Path(p) for f in args.get("files", []) if (p := dig(f, "path"))]
    readable = [p for p in paths if p.exists() or archive_member(p)]
    if missing := [p for p in paths if p not in readable]:
        log.warning(
            "Stash sees these files at paths this scraper cannot read, which"
            f" usually means differing mount points: {', '.join(map(str, missing))}"
        )
    return readable


def gallery_paths(args: dict[str, Any]) -> list[Path]:
    """
    Galleries need a fallback: a folder-based gallery has no `files` at all

    Stash sends `files[]` for a zipped gallery but nothing locating a gallery
    that is just a directory of images, so that one case has to ask Stash. The
    import is deferred to keep `requests` and config.ini off the scene path
    """
    if paths := media_paths(args):
        return paths

    if not (gallery_id := args.get("id")):
        return []

    from py_common.graphql import getGalleryPath

    if not (path := getGalleryPath(gallery_id)):
        log.error(
            f"Could not determine the path of gallery {gallery_id}. Folder-based"
            " galleries have to be looked up in Stash, which needs the URL and"
            " API key set in py_common/config.ini"
        )
        return []

    return [Path(path)] if Path(path).exists() else []


SHARED_FIELDS = (
    "title",
    "code",
    "details",
    "urls",
    "date",
    "studio",
    "tags",
    "performers",
)


def to_gallery(scene: ScrapedScene) -> ScrapedGallery:
    gallery = cast(
        ScrapedGallery, {k: v for k, v in scene.items() if k in SHARED_FIELDS}
    )
    if director := scene.get("director"):
        gallery["photographer"] = director
    return gallery


def to_image(scene: ScrapedScene) -> ScrapedImage:
    return cast(ScrapedImage, to_gallery(scene))


def clean(scraped: Any) -> Any:
    """Drop empty values so Stash never offers to overwrite a field with nothing"""
    match scraped:
        case dict():
            return {
                k: c
                for k, v in scraped.items()
                if (c := clean(v)) not in (None, [], {}, "")
            }
        case list():
            return [c for v in scraped if (c := clean(v)) not in (None, [], {}, "")]
        case _:
            return scraped


def main():
    op, args = scraper_args()

    result = None
    match op:
        case "scene-by-fragment" | "scene-by-query-fragment":
            result = scrape_media(media_paths(args))
        case "gallery-by-fragment":
            scene = scrape_media(gallery_paths(args))
            result = to_gallery(scene) if scene else None
        case "image-by-fragment":
            scene = scrape_media(media_paths(args))
            result = to_image(scene) if scene else None
        case _:
            log.error(f"Invalid operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(clean(result)))


if __name__ == "__main__":
    main()
