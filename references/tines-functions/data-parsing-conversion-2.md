# Tines formula functions: Data Parsing/Conversion (part 2 of 4: GZIP to NEAT_JSON)

Independent, unofficial porting notes for the functions Tines files under "Data Parsing/Conversion": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: GZIP, HCL_PARSE, HEX_PARSE, JSON_PARSE, JWK_TO_PEM, LDIF_PARSE, MIME_HEADER_DECODE, MSG_PARSE, NEAT_JSON

## GZIP

- **Summary:** gzip-compress text
- **Signature:** `GZIP(file_contents)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/gzip/

**Arguments**

- `file_contents` (required): Text to compress (a single file). Convert objects with TO_JSON first.

**Returns:** The compressed bytes. They are binary, so Base64-encode them before placing them in text.

**Porting semantics**

- Not specified in docs: non-text input behaviour; compression level; gzip header fields.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: BASE64_ENCODE(GZIP("ping pong"))
output:  Base64 text starting with "H4sI" that gunzips back to "ping pong" (exact bytes depend on the gzip implementation)
```

**TypeScript equivalent**

```ts
import { gzipSync } from "node:zlib";
gzipSync(Buffer.from(fileContents, "utf8"))                    // Buffer (binary)
gzipSync(Buffer.from(fileContents, "utf8")).toString("base64") // = BASE64_ENCODE(GZIP(...))
```

- The Base64 text will not be byte-identical to Tines' output (gzip headers and compression settings differ), but it decompresses to the same content.

## HCL_PARSE

- **Summary:** parse HashiCorp Configuration Language text
- **Signature:** `HCL_PARSE(hcl_text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hcl-parse/

**Arguments**

- `hcl_text` (required): HCL text.

**Returns:** The parsed data (the docs give no example of the output shape).

**Porting semantics**

- Not specified in docs: the output structure (how blocks, labels and repeated blocks are represented); behaviour on invalid HCL.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HCL_PARSE('retention { days = 30 }')
output:  the parsed data; its shape is not specified in docs (the hcl2-parser package gives {"retention": [{"days": 30}]})
```

**TypeScript equivalent** (APPROXIMATE: output structure of the npm package is not known to match Tines)

```ts
import hcl from "hcl2-parser";
const parsed = hcl.parseToObject(hclText)[0];
```

- npm package: `hcl2-parser`. Its shape: block type, then labels, as nested keys, with each block body inside an array (`{ resource: { aws_s3_bucket: { b: [{ bucket: "x" }] } } }`). Check that against what the rest of the story reads.

## HEX_PARSE

- **Summary:** convert hexadecimal text to the text/data it represents
- **Signature:** `HEX_PARSE(hex_text, [error_on_invalid_hex: FALSE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hex-parse/

**Arguments**

- `hex_text` (required): Hexadecimal text; digits may be upper or lower case.
- `error_on_invalid_hex` (optional): Keyword argument, off by default. When on, input that is not hexadecimal raises an error naming the function and the offending input.

**Returns:** The decoded text, or raw bytes when the data is not text.

**Porting semantics**

- Not specified in docs: what is returned for invalid hex when `error_on_invalid_hex` is FALSE; odd-length input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HEX_PARSE("6f6b2121")
output:  "ok!!"

# 2
formula: HEX_PARSE("zz", error_on_invalid_hex: TRUE)
output:  an error is raised
```

**TypeScript equivalent**

```ts
function hexParse(hex: string, errorOnInvalidHex = false): string {
  if (errorOnInvalidHex && !/^(?:[0-9a-fA-F]{2})*$/.test(hex))
    throw new Error(`HEX_PARSE: not a hexadecimal string: ${hex}`);
  return Buffer.from(hex, "hex").toString("utf8");
}
```

- `Buffer.from(x, "hex")` silently stops at the first invalid character.
- For binary results keep the `Buffer` (drop `.toString("utf8")`).

## JSON_PARSE

- **Summary:** parse JSON text into data
- **Signature:** `JSON_PARSE(text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/json-parse/

**Arguments**

- `text` (required): (Escaped) JSON text.

**Returns:** In a formula field: the parsed JSON object. Inside a text field: unescaped JSON text.

**Porting semantics**

- Not specified in docs: behaviour on invalid JSON (guard with IS_JSON or IF_ERROR); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: JSON_PARSE('{"sku": "A-1", "tags": ["x", "y"]}')
output:  {"sku": "A-1", "tags": ["x", "y"]}
```

