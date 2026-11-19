# Tines formula functions: Arrays (part 1 of 4: ARRAY to GROUP_BY)

Independent, unofficial porting notes for the functions Tines files under "Arrays": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: ARRAY, CHUNK_ARRAY, COMPACT, CONCAT, COUNTIF, DELETE, DIFFERENCE, FIRST, FLATTEN, GROUP_BY

## ARRAY

- **Summary:** build an array from the arguments
- **Signature:** `ARRAY(element1, element2, ...)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/array/

**Arguments**

- `element1, element2, ...` (optional): Any values; each becomes a member.

**Returns:** Array of the arguments, in order; members may be of different types.

**Porting semantics**

- Not specified in docs: `ARRAY()` with no arguments (presumably an empty array, but not stated).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ARRAY("a", 2, FALSE)
output:  ["a", 2]

# 2
formula: ARRAY("red", 7, FALSE, NULL)
output:  ["red", 7, false, null]
```

**TypeScript equivalent**

```ts
[element1, element2]
```

## CHUNK_ARRAY

- **Summary:** split an array into chunks of a given size
- **Signature:** `CHUNK_ARRAY(array, chunk_size)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/chunk-array/

**Arguments**

- `array` (required): The array to chunk.
- `chunk_size` (required): Number of elements per chunk.

**Returns:** Array of arrays. The last chunk may contain fewer than `chunk_size` elements.

**Porting semantics**

- Not specified in docs: empty array; chunk_size of 0 or negative; non-array input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - the last chunk is shorter
formula: CHUNK_ARRAY(["a", "b", "c", "d", "e"], 2)
output:  [["a", "b"], ["c", "d"], ["e"]]
```

**TypeScript equivalent**

```ts
const chunkArray = <T>(array: T[], size: number): T[][] =>
  Array.from({ length: Math.ceil(array.length / size) }, (_, i) => array.slice(i * size, (i + 1) * size));
```

## COMPACT

- **Summary:** remove null values from an array
- **Signature:** `COMPACT(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/compact/

**Arguments**

- `array` (required): The array.

**Returns:** New array without `null` members.

**Porting semantics**

- Only `null` is removed. Empty strings, `false`, `0`, `[]` are kept (the docs say "any null values").
- Not specified in docs: nested arrays; non-array input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - only the nulls go
formula: COMPACT([3, NULL, 0, "", NULL, FALSE])
output:  [3, 0, "", false]
```

**TypeScript equivalent**

```ts
array.filter((v: unknown) => v !== null && v !== undefined)
```

- `array.filter(Boolean)` is wrong: it also drops `0`, `""` and `false`.

## CONCAT

- **Summary:** concatenate arrays
- **Signature:** `CONCAT(array1, array2, ...)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/concat/

**Arguments**

- `array1, array2, ...` (required): Two or more arrays.

**Returns:** One array containing all elements in order. Duplicates are kept (use UNION to dedupe).

**Porting semantics**

- Not specified in docs: non-array arguments; null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - duplicates stay
formula: CONCAT([1, 2], [2, 3])
output:  [1, 2, 2, 3]
```

**TypeScript equivalent**

```ts
[...array1, ...array2]
```

- Spreading `null` throws in JS; add `?? []` if an input may be missing.

## COUNTIF

- **Summary:** count elements equal to a value or accepted by a lambda
- **Signature:** `COUNTIF(array, comparison)`
- **Categories:** Arrays, Lambdas
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/countif/

**Arguments**

- `array` (required): The array.
- `comparison` (required): A value to compare each element with, or a LAMBDA taking one item.

**Returns:** Number of matching elements.

**Porting semantics**

- Not specified in docs: equality rules for objects/arrays and for `1` vs `"1"`; empty array (presumably 0).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: COUNTIF(["up", "down", "up", "up"], "up")
output:  3

# 2
formula: COUNTIF([12, 5, 31, 8], LAMBDA(n, n >= 10))
output:  2
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
const countIf = (array: any[], cmp: any): number =>
  array.filter((x) => (typeof cmp === "function" ? truthy(cmp(x)) : x === cmp)).length;
```

- `===` compares objects by identity; if the comparison value is an object or array, compare `JSON.stringify` of both instead.

## DELETE

- **Summary:** remove the item at an index from an array
- **Signature:** `DELETE(array, index)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/delete/

**Arguments**

- `array` (required): The array.
- `index` (required): 0-based index; negative indexes count from the end (`-1` is the last item).

