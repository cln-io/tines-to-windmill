# Tines formula functions: Data Parsing/Conversion (part 1 of 4: BASE64URL_DECODE to GUNZIP)

Independent, unofficial porting notes for the functions Tines files under "Data Parsing/Conversion": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: BASE64URL_DECODE, BASE64URL_ENCODE, BASE64_DECODE, BASE64_ENCODE, COMBINE_COLUMNS_AND_ROWS, CSV_PARSE, CSV_PARSE_TO_OBJECTS, EML_PARSE, GUNZIP

## BASE64URL_DECODE

- **Summary:** decode URL-safe Base64 text
- **Signature:** `BASE64URL_DECODE(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/base64url-decode/

**Arguments**

- `text` (required): URL-safe Base64 encoded text.

**Returns:** The decoded text.

**Porting semantics**

- Not specified in docs: padded vs unpadded input; malformed input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: BASE64URL_DECODE("YT9iPmM")
output:  "a?b>c"
```

**TypeScript equivalent**

```ts
Buffer.from(text, "base64url").toString("utf8")
```

## BASE64URL_ENCODE

- **Summary:** encode text as URL-safe Base64
- **Signature:** `BASE64URL_ENCODE(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/base64url-encode/

**Arguments**

- `text` (required): Text to encode.

**Returns:** URL-safe Base64 text.

**Porting semantics**

- Not specified in docs: whether `=` padding is emitted (the only example needs none); object input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - standard Base64 would be "YT9iPmM="
formula: BASE64URL_ENCODE("a?b>c")
output:  "YT9iPmM"

# 2 - "-" and "_" replace "+" and "/" (standard Base64: "fn5+")
formula: BASE64URL_ENCODE("~~~")
output:  "fn5-"
```

**TypeScript equivalent**

```ts
Buffer.from(text).toString("base64url")
```

- Node/Bun emit no `=` padding. If the receiving system needs padding and Tines emitted it, the outputs differ - not determinable from the docs.

## BASE64_DECODE

- **Summary:** decode Base64 text
- **Signature:** `BASE64_DECODE(text, [strict: TRUE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/base64-decode/

**Arguments**

- `text` (required): Base64 encoded text.
- `strict` (optional): Keyword argument, default `TRUE` (RFC 4648 rules). `strict: FALSE` switches to the more lenient RFC 2045 rules, which tolerate wrong padding.

**Returns:** The decoded text (or binary data, when the input encodes binary - see GUNZIP, MSG_PARSE, UNZIP, TO_HEX examples).

**Porting semantics**

- With `strict: FALSE`, input with wrong padding still decodes.
- Not specified in docs: what happens with malformed input when strict is TRUE (error vs partial result); null/blank input; URL-safe alphabet input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: BASE64_DECODE("cGFyY2VsIDQy")
output:  "parcel 42"

# 2 - one padding character too many
formula: BASE64_DECODE("b2s==", strict: FALSE)
output:  "ok"
```

**TypeScript equivalent**

```ts
Buffer.from(text, "base64").toString("utf8") // text result
Buffer.from(text, "base64")                  // keep the bytes when the result feeds GUNZIP / UNZIP / MSG_PARSE / TO_HEX
```

- Node/Bun's decoder is always lenient (it behaves like `strict: FALSE` and never throws), so a story that relies on strict decoding raising an error needs an explicit validity check.
- Calling `.toString("utf8")` on binary data corrupts it. Keep a `Buffer` whenever the next function expects file bytes.

## BASE64_ENCODE

- **Summary:** Base64-encode text, or the JSON of an object
- **Signature:** `BASE64_ENCODE(text_or_object, [strict: TRUE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/base64-encode/

**Arguments**

- `text_or_object` (required): Text, or an object.
- `strict` (optional): Keyword argument, default `TRUE` (RFC 4648, a single line). `strict: FALSE` gives RFC 2045 output with line breaks.

**Returns:** Base64 text.

**Porting semantics**

- An object is first turned into compact JSON text, and that text is encoded.
- With `strict: FALSE` the output is broken into lines with `\n` and also ends with `\n`. The line length used here (72) is the one the Tines docs example displays.
- Not specified in docs: null input; how arrays or numbers are stringified.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: BASE64_ENCODE("parcel 42")
output:  "cGFyY2VsIDQy"

# 2 - encodes the JSON text {"id":7}
formula: BASE64_ENCODE({id: 7})
output:  "eyJpZCI6N30="

# 3
formula: BASE64_ENCODE("ok", strict: FALSE)
output:  "b2s=\n"
```