**TypeScript equivalent**

```ts
JSON.parse(text)
```

- `JSON.parse` throws on invalid input and on non-string input such as an already-parsed object; whether Tines errors is not specified.
- When the Tines formula is embedded in surrounding text, the parsed value is rendered back to JSON text there: use `JSON.stringify(JSON.parse(text))`.

## JWK_TO_PEM

- **Summary:** convert a JSON Web Key to PEM
- **Signature:** `JWK_TO_PEM(jwk, [include_private: FALSE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/jwk-to-pem/

**Arguments**

- `jwk` (required): JSON Web Key object. Only RSA and ECDSA keys are supported.
- `include_private` (optional): Keyword argument, off by default. When on, and the key has a private part, the private key is returned instead.

**Returns:** PEM text: the public key by default (`-----BEGIN PUBLIC KEY-----`), or the private key (`-----BEGIN PRIVATE KEY-----`).

**Porting semantics**

- The key material shown in the Tines docs is shortened placeholder data, not a usable key.
- Not specified in docs: result when `include_private` is TRUE but the JWK has no private part; unsupported key types.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - for a freshly generated RSA public JWK
formula: JWK_TO_PEM(jwk)
output:  PEM text beginning "-----BEGIN PUBLIC KEY-----", identical to the SPKI export of the same key
```

**TypeScript equivalent**

```ts
import { createPrivateKey, createPublicKey } from "node:crypto";
function jwkToPem(jwk: Record<string, any>, includePrivate = false): string {
  if (includePrivate && jwk.d) return createPrivateKey({ key: jwk, format: "jwk" }).export({ type: "pkcs8", format: "pem" }) as string;
  const { d, p, q, dp, dq, qi, ...pub } = jwk;
  return createPublicKey({ key: pub, format: "jwk" }).export({ type: "spki", format: "pem" }) as string;
}
```

- Falling back to the public key when no private part exists is an assumption.

## LDIF_PARSE

- **Summary:** parse LDIF text into an array of entry objects
- **Signature:** `LDIF_PARSE(ldif_file_text)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/ldif-parse/

**Arguments**

- `ldif_file_text` (required): The text content of an LDIF (LDAP export) file.

**Returns:** Array of objects, one per entry. In the example each attribute name is lowercased (`objectClass` becomes `objectclass`), each value is an array of text, and the `dn` line is not present in the output.

**Porting semantics**

- Not specified in docs: where the DN goes; base64 (`attr:: value`) values; change records; comments; folded lines.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: LDIF_PARSE("dn: uid=apark,ou=people,dc=example,dc=org\nuid: apark\nmail: apark@example.org\nmail: ada@example.org")
output:  [{"uid": ["apark"], "mail": ["apark@example.org", "ada@example.org"]}]
```

**TypeScript equivalent** (APPROXIMATE: hand-written parser covering simple content records only)

```ts
function ldifParse(text: string): Record<string, string[]>[] {
  return text.replace(/\r?\n /g, "").split(/\r?\n\s*\r?\n/).map((rec) => {
    const out: Record<string, string[]> = {};
    for (const line of rec.split(/\r?\n/)) {
      const m = /^([^:#\s][^:]*)(::?)\s*(.*)$/.exec(line);
      if (!m || ["dn", "version"].includes(m[1].toLowerCase())) continue;
      (out[m[1].toLowerCase()] ??= []).push(m[2] === "::" ? Buffer.from(m[3], "base64").toString("utf8") : m[3]);
    }
    return out;
  }).filter((o) => Object.keys(o).length > 0);
}
```

## MIME_HEADER_DECODE

- **Summary:** decode RFC 2047 encoded email header text
- **Signature:** `MIME_HEADER_DECODE(encoded_string, target_encoding = "utf-8")`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/mime-header-decode/

**Arguments**

- `encoded_string` (required): Header text containing RFC 2047 encoded words.
- `target_encoding` (optional): Character encoding wanted for the result; UTF-8 by default.

