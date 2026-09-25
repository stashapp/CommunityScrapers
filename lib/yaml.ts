import { parse } from "yaml";

export type ScraperData = Record<string, unknown>;

/** Throws on invalid YAML; merge keys are enabled because Stash's YAML decoder supports them */
export function parseScraperYaml(source: string): ScraperData {
  return (
    parse(source, { prettyErrors: true, version: "1.2", merge: true }) ?? {}
  );
}
