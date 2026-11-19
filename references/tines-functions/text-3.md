# Tines formula functions: Text (part 3 of 7: IS_PRESENT to NEWLINE_TO_BR)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: IS_PRESENT, IS_URL, IS_XML, IS_YAML, LEGACY_STRINGIFY, LEVENSHTEIN_DISTANCE, LSTRIP, MATCH, NEWLINE_TO_BR

## IS_PRESENT

- **Summary:** opposite of IS_BLANK
- **Signature:** `IS_PRESENT(any)`
- **Categories:** Text, Objects, Arrays, Logic, Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-present/

**Arguments**

- `any` (required): Any value.

**Returns:** Boolean: false for `FALSE`, `""`, `[]`, `{}`, `NULL`; true otherwise.

**Porting semantics**

- Numbers are present, `0` included.
- The result is a plain boolean.
- Not specified in docs: whether text made only of spaces is present (WHERE treats such a value as absent; the IS_PRESENT page lists only the empty text).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_PRESENT("x")
output:  true

# 2
formula: IS_PRESENT({})
output:  false

# 3
formula: IS_PRESENT(0)
output:  true
```

**TypeScript equivalent**

```ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
const isPresent = (v: any): boolean => !isBlank(v);
```

- `!!value` / `Boolean(value)` is wrong: `0` is present in Tines, while `[]` and `{}` are not.

## IS_URL

- **Summary:** check that text looks like a URL
- **Signature:** `IS_URL(text, [strict: FALSE])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-url/

**Arguments**

- `text` (required): Text to check.
- `strict` (optional): Keyword argument, off by default. When on, the scheme must be http, https or ftp and a host must be present.

**Returns:** Boolean. Follows "the URL standard"; does not guarantee the URL is valid.

**Porting semantics**

- Text without a scheme is not a URL.
- In strict mode a URL with any other scheme is rejected.
- Not specified in docs: the exact rules in non-strict mode; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_URL("https://status.example.org/api")
output:  true

# 2 - no scheme
formula: IS_URL("status.example.org")
output:  false

