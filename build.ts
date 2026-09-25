/**
 * Builds the package repository Stash installs scrapers from:
 * <outdir>/index.yml plus one <id>.zip per package
 */
import { join } from "@std/path";
import { mapConcurrent } from "./lib/concurrent.ts";
import { lastCommit } from "./lib/git.ts";
import { type IndexEntry, renderIndex } from "./lib/index.ts";
import { packageMetadata } from "./lib/metadata.ts";
import { discoverPackages, type ScraperPackage } from "./lib/package.ts";
import { sha256, zipPackage } from "./lib/zip.ts";

async function buildPackage(
  pkg: ScraperPackage,
  outdir: string,
): Promise<IndexEntry> {
  const path = `${pkg.id}.zip`;
  const zipPath = join(outdir, path);
  const [commit] = await Promise.all([
    lastCommit(pkg.versionPath),
    zipPackage(pkg, zipPath),
  ]);
  return {
    id: pkg.id,
    name: pkg.name,
    ...commit,
    path,
    sha256: await sha256(zipPath),
    requires: pkg.headers.requires,
    metadata: packageMetadata(pkg),
  };
}

const outdir = Deno.args[0] ?? "_site";
await Deno.remove(outdir, { recursive: true }).catch(() => {});
await Deno.mkdir(outdir, { recursive: true });

const packages = discoverPackages();
const entries = await mapConcurrent(packages, (pkg) =>
  buildPackage(pkg, outdir),
);
await Deno.writeTextFile(join(outdir, "index.yml"), renderIndex(entries));
console.log(`Built ${entries.length} packages into ${outdir}`);