**TypeScript equivalent**

```ts
function base64Encode(v: unknown, strict = true): string {
  const buf = Buffer.isBuffer(v) ? v : Buffer.from(typeof v === "string" ? v : JSON.stringify(v));
  const b64 = buf.toString("base64");
  return strict ? b64 : b64.replace(/.{1,72}/g, "$&\n"); // 72 = line length shown in the Tines docs
}
```

- Pass a `Buffer` straight through when the input is binary (e.g. output of GZIP or ZIP).
- `btoa()` only handles Latin-1 text; use `Buffer`.

## COMBINE_COLUMNS_AND_ROWS

- **Summary:** zip column names and row arrays into objects
- **Signature:** `COMBINE_COLUMNS_AND_ROWS(columns, rows)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/combine-columns-and-rows/

**Arguments**

- `columns` (required): Array of column names, used as keys exactly as written.
- `rows` (required): Array of arrays, one inner array per row.

**Returns:** Array of objects, one per row.

**Porting semantics**

- Values are copied as they are; numeric text stays text.
- Not specified in docs: a row shorter or longer than the column list; duplicate column names; empty inputs.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: COMBINE_COLUMNS_AND_ROWS(["sku", "qty"], [["A-1", "4"], ["B-9", 12]])
output:  [{"sku": "A-1", "qty": "4"}, {"sku": "B-9", "qty": 12}]
```

**TypeScript equivalent**

```ts
rows.map((row: any[]) => Object.fromEntries(columns.map((c: string, i: number) => [c, row[i] ?? null])))
```

- The `?? null` fills a short row with null (an assumption; without it the key would be `undefined` and vanish when serialised).

## CSV_PARSE

- **Summary:** parse CSV text into an array of arrays
- **Signature:** `CSV_PARSE(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/csv-parse/

**Arguments**

- `text` (required): CSV-formatted text.

**Returns:** Array of rows, each an array of text values (the header row is row 0).

**Porting semantics**

- The delimiter character is detected automatically.
- Every value comes back as text, numbers included.
- Spaces that follow a delimiter are not part of the values.
- Not specified in docs: quoting rules; blank lines; ragged rows; which delimiters are detected.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - semicolons detected
formula: CSV_PARSE("sku;qty\nA-1;4\nB-9;12")
output:  [["sku", "qty"], ["A-1", "4"], ["B-9", "12"]]
```

**TypeScript equivalent** (APPROXIMATE: delimiter detection and whitespace trimming follow papaparse, not Tines)

```ts
import Papa from "papaparse";
const rows = Papa.parse<string[]>(text.trim(), { skipEmptyLines: true }).data.map((r) => r.map((c) => c.trim()));
```

- npm package: `papaparse` (auto-detects the delimiter when none is given).

## CSV_PARSE_TO_OBJECTS

- **Summary:** parse CSV text into an array of objects keyed by header
- **Signature:** `CSV_PARSE_TO_OBJECTS(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/csv-parse-to-objects/

**Arguments**

- `text` (required): CSV text; its first line names the columns.

**Returns:** Array of objects, one per data row, keyed by the header row.

**Porting semantics**

- The delimiter character is detected automatically.
- Every value comes back as text, numbers included.
- Spaces that follow a delimiter are not part of keys or values.
- Not specified in docs: duplicate header names; quoting rules; blank lines; ragged rows.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CSV_PARSE_TO_OBJECTS("sku, qty\nA-1, 4\nB-9, 12")
output:  [{"sku": "A-1", "qty": "4"}, {"sku": "B-9", "qty": "12"}]
```