# 3
formula: IS_URL("myapp://open/settings", strict: TRUE)
output:  false
```

**TypeScript equivalent** (APPROXIMATE: uses the WHATWG URL parser, whose acceptance rules differ in detail from Tines)

```ts
function isUrl(text: unknown, strict = false): boolean {
  if (typeof text !== "string") return false;
  try {
    const u = new URL(text);
    return strict ? ["http:", "https:", "ftp:"].includes(u.protocol) && u.hostname !== "" : true;
  } catch { return false; }
}
```

## IS_XML

- **Summary:** check that text is valid XML
- **Signature:** `IS_XML(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-xml/

**Arguments**

- `text` (required): Text to check.

**Returns:** Boolean.

**Porting semantics**

- Not specified in docs: whether an XML declaration or single root is required; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_XML("<order><id>7</id></order>")
output:  true

# 2 - tags do not match
formula: IS_XML("<order><id>7</order>")
output:  false
```

**TypeScript equivalent**

```ts
import { XMLValidator } from "fast-xml-parser";
XMLValidator.validate(text) === true
```

- npm package: `fast-xml-parser`. `validate` returns `true` or an error object, hence `=== true`.

## IS_YAML

- **Summary:** check that text is valid YAML
- **Signature:** `IS_YAML(text, [parse_date_or_time: FALSE], [strict: FALSE])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-yaml/

**Arguments**

- `text` (required): Text to check.
- `parse_date_or_time` (optional): Keyword argument, off by default; turn it on when the YAML contains date or time values.
- `strict` (optional): Keyword argument, off by default. When on, the text must parse to a document made of keys and values.

**Returns:** Boolean.

**Porting semantics**

- In strict mode text that is not a key/value document, such as XML, is rejected.
- Not specified in docs: what `parse_date_or_time: FALSE` rejects; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_YAML("retries: 3\nhosts:\n  - a\n  - b")
output:  true

# 2
formula: IS_YAML("<a>1</a>", strict: TRUE)
output:  false
```

**TypeScript equivalent** (APPROXIMATE: validity is judged by the npm yaml parser, which may accept or reject different edge cases)

```ts
import YAML from "yaml";
function isYaml(text: string, strict = false): boolean {
  try {
    const v = YAML.parse(text);
    return strict ? typeof v === "object" && v !== null && !Array.isArray(v) : true;
  } catch { return false; }
}
```

- npm package: `yaml`.

## LEGACY_STRINGIFY

- **Summary:** object to legacy {"key"=>"value"} text
- **Signature:** `LEGACY_STRINGIFY(object)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/legacy-stringify/

**Arguments**

- `object` (required): The object to convert.

**Returns:** Text in an older, Ruby-style notation in which each key is followed by `=>` and its value. It is not valid JSON.

**Porting semantics**

- The TEXT function renders objects the same way. TO_JSON is the function that produces JSON text.
- Not specified in docs: rendering of nested arrays, numbers, booleans and null; separator between multiple pairs.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: LEGACY_STRINGIFY({sku: "A-1"})
output:  "{\"sku\"=>\"A-1\"}"
```

**TypeScript equivalent** (APPROXIMATE: only the single-pair `{"foo"=>"bar"}` case is documented; the rest of this helper follows Ruby's inspect format by assumption)

```ts
const legacyStringify = (v: any): string =>
  v === null || v === undefined ? "nil"
  : Array.isArray(v) ? `[${v.map(legacyStringify).join(", ")}]`
  : typeof v === "object" ? `{${Object.entries(v).map(([k, x]) => `${JSON.stringify(k)}=>${legacyStringify(x)}`).join(", ")}}`
  : typeof v === "string" ? JSON.stringify(v) : String(v);
```

- If the output only feeds a human-readable message, prefer `JSON.stringify` and say so in the port notes.

## LEVENSHTEIN_DISTANCE

- **Summary:** weighted Levenshtein edit distance between two strings
- **Signature:** `LEVENSHTEIN_DISTANCE(string_one, string_two, [insertion_cost: 2], [deletion_cost: 2], [substitution_cost: 1])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/levenshtein-distance/

**Arguments**

- `string_one` (required): First string.
- `string_two` (required): Second string.
- `insertion_cost` (optional): Keyword argument, default `2`.
- `deletion_cost` (optional): Keyword argument, default `2`.
- `substitution_cost` (optional): Keyword argument, default `1`.

**Returns:** Number: the minimum total cost of edits turning one string into the other.

**Porting semantics**

- The default costs are NOT the textbook 1/1/1: insertion 2, deletion 2, substitution 1.
- Not specified in docs: case sensitivity (examples are case-matched); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - one substitution costs 1
formula: LEVENSHTEIN_DISTANCE("cart", "card")
output:  1

# 2 - one insertion costs 2 by default
formula: LEVENSHTEIN_DISTANCE("cart", "carts")
output:  2

# 3
formula: LEVENSHTEIN_DISTANCE("cart", "carts", insertion_cost: 1)
output:  1
```

**TypeScript equivalent**

```ts
function levenshtein(a: string, b: string, ins = 2, del = 2, sub = 1): number {
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j * ins);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i * del];
    for (let j = 1; j <= b.length; j++)
      cur[j] = Math.min(prev[j] + del, cur[j - 1] + ins, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : sub));
    prev = cur;
  }
  return prev[b.length];
}
```

- npm Levenshtein packages (`fastest-levenshtein`, `leven`) use unit costs and give different numbers whenever lengths differ (e.g. `"cat"` vs `"cats"`: 1 there, 2 in Tines).

## LSTRIP

- **Summary:** remove leading whitespace
- **Signature:** `LSTRIP(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/lstrip/

**Arguments**

- `text` (required): Text.

**Returns:** Text with all whitespace (tabs, spaces, newlines) removed from the beginning. Spaces between words and trailing whitespace are untouched.

**Porting semantics**

- Not specified in docs: null input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: LSTRIP("\t  left pad  ")
output:  "left pad  "
```

**TypeScript equivalent**

```ts
text.trimStart()
```

## MATCH

- **Summary:** true if text matches a regex
- **Signature:** `MATCH(text, regex_to_match,  [modifiers])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/match/

**Arguments**

- `text` (required): Text to test.
- `regex_to_match` (required): Regular expression, given as text.
- `modifiers` (optional): Ruby regex modifier letters as text; `"i"` makes the match ignore case.

**Returns:** Boolean: true if the text contains a match, false otherwise.

**Porting semantics**

- Unanchored: matches anywhere in the text.
- Not specified in docs: null input; invalid regex.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MATCH("Ticket INC-2291 reopened", "INC-\d+")
output:  true

# 2
formula: MATCH("ticket inc-2291", "INC", "i")
output:  true

# 3
formula: MATCH("ticket inc-2291", "INC")
output:  false
```

**TypeScript equivalent**

```ts
new RegExp(regexToMatch, modifiers.includes("i") ? "i" : "").test(text)
```

- Tines regexes are Ruby regexes (the docs speak of "Ruby modifiers"). Differences from JS that are my own porting notes, not from the Tines page: Ruby `^`/`$` match at every line (JS needs the `m` flag); Ruby modifier `m` means "dot matches newline" (JS flag `s`); `\A`, `\z`, `\Z`, `\h`, possessive quantifiers and inline `(?i)` do not exist in JS and must be rewritten.
- Never reuse a RegExp object with the `g` flag for `.test()` - it keeps state between calls.
- Backslashes: a formula string `"\d+"` keeps the backslash (see REPLACE). In TS write `"\\d+"` or a regex literal `/\d+/`.

## NEWLINE_TO_BR

- **Summary:** insert an HTML line break before each newline
- **Signature:** `NEWLINE_TO_BR(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/newline-to-br/

**Arguments**

- `text` (required): Text.

**Returns:** Text where every newline (`\n`) is replaced with an HTML line break.

**Porting semantics**

- Per the example, each `\n` becomes `<br />\n` - the newline is kept after the tag (the description mentions `<br>`, the output shows `<br />`).
- Not specified in docs: handling of `\r\n`; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - the newline is kept after the tag
formula: NEWLINE_TO_BR("line one\nline two")
output:  "line one<br />\nline two"
```

**TypeScript equivalent**

```ts
text.replace(/\n/g, "<br />\n")
```
