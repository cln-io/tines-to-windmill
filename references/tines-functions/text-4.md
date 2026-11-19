# Tines formula functions: Text (part 4 of 7: PAD_LEFT to REMOVE_FIRST)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: PAD_LEFT, PAD_RIGHT, PLURALIZE, PREPEND, RANDOM_STRING, REGEX_EXTRACT, REGEX_REPLACE, REMOVE, REMOVE_FIRST

## PAD_LEFT

- **Summary:** left-pad text to a target length
- **Signature:** `PAD_LEFT(input, target_length, pad_value)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/pad-left/

**Arguments**

- `input` (required): The text to pad.
- `target_length` (required): Desired total length. Cannot exceed 65536.
- `pad_value` (required): Text to prepend repeatedly; it is cut off when the target length is reached (`"abc"` gives `"abcabinput"`).

**Returns:** The padded text.

**Porting semantics**

- Not specified in docs: input already longer than the target; number input; empty pad_value; target above 65536 (presumably an error).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PAD_LEFT("42", 6, "0")
output:  "000042"

# 2 - the pad text is cut to fit
formula: PAD_LEFT("7", 4, "xy")
output:  "xyx7"
```

**TypeScript equivalent**

```ts
String(input).padStart(targetLength, padValue)
```

- `padStart` returns the input unchanged when it is already long enough - presumably the same in Tines, but not stated.

## PAD_RIGHT

- **Summary:** right-pad text to a target length
- **Signature:** `PAD_RIGHT(input, target_length, pad_value)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/pad-right/

**Arguments**

- `input` (required): The text to pad.
- `target_length` (required): Desired total length. Cannot exceed 65536.
- `pad_value` (required): Text to append repeatedly; it is cut off when the target length is reached (`"abc"` gives `"inputabcab"`).

**Returns:** The padded text.

**Porting semantics**

- Not specified in docs: input already longer than the target; number input; empty pad_value; target above 65536 (presumably an error).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PAD_RIGHT("ID", 5, ".")
output:  "ID..."

# 2 - the pad text is cut to fit
formula: PAD_RIGHT("7", 4, "xy")
output:  "7xyx"
```

**TypeScript equivalent**

```ts
String(input).padEnd(targetLength, padValue)
```

## PLURALIZE

- **Summary:** singular or plural form of a word based on a count
- **Signature:** `PLURALIZE(counter, text, [plural_text])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/pluralize/

**Arguments**

- `counter` (required): The number that decides singular vs plural.
- `text` (required): The singular form.
- `plural_text` (optional): Custom plural form (e.g. `"bonuses"`).

**Returns:** The singular text when the counter is 1, otherwise the plural.

**Porting semantics**

- Not specified in docs: how the default plural is derived for irregular words; counter of 0, negative or decimal values; whether the number itself is included (the examples show it is not).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PLURALIZE(1, "ticket")
output:  "ticket"

# 2
formula: PLURALIZE(3, "ticket")
output:  "tickets"

# 3
formula: PLURALIZE(4, "box", "boxes")
output:  "boxes"
```