**Returns:** The array minus the deleted item.

**Porting semantics**

- Not specified in docs: index out of range; non-integer index.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DELETE(["mon", "tue", "wed"], 0)
output:  ["tue", "wed"]

# 2
formula: DELETE(["mon", "tue", "wed"], -2)
output:  ["mon", "wed"]
```

**TypeScript equivalent**

```ts
array.filter((_: unknown, i: number) => i !== (index < 0 ? array.length + index : index))
```

- Do not use `array.splice(index, 1)` directly: it mutates the input and returns the removed items, not the remaining array.

## DIFFERENCE

- **Summary:** items in the first array that are not in the second
- **Signature:** `DIFFERENCE(array1, array2)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/difference/

**Arguments**

- `first` (required): Array whose items are kept.
- `second` (required): Array of items to leave out.

**Returns:** Array of the items of the first array that do not occur in the second.

**Porting semantics**

- Not specified in docs: whether duplicates in the first array survive; equality rules for objects; null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DIFFERENCE(["a", "b", "c", "d"], ["b", "d", "x"])
output:  ["a", "c"]
```

**TypeScript equivalent**

```ts
array1.filter((x: unknown) => !array2.includes(x))
```

- `includes` compares objects by identity; for arrays of objects compare `JSON.stringify(x)` values instead.

## FIRST

- **Summary:** first element of an array
- **Signature:** `FIRST(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/first/

**Arguments**

- `array` (required): The array.

**Returns:** The first element.

**Porting semantics**

- Not specified in docs: empty array; null input; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FIRST(["alpha", "beta", "gamma"])
output:  "alpha"
```

**TypeScript equivalent**

```ts
array[0] ?? null
```

- The `?? null` (null for an empty array) is an assumption; the docs do not cover it.

## FLATTEN

- **Summary:** flatten nested arrays into one array
- **Signature:** `FLATTEN(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/flatten/

**Arguments**

- `array` (required): Array that may contain nested arrays.

**Returns:** A single one-dimensional array.

**Porting semantics**

- The description says nested arrays become "a single 1 dimensional array", i.e. flattening is fully recursive (the example only shows one level).
- Not specified in docs: non-array input; null members.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FLATTEN([1, [2, [3, [4]]], 5])
output:  [1, 2, 3, 4, 5]
```

**TypeScript equivalent**

```ts
array.flat(Infinity)
```

- `array.flat()` with no argument only flattens one level.

## GROUP_BY

- **Summary:** group array items by a field or by a lambda result
- **Signature:** `GROUP_BY(items, key_or_lambda, [as_array: FALSE])`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/group-by/

**Arguments**

- `items` (required): Array of objects.
- `field_or_lambda` (required): A field name, or a LAMBDA that receives one item and returns its group.
- `as_array` (optional): Boolean keyword argument, off by default.

**Returns:** By default an object with one entry per group, each holding the array of its items. With `as_array: TRUE`, an array of objects with the two fields `key` and `values`.

**Porting semantics**

- Groups appear in order of first occurrence in the examples; items keep their original order inside a group.
- Not specified in docs: items that lack the field; whether a dotted path may be used as the field; group names that are not text.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: GROUP_BY([{n: "Ada", team: "ops"}, {n: "Bo", team: "dev"}, {n: "Cy", team: "ops"}], "team")
output:  {"ops": [{"n": "Ada", "team": "ops"}, {"n": "Cy", "team": "ops"}], "dev": [{"n": "Bo", "team": "dev"}]}

# 2
formula: GROUP_BY([3, 10, 8], LAMBDA(n, IF(n > 5, "big", "small")), as_array: TRUE)
output:  [{"key": "small", "values": [3]}, {"key": "big", "values": [10, 8]}]
```

**TypeScript equivalent**

```ts
function groupBy(items: any[], keyOrFn: string | ((item: any) => any), asArray = false): any {
  const g: Record<string, any[]> = {};
  for (const it of items) (g[typeof keyOrFn === "function" ? keyOrFn(it) : it?.[keyOrFn] ?? null] ??= []).push(it);
  return asArray ? Object.entries(g).map(([key, values]) => ({ key, values })) : g;
}
```

- With a literal field this is one expression: `items.reduce((g, o) => ((g[o?.team ?? null] ??= []).push(o), g), {})`.
- Group names become text (object keys). A JS object lists integer-like keys before other keys regardless of insertion order.
- Items without the field land in a group named `"null"` here - an assumption.
