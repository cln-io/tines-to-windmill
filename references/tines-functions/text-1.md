# Tines formula functions: Text (part 1 of 7: APPEND to ESCAPE_ONCE)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: APPEND, BYTESIZE, CAMELIZE, CAPITALIZE, CONST_EQUALS, CONTAINS_URL, DOWNCASE, ENDS_WITH, ESCAPE, ESCAPE_ONCE

## APPEND

- **Summary:** concatenate text values
- **Signature:** `APPEND(text1, text2, ...)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/append/

**Arguments**

- `text1, text2, ...` (required): Two or more text values.

**Returns:** Text: the arguments concatenated in order.

**Porting semantics**

- Equivalent to chaining the `&` operator.
- Not specified in docs: non-text arguments (numbers, null, arrays, objects).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: APPEND("report", "-", "final")
output:  "report-final"

# 2
formula: APPEND("inv", "oice", ".pdf")
output:  "invoice.pdf"
```

**TypeScript equivalent**

```ts
[text1, text2].join("") // any number of items
```

- `Array.join` renders `null`/`undefined` as `""`; a template literal would print `"null"`. Which of the two Tines does is not specified in docs.
- Do not port with `+`: if both operands are numbers JS adds them.

## BYTESIZE

- **Summary:** length of text in bytes
- **Signature:** `BYTESIZE(string)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/bytesize/

**Arguments**

- `string` (required): Text.

**Returns:** Number of bytes of the text in UTF-8.

**Porting semantics**

- Not specified in docs: non-text input; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: BYTESIZE("depot")
output:  5

# 2 - é takes two bytes
formula: BYTESIZE("née")
output:  4

# 3
formula: BYTESIZE("🚚")
output:  4
```

**TypeScript equivalent**

```ts
Buffer.byteLength(string, "utf8")
```

- `string.length` is wrong here: it counts UTF-16 code units, so `"née".length` is 3 and `"🚚".length` is 2.

## CAMELIZE

- **Summary:** convert text to camelCase
- **Signature:** `CAMELIZE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/camelize/

**Arguments**

- `text` (required): Text.

**Returns:** Text in camel case with a lowercase first letter; underscores and spaces mark word boundaries.

**Porting semantics**

- Not specified in docs: treatment of hyphens, existing capitals, digits, leading/trailing separators; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CAMELIZE("order_line_total")
output:  "orderLineTotal"

# 2
formula: CAMELIZE("ship to")
output:  "shipTo"
```