**TypeScript equivalent** (APPROXIMATE: default plural simply appends "s"; Tines' own inflection rules are not documented)

```ts
Number(counter) === 1 ? text : pluralText ?? `${text}s`
```

- The result does not include the number: `PLURALIZE(2, "item")` is `"items"`, not `"2 items"`.

## PREPEND

- **Summary:** add text to the beginning of other text
- **Signature:** `PREPEND(text, prefix)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/prepend/

**Arguments**

- `text` (required): The original text.
- `prefix` (required): The text to put in front.

**Returns:** `prefix` followed by `text`.

**Porting semantics**

- Argument order: the text comes first, the prefix second - the result is `prefix + text`.
- Not specified in docs: non-text or null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PREPEND("4471", "INV-")
output:  "INV-4471"
```

**TypeScript equivalent**

```ts
[prefix, text].join("")
```

- `join` renders a null argument as `""`; non-text arguments are not specified in docs.

## RANDOM_STRING

- **Summary:** random string of a given length and character set
- **Signature:** `RANDOM_STRING(length, mode, custom_characters)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/random-string/

**Arguments**

- `length` (optional): Number of characters; 16 when omitted.
- `mode` (optional): Character set by name: `"alphanumeric"` (the default: letters of both cases and digits), `"letters"`, `"numbers"`, `"hex"` (lowercase), or `"custom"`.
- `custom_characters` (optional): Only used when mode is `"custom"`: the characters to draw from (special characters and emojis are accepted).

**Returns:** Random text of the requested length.

**Porting semantics**

- All three arguments are positional and optional.
- Not specified in docs: whether the generator is cryptographically secure; unknown mode; "custom" mode without characters.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RANDOM_STRING()
output:  16 random letters and digits, e.g. "q7ZpL0vTx2MhB9dK"

# 2
formula: RANDOM_STRING(8, "hex")
output:  8 random lowercase hex digits, e.g. "3fa90c1e"

# 3
formula: RANDOM_STRING(5, "custom", "XYZ")
output:  5 characters drawn from X, Y, Z, e.g. "ZXXYZ"
```

**TypeScript equivalent**

```ts
import { randomInt } from "node:crypto";
function randomString(length = 16, mode = "alphanumeric", custom = ""): string {
  const lower = "abcdefghijklmnopqrstuvwxyz", L = lower + lower.toUpperCase(), D = "0123456789";
  const sets: Record<string, string> = { alphanumeric: L + D, letters: L, numbers: D, hex: D + "abcdef", custom };
  const chars = [...sets[mode]]; // spread splits by code point, so emojis stay intact
  return Array.from({ length }, () => chars[randomInt(chars.length)]).join("");
}
```

## REGEX_EXTRACT

- **Summary:** all regex matches in text as an array
- **Signature:** `REGEX_EXTRACT(text, regex, [modifiers])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/regex-extract/

**Arguments**

- `text` (required): Text to search.
- `regex` (required): Regular expression, given as text.
- `modifiers` (optional): Ruby regex modifier letters as text; `"i"` makes the match ignore case.

**Returns:** Array of all matches. Without capture groups: an array of matched texts. With capture groups: an array of arrays, one inner array per match containing the groups (not the whole match).

**Porting semantics**

- As soon as the regex has a capture group, even a single one, every match is returned as an array of its groups, so the first group of the first match is read with `[0][0]`.
- Results are 0-indexed arrays.
- Not specified in docs: result when nothing matches (empty array vs null); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REGEX_EXTRACT("INC-12 blocks INC-7 and inc-99", "INC-\d+")
output:  ["INC-12", "INC-7"]

# 2 - groups give nested arrays
formula: REGEX_EXTRACT("w=30;h=45", "(\w)=(\d+)")
output:  [["w", "30"], ["h", "45"]]

# 3
formula: REGEX_EXTRACT("INC-12 and inc-99", "inc-\d+", "i")
output:  ["INC-12", "inc-99"]
```

**TypeScript equivalent**

```ts
function regexExtract(text: string, regex: string, modifiers = ""): (string | string[])[] {
  const flags = "g" + (modifiers.includes("i") ? "i" : "") + (modifiers.includes("m") ? "s" : "");
  return [...text.matchAll(new RegExp(regex, flags))].map((m) => (m.length > 1 ? m.slice(1) : m[0]));
}
```

- `text.match(/re/g)` is subtly wrong: it returns `null` on no match and ignores capture groups.
- This helper returns `[]` on no match; Tines' no-match result is not specified, so guard with a blank check rather than indexing blindly.
- Tines regexes are Ruby regexes (the docs speak of "Ruby modifiers"). Differences from JS that are my own porting notes, not from the Tines page: Ruby `^`/`$` match at every line (JS needs the `m` flag); Ruby modifier `m` means "dot matches newline" (JS flag `s`); `\A`, `\z`, `\Z`, `\h`, possessive quantifiers and inline `(?i)` do not exist in JS and must be rewritten.
- Backslashes: a formula string `"\d+"` keeps the backslash (see REPLACE). In TS write `"\\d+"` or use a regex literal.

## REGEX_REPLACE

- **Summary:** replace every regex match in text
- **Signature:** `REGEX_REPLACE(text, regex, replacement)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/regex-replace/

**Arguments**

- `text` (required): Text to search.
- `regex` (required): Regular expression, given as text.
- `replacement` (required): Replacement text. A backslash and a digit inserts that numbered capture group; `\k<name>` inserts a named one.

**Returns:** Text with every occurrence of a match replaced.

**Porting semantics**

- Replaces all matches (global), not just the first.
- Not specified in docs: modifiers (the syntax has no modifiers argument); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - every match
formula: REGEX_REPLACE("tel 555 0199 or 555 0142", "\d{3} \d{4}", "[hidden]")
output:  "tel [hidden] or [hidden]"

# 2
formula: REGEX_REPLACE("1920x1080", "(\d+)x(\d+)", "\2 by \1")
output:  "1080 by 1920"

# 3
formula: REGEX_REPLACE("key=abc", "(?<k>\w+)=(?<v>\w+)", "\k<v> is \k<k>")
output:  "abc is key"
```

**TypeScript equivalent**

```ts
function regexReplace(text: string, regex: string, replacement: string): string {
  const js = replacement
    .replace(/\$/g, () => "$$")                                   // literal $ must be escaped for JS
    .replace(/\\k<(\w+)>/g, (_m, name) => "$<" + name + ">")       // \k<name> -> $<name>
    .replace(/\\(\d)/g, (_m, d) => (d === "0" ? "$&" : "$" + d));  // \1 -> $1
  return text.replace(new RegExp(regex, "g"), js);
}
```

- Backreference syntax differs: Tines `\1` and `\k<name>` are `$1` and `$<name>` in JS. With a literal pattern write it directly: `text.replace(/(\d+)x(\d+)/g, "$2 by $1")`.
- Forgetting the `g` flag replaces only the first match.
- Tines regexes are Ruby regexes. Differences from JS that are my own porting notes, not from the Tines page: Ruby `^`/`$` match at every line (JS needs the `m` flag); `\A`, `\z`, `\Z`, `\h`, possessive quantifiers and inline `(?i)` do not exist in JS and must be rewritten.
- Backslashes: a formula string keeps the backslash of a sequence such as `\d` (see REPLACE). In TS write `"\\d+"` or use a regex literal.

## REMOVE

- **Summary:** remove every occurrence of a substring, or matching array items
- **Signature:** `REMOVE(text, text_to_remove)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/remove/

**Arguments**

- `text` (required): Text, or an array.
- `text_to_remove` (required): The sub-text to remove (literal); for an array, the value whose exactly-matching items are removed.

**Returns:** Text with every occurrence removed; or the array without the items that exactly match the value.

**Porting semantics**

- On an array only elements equal to the value as a whole are removed; an element that merely contains it stays.
- On text nothing else changes, so spaces around the removed pieces stay.
- Not specified in docs: null input; empty sub-text.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REMOVE("2025-09-08", "-")
output:  "20250908"

# 2
formula: REMOVE(["draft", "final", "draft-2", "draft"], "draft")
output:  ["final", "draft-2"]
```

**TypeScript equivalent**

```ts
Array.isArray(text) ? text.filter((x: unknown) => x !== textToRemove) : text.split(textToRemove).join("")
```

- `text.replace(sub, "")` only removes the first occurrence (that is REMOVE_FIRST).

## REMOVE_FIRST

- **Summary:** remove the first occurrence of a substring
- **Signature:** `REMOVE_FIRST(text, text_to_remove)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/remove-first/

**Arguments**

- `text` (required): Text.
- `text_to_remove` (required): The sub-text to remove (literal, not a regex).

**Returns:** Text with the first occurrence taken out. Nothing else changes, so spaces around the removed piece stay.

**Porting semantics**

- Not specified in docs: null input; sub-text not present (presumably unchanged).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REMOVE_FIRST("re: re: status", "re: ")
output:  "re: status"
```

**TypeScript equivalent**

```ts
text.replace(textToRemove, "")
```

- Safe only because the pattern is a string: JS string patterns are literal and replace the first occurrence only. Do not build a RegExp from the value.
