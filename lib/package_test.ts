import { assertEquals } from "@std/assert";
import { fromFileUrl } from "@std/path";
import { packageMetadata } from "./metadata.ts";
import { discoverPackages } from "./package.ts";

const root = fromFileUrl(new URL("./testdata/scrapers", import.meta.url));
const packages = discoverPackages(root);
const byId = (id: string) => packages.find((pkg) => pkg.id === id)!;

Deno.test("discovers one package per rule, sorted by id", () => {
  assertEquals(
    packages.map((pkg) => pkg.id),
    ["Dependency", "Folder", "Network", "Single"],
  );
});

Deno.test("a top-level scraper is versioned by its own file", () => {
  const single = byId("Single");
  assertEquals(single.folder, undefined);
  assertEquals(single.versionPath, `${root}/Single.yml`);
});

Deno.test("a scraper in a folder ships and is versioned by the folder", () => {
  const folder = byId("Folder");
  assertEquals(folder.folder, `${root}/Folder`);
  assertEquals(folder.versionPath, `${root}/Folder`);
  assertEquals(folder.headers.requires, ["py_common", "AyloAPI"]);
});

Deno.test(
  "a package file names the package and covers every scraper in its folder",
  () => {
    const network = byId("Network");
    assertEquals(network.name, "The Network");
    assertEquals(network.headers.requires, ["py_common"]);
    assertEquals(network.scrapers.length, 2);
    assertEquals(packageMetadata(network), {
      scrapes: ["A Studio", "B Studio"],
      scene_urls: ["a.com/"],
      gallery_urls: ["b.com/gallery/"],
    });
  },
);

Deno.test("a dependency-only package has no metadata", () => {
  assertEquals(packageMetadata(byId("Dependency")), {});
});

Deno.test(
  "metadata resolves YAML aliases and folds movieByURL into groups",
  () => {
    assertEquals(packageMetadata(byId("Single")), {
      scrapes: ["Site A", "Site B"],
      scene_urls: ["sitea.com/video/", "siteb.com/video/"],
      performer_urls: ["sitea.com/video/", "siteb.com/video/"],
      group_urls: ["sitea.com/dvd/"],
    });
  },
);

Deno.test("metadata values are flat string lists, as Stash requires", () => {
  for (const pkg of packages) {
    for (const values of Object.values(packageMetadata(pkg))) {
      assertEquals(Array.isArray(values), true);
      for (const value of values) assertEquals(typeof value, "string");
    }
  }
});
