import json
import sys
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedImage, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("PIL:pillow")
from PIL import ExifTags, Image, ImageFile, IptcImagePlugin

config = get_config(
    default="""
# The scraper picks one of several possibly conflicting fields for the date, title
# and studio / photographer: these add every value it saw to the details instead
details_date_fields = False
details_title_fields = False
details_author_fields = False

# Add camera make, model, lens make and lens model as one line to the details
details_camera_infos = False

# Add every field the scraper doesn't otherwise use to the details
details_unprocessed_fields = False

# Comma-separated field names to leave out of the unprocessed fields
# (the default ignore list already skips most camera settings)
details_unprocessed_fields_ignored =

# Comma-separated field names from the default ignore list to include anyway
details_unprocessed_fields_unignored =
"""
)

DESCRIPTION_FIELDS = [
    "EXIF:ImageDescription",
    "EXIF:XPComment",
    "EXIF:UserComment",
    "IPTC:Caption-Abstract",
    "XMP:dc:description",
]
# The last valid date wins, so the most authoritative fields come last
DATE_FIELDS = [
    "IPTC:DateCreated",
    "EXIF:DateTime",
    "IPTC:DigitalCreationDate",
    "EXIF:DateTimeDigitized",
    "EXIF:DateTimeOriginal",
]
TITLE_FIELDS = [
    "EXIF:DocumentName",
    "EXIF:XPTitle",
    "IPTC:ObjectName",
    "IPTC:Headline",
    "XMP:dc:title",
    "XMP:photoshop:Headline",
]
AUTHOR_FIELDS = [
    "EXIF:XPAuthor",
    "IPTC:By-line",
    "XMP:dc:creator",
    "EXIF:Artist",
]
KEYWORD_FIELDS = [
    "EXIF:XPKeywords",
    "IPTC:Keywords",
    "XMP:dc:subject",
    "XMP:pdf:Keywords",
]
CAMERA_FIELDS = {
    "make": ["EXIF:Make"],
    "model": ["EXIF:Model"],
    "lens_make": ["EXIF:LensMake"],
    "lens_model": ["EXIF:LensSpecification", "EXIF:LensModel", "XMP:aux:Lens"],
}

DATE_FORMATS = {"EXIF:": "%Y:%m:%d %H:%M:%S", "IPTC:": "%Y%m%d"}

# IPTC-IIM application record (2) datasets, named as exiftool names them
IPTC_DATASETS = {
    5: "ObjectName",
    15: "Category",
    20: "SupplementalCategories",
    25: "Keywords",
    40: "SpecialInstructions",
    55: "DateCreated",
    60: "TimeCreated",
    62: "DigitalCreationDate",
    80: "By-line",
    85: "By-lineTitle",
    90: "City",
    92: "Sub-location",
    95: "Province-State",
    101: "Country-PrimaryLocationName",
    105: "Headline",
    110: "Credit",
    115: "Source",
    116: "CopyrightNotice",
    120: "Caption-Abstract",
    122: "Writer-Editor",
}

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
XMP_PREFIXES = {
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/xap/1.0/mm/": "xmpMM",
    "http://ns.adobe.com/xap/1.0/rights/": "xmpRights",
    "http://ns.adobe.com/photoshop/1.0/": "photoshop",
    "http://ns.adobe.com/pdf/1.3/": "pdf",
    "http://ns.adobe.com/exif/1.0/": "exif",
    "http://ns.adobe.com/exif/1.0/aux/": "aux",
    "http://ns.adobe.com/tiff/1.0/": "tiff",
    "http://ns.adobe.com/lightroom/1.0/": "lr",
    "http://ns.adobe.com/camera-raw-settings/1.0/": "crs",
    "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/": "Iptc4xmpCore",
}

DEFAULT_IGNORED_LABELS = {
    "AFAreaMode", "AFPoint", "AFPointsInFocus", "ActiveDLighting", "ApertureValue",
    "BaselineExposure", "BaselineExposureOffset", "BitsPerSample", "BrightnessValue",
    "ByteOrder", "ColorMode", "ColorSpace", "ComponentsConfiguration",
    "CompressedBitsPerPixel", "Compression", "Contrast", "CustomRendered", "DataDump",
    "DerivedFrom", "DigitalZoom", "DigitalZoomRatio", "ExifImageHeight", "ExifImageWidth",
    "ExifInteroperabilityOffset", "ExifOffset", "ExifVersion", "ExposureBiasValue",
    "ExposureCompensation", "ExposureIndex", "ExposureMode", "ExposureProgram",
    "ExposureTime", "FNumber", "FileSource", "Flash", "FlashCompensation", "FlashSetting",
    "FlashPixVersion", "FocalLength", "FocalLengthIn35mmFilm", "FocalPlaneResolutionUnit",
    "FocalPlaneXResolution", "FocalPlaneYResolution", "Focus", "GPSInfo", "GPSVersionID",
    "GainControl", "ICCProfile", "ISO", "ISOSelection", "ISOSpeed", "ISOSpeedRatings",
    "ImageAdjustment", "ImageHeight", "ImageLength", "ImageStabilization", "ImageWidth",
    "InteropIndex", "InteropVersion", "JpegIFByteCount", "JpegIFOffset", "LensID",
    "LightSource", "MakerNote", "MaxApertureValue", "MeteringMode", "ModifyDate",
    "NativeDigest", "NoiseReduction", "Orientation", "Padding",
    "PhotometricInterpretation", "PixelXDimension", "PixelYDimension", "PrintImageMatching",
    "Quality", "RelatedImageHeight", "RelatedImageWidth", "ResolutionUnit",
    "RetouchHistory", "Saturation", "SceneCaptureType", "SceneMode", "SceneType",
    "SensingMethod", "Sharpening", "Sharpness", "ShutterSpeedValue", "SubsecTime", "SubsecTimeDigitized", "SubsecTimeOriginal", "ToneComp", "WhiteBalance",
    "XMPToolkit", "XResolution", "YCbCrPositioning", "YResolution", "format",
}  # fmt: skip


