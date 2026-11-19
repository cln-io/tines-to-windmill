# Tines formula functions: Data Parsing/Conversion (part 4 of 4: TO_YAML to ZIP)

Independent, unofficial porting notes for the functions Tines files under "Data Parsing/Conversion": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: TO_YAML, UNTAR, UNZIP, XML_PARSE, YAML_PARSE, ZIP

## TO_YAML

- **Summary:** convert an object to YAML text
- **Signature:** `TO_YAML(object)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-yaml/

**Arguments**

- `object` (required): The object to convert.

**Returns:** YAML text starting with the document marker `---\n` and ending with a newline.

**Porting semantics**

- Not specified in docs: quoting style for strings; indentation of nested sequences; key order.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_YAML({site: "north", pumps: 3})
output:  "---\nsite: north\npumps: 3\n"
```

**TypeScript equivalent** (APPROXIMATE: quoting and indentation choices of the npm yaml package may differ from Tines' output)

```ts
import YAML from "yaml";
"---\n" + YAML.stringify(object)
```

- npm package: `yaml`. It does not emit the leading `---` by default, hence the prefix.

## UNTAR

- **Summary:** unpack the files of a tar archive
- **Signature:** `UNTAR(tar_data)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/untar/

**Arguments**

- `tar_data` (required): Tarball binary data.

**Returns:** A list of files (the docs give no example of the shape).

**Porting semantics**

- Not specified in docs: the keys of each file object (UNZIP returns `filename`, `content_type`, `guid`, `md5`, `sha256`, `sizeinbytes`, `base64encodedcontents`, `path`; whether UNTAR matches is not stated); gzip-compressed tarballs.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - an archive holding notes.txt with the text "alpha"
formula: UNTAR(tar_bytes)
output:  a list with one file entry; the field names are not specified in docs (this helper returns the name and the Base64 contents "YWxwaGE=")
```

**TypeScript equivalent** (APPROXIMATE: output shape is not documented; this helper returns name plus base64 contents)

```ts
import tar from "tar-stream";
import { Readable } from "node:stream";
async function untar(data: Buffer): Promise<{ name: string; base64encodedcontents: string }[]> {
  const extract = tar.extract(), files: { name: string; base64encodedcontents: string }[] = [];
  Readable.from([data]).pipe(extract);
  for await (const entry of extract) {
    const chunks: Buffer[] = [];
    for await (const c of entry) chunks.push(c as Buffer);
    if (entry.header.type === "file") files.push({ name: entry.header.name, base64encodedcontents: Buffer.concat(chunks).toString("base64") });
  }
  return files;
}
```

- npm package: `tar-stream`. Check which keys the rest of the story reads and rename accordingly.

## UNZIP

- **Summary:** extract files from a ZIP archive
- **Signature:** `UNZIP(zip_data, [password])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/unzip/

**Arguments**

- `zip_data` (required): ZIP binary data (typically `BASE64_DECODE(...)`).
- `password` (optional): Password for a protected archive.

**Returns:** Array with one object per file, with the fields `filename`, `content_type`, `guid`, `md5`, `sha256`, `sizeinbytes`, `base64encodedcontents`, `path`.

**Porting semantics**

- Not specified in docs: how `content_type` is determined; how directories are represented; error behaviour for a wrong password.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - an archive holding readme.txt with the text "alpha"; selected fields
formula: UNZIP(zip_bytes)
output:  [{"filename": "readme.txt", "path": "readme.txt", "sizeinbytes": 5, "base64encodedcontents": "YWxwaGE=", "md5": "2c1743a391305fbf367df8e4f069f9f9"}]
```

**TypeScript equivalent** (APPROXIMATE: content_type is fixed and guid is freshly generated; password-protected archives need a different package)

```ts
import { unzipSync } from "fflate";
import { createHash, randomUUID } from "node:crypto";
const unzip = (zip: Uint8Array) =>
  Object.entries(unzipSync(zip)).filter(([path]) => !path.endsWith("/")).map(([path, bytes]) => {
    const b = Buffer.from(bytes);
    return {
      filename: path.split("/").pop(), content_type: "application/octet-stream", guid: randomUUID(),
      md5: createHash("md5").update(b).digest("hex"), sha256: createHash("sha256").update(b).digest("hex"),
      sizeinbytes: b.length, base64encodedcontents: b.toString("base64"), path,
    };
  });
```

- npm package: `fflate` (no password support). For password-protected archives use `@zip.js/zip.js`.
- Pass the raw bytes (`Buffer.from(b64, "base64")`), not a UTF-8 decoded string.

## XML_PARSE

- **Summary:** parse XML text into an object
- **Signature:** `XML_PARSE(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/xml-parse/

**Arguments**

- `text` (required): Text containing XML.

**Returns:** An object keyed by the root element name, with child elements as nested keys and element text as values (`{"message": {"body": ..., "from": ..., "to": ...}}`).

**Porting semantics**

- Not specified in docs: representation of attributes, repeated elements, mixed content and namespaces; whether numeric text is converted; behaviour on invalid XML.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: XML_PARSE("<order><ref>A7</ref><ship><city>Oslo</city></ship></order>")
output:  {"order": {"ref": "A7", "ship": {"city": "Oslo"}}}
```

**TypeScript equivalent** (APPROXIMATE: attribute and repeated-element representation follow fast-xml-parser, which may differ from the platform)

```ts
import { XMLParser } from "fast-xml-parser";
new XMLParser({ parseTagValue: false }).parse(text)
```

- npm package: `fast-xml-parser`. `parseTagValue: false` keeps values as text; by default the package turns `"10"` into the number `10`.
- Attributes are ignored unless `ignoreAttributes: false` is set; repeated elements become arrays only when they repeat.

## YAML_PARSE

- **Summary:** parse YAML text into data
- **Signature:** `YAML_PARSE(text, [parse_date_or_time: FALSE], [version: 1])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/yaml-parse/

**Arguments**

- `text` (required): Text containing YAML.
- `parse_date_or_time` (optional): Keyword argument, off by default. When on, date and time values in the YAML are recognised; the docs show such a value coming back as text with a UTC suffix.
- `version` (optional): Keyword argument, default `1`. With `version: 2` the docs show a date coming back the same way and a Ruby-style symbol (a word with a leading colon) coming back as plain text.

**Returns:** The parsed object/array.

**Porting semantics**

- Not specified in docs: what `parse_date_or_time: FALSE` does with a date value (error vs plain text); the differences between version 1 and 2 beyond the example; behaviour on invalid YAML.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: YAML_PARSE("site: north\npumps:\n  - id: 1\n  - id: 2\nactive: true")
output:  {"site": "north", "pumps": [{"id": 1}, {"id": 2}], "active": true}
```

**TypeScript equivalent** (APPROXIMATE: date/time values stay plain text with the npm yaml package (Tines shows "... UTC"); Ruby symbols such as :foo are kept as ":foo")

```ts
import YAML from "yaml";
YAML.parse(text)
```

- npm package: `yaml`. It throws on invalid YAML.

## ZIP

- **Summary:** create a ZIP archive from file contents
- **Signature:** `ZIP(fileContentsOrFilesArray, [filename], [password])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/zip/

**Arguments**

- `fileContentsOrFilesArray` (required): Either the content of a single file, or an array of file objects. A file object needs a `name` and its content, as text under `contents` or Base64 under `base64encodedcontents`; an ISO 8601 `created_at` is optional.
- `filename` (optional): Name of the file inside the archive, for the single-content form. Several content/name pairs may be given one after another.
- `password` (optional): If present, the archive is password protected. It is the last argument in every form.

**Returns:** ZIP binary data. When it goes into event data, wrap it: `BASE64_ENCODE(ZIP(...))`.

**Porting semantics**

- Call forms shown: `ZIP(contents, "name", "password")`; `ZIP(contents1, "name1", contents2, "name2", "password")`; `ZIP(files_array, "password")`.
- Not specified in docs: default file name when none is given; encryption method used for passwords; compression level.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ZIP([{name: "a.txt", contents: "alpha"}, {name: "b.bin", base64encodedcontents: "AQID"}])
output:  ZIP bytes holding a.txt ("alpha") and b.bin (three bytes); wrap in BASE64_ENCODE before putting it in event data
```

**TypeScript equivalent** (APPROXIMATE: archive bytes will not match Tines; password protection needs a different package)

```ts
import { zipSync } from "fflate";
type ZipFile = { name: string; contents?: string; base64encodedcontents?: string; created_at?: string };
function zip(files: ZipFile[]): Buffer {
  const entries = Object.fromEntries(files.map((f): [string, [Uint8Array, { mtime?: string }]] => [
    f.name,
    [f.base64encodedcontents != null ? Buffer.from(f.base64encodedcontents, "base64") : Buffer.from(f.contents ?? "", "utf8"),
      f.created_at ? { mtime: f.created_at } : {}],
  ]));
  return Buffer.from(zipSync(entries));
}
// single file: zip([{ name: filename, contents }]);  BASE64_ENCODE(ZIP(...)) -> zip(...).toString("base64")
```

- npm package: `fflate` (no password support). For password-protected archives use `@zip.js/zip.js`.
