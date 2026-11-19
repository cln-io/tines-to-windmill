# Tines formula functions: Objects (part 1 of 2: DEEP_MERGE to OBJECT)

Independent, unofficial porting notes for the functions Tines files under "Objects": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: DEEP_MERGE, FLATTEN_JSON, GET, IS_VALID_JSON_SCHEMA, JSONPATH, JSON_SCHEMA_VALIDATE, KEYS, MERGE, OBJECT

## DEEP_MERGE

- **Summary:** recursively merge two or more objects
- **Signature:** `DEEP_MERGE(object, object, ...)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/deep-merge/

**Arguments**

- `object, object, ...` (required): Two or more objects.

**Returns:** A new object. Nested objects are merged recursively; on key collisions the last value is used.

**Porting semantics**

- Not specified in docs: how arrays inside the objects are combined (replaced vs concatenated); null arguments; non-object arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DEEP_MERGE({ship: {city: "Oslo"}, qty: 1}, {ship: {zip: "0150"}, qty: 2})
output:  {"ship": {"city": "Oslo", "zip": "0150"}, "qty": 2}
```

**TypeScript equivalent**

```ts
const isObj = (v: unknown): v is Record<string, any> => typeof v === "object" && v !== null && !Array.isArray(v);
function deepMerge(...objs: Record<string, any>[]): Record<string, any> {
  return objs.reduce((acc, o) => {
    for (const [k, v] of Object.entries(o ?? {})) acc[k] = isObj(acc[k]) && isObj(v) ? deepMerge(acc[k], v) : v;
    return acc;
  }, {} as Record<string, any>);
}
```

- `{...a, ...b}` is a shallow merge (that is MERGE): a nested object from `a` would be replaced wholesale instead of combined.
- This helper replaces arrays wholesale (last wins) - an assumption.

## FLATTEN_JSON

- **Summary:** flatten nested data to one level of dotted keys
- **Signature:** `FLATTEN_JSON(object, [separator])`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/flatten-json/

**Arguments**

- `object` (required): Nested object.
- `separator` (optional): Key separator; default is a period (`.`).

**Returns:** A new object one level deep, whose keys are the joined paths.

**Porting semantics**

- An array element contributes its zero-based position as a path segment.
- Not specified in docs: how empty objects/arrays are represented; keys that already contain the separator.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FLATTEN_JSON({order: {id: 7, lines: [{sku: "A-1"}, {sku: "B-9"}]}})
output:  {"order.id": 7, "order.lines.0.sku": "A-1", "order.lines.1.sku": "B-9"}

# 2
formula: FLATTEN_JSON({a: {b: 1}}, "/")
output:  {"a/b": 1}
```

**TypeScript equivalent**

```ts
import { flatten } from "flat";
flatten(object)                        // default separator "."
flatten(object, { delimiter: sep })    // custom separator
```

- npm package: `flat`. It keeps an empty object or array as the value of its key; what Tines does there is not specified.

## GET

- **Summary:** read a value from an object by key or dotted path
- **Signature:** `GET(object, path)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/get/

**Arguments**

- `object` (required): The object to read from.
- `path` (required): One key, or several joined with dots. A key containing a space is written in brackets and quotes, as in `'owner["Full Name"]'`.

**Returns:** The value at the path.

**Porting semantics**

- Not specified in docs: result when the path does not exist; array indexes inside the path; null object.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: GET({ship: {city: "Oslo"}}, "ship.city")
output:  "Oslo"

# 2
formula: GET({owner: {"Full Name": "Ada Park"}}, 'owner["Full Name"]')
output:  "Ada Park"
```

**TypeScript equivalent**

```ts
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
```

- Path forms handled: `a.b.c`, `a[0].b`, `owner["Full Name"]`. Keys containing dots or quotes are not.
- This helper returns `null` for a missing path (an assumption, in line with a reference to a missing key evaluating to null).
- When the path is a literal you can inline it: `GET(x, "ship.city")` is `x?.ship?.city ?? null`.
- npm alternative: `import { get } from "lodash"` understands the same path syntax (returns `undefined` when missing).

## IS_VALID_JSON_SCHEMA

- **Summary:** true if a value matches a JSON schema
- **Signature:** `IS_VALID_JSON_SCHEMA(schema, value)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/is-valid-json-schema/

**Arguments**

- `schema` (required): The JSON Schema (object). Passed first.
- `value` (required): The value to check. Passed second.

**Returns:** Boolean.

**Porting semantics**

- Not specified in docs: supported JSON Schema draft; behaviour for an invalid schema.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IS_VALID_JSON_SCHEMA({type: "object", required: ["sku"]}, {sku: "A-1"})
output:  true

# 2
formula: IS_VALID_JSON_SCHEMA({type: "array", maxItems: 2}, [1, 2, 3])
output:  false
```

**TypeScript equivalent**

```ts
import Ajv from "ajv";
new Ajv({ strict: false, allErrors: true }).validate(schema, value) as boolean
```

- npm package: `ajv`. Argument order is schema first, value second in both Tines and ajv.

## JSONPATH

- **Summary:** evaluate a JSONPath expression against data
- **Signature:** `JSONPATH(object, path)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/jsonpath/

