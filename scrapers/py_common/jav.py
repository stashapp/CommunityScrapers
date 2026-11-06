import re

_VIDEO_EXTENSION = re.compile(
    r"\.(?:mp4|mkv|avi|wmv|mov|m4v|ts|flv|webm|mpg|mpeg|rmvb|iso)$", re.IGNORECASE
)

_NOISE = re.compile(
    r"""
    [a-z\d]{2,20}\.(?:com|net|org|me|cc|co|xyz|vip|app|tv|la|one|top|info|biz|club|jp|cn|in)(?![a-z])  # pirate group names/sites
    |(?<![a-z\d])(?:fhd|hd|sd|\d(?:\.\d)?k|\d{3,4}p|[hx]26[45]|hevc|uncensored|leak(?:ed)?|hack)(?![a-z\d])  # quality tags
    |(?<![a-z\d])(?:cd|disc|part|pt)[-_ ]?\d{1,2}(?!\d)  # disc markers
    |(?:(?<=\d)|(?<=\d[a-z]))[-_]?(?:ch|cs|uc)(?![a-z\d])  # subtitle and leak tags: SSNI-782ch, MIAA-291-CS
    """,
    re.IGNORECASE | re.VERBOSE,
)

_FC2 = re.compile(
    r"FC2[^A-Z\d]{0,5}(?:PPV[^A-Z\d]{0,5})?(\d{5,7})(?!\d)", re.IGNORECASE
)

_HEYZO = re.compile(
    r"HEYZO[^A-Z\d]{0,3}(?:[A-Z]{2}[^A-Z\d]{0,3})?(\d{4})(?!\d)", re.IGNORECASE
)

# Uncensored studios with their own ID formats, left to their site scrapers:
# Caribbeancom/1pondo/Paco/10musume 062620-001, Tokyo-Hot n1340, Heydouga 4030-123
_OTHER_STUDIO = re.compile(
    r"""
    (?<!\d)\d{6}[-_]\d{2,3}(?!\d)
    |(?<![a-z\d])(?:n|k|kb|red|sky|ex|cz|gedo|se)\d{3,4}(?![a-z\d])
    |heydouga|(?<![a-z\d])hey[-_]?\d{4}[-_]\d{3,5}
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SEPARATED = re.compile(
    r"""
    (?<![A-Z\d])
    (\d{0,4}[A-Z]{1,10}\d{0,2})   # label: 259LUXU, T28, D1, CPZ69, MURIKURI
    [-_]
    ([A-Z]{0,2}\d{1,5})           # number, zero padding kept: 0287, AA245, H014
    ([A-Z])?                      # attached suffix: DANDY-602A, IBW-699Z
    (?![A-Z\d])
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Letters-only labels, so DMM content IDs like 1dandy00602a never match
_DASHLESS = re.compile(
    r"(?<![A-Z\d])([A-Z]{2,10})(\d{3,5})([A-Z])?(?![A-Z\d])", re.IGNORECASE
)


def extract_codes(text: str) -> list[str]:
    """
    Finds a JAV product code in a filename or title and returns its candidate
    canonical forms, most likely first, e.g. "SONE-614", "259LUXU-1875", "FC2-PPV-4785741"

    Callers should try each candidate against their site until one exists:
    a letter attached to the number is usually a subtitle or disc tag on
    pirated files (IPX-568C, OFJE-287B) but is sometimes part of the code
    (NHDTB-720C, DANDY-602A), so both forms are returned

    >>> extract_codes("hhd800.com@SONE-614-C.mp4")
    ['SONE-614']
    >>> extract_codes("[44x.me]ipx568C.mp4")
    ['IPX-568C', 'IPX-568']
    >>> extract_codes("fc2-ppv_1234567-2.mp4")
    ['FC2-PPV-1234567']
    >>> extract_codes("1dandy00602a.mp4")
    []
    """
    stem = _VIDEO_EXTENSION.sub("", text)

    if fc2 := _FC2.search(stem):
        return [f"FC2-PPV-{fc2[1]}"]
    if heyzo := _HEYZO.search(stem):
        return [f"HEYZO-{heyzo[1]}"]
    if _OTHER_STUDIO.search(stem):
        return []

    cleaned = _NOISE.sub(" ", stem)
    match _SEPARATED.search(cleaned) or _DASHLESS.search(cleaned):
        case None:
            return []
        case m:
            label, number, suffix = m[1].upper(), m[2].upper(), (m[3] or "").upper()

    code = f"{label}-{number}"
    return [f"{code}{suffix}", code] if suffix else [code]