**TypeScript equivalent** (APPROXIMATE: only the two documented cases (underscore and space separators) are known; other inputs follow this helper's own rules)

```ts
const camelize = (text: string): string =>
  text.replace(/[_\s-]+(.)?/g, (_m, c?: string) => (c ? c.toUpperCase() : "")).replace(/^./, (c) => c.toLowerCase());
```

## CAPITALIZE

- **Summary:** uppercase first character, lowercase the rest
- **Signature:** `CAPITALIZE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/capitalize/

**Arguments**

- `text` (required): Text.

**Returns:** Text with the first character uppercase and all remaining characters lowercase.

**Porting semantics**

- Only the very first character is uppercased; everything after it, including later words, is lowercased.
- Not specified in docs: null/blank input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CAPITALIZE("urgent NOTICE")
output:  "Urgent notice"

# 2
formula: CAPITALIZE("pARIS")
output:  "Paris"
```

**TypeScript equivalent**

```ts
text.charAt(0).toUpperCase() + text.slice(1).toLowerCase()
```

- Do not forget the `.toLowerCase()` on the remainder; CSS-style "capitalize" or lodash `upperFirst` leave the rest untouched.

## CONST_EQUALS

- **Summary:** compare two values in constant time
- **Signature:** `CONST_EQUALS(string1, string2)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/const-equals/

**Arguments**

- `string1` (required): First value.
- `string2` (required): Second value.

**Returns:** Boolean: true if identical, false otherwise.

**Porting semantics**

- Non-string arguments are stringified before comparison.
- Not resistant to timing attacks that determine secret length.
- Not specified in docs: how non-text values are turned into text; null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CONST_EQUALS("tok_9f2", "tok_9f2")
output:  true

# 2
formula: CONST_EQUALS("tok_9f2", "tok_9f3")
output:  false
```

**TypeScript equivalent**

```ts
import { timingSafeEqual } from "node:crypto";
function constEquals(a: unknown, b: unknown): boolean {
  const x = Buffer.from(typeof a === "string" ? a : JSON.stringify(a));
  const y = Buffer.from(typeof b === "string" ? b : JSON.stringify(b));
  return x.length === y.length && timingSafeEqual(x, y);
}
```

- `timingSafeEqual` throws on different lengths, hence the length check first.
- Stringifying non-strings with `JSON.stringify` is an assumption.

## CONTAINS_URL

- **Summary:** true if text contains a URL
- **Signature:** `CONTAINS_URL(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/contains-url/

**Arguments**

- `text` (required): Text to scan.

**Returns:** Boolean: true when a URL occurs anywhere in the text.

**Porting semantics**

- Not specified in docs: the exact URL pattern (schemes accepted, whether bare domains or `www.` count); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CONTAINS_URL("Docs moved to https://docs.example.org/start today")
output:  true

# 2
formula: CONTAINS_URL("no links in this sentence")
output:  false
```

**TypeScript equivalent** (APPROXIMATE: the URL pattern is not documented; this only looks for an http, https or ftp scheme prefix)

```ts
["http://", "https://", "ftp://"].some((p) => text.toLowerCase().includes(p))
```

## DOWNCASE

- **Summary:** lowercase text
- **Signature:** `DOWNCASE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/downcase/

**Arguments**

- `text` (required): Text.

**Returns:** Text with each character in lowercase.

**Porting semantics**

- Not specified in docs: null/blank input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DOWNCASE("Track & TRACE")
output:  "track & trace"
```

**TypeScript equivalent**

```ts
text.toLowerCase()
```

- `null.toLowerCase()` throws; use `String(text ?? "")` if the value may be missing.

## ENDS_WITH

- **Summary:** true if text ends with a suffix
- **Signature:** `ENDS_WITH(text, suffix)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/ends-with/

**Arguments**

- `text` (required): Text to test.
- `suffix` (required): Suffix to look for.

**Returns:** Boolean.

**Porting semantics**

- The comparison is case-sensitive.
- The docs display the result in quotes, as if it were text; the described behaviour is a true/false value, so port it as a boolean.
- Not specified in docs: null input; non-text input; empty suffix.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ENDS_WITH("invoice_2025.pdf", ".pdf")
output:  true

# 2 - case matters
formula: ENDS_WITH("invoice_2025.PDF", ".pdf")
output:  false
```

**TypeScript equivalent**

```ts
text.endsWith(suffix)
```

## ESCAPE

- **Summary:** HTML-escape text (entities)
- **Signature:** `ESCAPE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/escape/

**Arguments**

- `text` (required): Text.

**Returns:** Text with special characters replaced by escape sequences. The example shows HTML entities: `'` becomes `&#39;`, `&` becomes `&amp;`.

**Porting semantics**

- The escaping is HTML entity escaping, not URL encoding, whatever the wording of the Tines description suggests. For URLs use URL_ENCODE.
- Entities that are already present are escaped a second time (contrast ESCAPE_ONCE).
- Not specified in docs: the full character set escaped (`<`, `>`, `"` are not shown in the examples); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ESCAPE("Tom & Jerry's")
output:  "Tom &amp; Jerry&#39;s"

# 2 - escaped again
formula: ESCAPE("&amp;")
output:  "&amp;amp;"
```

**TypeScript equivalent**

```ts
const ENT: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const escape = (text: string): string => text.replace(/[&<>"']/g, (c) => ENT[c]);
```

- Do not use `encodeURIComponent` or the deprecated global `escape()` here.

## ESCAPE_ONCE

- **Summary:** HTML-escape text without double-escaping existing entities
- **Signature:** `ESCAPE_ONCE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/escape-once/

**Arguments**

- `text` (required): Text.

**Returns:** Text with `&`, `<`, `>` (and quotes, per ESCAPE) replaced by HTML entities; entities already present are left unchanged.

**Porting semantics**

- An ampersand that already starts an entity is left alone; a bare ampersand is escaped.
- Not specified in docs: the exact character set escaped; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ESCAPE_ONCE("5 &lt; 7 & 9 > 2")
output:  "5 &lt; 7 &amp; 9 &gt; 2"
```

**TypeScript equivalent**

```ts
const ENT: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const escapeOnce = (text: string): string =>
  text.replace(/[&<>"']/g, (c) => ENT[c]).replace(/&amp;(?=#?\w+;)/g, "&"); // escape everything, then undo the double escape of existing entities
```
