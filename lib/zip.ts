import { basename, dirname, resolve } from "@std/path";
import { PACKAGE_FILE, type ScraperPackage } from "./package.ts";

/** Uses the zip CLI so `# ignore:` keeps zip's own -x pattern semantics */
export async function zipPackage(
  pkg: ScraperPackage,
  zipPath: string,
): Promise<void> {
  const zipFile = resolve(zipPath);
  const [cwd, args] = pkg.folder
    ? [
        pkg.folder,
        ["-r", zipFile, ".", "-x", ...pkg.headers.ignore, PACKAGE_FILE],
      ]
    : [
        dirname(pkg.scrapers[0].path),
        [zipFile, basename(pkg.scrapers[0].path)],
      ];
  const { success, stderr } = await new Deno.Command("zip", {
    args,
    cwd,
  }).output();
  if (!success) {
    throw new Error(`zip ${pkg.id}: ${new TextDecoder().decode(stderr)}`);
  }
}

export async function sha256(path: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    await Deno.readFile(path),
  );
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
