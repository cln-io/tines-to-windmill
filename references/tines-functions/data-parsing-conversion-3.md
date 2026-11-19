# Tines formula functions: Data Parsing/Conversion (part 3 of 4: OBJECTS_TO_CSV to TO_XML)

Independent, unofficial porting notes for the functions Tines files under "Data Parsing/Conversion": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: OBJECTS_TO_CSV, OBJECTS_TO_MARKDOWN_TABLE, PARSE_URL, PEM_TO_JWK, TAR, TO_CSV, TO_HEX, TO_JSON, TO_XML

## OBJECTS_TO_CSV

- **Summary:** array of objects to CSV text
- **Signature:** `OBJECTS_TO_CSV(objects, headers)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/objects-to-csv/

**Arguments**

- `objects` (required): Array of objects that share their keys.
- `headers` (optional): Array of column names; it also selects and orders the columns. Without it the columns come from the first object's keys.

**Returns:** CSV text: a header line followed by one line per object, each line ending with `\n`.

**Porting semantics**

- An object that lacks a column's key gets an empty field in that column.
- The Tines docs print a space after each comma in their sample output; whether real output contains it cannot be confirmed from the docs.
- Not specified in docs: quoting/escaping rules for values containing commas, quotes or newlines; the exact separator (see caveat).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: OBJECTS_TO_CSV([{sku: "A-1", qty: 4}, {sku: "B-9", qty: 12}])
output:  three lines of CSV: the header sku / qty, then A-1 / 4 and B-9 / 12 (this helper separates fields with a bare comma)

# 2 - chosen columns, one value missing
formula: OBJECTS_TO_CSV([{sku: "A-1", qty: 4}, {sku: "B-9"}], ["qty", "sku"])
output:  the header qty / sku, then 4 / A-1, then a line whose qty field is empty
```

**TypeScript equivalent** (APPROXIMATE: emits standard RFC 4180 CSV with a bare comma separator; the docs examples show ", " and do not define quoting)

```ts
function objectsToCsv(objects: Record<string, any>[], headers: string[] = Object.keys(objects[0] ?? {})): string {
  const cell = (v: any): string => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [headers, ...objects.map((o) => headers.map((h) => o[h]))].map((r) => r.map(cell).join(",")).join("\n") + "\n";
}
```

- If a downstream system needs byte-identical CSV, compare against a real Tines run before relying on this helper.

## OBJECTS_TO_MARKDOWN_TABLE

- **Summary:** array of objects to a markdown table
- **Signature:** `OBJECTS_TO_MARKDOWN_TABLE(objects, headers)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/objects-to-markdown-table/

**Arguments**

- `objects` (required): Array of objects.
- `headers` (optional): Array of column names; it also selects and orders the columns. Without it the columns come from the first object's keys.

**Returns:** Markdown table text: header row, `| --- |` separator row, one row per object, joined by `\n` with no trailing newline.

**Porting semantics**

- A pipe character inside a value is escaped so that it cannot break the table.
- Not specified in docs: how pipes are escaped (presumably `\|`); rendering of null/missing values, newlines inside values, nested objects; empty array.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: OBJECTS_TO_MARKDOWN_TABLE([{sku: "A-1", qty: 4}, {sku: "B-9", qty: 12}])
output:  "| sku | qty |\n| --- | --- |\n| A-1 | 4 |\n| B-9 | 12 |"

# 2
formula: OBJECTS_TO_MARKDOWN_TABLE([{sku: "A-1", qty: 4}], ["qty"])
output:  "| qty |\n| --- |\n| 4 |"
```

**TypeScript equivalent**

```ts
function objectsToMarkdownTable(objects: Record<string, any>[], headers: string[] = Object.keys(objects[0] ?? {})): string {
  const row = (cells: any[]): string => `| ${cells.map((c) => String(c ?? "").replace(/\|/g, "\\|")).join(" | ")} |`;
  return [row(headers), row(headers.map(() => "---")), ...objects.map((o) => row(headers.map((h) => o[h])))].join("\n");
}
```

- Escaping pipes as `\|` and rendering missing values as empty cells are assumptions.

## PARSE_URL

- **Summary:** parse a URL into its components
- **Signature:** `PARSE_URL(text, [include_public_suffix_domains: FALSE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/parse-url/

**Arguments**

- `text` (required): The URL text.
- `include_public_suffix_domains` (optional): Keyword argument, off by default. It changes how `domain` and `tld` are worked out for hosts that sit under a suffix operated by a hosting provider.

**Returns:** Object with keys `scheme`, `host`, `path`, `port`, `query`, `fragment`, `domain`, `tld`.

**Porting semantics**

- `port` is a number and is filled with the scheme default when absent (80 for http, 443 for https).
- `query` is an object; a parameter that occurs more than once becomes an array. With no query string it is `null`.
- `fragment` has no leading `#` and is `null` when absent. `path` is `""` when the URL has no path.
- `domain` is the registrable domain and `tld` the suffix after it.
- With the option on, a host under a provider-operated suffix is reported with the provider's own registrable domain and the generic suffix.
- Not specified in docs: result for text that is not a URL; userinfo fields; `domain` and `tld` for provider-suffix hosts when the option is off.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PARSE_URL("https://shop.example.org:8443/cart/items?id=7&tag=a&tag=b#top")
output:  {"scheme": "https", "host": "shop.example.org", "path": "/cart/items", "port": 8443, "query": {"id": "7", "tag": ["a", "b"]}, "fragment": "top", "domain": "example.org", "tld": "org"}

