import { assertEquals } from "@std/assert";
import { parseHeaders } from "./headers.ts";

Deno.test("headers split requires on commas and spaces", () => {
  const headers = parseHeaders("# requires: py_common, AyloAPI other\n");
  assertEquals(headers.requires, ["py_common", "AyloAPI", "other"]);
});

Deno.test("headers split scrapes on commas only", () => {
  const headers = parseHeaders("# scrapes: Big Toy XXX, Brit Studio\n");
  assertEquals(headers.scrapes, ["Big Toy XXX", "Brit Studio"]);
});

Deno.test("headers tolerate CRLF line endings", () => {
  const headers = parseHeaders("# requires: py_common\r\nname: x\r\n");
  assertEquals(headers.requires, ["py_common"]);
});

Deno.test("headers collect every matching line", () => {
  const headers = parseHeaders("# scrapes: A\n# scrapes: B\n");
  assertEquals(headers.scrapes, ["A", "B"]);
});

Deno.test("headers are found anywhere in the file", () => {
  const headers = parseHeaders(
    "name: x\nsceneByURL: []\n# requires: py_common\n",
  );
  assertEquals(headers.requires, ["py_common"]);
});

Deno.test("headers must start their line", () => {
  const headers = parseHeaders("name: x # requires: nope\n  # scrapes: nope\n");
  assertEquals(headers, { requires: [], ignore: [], scrapes: [] });
});