def comma_separated(value: Any) -> set[str]:
    return {part for item in str(value).split(",") if (part := item.strip())}


ignored_labels = (
    DEFAULT_IGNORED_LABELS | comma_separated(config.details_unprocessed_fields_ignored)
) - comma_separated(config.details_unprocessed_fields_unignored)


def exif_value(name: str, value: Any, endian: str) -> Any:
    match name, value:
        case ("XPTitle" | "XPComment" | "XPAuthor" | "XPKeywords" | "XPSubject", _):
            # Windows' XP* tags are UTF-16LE whatever the file's byte order
            return bytes(value).decode("utf-16-le", "replace")
        case ("UserComment", bytes()):
            # The first 8 bytes name the comment's character code
            code, text = value[:8], value[8:]
            if code.startswith(b"UNICODE"):
                return text.decode(
                    "utf-16-be" if endian == ">" else "utf-16-le", "replace"
                )
            return text.decode("utf-8", "replace")
        case (_, bytes()):
            text = value.decode("utf-8", "replace").strip("\x00")
            if text and text.isprintable():
                return text
            # Binary values such as GPSAltitudeRef are a few raw numbers
            return " ".join(str(byte) for byte in value)
        case (_, tuple()):
            return " ".join(str(item) for item in value)
        case _:
            return value


def read_exif(image: ImageFile.ImageFile) -> dict[str, Any]:
    exif = image.getexif()
    endian = getattr(exif, "endian", "<")
    tags = [
        (ExifTags.TAGS, dict(exif)),
        (ExifTags.TAGS, exif.get_ifd(ExifTags.IFD.Exif)),
        (ExifTags.GPSTAGS, exif.get_ifd(ExifTags.IFD.GPSInfo)),
    ]
    return {
        f"EXIF:{name}": exif_value(name, value, endian)
        for names, ifd in tags
        for tag_id, value in ifd.items()
        if (name := names.get(tag_id))
    }


def iptc_text(raw: bytes) -> str:
    "IPTC is UTF-8 in practice, but older files are Latin-1"
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def read_iptc(image: ImageFile.ImageFile) -> dict[str, Any]:
    info = IptcImagePlugin.getiptcinfo(image) or {}
    return {
        f"IPTC:{name}": [iptc_text(v) for v in value]
        if isinstance(value, list)
        else iptc_text(value)
        for (record, dataset), value in info.items()
        if record == 2 and (name := IPTC_DATASETS.get(dataset))
    }


def xmp_name(qualified: str) -> str:
    uri, _, local = qualified[1:].partition("}")
    prefix = XMP_PREFIXES.get(uri) or uri.rstrip("/#").rpartition("/")[2]
    return f"XMP:{prefix}:{local}"


def xmp_values(prop: ElementTree.Element) -> list[str]:
    "Bag and Seq values are all kept; for language alternatives only x-default when present"
    items = [li for li in prop.findall(f"./*/{RDF}li") if len(li) == 0 and li.text]
    if prop.find(f"{RDF}Alt") is not None and (
        default := [li for li in items if li.get(XML_LANG) == "x-default"]
    ):
        items = default
    return [li.text for li in items if li.text]


def read_xmp(packet: str | bytes) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(packet)
    except ElementTree.ParseError as e:
        log.debug(f"Ignoring unparseable XMP: {e}")
        return {}
    fields: dict[str, Any] = {}
    for description in root.iterfind(f".//{RDF}RDF/{RDF}Description"):
        for attribute, value in description.attrib.items():
            if not attribute.startswith((RDF, "{http://www.w3.org/XML/")):
                fields[xmp_name(attribute)] = value
        for prop in description:
            if values := xmp_values(prop):
                fields[xmp_name(prop.tag)] = values
            elif len(prop) == 0 and prop.text and prop.text.strip():
                fields[xmp_name(prop.tag)] = prop.text
    return fields


