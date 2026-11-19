# Tines formula functions: Text (part 7 of 7: TO_SNAKE_CASE to UUID)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: TO_SNAKE_CASE, TRANSLITERATE, TRUNCATE, TRUNCATEWORDS, UPCASE, URL_DECODE, URL_ENCODE, UUID

## TO_SNAKE_CASE

- **Summary:** convert text to snake_case
- **Signature:** `TO_SNAKE_CASE(text, [from_camel_case: FALSE])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-snake-case/

**Arguments**

- `text` (required): Text.
- `from_camel_case` (optional): Keyword argument, off by default. When on, a camelCase boundary becomes an underscore.

**Returns:** Lowercase text with the words joined by underscores; punctuation and separators are dropped.

**Porting semantics**

- With the option off, camelCase is merely lowercased: no underscore appears at the boundary.
- Not specified in docs: non-ASCII letters; consecutive capitals with from_camel_case (`"HTTPServer"`); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_SNAKE_CASE("Total Net-Weight (kg)")
output:  "total_net_weight_kg"

# 2
formula: TO_SNAKE_CASE("lastLogin")
output:  "lastlogin"

# 3
formula: TO_SNAKE_CASE("lastLogin", from_camel_case: TRUE)
output:  "last_login"
```

**TypeScript equivalent**

```ts
const toSnakeCase = (text: string, fromCamelCase = false): string =>
  (fromCamelCase ? text.replace(/([a-z\d])([A-Z])/g, "$1_$2") : text)
    .toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
```

- lodash `snakeCase` always splits camelCase, which is wrong for the default mode.

## TRANSLITERATE

- **Summary:** replace non-ASCII characters with ASCII approximations
- **Signature:** `TRANSLITERATE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/transliterate/

**Arguments**

- `text` (required): Text.

**Returns:** Text where non-ASCII characters are replaced with an ASCII approximation, or with `?` when none exists (`"À È Î"` gives `"A E I"`; `™`, `£`, `¢` give `?`).

**Porting semantics**

- Not specified in docs: the approximation table (e.g. what `ß`, `Æ`, `ø` become); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TRANSLITERATE("Crème brûlée, señor")
output:  "Creme brulee, senor"

# 2 - no ASCII stand-in: question marks
formula: TRANSLITERATE("50 € ≈ 55 $")
output:  "50 ? ? 55 $"
```

**TypeScript equivalent** (APPROXIMATE: strips diacritics via Unicode decomposition; characters with multi-letter approximations (ß, Æ, ...) become "?" here)

```ts
text.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\x00-\x7f]/g, "?")
```

## TRUNCATE

- **Summary:** shorten text to a number of characters, adding an ellipsis
- **Signature:** `TRUNCATE(text, length, [ellipsis])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/truncate/

**Arguments**

- `text` (required): Text.
- `length` (required): Maximum number of characters of the result, including the ellipsis.
- `ellipsis` (optional): Text appended when truncation happens; default `...`. Pass `""` to append nothing.

**Returns:** The text unchanged when it fits; otherwise shortened so that text plus ellipsis is exactly `length` characters.

**Porting semantics**

- The ellipsis counts towards the length.
- Not specified in docs: length smaller than the ellipsis; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TRUNCATE("Conveyor belt jammed", 11)
output:  "Conveyor..."

# 2
formula: TRUNCATE("Conveyor belt jammed", 8, "")
output:  "Conveyor"

# 3
formula: TRUNCATE("short", 20)
output:  "short"
```

**TypeScript equivalent**

```ts
const truncate = (text: string, length: number, ellipsis = "..."): string =>
  text.length <= length ? text : text.slice(0, Math.max(0, length - ellipsis.length)) + ellipsis;
```

- `text.slice(0, length) + "..."` is wrong: the result would be 3 characters too long.

## TRUNCATEWORDS

