# Tines formula functions: Text (part 5 of 7: REPLACE to STRIP_NEWLINES)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: REPLACE, REPLACE_FIRST, RSTRIP, SIZE, SLICE, SPLIT, STARTS_WITH, STRIP, STRIP_HTML, STRIP_NEWLINES

## REPLACE

- **Summary:** replace every occurrence of a substring
- **Signature:** `REPLACE(text, search, replace_with)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/replace/

**Arguments**

- `text` (required): Text.
- `search` (required): The text to find (literal, not a regex).
- `replace_with` (required): The replacement text.

**Returns:** The text with all occurrences of the search text swapped for the replacement.

**Porting semantics**

- Matching is literal and case-sensitive.
- Escapes inside formula text: backslash-n is a newline, backslash-t a tab, backslash-quote a quote and a doubled backslash one backslash; this holds in single-quoted text as well, so a lone backslash cannot end a string. Any other backslash sequence (backslash-d, for instance) stays as typed.
- Not specified in docs: null input; empty search text; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REPLACE("a-b-c", "-", "+")
output:  "a+b+c"

# 2 - case matters
formula: REPLACE("Draft draft", "draft", "final")
output:  "Draft final"

# 3 - the formula text \t is a tab
formula: REPLACE("x\ty", "\t", " ")
output:  "x y"
```

**TypeScript equivalent**

```ts
text.split(search).join(replaceWith)
```

- `text.replace(search, x)` with a string pattern replaces only the first occurrence.
- `text.replaceAll(search, replaceWith)` works too, but a replacement containing `$&`, `$1` or `$$` is interpreted specially; `split`/`join` (or a function replacement) avoids that.
- Escapes when porting: the Tines formula `REPLACE(x, "\\", "/")` searches for one backslash; in TS that string is also written `"\\"`. A formula `"\d"` is backslash + d, written `"\\d"` in TS.
- For regex-based replacement use REGEX_REPLACE.

## REPLACE_FIRST

- **Summary:** replace the first occurrence of a substring
- **Signature:** `REPLACE_FIRST(text, search, replace_with)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/replace-first/

**Arguments**

- `text` (required): Text.
- `search` (required): The text to find (literal, not a regex).
- `replace_with` (required): The replacement text.

**Returns:** Text with the first occurrence replaced.

**Porting semantics**

- Case-sensitive literal match (see REPLACE).
- Not specified in docs: null input; search text not present (presumably unchanged).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REPLACE_FIRST("a-b-c", "-", "+")
output:  "a+b-c"

# 2 - the replacement is literal
formula: REPLACE_FIRST("cost: 5", "5", "$&$&")
output:  "cost: $&$&"
```

**TypeScript equivalent**

```ts
text.replace(search, () => replaceWith)
```

- Pass the replacement as a function: a replacement string containing `$&`, `$1` or `$$` is interpreted specially by JS.

## RSTRIP

- **Summary:** remove trailing whitespace
- **Signature:** `RSTRIP(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rstrip/

**Arguments**

- `text` (required): Text.

**Returns:** Text with all whitespace (tabs, spaces, newlines) removed from the right side. Leading whitespace is untouched.

**Porting semantics**

- Not specified in docs: null input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RSTRIP("  right pad \n")
output:  "  right pad"
```

**TypeScript equivalent**

```ts
text.trimEnd()
```

## SIZE

- **Summary:** length of text or of an array
- **Signature:** `SIZE(text_or_array)`
- **Categories:** Text, Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/size/

**Arguments**

- `text_or_array` (required): Text or an array.

**Returns:** How many characters the text has, or how many elements the array has.

**Porting semantics**

- The docs display the result in quotes; the described behaviour is a count, so port it as a number.
- Not specified in docs: objects (number of keys?); null input; numbers.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SIZE("depot-7")
output:  7

# 2
formula: SIZE([10, 20, 30])
output:  3

# 3
formula: SIZE([])
output:  0
```

**TypeScript equivalent**

```ts
Array.isArray(v) ? v.length : [...String(v)].length
```

- `string.length` counts UTF-16 code units, so emoji and other astral characters count double; spreading counts code points.
- `null.length` throws; Tines behaviour for null is not specified - use `(v ?? []).length` only if you have confirmed what the story expects.

## SLICE

- **Summary:** 1 or `length` characters of text from a start index
- **Signature:** `SLICE(text, start_index, [length])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/slice/

