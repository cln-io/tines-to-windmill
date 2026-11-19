# Tines formula functions: Other

Independent, unofficial porting notes for the functions Tines files under "Other": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: TYPE

## TYPE

- **Summary:** type (Ruby class name) of a value as text
- **Signature:** `TYPE(value)`
- **Categories:** Other
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/type/

**Arguments**

- `value` (required): Any value.

**Returns:** The Ruby class name of the value, as text: one name for text, one each for whole and decimal numbers, for arrays, for objects, for each of the two booleans, and for null (the exact names are in the helper below).

**Porting semantics**

- These are Ruby names, not JS `typeof` names: an object is a "Hash", null is "NilClass", and true and false have separate names.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TYPE("depot")
output:  "String"

# 2
formula: TYPE(12.5)
output:  "Float"

# 3
formula: TYPE({sku: "A-1"})
output:  "Hash"
```

**TypeScript equivalent**

```ts
const tinesType = (v: unknown): string =>
  v === null || v === undefined ? "NilClass" : v === true ? "TrueClass" : v === false ? "FalseClass"
  : typeof v === "string" ? "String" : typeof v === "number" ? (Number.isInteger(v) ? "Integer" : "Float")
  : Array.isArray(v) ? "Array" : "Hash";
```

- Seen in a real story export (not in the docs): a formula comparing the result with `"Object"`, although the docs name objects `"Hash"`. If a formula tests for `"Object"`, translate it as "is a plain object" (`tinesType(x) === "Hash"`) and flag it.
- A comparison of the result with one of these names can also be rewritten natively, e.g. `typeof x === "string"` or `Array.isArray(x)`.
- JS cannot distinguish `1.0` from `1`: a decimal number holding a whole value reports the whole-number name here.