- **Summary:** shorten text to a number of words, adding an ellipsis
- **Signature:** `TRUNCATEWORDS(text, length, [ellipsis])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/truncatewords/

**Arguments**

- `text` (required): Text.
- `length` (required): Maximum number of words to keep.
- `ellipsis` (optional): Text appended when truncation happens; default `...`. Pass `""` to append nothing.

**Returns:** The first `length` words with the ellipsis attached directly; the text unchanged when it has no more words than that.

**Porting semantics**

- The ellipsis is appended with no space before it; a custom ellipsis supplies its own space (`" etc"`).
- Not specified in docs: how words are delimited (whitespace assumed); whether repeated whitespace is normalised; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TRUNCATEWORDS("Conveyor belt jammed near dock four", 3)
output:  "Conveyor belt jammed..."

# 2
formula: TRUNCATEWORDS("Conveyor belt jammed near dock four", 2, " [more]")
output:  "Conveyor belt [more]"
```

**TypeScript equivalent**

```ts
function truncateWords(text: string, length: number, ellipsis = "..."): string {
  const words = text.split(/\s+/).filter(Boolean);
  return words.length <= length ? text : words.slice(0, length).join(" ") + ellipsis;
}
```

## UPCASE

- **Summary:** uppercase text
- **Signature:** `UPCASE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/upcase/

**Arguments**

- `text` (required): Text.

**Returns:** Text with each character in uppercase.

**Porting semantics**

- Not specified in docs: null/blank input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UPCASE("Track & trace")
output:  "TRACK & TRACE"
```

**TypeScript equivalent**

```ts
text.toUpperCase()
```

## URL_DECODE

- **Summary:** decode URL-encoded text
- **Signature:** `URL_DECODE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/url-decode/

**Arguments**

- `text` (required): URL-encoded text, such as the output of URL_ENCODE.

**Returns:** The decoded text; a `+` is read as a space.

**Porting semantics**

- Not specified in docs: malformed percent sequences; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: URL_DECODE("caf%C3%A9+%26+bar")
output:  "café & bar"
```

**TypeScript equivalent**

```ts
decodeURIComponent(text.replace(/\+/g, " "))
```

- Bare `decodeURIComponent` leaves `+` as a plus sign.
- `decodeURIComponent` throws on malformed sequences such as `%E0%A4%A`.

## URL_ENCODE

- **Summary:** URL-encode text (form encoding by default)
- **Signature:** `URL_ENCODE(text, [encoding: "form"])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/url-encode/

**Arguments**

- `text` (required): Text to encode.
- `encoding` (optional): Keyword argument, default `"form"`. `encoding: "uri"` uses URI (percent) encoding.

**Returns:** The encoded text. In the default form encoding a space becomes `+`; with `encoding: "uri"` it becomes `%20`. Reserved characters such as `@` and `&` are percent-encoded in both.

**Porting semantics**

- URL_DECODE's example shows `'` and `!` in their percent-encoded forms (`%27`, `%21`).
- Not specified in docs: the exact set of characters left unencoded in each mode; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: URL_ENCODE("café & bar")
output:  "caf%C3%A9+%26+bar"

# 2
formula: URL_ENCODE("café & bar", encoding: "uri")
output:  "caf%C3%A9%20%26%20bar"
```

**TypeScript equivalent** (APPROXIMATE: the exact unreserved character set is not documented; `!'()*` are percent-encoded here)

```ts
function urlEncode(text: string, encoding: "form" | "uri" = "form"): string {
  const s = encodeURIComponent(text).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
  return encoding === "form" ? s.replace(/%20/g, "+") : s;
}
```

- Bare `encodeURIComponent` encodes a space as `%20`, which matches `encoding: "uri"` but not the default form encoding (`+`).
- When building a query string, prefer `new URLSearchParams({ key: value }).toString()` or let the HTTP client encode parameters, and do not encode twice.

## UUID

- **Summary:** generate a UUID
- **Signature:** `UUID()`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/uuid/

**Arguments**

- None.

**Returns:** Text: a freshly generated universally unique identifier in the usual 8-4-4-4-12 hexadecimal layout.

**Porting semantics**

- Not specified in docs: UUID version (the example has the version-4 shape).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UUID()
output:  text shaped like "6b1f0c2e-9a47-4d3b-8e15-0c7a52f9d410", different on every call
```

**TypeScript equivalent**

```ts
crypto.randomUUID()
```

- `crypto` is a global in Bun and Node; `import { randomUUID } from "node:crypto"` also works.
