# Tines formula functions: Text (part 6 of 7: TEXT to TO_MARKDOWN_STRIKE)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: TEXT, TITLEIZE, TO_MARKDOWN_BLOCKQUOTE, TO_MARKDOWN_BOLD, TO_MARKDOWN_CALLOUT, TO_MARKDOWN_CODEBLOCK, TO_MARKDOWN_HEADING, TO_MARKDOWN_ITALIC, TO_MARKDOWN_LIST, TO_MARKDOWN_STRIKE

## TEXT

- **Summary:** convert a value to text
- **Signature:** `TEXT(value)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/text/

**Arguments**

- `value` (required): Any value.

**Returns:** Text. `100` gives `"100"`.

**Porting semantics**

- Objects are rendered in the legacy `{"key"=>"value"}` format, which is not valid JSON (stated on the LEGACY_STRINGIFY page). Use TO_JSON for JSON text.
- Not specified in docs: rendering of null, booleans, arrays and decimals.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TEXT(250)
output:  "250"

# 2 - Ruby-style notation, not JSON
formula: TEXT({sku: "A-1"})
output:  "{\"sku\"=>\"A-1\"}"
```

**TypeScript equivalent** (APPROXIMATE: rendering of anything other than numbers and flat objects is assumed)

```ts
const legacyStringify = (v: any): string =>
  v === null || v === undefined ? "nil"
  : Array.isArray(v) ? `[${v.map(legacyStringify).join(", ")}]`
  : typeof v === "object" ? `{${Object.entries(v).map(([k, x]) => `${JSON.stringify(k)}=>${legacyStringify(x)}`).join(", ")}}`
  : typeof v === "string" ? JSON.stringify(v) : String(v);
// Named textFn so it is not confused with text(), the helper for pills and "&" (which gives JSON for objects).
const textFn = (v: unknown): string =>
  typeof v === "string" ? v : v == null ? "" : typeof v === "object" ? legacyStringify(v) : String(v);
```

- For numbers and strings this is just `String(value)`.
- `String(obj)` gives `[object Object]` and `String(null)` gives `"null"`; neither matches Tines. Rendering null as `""` here is an assumption.

## TITLEIZE

- **Summary:** capitalize each word and prettify separators
- **Signature:** `TITLEIZE(text, [keep_id_suffix: FALSE])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/titleize/

**Arguments**

- `text` (required): Text.
- `keep_id_suffix` (optional): Keyword argument, off by default: a trailing `_id` is dropped. Turn it on to keep it as a word.

**Returns:** Text with every word capitalised; underscores and camelCase boundaries become spaces.

**Porting semantics**

- Not specified in docs: the full list of characters replaced; handling of hyphens, acronyms and apostrophes; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TITLEIZE("lastLoginTime")
output:  "Last Login Time"

# 2
formula: TITLEIZE("customer_id")
output:  "Customer"

# 3
formula: TITLEIZE("customer_id", keep_id_suffix: TRUE)
output:  "Customer Id"
```

**TypeScript equivalent** (APPROXIMATE: covers the documented cases (spaces, underscores, camelCase, _id suffix); other inputs follow this helper's own rules)

```ts
function titleize(text: string, keepIdSuffix = false): string {
  let s = text.replace(/([a-z\d])([A-Z])/g, "$1_$2").toLowerCase();
  if (!keepIdSuffix) s = s.replace(/_id$/, "");
  return s.replace(/[_-]+/g, " ").replace(/(^\s*\S)/g, (c) => c.toUpperCase()).replace(/\s[a-z]/g, (c) => c.toUpperCase());
}
```

## TO_MARKDOWN_BLOCKQUOTE

- **Summary:** quote text as a markdown blockquote
- **Signature:** `TO_MARKDOWN_BLOCKQUOTE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-blockquote/

**Arguments**

- `text` (required): Text; may span multiple lines.

**Returns:** The text with `> ` in front of every line. Blank input gives empty text.

**Porting semantics**

- Not specified in docs: prefix used for empty lines inside the text; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_BLOCKQUOTE("Valve 3 leaking\nCrew notified")
output:  "> Valve 3 leaking\n> Crew notified"

# 2
formula: TO_MARKDOWN_BLOCKQUOTE("   ")
output:  ""
```

**TypeScript equivalent**

```ts
const toMarkdownBlockquote = (text: unknown): string =>
  text == null || String(text).trim() === "" ? "" : String(text).split("\n").map((l) => `> ${l}`).join("\n");
```

## TO_MARKDOWN_BOLD

- **Summary:** wrap text in markdown bold markers
- **Signature:** `TO_MARKDOWN_BOLD(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-bold/

**Arguments**

- `text` (required): Text.

**Returns:** The trimmed text between double asterisks. Blank input gives empty text.

**Porting semantics**

- Not specified in docs: text that already contains `**`; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_BOLD("  High priority ")
output:  "**High priority**"

# 2
formula: TO_MARKDOWN_BOLD("")
output:  ""
```

**TypeScript equivalent**

```ts
const toMarkdownBold = (text: unknown): string => { const t = String(text ?? "").trim(); return t === "" ? "" : `**${t}**`; };
```

## TO_MARKDOWN_CALLOUT

- **Summary:** wrap text in a markdown callout (GitHub alert)
- **Signature:** `TO_MARKDOWN_CALLOUT(text, [type])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-callout/

**Arguments**

- `text` (required): Text; may span multiple lines.
- `type` (optional): The callout kind; `NOTE` when omitted. It has to be one word made of letters only (TIP and WARNING are typical) and is converted to upper case.

**Returns:** A first line of the form `> [!TYPE]`, then the text with `> ` in front of every line. Blank input gives just the first line.

**Porting semantics**

- Not specified in docs: behaviour for an invalid type (not a single word of letters).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_CALLOUT("Pump offline until 14:00")
output:  "> [!NOTE]\n> Pump offline until 14:00"

# 2
formula: TO_MARKDOWN_CALLOUT("Check seals\nthen restart", "tip")
output:  "> [!TIP]\n> Check seals\n> then restart"
```

**TypeScript equivalent**

```ts
function toMarkdownCallout(text: unknown, type = "NOTE"): string {
  if (!/^[A-Za-z]+$/.test(type)) throw new Error("TO_MARKDOWN_CALLOUT: type has to be one alphabetic word");
  const title = `> [!${type.toUpperCase()}]`, t = String(text ?? "");
  return t.trim() === "" ? title : [title, ...t.split("\n").map((l) => `> ${l}`)].join("\n");
}
```

- Throwing on an invalid type is an assumption.

## TO_MARKDOWN_CODEBLOCK

- **Summary:** wrap text in a markdown code fence
- **Signature:** `TO_MARKDOWN_CODEBLOCK(text, [language])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-codeblock/

**Arguments**

- `text` (required): The code/text.
- `language` (optional): Language name for syntax highlighting.

**Returns:** The text wrapped in a fence: `` ```language ``, newline, text, newline, `` ``` ``.

**Porting semantics**

- The fence grows when needed: it is always longer than any backtick sequence inside the text, so text that contains its own fenced block stays inside the outer one.
- Not specified in docs: blank text; trailing newline handling.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_CODEBLOCK("SELECT 1;", "sql")
output:  "```sql\nSELECT 1;\n```"

# 2 - four backticks inside, so a five-backtick fence
formula: TO_MARKDOWN_CODEBLOCK("a ```` b")
output:  "`````\na ```` b\n`````"
```

**TypeScript equivalent**

```ts
function toMarkdownCodeblock(text: string, language = ""): string {
  const longest = Math.max(0, ...(text.match(/`+/g) ?? []).map((r) => r.length));
  const fence = "`".repeat(Math.max(3, longest + 1));
  return `${fence}${language}\n${text}\n${fence}`;
}
```

## TO_MARKDOWN_HEADING

- **Summary:** turn text into a markdown heading line
- **Signature:** `TO_MARKDOWN_HEADING(text, [level])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-heading/

