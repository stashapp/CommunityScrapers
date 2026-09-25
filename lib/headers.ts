/**
 * Package metadata carried in `# key: value` comment lines.
 *
 * These live in comments because Stash loads scraper YAML strictly: an unknown
 * top-level key makes older Stash versions reject the whole scraper.
 */
export interface Headers {
  /** Package ids this package depends on */
  requires: string[];
  /** zip exclusion patterns, relative to the package folder */
  ignore: string[];
  /** Human-readable names of the sites or studios this scraper covers */
  scrapes: string[];
}

function headerLines(source: string, key: string): string[] {
  const pattern = new RegExp(`^# ${key}:(.*?)\\r?$`, "gm");
  return [...source.matchAll(pattern)].map((match) => match[1]);
}

function splitValues(lines: string[], separator: RegExp): string[] {
  return lines
    .flatMap((line) => line.split(separator))
    .map((value) => value.trim())
    .filter((value) => value !== "");
}

export function parseHeaders(source: string): Headers {
  return {
    requires: splitValues(headerLines(source, "requires"), /[\s,]+/),
    ignore: splitValues(headerLines(source, "ignore"), /\s+/),
    scrapes: splitValues(headerLines(source, "scrapes"), /,/),
  };
}