def read_metadata(path: str) -> dict[str, Any]:
    try:
        with Image.open(path) as image:
            xmp = image.info.get("xmp") or image.info.get("XML:com.adobe.xmp")
            return read_exif(image) | read_iptc(image) | (read_xmp(xmp) if xmp else {})
    except OSError as e:
        log.debug(f"Could not read metadata from '{path}': {e}")
        return {}


def clean_text(value: Any) -> str:
    return str(value).replace("\x00", "").strip()


def texts(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value]
    return [text for item in items if (text := clean_text(item))]


def present(data: dict[str, Any], fields: list[str]) -> list[tuple[str, list[str]]]:
    return [
        (field, values)
        for field in fields
        if (value := data.get(field)) and (values := texts(value))
    ]


def label(field: str) -> str | None:
    "`EXIF:Artist` is labelled `Artist`, `XMP:dc:title` is labelled `title`"
    name = field.rpartition(":")[2]
    return None if name in ignored_labels else name


def parse_date(field: str, value: Any) -> datetime | None:
    if not (
        fmt := next((f for p, f in DATE_FORMATS.items() if field.startswith(p)), None)
    ):
        return None
    try:
        # EXIF/IPTC dates carry no timezone
        date = datetime.strptime(clean_text(value), fmt)  # noqa: DTZ007
    except ValueError:
        return None
    # Cameras with an unset clock write 2000-01-01
    return None if (date.year, date.month, date.day) == (2000, 1, 1) else date


def labelled_lines(fields: list[tuple[str, list[str]]]) -> str:
    return "".join(
        f"{name}: {value}\n"
        for field, values in fields
        if (name := label(field))
        for value in values
    )


def unprocessed_details(data: dict[str, Any], processed: set[str]) -> str:
    details = ""
    sections_seen: set[str] = set()
    for field in sorted(data):
        if field in processed or not (name := label(field)):
            continue
        if (section := field.partition(":")[0]) not in sections_seen:
            details += f"\n{section} metadata:\n"
            sections_seen.add(section)
        value = data[field]
        items = value if isinstance(value, list) else [value]
        details += f"{name}: {' '.join(clean_text(item) for item in items)}\n"
    return details


def to_scraped_image(data: dict[str, Any]) -> ScrapedImage:
    image: ScrapedImage = {}
    details = ""

    if description_lines := "".join(
        f"{value}\n"
        for _, values in present(data, DESCRIPTION_FIELDS)
        for value in values
    ):
        details += description_lines + "\n"

    dates = [
        (field, date)
        for field in DATE_FIELDS
        if (value := data.get(field)) and (date := parse_date(field, value))
    ]
    if dates:
        image["date"] = dates[-1][1].date().isoformat()
    if config.details_date_fields and (
        date_lines := "".join(
            f"{name}: {date.isoformat()}\n"
            for field, date in dates
            if (name := label(field))
        )
    ):
        details += f"Dates:\n{date_lines}\n"

    titles = present(data, TITLE_FIELDS)
    if titles:
        image["title"] = titles[-1][1][-1]
    if config.details_title_fields and (title_lines := labelled_lines(titles)):
        details += f"Titles:\n{title_lines}\n"

    authors = present(data, AUTHOR_FIELDS)
    if authors:
        author = authors[-1][1][-1]
        image["studio"] = {"name": author}
        image["photographer"] = author
    if config.details_author_fields and (author_lines := labelled_lines(authors)):
        details += f"Authors:\n{author_lines}\n"

    tags = {
        tag: None
        for _, values in present(data, KEYWORD_FIELDS)
        for value in values
        for part in value.split(",")
        if (tag := part.strip())
    }
    if tags:
        image["tags"] = [ScrapedTag(name=tag) for tag in tags]

    camera = {
        kind: found[-1][1][-1]
        for kind, fields in CAMERA_FIELDS.items()
        if (found := present(data, fields))
    }
    if config.details_camera_infos and "make" in camera and "model" in camera:
        details += " ".join(camera[kind] for kind in CAMERA_FIELDS if kind in camera)
        details += "\n"

    if config.details_unprocessed_fields:
        # Handled fields count as processed even when they turned out empty
        processed = {field for field, _ in dates} | {
            field
            for fields in (
                DESCRIPTION_FIELDS,
                TITLE_FIELDS,
                AUTHOR_FIELDS,
                KEYWORD_FIELDS,
                *CAMERA_FIELDS.values(),
            )
            for field in fields
            if field in data
        }
        details += unprocessed_details(data, processed)

    if details:
        image["details"] = details
    return image


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "image-by-fragment", {"files": list() as files}:
            for path in (path for file in files if (path := file.get("path"))):
                log.debug(f"Reading metadata from '{path}'")
                result = to_scraped_image(read_metadata(path))
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