# 2 - default port, no path, query or fragment
formula: PARSE_URL("http://intranet.example.org")
output:  {"scheme": "http", "host": "intranet.example.org", "path": "", "port": 80, "query": null, "fragment": null, "domain": "example.org", "tld": "org"}
```

**TypeScript equivalent** (APPROXIMATE: domain/tld come from the tldts package; how the option maps onto that package's settings is inferred, not documented)

```ts
import { parse as parseDomain } from "tldts";
function parseUrl(text: string, includePublicSuffixDomains = false) {
  const u = new URL(text);
  const scheme = u.protocol.replace(":", "");
  const query: Record<string, string | string[]> = {};
  for (const [k, v] of u.searchParams) query[k] = k in query ? [query[k]].flat().concat(v) : v;
  const d = parseDomain(u.hostname, { allowPrivateDomains: !includePublicSuffixDomains });
  return {
    scheme, host: u.hostname,
    path: u.pathname === "/" && !text.split(/[?#]/)[0].endsWith("/") ? "" : u.pathname,
    port: u.port ? Number(u.port) : ({ http: 80, https: 443 } as Record<string, number>)[scheme] ?? null,
    query: u.search ? query : null, fragment: u.hash ? u.hash.slice(1) : null,
    domain: d.domain, tld: d.publicSuffix,
  };
}
```

- npm package: `tldts`. If the story only reads `host`, `path` or `query`, plain `new URL(text)` is enough and needs no package.
- `new URL` throws on invalid input; `URL.pathname` is `"/"` where Tines shows `""`.

## PEM_TO_JWK

- **Summary:** convert a PEM key or certificate to a JSON Web Key
- **Signature:** `PEM_TO_JWK(pem, [include_private: FALSE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/pem-to-jwk/

**Arguments**

- `pem` (required): A key, or an X.509 certificate, in PEM form. RSA and ECDSA are supported; from a certificate the public key is taken.
- `include_private` (optional): Keyword argument, off by default: the result has public members only. When on, private members are included if the PEM holds a private key.

**Returns:** JWK object (e.g. `{"kty": "RSA", "n": ..., "e": "AQAB"}`; with private parts also `"d"`).

**Porting semantics**

- The key material shown in the Tines docs is shortened placeholder data, not a usable key.
- Not specified in docs: whether `kid`, `use` or `alg` members are added; exactly which private members are included (the example shows only `d`).

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - for a freshly generated RSA key
formula: PEM_TO_JWK(public_key_pem)
output:  an object with "kty": "RSA", the modulus "n" and the exponent "e": "AQAB"; no private members
```

**TypeScript equivalent**

```ts
import { createPrivateKey, createPublicKey } from "node:crypto";
const pemToJwk = (pem: string, includePrivate = false) =>
  includePrivate && pem.includes("PRIVATE KEY")
    ? createPrivateKey(pem).export({ format: "jwk" })
    : createPublicKey(pem).export({ format: "jwk" });
```

- `createPublicKey` accepts public keys, private keys (derives the public key) and X.509 certificates in PEM form.
- Node's private JWK export includes `p`, `q`, `dp`, `dq`, `qi` as well as `d`.

## TAR

- **Summary:** create a tarball from a list of files
- **Signature:** `TAR(compressed_file_data)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/tar/

**Arguments**

- `compressed_file_data` (required): Despite the parameter name in the syntax line, the example passes a list of file objects with `name` and `contents`.

**Returns:** Tarball binary data (wrap in BASE64_ENCODE to put it in event data, as the ZIP docs advise for archives).

**Porting semantics**

- The docs example for this function is inconsistent in its naming and shows no output, so only the input shape (a list of objects with `name` and `contents`) is known.
- Not specified in docs: other accepted file-object keys (e.g. `base64encodedcontents`, as ZIP accepts); file modes and timestamps; whether output is gzip-compressed (the description says tarball only).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TAR([{name: "a.txt", contents: "alpha"}, {name: "b.txt", contents: "beta"}])
output:  tar bytes containing the two files (binary; Base64-encode before putting it in event data)
```

**TypeScript equivalent** (APPROXIMATE: built with the tar-stream package; headers (mode, mtime, owner) will not match Tines byte for byte)

```ts
import tar from "tar-stream";
async function tarFiles(files: { name: string; contents: string }[]): Promise<Buffer> {
  const pack = tar.pack();
  for (const f of files) pack.entry({ name: f.name }, f.contents);
  pack.finalize();
  const chunks: Buffer[] = [];
  for await (const c of pack) chunks.push(c as Buffer);
  return Buffer.concat(chunks);
}
```

- npm package: `tar-stream`.

## TO_CSV

- **Summary:** array of arrays to CSV text
- **Signature:** `TO_CSV(array_of_arrays)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-csv/

**Arguments**

- `array_of_arrays` (required): Rows; each row is an array of values.

**Returns:** CSV text, one line per row, each line ending with `\n`.

**Porting semantics**

- The Tines docs print a space after each comma in their sample output and put quotes around values that contain a space; whether real output does the same cannot be confirmed from the docs.
- Not specified in docs: quoting/escaping rules; the exact separator (see caveat); rendering of null.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_CSV([["sku", "qty"], ["A-1", 4], ["B-9", 12]])
output:  three lines of CSV, one per inner array, each ending with a line break (this helper separates fields with a bare comma)
```

**TypeScript equivalent** (APPROXIMATE: emits standard RFC 4180 CSV with a bare comma separator; the docs examples show ", " and quote values containing spaces)

```ts
function toCsv(rows: any[][]): string {
  const cell = (v: any): string => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return rows.map((r) => r.map(cell).join(",")).join("\n") + "\n";
}
```

- If a downstream system needs byte-identical CSV, compare against a real Tines run before relying on this helper.

## TO_HEX

- **Summary:** convert text or data to hexadecimal text
- **Signature:** `TO_HEX(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-hex/

**Arguments**

- `text` (required): Text or binary data.

**Returns:** Lowercase hexadecimal text.

**Porting semantics**

- Not specified in docs: null input; number input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_HEX("ok!!")
output:  "6f6b2121"
```

**TypeScript equivalent**

```ts
Buffer.from(text).toString("hex")
```

- For binary data pass the `Buffer` (e.g. `Buffer.from(b64, "base64").toString("hex")` for `TO_HEX(BASE64_DECODE(x))`); never route binary through a UTF-8 string.

## TO_JSON

- **Summary:** convert an object to compact JSON text
- **Signature:** `TO_JSON(object)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-json/

**Arguments**

- `object` (required): The value to serialise.

**Returns:** Compact JSON text (no spaces after `:` or `,` in the example).

**Porting semantics**

- Not specified in docs: key order; non-object input (text, numbers, null).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_JSON({sku: "A-1", tags: ["x", "y"]})
output:  "{\"sku\":\"A-1\",\"tags\":[\"x\",\"y\"]}"
```

**TypeScript equivalent**

```ts
JSON.stringify(object)
```

- `JSON.stringify` drops keys whose value is `undefined`; make sure missing values are `null`, not `undefined`.
- `JSON.stringify(undefined)` returns `undefined`, not text.

## TO_XML

- **Summary:** convert an object to XML text
- **Signature:** `TO_XML(object, root_element_name = "hash")`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-xml/

**Arguments**

- `object` (required): The object to convert.
- `root_element_name` (optional): Name of the root element; default `"hash"`.

**Returns:** XML text: a declaration line, then the root element with one indented child per key, ending with a line break.

**Porting semantics**

- An underscore in a key becomes a dash in the element name, and a whole-number value is marked with a `type="integer"` attribute.
- A key whose value is a lambda does not appear in the output; lambdas get no access to the XML builder, and other kinds of callback are refused.
- Not specified in docs: rendering of arrays, nested objects, booleans, decimals and null; escaping rules.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_XML({unit_count: 3, label: "north"})
output:  "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<hash>\n  <unit-count type=\"integer\">3</unit-count>\n  <label>north</label>\n</hash>\n"

# 2 - custom root
formula: TO_XML({label: "x"}, "item")
output:  "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<item>\n  <label>x</label>\n</item>\n"
```

**TypeScript equivalent** (APPROXIMATE: only flat objects with text and integer values are documented; the array/boolean/float/null rendering in this helper is assumed)

```ts
function toXml(object: Record<string, any>, root = "hash"): string {
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const node = (name: string, v: any, pad: string): string => {
    const tag = name.replace(/_/g, "-");
    if (typeof v === "function") return "";
    if (Array.isArray(v)) return `${pad}<${tag} type="array">\n${v.map((x) => node(tag.replace(/s$/, ""), x, pad + "  ")).join("")}${pad}</${tag}>\n`;
    if (v !== null && typeof v === "object") return `${pad}<${tag}>\n${Object.entries(v).map(([k, x]) => node(k, x, pad + "  ")).join("")}${pad}</${tag}>\n`;
    if (v === null || v === undefined) return `${pad}<${tag} nil="true"/>\n`;
    const type = typeof v === "number" ? (Number.isInteger(v) ? ' type="integer"' : ' type="float"') : typeof v === "boolean" ? ' type="boolean"' : "";
    return `${pad}<${tag}${type}>${esc(String(v))}</${tag}>\n`;
  };
  const body = Object.entries(object).map(([k, x]) => node(k, x, "  ")).join("");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<${root}>\n${body}</${root}>\n`;
}
```

- If the consumer needs a specific XML schema rather than this exact layout, build the XML explicitly (npm `fast-xml-parser` `XMLBuilder`).
