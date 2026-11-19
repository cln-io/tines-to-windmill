# Tines formula functions: Arrays (part 4 of 4: UNION to WHERE)

Independent, unofficial porting notes for the functions Tines files under "Arrays": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: UNION, UNIQ, WHERE

## UNION

- **Summary:** merge two arrays without duplicates
- **Signature:** `UNION(array1, array2)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/union/

**Arguments**

- `first` (required): First array.
- `second` (required): Second array.

**Returns:** One array holding the elements of both without repeats, in the order the arrays were given.

**Porting semantics**

- Both inputs have to be arrays; an array stored inside an object works when the reference points at the array itself.
- Not specified in docs: more than two arrays; equality rules for objects; non-array input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UNION(["a", "b", "c"], ["c", "d", "a"])
output:  ["a", "b", "c", "d"]
```

**TypeScript equivalent**

```ts
[...new Set([...array1, ...array2])]
```

- `Set` compares objects by identity; for arrays of objects dedupe on `JSON.stringify` instead.
- CONCAT is the variant that keeps duplicates.

## UNIQ

- **Summary:** remove duplicate elements from an array
- **Signature:** `UNIQ(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/uniq/

**Arguments**

- `array` (required): The array.

**Returns:** Array with duplicates removed, keeping the first occurrence of each element in order.

**Porting semantics**

- Not specified in docs: equality rules for objects and for `1` vs `"1"`; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UNIQ(["x", "y", "x", "z", "y"])
output:  ["x", "y", "z"]
```

**TypeScript equivalent**

```ts
[...new Set(array)]
```

- `Set` compares objects by identity; for arrays of objects dedupe on `JSON.stringify` instead.

## WHERE

- **Summary:** filter an array of objects by the value at a key/path
- **Signature:** `WHERE(array, path, [value], [null_on_path_error: FALSE])`
- **Categories:** Arrays, Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/where/

**Arguments**

- `array` (required): Array of objects.
- `path` (required): One key, or several joined with dots.
- `value` (optional): The value to look for. Without it, the test is whether something is there at the path.
- `null_on_path_error` (optional): Keyword argument, off by default. When on, a `NULL` path makes the whole call return NULL.

**Returns:** A new array with the objects that pass the test.

**Porting semantics**

- With a value: an object is kept when what it holds at the path equals that value.
- Without a value: an object is kept when the path exists and holds something that counts as present. Missing keys are out, and so is text made only of spaces.
- `NULL` given as the value counts as no value at all, so WHERE cannot select entries that hold null; use FILTER with a lambda comparing against NULL for that.
- Not specified in docs: equality rules across types (`1` vs `"1"`); behaviour for a NULL path without `null_on_path_error`; non-object items.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: WHERE([{n: "Ada", role: "ops"}, {n: "Bo", role: "dev"}, {n: "Cy", role: "ops"}], "role", "ops")
output:  [{"n": "Ada", "role": "ops"}, {"n": "Cy", "role": "ops"}]

# 2 - present values only
formula: WHERE([{n: "Ada", contact: {phone: "555-0101"}}, {n: "Bo", contact: {phone: "  "}}, {n: "Cy"}], "contact.phone")
output:  [{"n": "Ada", "contact": {"phone": "555-0101"}}]

# 3
formula: WHERE([{n: "Ada"}], NULL, null_on_path_error: TRUE)
output:  null
```

**TypeScript equivalent**

```ts
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
const present = (v: unknown): boolean =>
  !(v == null || v === false || (typeof v === "string" && v.trim() === "") ||
    (Array.isArray(v) && v.length === 0) || (typeof v === "object" && Object.keys(v as object).length === 0));
function where(array: any[], path: string | null, value?: unknown, nullOnPathError = false): any[] | null {
  if (path == null) { if (nullOnPathError) return null; throw new Error("WHERE: path is NULL"); }
  return array.filter((o) => { const v = get(o, path); return value == null ? present(v) : v === value; });
}
```

- For a literal key and value this is `array.filter((o) => o.department === "engineering")`.
- `value == null` deliberately routes both "omitted" and `null` to the presence check, as the docs describe.
- Throwing for a NULL path without `null_on_path_error` is an assumption.
