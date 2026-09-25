import { assertEquals, assertStringIncludes } from "@std/assert";
import { parse } from "yaml";
import { renderIndex } from "./index.ts";

const entry = {
  id: "Example",
  name: "Yes",
  version: "77340626",
  date: "2026-09-21 17:50:02",
  path: "Example.zip",
  sha256: "abc",
};

Deno.test("index values stay strings under YAML 1.1, which Stash uses", () => {
  const output = renderIndex([entry]);
  assertEquals(parse(output, { version: "1.1" }), [entry]);
});

Deno.test("index omits empty requires and metadata", () => {
  const output = renderIndex([{ ...entry, requires: [], metadata: {} }]);
  assertEquals(output.includes("requires"), false);
  assertEquals(output.includes("metadata"), false);
});

Deno.test("index writes metadata lists", () => {
  const output = renderIndex([
    {
      ...entry,
      metadata: { scene_urls: ["example.com/video/"] },
    },
  ]);
  assertStringIncludes(output, "scene_urls:\n      - example.com/video/");
});