**Returns:** The decoded text. Parts that were not encoded are left as they are.

**Porting semantics**

- Not specified in docs: behaviour for malformed encoded words; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MIME_HEADER_DECODE("=?UTF-8?B?UsOpc3Vtw6k=?= attached")
output:  "Résumé attached"

# 2
formula: MIME_HEADER_DECODE("=?ISO-8859-1?Q?Gr=FC=DFe?= <team@example.org>")
output:  "Grüße <team@example.org>"
```

**TypeScript equivalent**

```ts
import libmime from "libmime";
libmime.decodeWords(encodedString)
```

- npm package: `libmime`. The result is a normal JS (Unicode) string, so `target_encoding` has no counterpart.

## MSG_PARSE

- **Summary:** parse an Outlook .msg file into an object
- **Signature:** `MSG_PARSE(file, [extract_multiline_headers: FALSE], [single_body: TRUE])`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/msg-parse/

**Arguments**

- `file` (required): The bytes of an Outlook `.msg` file, usually obtained by Base64-decoding uploaded file contents.
- `extract_multiline_headers` (optional): Keyword argument, off by default: a header value stops at its first line break. Turn it on to get complete multi-line header values.
- `single_body` (optional): Keyword argument, on by default: one `body` field, HTML when there is an HTML part and plain text otherwise. `single_body: FALSE` gives `body_html` and `body_text` instead.

**Returns:** Object with the same fields as EML_PARSE: `attachments`, `body` (or `body_html` and `body_text`), `cc`, `date`, `from`, `headers`, `message_id`, `subject`, `to`.

**Porting semantics**

- Not specified in docs: the shape of items in `attachments`; behaviour on invalid input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MSG_PARSE(BASE64_DECODE(upload.contents)).subject
output:  the subject line of the message, e.g. "Sample 42 ready"
(not executed: needs a real .msg file and the msgreader package, neither available where the examples were run)
```

**TypeScript equivalent** (APPROXIMATE: built on @kenjiuno/msgreader; field names must be mapped by hand and details will differ)

```ts
import MsgReader from "@kenjiuno/msgreader";
function msgParse(file: Buffer, singleBody = true) {
  const m = new MsgReader(file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength) as ArrayBuffer).getFileData();
  const rcpt = (type: string) => (m.recipients ?? []).filter((r) => r.recipType === type).map((r) => r.smtpAddress ?? r.email ?? "");
  const html = m.bodyHtml ?? (m.html ? Buffer.from(m.html).toString("utf8") : undefined);
  const base = {
    attachments: m.attachments ?? [], cc: rcpt("cc"), date: m.messageDeliveryTime ?? m.clientSubmitTime ?? null,
    from: m.senderSmtpAddress ?? m.senderEmail ?? null, headers: m.headers ?? "", message_id: m.messageId ?? null,
    subject: m.subject ?? null, to: rcpt("to"),
  };
  return singleBody ? { ...base, body: html ?? m.body ?? "" } : { ...base, body_html: html ?? null, body_text: m.body ?? null };
}
```

- npm package: `@kenjiuno/msgreader`. `headers` comes back as raw text there, not as an object like Tines; parse it if the story reads individual headers.
- Pass the raw bytes (a `Buffer`), not a UTF-8 decoded string.

## NEAT_JSON

- **Summary:** pretty-print an object as JSON text
- **Signature:** `NEAT_JSON(object)`
- **Categories:** Data Parsing/Conversion
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/neat-json/

**Arguments**

- `object` (required): The object to format.

**Returns:** Multi-line, indented JSON text.

**Porting semantics**

- Only the general shape (one key per line, indented) is documented; the indent width and key order of real Tines output are not pinned down.
- Not specified in docs: indentation width; key ordering; alignment options.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: NEAT_JSON({sku: "A-1", tags: ["x"]})
output:  the same data as JSON text spread over several indented lines (exact indentation not specified in docs)
```

**TypeScript equivalent** (APPROXIMATE: exact whitespace of the Tines formatter is not specified; JSON content is identical)

```ts
JSON.stringify(object, null, 2)
```

- If the consumer parses the JSON, whitespace does not matter. If byte-exact text matters, verify against a real Tines run.
