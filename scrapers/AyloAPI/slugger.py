import re

"""
This ports the kebabCase function from lodash to Python. It is used to generate
slugs for the URLs for scenes, performers and movies scraped from the Aylo API.

https://github.com/lodash/lodash/blob/main/src/kebabCase.ts
"""

rsAstralRange = "\\ud800-\\udfff"
rsComboMarksRange = "\\u0300-\\u036f"
reComboHalfMarksRange = "\\ufe20-\\ufe2f"
rsComboSymbolsRange = "\\u20d0-\\u20ff"
rsComboMarksExtendedRange = "\\u1ab0-\\u1aff"
rsComboMarksSupplementRange = "\\u1dc0-\\u1dff"
rsComboRange = (
    rsComboMarksRange
    + reComboHalfMarksRange
    + rsComboSymbolsRange
    + rsComboMarksExtendedRange
    + rsComboMarksSupplementRange
)
rsDingbatRange = "\\u2700-\\u27bf"
rsLowerRange = "a-z\\xdf-\\xf6\\xf8-\\xff"
rsMathOpRange = "\\xac\\xb1\\xd7\\xf7"
rsNonCharRange = "\\x00-\\x2f\\x3a-\\x40\\x5b-\\x60\\x7b-\\xbf"
rsPunctuationRange = "\\u2000-\\u206f"
rsSpaceRange = " \\t\\x0b\\f\\xa0\\ufeff\\n\\r\\u2028\\u2029\\u1680\\u180e\\u2000\\u2001\\u2002\\u2003\\u2004\\u2005\\u2006\\u2007\\u2008\\u2009\\u200a\\u202f\\u205f\\u3000"
rsUpperRange = "A-Z\\xc0-\\xd6\\xd8-\\xde"
rsVarRange = "\\ufe0e\\ufe0f"
rsBreakRange = rsMathOpRange + rsNonCharRange + rsPunctuationRange + rsSpaceRange

rsApos = "['\u2019]"
rsBreak = f"[{rsBreakRange}]"
rsCombo = f"[{rsComboRange}]"
rsDigit = "\\d"
rsDingbat = f"[{rsDingbatRange}]"
rsLower = f"[{rsLowerRange}]"
rsMisc = f"[^{rsAstralRange}{rsBreakRange + rsDigit + rsDingbatRange + rsLowerRange + rsUpperRange}]"
rsFitz = "\\ud83c[\\udffb-\\udfff]"
rsModifier = f"(?:{rsCombo}|{rsFitz})"
rsNonAstral = f"[^{rsAstralRange}]"
rsRegional = "(?:\\ud83c[\\udde6-\\uddff]){2}"
rsSurrPair = "[\\ud800-\\udbff][\\udc00-\\udfff]"
rsUpper = f"[{rsUpperRange}]"
rsZWJ = "\\u200d"

rsMiscLower = f"(?:{rsLower}|{rsMisc})"
rsMiscUpper = f"(?:{rsUpper}|{rsMisc})"
rsOptContrLower = f"(?:{rsApos}(?:d|ll|m|re|s|t|ve))?"
rsOptContrUpper = f"(?:{rsApos}(?:D|LL|M|RE|S|T|VE))?"
reOptMod = f"{rsModifier}?"
rsOptVar = f"[{rsVarRange}]?"
rsOptJoin = f"(?:{rsZWJ}(?:{('|').join([rsNonAstral, rsRegional, rsSurrPair])}){rsOptVar + reOptMod})*"
rsOrdLower = "\\d*(?:1st|2nd|3rd|(?![123])\\dth)(?=\\b|[A-Z_])"
rsOrdUpper = "\\d*(?:1ST|2ND|3RD|(?![123])\\dTH)(?=\\b|[a-z_])"
rsSeq = rsOptVar + reOptMod + rsOptJoin
rsEmoji = rf"(?:{('|').join([rsDingbat, rsRegional, rsSurrPair])}){rsSeq}"

reUnicodeWords = re.compile(
    "|".join(
        [
            f"{rsUpper}?{rsLower}+{rsOptContrLower}(?={('|').join([rsBreak, rsUpper, '$'])})",
            f"{rsMiscUpper}+{rsOptContrUpper}(?={('|').join([rsBreak, rsUpper + rsMiscLower, '$'])})",
            f"{rsUpper}?{rsMiscLower}+{rsOptContrLower}",
            f"{rsUpper}+{rsOptContrUpper}",
            rsOrdUpper,
            rsOrdLower,
            f"{rsDigit}+",
            rsEmoji,
        ]
    )
)

reAsciiWords = re.compile(r"[^\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+")


def slugify(string):
    cleaned = re.sub("['\u2019]", "", string)
    if reUnicodeWords.search(cleaned):
        return "-".join(reUnicodeWords.findall(cleaned)).lower()
    return "-".join(reAsciiWords.findall(cleaned)).lower()