**Arguments**

- `text` (required): Heading text.
- `level` (optional): Heading depth from 1 to 6, as a whole number; 1 when omitted.

**Returns:** `#` repeated `level` times, a space, then the text with whitespace collapsed (embedded newlines become spaces).

**Porting semantics**

- Not specified in docs: behaviour for a level outside 1..6; blank text.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_HEADING("Shift report")
output:  "# Shift report"

# 2 - whitespace collapses to single spaces
formula: TO_MARKDOWN_HEADING("Open\n  items", 3)
output:  "### Open items"
```

**TypeScript equivalent**

```ts
function toMarkdownHeading(text: unknown, level = 1): string {
  if (!Number.isInteger(level) || level < 1 || level > 6) throw new Error("TO_MARKDOWN_HEADING: level has to be an integer from 1 to 6");
  return `${"#".repeat(level)} ${String(text ?? "").trim().replace(/\s+/g, " ")}`;
}
```

- Throwing on an invalid level is an assumption.

## TO_MARKDOWN_ITALIC

- **Summary:** wrap text in markdown italic markers
- **Signature:** `TO_MARKDOWN_ITALIC(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-italic/

**Arguments**

- `text` (required): Text.

**Returns:** The trimmed text between underscores (not asterisks). Blank input gives empty text.

**Porting semantics**

- Not specified in docs: non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_ITALIC(" pending review ")
output:  "_pending review_"
```

**TypeScript equivalent**

```ts
const toMarkdownItalic = (text: unknown): string => { const t = String(text ?? "").trim(); return t === "" ? "" : `_${t}_`; };
```

## TO_MARKDOWN_LIST

- **Summary:** turn an array into a markdown list
- **Signature:** `TO_MARKDOWN_LIST(array, [ordered: FALSE])`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-list/

**Arguments**

- `array` (required): Array of items.
- `ordered` (optional): Keyword argument, default `FALSE` (bulleted with `- `). `TRUE` gives a numbered list (`1. `, `2. `, ...).

**Returns:** One line per item, joined with line breaks and without a trailing one; runs of whitespace inside an item become one space. No items gives empty text.

**Porting semantics**

- Not specified in docs: rendering of non-text items (objects, nested arrays, null).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_LIST(["Drain tank", "Swap  filter"])
output:  "- Drain tank\n- Swap filter"

# 2
formula: TO_MARKDOWN_LIST(["Drain tank", "Swap filter"], ordered: TRUE)
output:  "1. Drain tank\n2. Swap filter"
```

**TypeScript equivalent**

```ts
const toMarkdownList = (array: unknown[], ordered = false): string =>
  array.map((v, i) => `${ordered ? `${i + 1}.` : "-"} ${String(v).trim().replace(/\s+/g, " ")}`).join("\n");
```

## TO_MARKDOWN_STRIKE

- **Summary:** wrap text in markdown strikethrough markers
- **Signature:** `TO_MARKDOWN_STRIKE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/to-markdown-strike/

**Arguments**

- `text` (required): Text.

**Returns:** The trimmed text between double tildes. Blank input gives empty text.

**Porting semantics**

- Not specified in docs: non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TO_MARKDOWN_STRIKE("old price")
output:  "~~old price~~"
```

**TypeScript equivalent**

```ts
const toMarkdownStrike = (text: unknown): string => { const t = String(text ?? "").trim(); return t === "" ? "" : `~~${t}~~`; };
```
