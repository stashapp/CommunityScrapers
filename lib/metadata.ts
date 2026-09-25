import type { ScraperFile, ScraperPackage } from "./package.ts";

/**
 * Must stay flat string lists: Stash decodes the index with yaml.v2, whose
 * nested maps its GraphQL `Map` scalar cannot marshal, crashing the package list
 */
export type PackageMetadata = Record<string, string[]>;

export const contentTypes = [
  "scene",
  "performer",
  "gallery",
  "group",
  "image",
] as const;
export type ContentType = (typeof contentTypes)[number];

/** movieByURL is folded into group */
const urlKeys: Record<ContentType, string[]> = {
  scene: ["sceneByURL"],
  performer: ["performerByURL"],
  gallery: ["galleryByURL"],
  group: ["movieByURL", "groupByURL"],
  image: ["imageByURL"],
};

const sortedUnique = (values: string[]) => [...new Set(values)].sort();

/** URL patterns the scrapers match, by content type, using Stash's substring semantics */
export function urlPatterns(
  scrapers: ScraperFile[],
  type: ContentType,
): string[] {
  return sortedUnique(
    scrapers.flatMap(({ data }) =>
      urlKeys[type].flatMap((key) => {
        const definitions = data[key];
        if (!Array.isArray(definitions)) return [];
        return definitions.flatMap((definition) =>
          Array.isArray(definition?.url)
            ? definition.url.filter((u: unknown) => typeof u === "string")
            : [],
        );
      }),
    ),
  );
}

export function packageMetadata(pkg: ScraperPackage): PackageMetadata {
  const metadata: PackageMetadata = {
    scrapes: sortedUnique(pkg.headers.scrapes),
  };
  for (const type of contentTypes) {
    metadata[`${type}_urls`] = urlPatterns(pkg.scrapers, type);
  }
  return Object.fromEntries(
    Object.entries(metadata).filter(([, values]) => values.length > 0),
  );
}