**Arguments**

- `object` (required): The data (escaped JSON text or non-escaped JSON are both supported).
- `path` (required): JSONPath expression; wildcards, filters and slices are supported.

**Returns:** The matching values; an array when the path selects several.

**Porting semantics**

- Tines evaluates with an old release (0.9.9) of the Ruby JSONPath library, so newer JSONPath features may be missing.
- Not specified in docs: result when nothing matches; whether a single match is still wrapped in an array.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: JSONPATH({lines: [{sku: "A-1", qty: 4}, {sku: "B-9", qty: 12}]}, "$.lines[*].sku")
output:  ["A-1", "B-9"]
```

**TypeScript equivalent** (APPROXIMATE: jsonpath-plus implements a different JSONPath dialect; filters and edge cases may differ)

```ts
import { JSONPath } from "jsonpath-plus";
JSONPath({ path, json: typeof object === "string" ? JSON.parse(object) : object })
```

- npm package: `jsonpath-plus`. For simple paths prefer plain code: `$.lines[*].sku` is `obj.lines.map((l) => l.sku)`.

## JSON_SCHEMA_VALIDATE

- **Summary:** validation error message for a value against a JSON schema
- **Signature:** `JSON_SCHEMA_VALIDATE(schema, value)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/json-schema-validate/

**Arguments**

- `schema` (required): The JSON Schema (object). Passed first.
- `value` (required): The value to check. Passed second.

**Returns:** Text: empty when the value satisfies the schema, otherwise a message describing what is wrong.

**Porting semantics**

- The Tines message names the kind of value, its location in the data and the rule that failed.
- Not specified in docs: message when several errors exist; supported JSON Schema draft.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - valid, so empty text
formula: JSON_SCHEMA_VALIDATE({type: "object", required: ["sku"]}, {sku: "A-1"})
output:  ""

# 2
formula: JSON_SCHEMA_VALIDATE({type: "array", maxItems: 2}, [1, 2, 3])
output:  a non-empty message (wording differs between Tines and ajv)
```

**TypeScript equivalent** (APPROXIMATE: ajv's error wording differs from Tines' wording; only the empty-string-on-success contract is preserved)

```ts
import Ajv from "ajv";
function jsonSchemaValidate(schema: object, value: unknown): string {
  const ajv = new Ajv({ strict: false });
  return ajv.validate(schema, value) ? "" : ajv.errorsText();
}
```

- npm package: `ajv`. If the story displays or matches on the message text, the wording will differ.

## KEYS

- **Summary:** array of an object's keys
- **Signature:** `KEYS(object)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/keys/

**Arguments**

- `object` (required): The object.

**Returns:** Array of the keys present in the object.

**Porting semantics**

- Do not rely on the order of the returned keys: the Tines docs themselves show input and output in different orders.
- Not specified in docs: key order; null or non-object input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: KEYS({sku: "A-1"})
output:  ["sku"]
```

**TypeScript equivalent**

```ts
Object.keys(object)
```

- JS lists integer-like keys first in ascending order, then other keys in insertion order.
- `Object.keys(null)` throws.

## MERGE

- **Summary:** shallow-merge two or more objects
- **Signature:** `MERGE(object, object, ...)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/merge/

**Arguments**

- `object, object, ...` (required): Two or more objects.

**Returns:** A new object with the keys of all arguments. When a key occurs more than once, the value from the later argument is used.

**Porting semantics**

- Shallow: nested objects are replaced, not combined (use DEEP_MERGE for recursive merging).
- Not specified in docs: null or non-object arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MERGE({sku: "A-1", qty: 4}, {qty: 6, bin: "R2"})
output:  {"sku": "A-1", "qty": 6, "bin": "R2"}

# 2 - shallow: the nested object is replaced
formula: MERGE({ship: {city: "Oslo"}}, {ship: {zip: "0150"}})
output:  {"ship": {"zip": "0150"}}
```

**TypeScript equivalent**

```ts
{ ...object1, ...object2 }
```

- Spreading `null`/`undefined` is a no-op in JS; whether Tines accepts null here is not specified.

## OBJECT

- **Summary:** build an object from key/value arguments
- **Signature:** `OBJECT(key1, value1, key2, value2, ...)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/object/

**Arguments**

- `key1, value1, key2, value2, ...` (optional): Alternating keys and values.

**Returns:** An object built from the pairs. Called with no arguments it gives an empty object, handy as the starting value of a REDUCE.

**Porting semantics**

- A value may be any expression, including another function call.
- Not specified in docs: duplicate keys; an odd number of arguments; non-text keys.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: OBJECT("sku", "A-1", "qty", 2 + 2)
output:  {"sku": "A-1", "qty": 4}

# 2
formula: OBJECT()
output:  {}
```

**TypeScript equivalent**

```ts
({ [key1]: value1, [key2]: value2 })
// literal keys: OBJECT("city", c, "state", s)  ->  { city: c, state: s }
```

- Key order in the docs example output is alphabetised by the docs renderer; JS keeps insertion order.
