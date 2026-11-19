# Tines formula functions: Objects (part 2 of 2: REMOVE_KEY to VALUES)

Independent, unofficial porting notes for the functions Tines files under "Objects": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: REMOVE_KEY, SET_KEY, UNFLATTEN_JSON, VALUES

## REMOVE_KEY

- **Summary:** remove a key (by dotted path) from an object
- **Signature:** `REMOVE_KEY(object, path)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/remove-key/

**Arguments**

- `object` (required): The object.
- `path` (required): The key to remove, or a dot-separated path to it. A dot that belongs to a key name is written with a backslash in front.

**Returns:** The object without that key.

**Porting semantics**

- Not specified in docs: path that does not exist (presumably unchanged); array indexes in the path; whether the input is modified (treat as non-mutating).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REMOVE_KEY({id: 7, ship: {city: "Oslo", zip: "0150"}}, "ship.zip")
output:  {"id": 7, "ship": {"city": "Oslo"}}

# 2 - escaped dot
formula: REMOVE_KEY({"v1.2": "old", name: "x"}, "v1\.2")
output:  {"name": "x"}
```

**TypeScript equivalent**

```ts
const splitPath = (path: string): string[] => path.split(/(?<!\\)\./).map((k) => k.replace(/\\\./g, "."));
function removeKey(object: any, path: string): any {
  const out = structuredClone(object), keys = splitPath(path), last = keys.pop()!;
  const parent = keys.reduce((o, k) => (o == null ? o : o[k]), out);
  if (parent != null && typeof parent === "object") delete parent[last];
  return out;
}
```

- With a literal top-level key use rest destructuring: `const { email, ...rest } = person;`.
- `delete obj.key` on the original mutates data other steps may still read; clone first as above.
- A backslash in the path must be doubled in TS source: the path `meta.file\.ext` is written `"meta.file\\.ext"`.

## SET_KEY

- **Summary:** set a key (by dotted path) on an object
- **Signature:** `SET_KEY(object, path, value)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/set-key/

**Arguments**

- `object` (required): The object.
- `path` (required): The key to set, or a dot-separated path for a nested key. A dot that belongs to a key name is written with a backslash in front.
- `value` (required): The value to set.

**Returns:** The object with the key set. An existing key is overwritten; a new key is added.

**Porting semantics**

- Not specified in docs: whether missing intermediate objects are created; array indexes in the path; whether the input is modified (treat as non-mutating).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SET_KEY({sku: "A-1"}, "qty", 4)
output:  {"sku": "A-1", "qty": 4}

# 2
formula: SET_KEY({ship: {city: "Oslo"}}, "ship.city", "Bergen")
output:  {"ship": {"city": "Bergen"}}

# 3 - escaped dot: one key, not a path
formula: SET_KEY({}, "v1\.2", "new")
output:  {"v1.2": "new"}
```

**TypeScript equivalent**

```ts
const splitPath = (path: string): string[] => path.split(/(?<!\\)\./).map((k) => k.replace(/\\\./g, "."));
function setKey(object: any, path: string, value: any): any {
  const out = structuredClone(object ?? {}), keys = splitPath(path), last = keys.pop()!;
  let o = out;
  for (const k of keys) o = o[k] = typeof o[k] === "object" && o[k] !== null ? o[k] : {};
  o[last] = value;
  return out;
}
```

- With a literal top-level key use spread: `{ ...object, bin: "R2" }`.
- Creating missing intermediate objects is an assumption.

## UNFLATTEN_JSON

- **Summary:** rebuild nested JSON from single-level dotted keys
- **Signature:** `UNFLATTEN_JSON(object, [separator])`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/unflatten-json/

**Arguments**

- `object` (required): A one-level object whose keys are joined paths.
- `separator` (optional): Key separator; default is a period (`.`).

**Returns:** The nested structure. A path segment that is a whole number is treated as an array position.

**Porting semantics**

- Not specified in docs: conflicting keys (`a` and `a.b`); sparse indexes.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UNFLATTEN_JSON({"order.id": 7, "order.lines.0.sku": "A-1", "order.lines.1.sku": "B-9"})
output:  {"order": {"id": 7, "lines": [{"sku": "A-1"}, {"sku": "B-9"}]}}
```

**TypeScript equivalent**

```ts
import { unflatten } from "flat";
unflatten(object)                        // default separator "."
unflatten(object, { delimiter: sep })    // custom separator
```

- npm package: `flat`.

## VALUES

- **Summary:** array of an object's values
- **Signature:** `VALUES(object)`
- **Categories:** Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/values/

**Arguments**

- `object` (required): The object.

**Returns:** Array of all the values of the object.

**Porting semantics**

- Not specified in docs: order; null or non-object input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: VALUES({sku: "A-1", qty: 4})
output:  ["A-1", 4]
```

**TypeScript equivalent**

```ts
Object.values(object)
```

- `Object.values(null)` throws.
