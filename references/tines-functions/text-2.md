# Tines formula functions: Text (part 2 of 7: ESTIMATED_TOKEN_COUNT to IS_JSON)

Independent, unofficial porting notes for the functions Tines files under "Text": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: ESTIMATED_TOKEN_COUNT, FORCE_ARRAY, HTML_DECODE, HTML_ENCODE, INCLUDES, IS_BLANK, IS_EMAIL, IS_EMPTY, IS_JSON

## ESTIMATED_TOKEN_COUNT

- **Summary:** estimate LLM token count of the input
- **Signature:** `ESTIMATED_TOKEN_COUNT(input)`
- **Categories:** Text, Objects, Arrays, Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/estimated-token-count/

**Arguments**

- `input` (required): Text, object, array or number.

**Returns:** Number: a rough count of the tokens the input would take in a Claude 3 model. It comes from an older tokenizer and is not exact.

**Porting semantics**

- Raises an error once the input is longer than one million characters.
- Not specified in docs: how non-text input is serialised before counting.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ESTIMATED_TOKEN_COUNT("Restart the print queue")
output:  a small number (the helper gives 6; Tines' own estimate may differ)
```

**TypeScript equivalent** (APPROXIMATE: there is no offline equivalent of the tokenizer; this is a rough characters/4 heuristic and will differ from Tines by a token or more even on short text)

```ts
function estimatedTokenCount(input: unknown): number {
  const s = typeof input === "string" ? input : JSON.stringify(input);
  if (s.length > 1_000_000) throw new Error("ESTIMATED_TOKEN_COUNT: input is longer than 1,000,000 characters");
  return Math.ceil(s.length / 4);
}
```

- Only use for coarse size checks (e.g. "is this too big to send to a model").

## FORCE_ARRAY

- **Summary:** wrap a value in an array unless it already is one
- **Signature:** `FORCE_ARRAY(anything)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/force-array/

**Arguments**

- `anything` (required): Any value.

**Returns:** The argument itself if it is an array, otherwise an array containing it.

**Porting semantics**

- `NULL`, including a reference to a key that does not exist, gives an empty array, not an array holding null.
- Not specified in docs: whether `""` or `{}` are wrapped or treated like null.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FORCE_ARRAY("solo")
output:  ["solo"]

# 2
formula: FORCE_ARRAY(["a", "b"])
output:  ["a", "b"]

# 3
formula: FORCE_ARRAY(order.missing_key)
output:  []
```

**TypeScript equivalent**

```ts
Array.isArray(anything) ? anything : anything == null ? [] : [anything]
```

- `[x].flat()` and lodash `castArray` are wrong for null: they give `[null]`.

## HTML_DECODE

- **Summary:** convert HTML entities back to characters
- **Signature:** `HTML_DECODE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/html-decode/

**Arguments**

- `text` (required): Text containing escaped characters.

**Returns:** Text with entities such as `&lt;` and `&gt;` converted to the characters they represent.

**Porting semantics**

- Not specified in docs: which entities are supported (named, numeric); null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HTML_DECODE("&lt;b&gt;R&amp;D&lt;/b&gt;")
output:  "<b>R&D</b>"
```

**TypeScript equivalent**

```ts
import { decode } from "he";
decode(text)
```

- npm package: `he`. Dependency-free alternative for the five basic entities: `text.replace(/&(lt|gt|amp|quot|#39);/g, (_m, e) => ({ lt: "<", gt: ">", amp: "&", quot: '"', "#39": "'" } as any)[e])`.

## HTML_ENCODE

- **Summary:** escape HTML syntax characters
- **Signature:** `HTML_ENCODE(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/html-encode/

**Arguments**

- `text` (required): Text.

**Returns:** Text in which the characters that have a meaning in HTML markup are replaced by entities.

**Porting semantics**

- Non-ASCII letters such as `é` are left as they are (per the description).
- Not specified in docs: whether quotes (`"` and `'`) are escaped; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - accented letters are untouched
formula: HTML_ENCODE("<em>café</em>")
output:  "&lt;em&gt;café&lt;/em&gt;"
```

**TypeScript equivalent**

```ts
const ENT: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const htmlEncode = (text: string): string => text.replace(/[&<>"']/g, (c) => ENT[c]);
```

- Escaping the two quote characters is an assumption (the docs only show `<` and `>`).
- Do not use `he.encode()`: it turns `é` into `&#xE9;`, which contradicts the docs.

## INCLUDES

- **Summary:** true if text/array/object includes a value
- **Signature:** `INCLUDES(target, value)`
- **Categories:** Text, Objects, Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/includes/

**Arguments**

- `target` (required): Text, an array, or an object.
- `value` (required): The value to look for.

**Returns:** Boolean `TRUE`/`FALSE`.

**Porting semantics**

- On text: true when the value occurs somewhere inside it. Case matters; lower-case both sides first for a case-insensitive test.
- On an array: true only when some element equals the value as a whole; a partial match inside an element does not count.
- On an object: true when the value is one of its keys (the keys are searched, not the values).
- Not specified in docs: null target; number vs numeric text (`1` vs `"1"`); matching objects inside arrays.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: INCLUDES("warehouse-7", "house")
output:  true

# 2 - no element equals it
formula: INCLUDES(["warehouse-7", "dock"], "house")
output:  false

# 3
formula: INCLUDES({sku: "A-1", qty: 4}, "qty")
output:  true
```

**TypeScript equivalent**

```ts
const includes = (target: any, value: any): boolean =>
  typeof target === "string" || Array.isArray(target) ? target.includes(value) : target != null && Object.hasOwn(target, value);
```

- `includes` on arrays uses strict identity for objects.
- Returning `false` for a null target is an assumption.

## IS_BLANK

- **Summary:** true for FALSE, "", [], {}, NULL
- **Signature:** `IS_BLANK(any)`
- **Categories:** Text, Objects, Arrays, Logic, Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-blank/

**Arguments**

- `any` (required): Any value.

**Returns:** Boolean: true if the value is `FALSE`, `""`, `[]`, `{}` or `NULL`; false otherwise.

**Porting semantics**

- Numbers are never blank, `0` included.
- A reference to a key that does not exist evaluates to null, hence blank.
- IS_PRESENT is the exact opposite. IS_EMPTY is narrower (only `""`, `[]`, `{}`).
- The result is a plain boolean.
- Not specified in docs: whether text made only of spaces is blank. WHERE treats such a value as absent, which hints that it is, but the IS_BLANK page lists only the empty text..

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_BLANK([])
output:  true

# 2 - a number is never blank
formula: IS_BLANK(0)
output:  false

# 3
formula: IS_BLANK(FALSE)
output:  true
```

**TypeScript equivalent**

```ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
```

- `!value` is wrong in both directions: it is true for `0` (not blank in Tines) and false for `[]` and `{}` (blank in Tines).
- To also treat whitespace-only text as blank, replace `v === ""` with `(typeof v === "string" && v.trim() === "")`.

## IS_EMAIL

- **Summary:** check that text looks like an email address
- **Signature:** `IS_EMAIL(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-email/

**Arguments**

- `text` (required): Text to check.
- `strict_tld` (optional): Keyword argument that appears only in a docs example, not in the documented signature. When on, the part after the `@` must contain a top-level domain.

**Returns:** Boolean. Follows "the email standard"; does not guarantee the address is valid.

**Porting semantics**

- By default a domain without a dot is accepted, and text without an `@` is rejected.
- Not specified in docs: the exact validation rules; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_EMAIL("ops@example.org")
output:  true

# 2
formula: IS_EMAIL("ops@intranet")
output:  true

# 3
formula: IS_EMAIL("ops@intranet", strict_tld: TRUE)
output:  false
```

**TypeScript equivalent** (APPROXIMATE: simple pattern check, not the full email standard)

```ts
const isEmail = (text: unknown, strictTld = false): boolean =>
  typeof text === "string" && (strictTld ? /^[^\s@]+@[^\s@]+\.[^\s@.]+$/ : /^[^\s@]+@[^\s@]+$/).test(text);
```

## IS_EMPTY

- **Summary:** true for "", [], {}
- **Signature:** `IS_EMPTY(text | array | object)`
- **Categories:** Text, Objects, Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-empty/

**Arguments**

- `text | array | object` (required): Target value; must be text, an array, or an object.

**Returns:** Boolean: true if the value is `""`, `[]` or `{}`; false otherwise.

**Porting semantics**

- Narrower than IS_BLANK: `NULL` and `FALSE` are not counted as empty.
- The result is a plain boolean.
- Not specified in docs: behaviour for null, booleans or numbers (only text, arrays and objects are said to be accepted).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_EMPTY({})
output:  true

# 2 - a space is not empty
formula: IS_EMPTY(" ")
output:  false
```

**TypeScript equivalent**

```ts
function isEmpty(v: unknown): boolean {
  if (typeof v === "string" || Array.isArray(v)) return v.length === 0;
  if (v !== null && typeof v === "object") return Object.keys(v).length === 0;
  throw new Error("IS_EMPTY: value must be text, an array or an object"); // assumption: other types are not specified in docs
}
```

- The throw for null, booleans and numbers is an assumption chosen to fail loudly; use IS_BLANK semantics if the value may be missing.

## IS_JSON

- **Summary:** check that text is valid JSON
- **Signature:** `IS_JSON(text)`
- **Categories:** Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-json/

**Arguments**

- `text` (required): Text to check.

**Returns:** Boolean.

**Porting semantics**

- Not specified in docs: whether bare scalars (`"123"`, `"null"`, `"\"x\""`) count as valid JSON; non-text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_JSON('{"qty": [1, 2]}')
output:  true

# 2
formula: IS_JSON("{qty: 1")
output:  false
```

**TypeScript equivalent**

```ts
const isJson = (text: unknown): boolean => {
  if (typeof text !== "string") return false;
  try { JSON.parse(text); return true; } catch { return false; }
};
```

- `JSON.parse` accepts bare scalars such as `123`; whether Tines does is not specified.