**Arguments**

- `text` (required): Text.
- `start_index` (required): Zero-based position. A negative value counts from the end of the text.
- `length` (optional): Number of characters to return. If omitted, exactly 1 character is returned.

**Returns:** Text. A length that runs beyond the end simply stops at the end.

**Porting semantics**

- Without a length the result is one single character, not the rest of the text.
- The third argument is a length, not an end index.
- Not specified in docs: start index beyond the end; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - no length: one character
formula: SLICE("tracking-88", 9)
output:  "8"

# 2
formula: SLICE("tracking-88", 0, 5)
output:  "track"

# 3
formula: SLICE("tracking-88", -2, 2)
output:  "88"
```

**TypeScript equivalent**

```ts
function slice(text: string, start: number, length = 1): string {
  const s = start < 0 ? Math.max(0, text.length + start) : start;
  return text.substring(s, s + length);
}
```

- `text.slice(6)` is wrong: JS returns the rest of the string (`"world"`), Tines returns one character (`"w"`).
- `text.slice(start, length)` is wrong: JS expects an end index.

## SPLIT

- **Summary:** split text into an array by a delimiter
- **Signature:** `SPLIT(text, delimiter)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/split/

**Arguments**

- `text` (required): Text to split.
- `delimiter` (required): Separator text (literal).

**Returns:** Array of text pieces.

**Porting semantics**

- An empty delimiter splits the text into single characters.
- Not specified in docs: whether trailing empty pieces are kept (`"a,b,"`); null input; regex delimiters.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SPLIT("2025-09-08", "-")
output:  ["2025", "09", "08"]

# 2
formula: SPLIT("abc", "")
output:  ["a", "b", "c"]
```

**TypeScript equivalent**

```ts
text.split(delimiter)
```

- JS keeps trailing empty strings (`"a,b,".split(",")` is `["a","b",""]`); whether Tines does is not specified - check if the story depends on the element count.
- `"".split(",")` is `[""]` in JS (one empty element), not `[]`.

## STARTS_WITH

- **Summary:** true if text begins with a prefix
- **Signature:** `STARTS_WITH(text, prefix)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/starts-with/

**Arguments**

- `text` (required): Text to test.
- `prefix` (required): Prefix to look for.

**Returns:** Boolean.

**Porting semantics**

- The comparison is case-sensitive.
- The docs display the result in quotes, as if it were text; the described behaviour is a true/false value, so port it as a boolean.
- Not specified in docs: null input; non-text input; empty prefix.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STARTS_WITH("INV-4471", "INV-")
output:  true

# 2 - case matters
formula: STARTS_WITH("inv-4471", "INV-")
output:  false
```

**TypeScript equivalent**

```ts
text.startsWith(prefix)
```

## STRIP

- **Summary:** remove leading and trailing whitespace
- **Signature:** `STRIP(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/strip/

**Arguments**

- `text` (required): Text.

**Returns:** The text without leading and trailing whitespace (spaces, tabs, line breaks). Whitespace inside the text is kept.

**Porting semantics**

- Not specified in docs: null input; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STRIP("  \tkeep  inner  \n")
output:  "keep  inner"
```

**TypeScript equivalent**

```ts
text.trim()
```

## STRIP_HTML

- **Summary:** remove HTML tags from text
- **Signature:** `STRIP_HTML(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/strip-html/

**Arguments**

- `text` (required): Text containing HTML.

**Returns:** The text with markup tags removed; the text between tags stays.

**Porting semantics**

- Not specified in docs: whether entities are decoded; treatment of `<script>`/`<style>` contents and comments; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STRIP_HTML("<li>Check <b>valve</b> 3</li>")
output:  "Check valve 3"
```

**TypeScript equivalent** (APPROXIMATE: regex tag stripping; does not decode entities or drop script/style contents)

```ts
text.replace(/<[^>]*>/g, "")
```

## STRIP_NEWLINES

- **Summary:** remove newline characters from text
- **Signature:** `STRIP_NEWLINES(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/strip-newlines/

**Arguments**

- `text` (required): Text.

**Returns:** The text with its line breaks removed; nothing is put in their place.

**Porting semantics**

- Not specified in docs: whether carriage returns (`\r`) are also removed; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STRIP_NEWLINES("row one\nrow two\n")
output:  "row onerow two"
```

**TypeScript equivalent**

```ts
text.replace(/\r?\n/g, "")
```
