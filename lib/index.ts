import { stringify } from "yaml";
import type { PackageMetadata } from "./metadata.ts";

/** One entry of index.yml, mirroring RemotePackage in Stash's pkg/pkg */
export interface IndexEntry {
  id: string;
  name: string;
  version: string;
  date: string;
  path: string;
  sha256: string;
  requires?: string[];
  metadata?: PackageMetadata;
}

/** Stash reads the index with yaml.v2, so values are quoted by YAML 1.1 rules */
export function renderIndex(entries: IndexEntry[]): string {
  const cleaned = entries.map(({ requires, metadata, ...entry }) => ({
    ...entry,
    ...(requires?.length ? { requires } : {}),
    ...(metadata && Object.keys(metadata).length ? { metadata } : {}),
  }));
  return stringify(cleaned, { version: "1.1", lineWidth: 0 });
}