**TypeScript equivalent** (APPROXIMATE: delimiter detection and whitespace trimming follow papaparse, not Tines)

```ts
import Papa from "papaparse";
const objects = Papa.parse<Record<string, string>>(text.trim(), {
  header: true, skipEmptyLines: true, transformHeader: (h) => h.trim(), transform: (v) => v.trim(),
}).data;
```

- npm package: `papaparse`.

## EML_PARSE

- **Summary:** parse EML (RFC822) email text into an object
- **Signature:** `EML_PARSE(text, [single_body: TRUE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/eml-parse/

**Arguments**

- `text` (required): The raw text of an email message (EML / RFC 822).
- `single_body` (optional): Keyword argument, on by default: the result has one `body` field, holding the HTML part when there is one and the plain-text part otherwise. `single_body: FALSE` gives `body_html` and `body_text` instead.

**Returns:** Object with the fields `attachments`, `body` (or `body_html` and `body_text`), `cc`, `date`, `from`, `headers`, `message_id`, `subject`, `to`.

**Porting semantics**

- `to` and `cc` are arrays of addresses; `from` is text; `date` is ISO 8601 text with a `+00:00` offset; `message_id` comes without its angle brackets; `headers` is an object keyed by header name, each value on one line.
- Not specified in docs: the shape of the items in `attachments`; `bcc` and `reply_to`; malformed input; several `from` addresses.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - .to and .body for a small two-part message
formula: EML_PARSE(raw_email).subject,
output:  {"subject": "Sample 42 ready", "to": ["ops@example.org"], "date": "2025-09-08T14:05:00+00:00", "message_id": "abc123@example.org", "body": "<p>html part</p>"}
```

**TypeScript equivalent** (APPROXIMATE: built on the mailparser package; field details (header formatting, address formatting, attachment shape) will differ)

```ts
import { simpleParser } from "mailparser";
async function emlParse(text: string, singleBody = true) {
  const m = await simpleParser(text);
  const addrs = (a: any): string[] => (a ? [a].flat().flatMap((x: any) => x.value.map((v: any) => v.address)) : []);
  const headers = Object.fromEntries(m.headerLines.map((h) => {
    const i = h.line.indexOf(":");
    return [h.line.slice(0, i), h.line.slice(i + 1).replace(/\r?\n\s*/g, " ").trim()];
  }));
  const base = {
    attachments: m.attachments, cc: addrs(m.cc), date: m.date ? m.date.toISOString().replace(/\.\d{3}Z$/, "+00:00") : null,
    from: m.from?.text ?? null, headers, message_id: (m.messageId ?? "").replace(/^<|>$/g, ""),
    subject: m.subject ?? null, to: addrs(m.to),
  };
  return singleBody ? { ...base, body: m.html || m.text || "" } : { ...base, body_html: m.html || null, body_text: m.text ?? null };
}
```

- npm package: `mailparser`. The function is async.

## GUNZIP

- **Summary:** decompress gzip data
- **Signature:** `GUNZIP(compressed_file_data)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/gunzip/

**Arguments**

- `gzip_data` (required): Gzip bytes, usually obtained by Base64-decoding a payload.

**Returns:** The decompressed content, as text.

**Porting semantics**

- Gzip data made of several members decompresses to all their contents joined together.
- Decompressed output is limited to less than 100 MB.
- Not specified in docs: behaviour on invalid gzip data; behaviour when the size limit is exceeded.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: GUNZIP(GZIP("ping pong"))
output:  "ping pong"

# 2 - two gzip members ("ab" then "cd") in one byte string
formula: GUNZIP(two_members)
output:  "abcd"
```

**TypeScript equivalent**

```ts
import { gunzipSync } from "node:zlib";
gunzipSync(Buffer.from(base64Text, "base64")).toString("utf8")
```

- The input must be a `Buffer` of the raw bytes. Do not base64-decode to a UTF-8 string first - that corrupts the binary data.
- `gunzipSync` throws on invalid input and has no 100 MB limit.
