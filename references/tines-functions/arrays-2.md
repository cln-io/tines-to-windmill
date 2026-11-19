# Tines formula functions: Arrays (part 2 of 4: INDEX_OF to RANDOM_ELEMENT)

Independent, unofficial porting notes for the functions Tines files under "Arrays": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: INDEX_OF, INSERT, INTERSECTION, JOIN, LAST, LAST_INDEX_OF, MAP, PUSH, RANDOM_ELEMENT

## INDEX_OF

- **Summary:** index of a term in text or an array (null if absent)
- **Signature:** `INDEX_OF(string_or_array, object | LAMBDA(value, expr))`
- **Categories:** Arrays, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/index-of/

**Arguments**

- `text_or_array` (required): Text or an array.
- `term | LAMBDA` (required): What to look for. On an array it may be a LAMBDA; the position of the first element it accepts is returned.

**Returns:** Zero-based position as a number, or `NULL` when nothing is found.

**Porting semantics**

- On text, the position of the first character of the first occurrence.
- Not specified in docs: null input; empty search term.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: INDEX_OF("tracking", "king")
output:  4

# 2 - not found is null, not -1
formula: INDEX_OF(["red", "green"], "blue")
output:  null

# 3
formula: INDEX_OF([5, 12, 40], LAMBDA(n, n > 10))
output:  1
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
function indexOf(target: string | any[], term: any): number | null {
  const i = Array.isArray(target) && typeof term === "function" ? target.findIndex((v) => truthy(term(v))) : target.indexOf(term);
  return i === -1 ? null : i;
}
```

- JS returns `-1` when not found; Tines returns `null`. A ported check like `INDEX_OF(a, x) = NULL` or `IS_BLANK(INDEX_OF(...))` breaks if you keep `-1`, and `-1` is also truthy in JS.
- A found index of `0` is not blank in Tines; do not test the result with JS truthiness.

## INSERT

- **Summary:** add an element to an array at a chosen position
- **Signature:** `INSERT(array, index, item)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/insert/

**Arguments**

- `array` (required): The array.
- `index` (required): 0-based position for the new item. Negative indexes are accepted.
- `item` (required): The item to insert.

**Returns:** The array with the item inserted.

**Porting semantics**

- A non-negative index is the position the new item takes; later items shift right.
- A negative index counts from the end, and the new item ends up at that position of the result: `-1` appends, `-2` puts it second to last.
- Not specified in docs: index beyond the array length; mutability of the input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: INSERT(["mon", "wed"], 1, "tue")
output:  ["mon", "tue", "wed"]

# 2
formula: INSERT([10, 20, 30, 40], -2, 35)
output:  [10, 20, 30, 35, 40]
```

**TypeScript equivalent**

```ts
const insert = <T>(array: T[], index: number, item: T): T[] => {
  const i = index < 0 ? array.length + index + 1 : index;
  return [...array.slice(0, i), item, ...array.slice(i)];
};
```

- `array.splice(-2, 0, item)` is wrong for negative indexes: it places the item one position too early, and it mutates the input.

## INTERSECTION

- **Summary:** items common to two arrays
- **Signature:** `INTERSECTION(array1, array2)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/intersection/

**Arguments**

- `first` (required): First array.
- `second` (required): Second array.

**Returns:** Array of the items found in both arrays, in the order of the first.

**Porting semantics**

- Not specified in docs: whether duplicates are removed; equality rules for objects; null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: INTERSECTION(["a", "b", "c", "d"], ["d", "x", "b"])
output:  ["b", "d"]
```

**TypeScript equivalent**

```ts
array1.filter((x: unknown) => array2.includes(x))
```

- This keeps duplicates from the first array; wrap in `[...new Set(...)]` if the story relies on unique results (not specified in docs).

## JOIN

- **Summary:** join array elements into text with a separator
- **Signature:** `JOIN(array, join_text)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/join/

**Arguments**

- `array` (required): The array.
- `join_text` (required): Separator placed between elements.

**Returns:** Text.

**Porting semantics**

- Not specified in docs: how non-text elements (null, numbers, objects, nested arrays) are rendered; empty array; omitted separator.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: JOIN(["2025", "09", "08"], "-")
output:  "2025-09-08"
```

**TypeScript equivalent**

```ts
array.join(joinText)
```

- JS renders `null`/`undefined` elements as `""`, nested arrays comma-joined, and objects as `[object Object]`. Map elements to strings first if the array is not all text.
- Always pass the separator: JS defaults to `","`.

## LAST

- **Summary:** last element of an array
- **Signature:** `LAST(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/last/

**Arguments**

- `array` (required): The array.

**Returns:** The last element.

**Porting semantics**

- Not specified in docs: empty array; null input; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: LAST(["alpha", "beta", "gamma"])
output:  "gamma"
```

**TypeScript equivalent**

```ts
array.at(-1) ?? null
```

- The `?? null` (null for an empty array) is an assumption; the docs do not cover it.

## LAST_INDEX_OF

- **Summary:** last index of a term in text or an array
- **Signature:** `LAST_INDEX_OF(string_or_array, term)`
- **Categories:** Arrays, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/last-index-of/

**Arguments**

- `string_or_array` (required): Text or an array.
- `term` (required): The term to find; with arrays it may be a LAMBDA.

**Returns:** 0-based index of the last occurrence (number); null when not found.

**Porting semantics**

- On text, the position of the first character of the last occurrence.
- Nothing found gives `NULL` (the docs render it as the word NULL in quotes; treat it as null, the same as INDEX_OF).
- Not specified in docs: null input; empty search term.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: LAST_INDEX_OF("a-b-c-d", "-")
output:  5

# 2
formula: LAST_INDEX_OF(["x", "y", "x", "z"], "x")
output:  2

# 3
formula: LAST_INDEX_OF(["x", "y"], "q")
output:  null
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
function lastIndexOf(target: string | any[], term: any): number | null {
  const i = Array.isArray(target) && typeof term === "function" ? target.findLastIndex((v) => truthy(term(v))) : target.lastIndexOf(term);
  return i === -1 ? null : i;
}
```

- JS returns `-1` when not found; Tines returns null.

## MAP

- **Summary:** pluck the value at a key/path from each object in an array
- **Signature:** `MAP(array_of_objects, path)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/map/

**Arguments**

- `array_of_objects` (required): Array of objects.
- `path` (required): One key, or several joined with dots. A key containing a space is written in brackets and double quotes, as in `'["Unit Price"]'`.

**Returns:** Array with the extracted value for each object.

**Porting semantics**

- This plucks a value by path; it does not take a function. To transform elements with a function use MAP_LAMBDA.
- The result is always an array, also for a one-element input (one docs example prints a bare value; the description says array).
- Not specified in docs: value produced for objects missing the key/path; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MAP([{sku: "A-1", dim: {w: 3}}, {sku: "B-9", dim: {w: 5}}], "dim.w")
output:  [3, 5]

# 2
formula: MAP([{"Unit Price": 9}, {"Unit Price": 12}], '["Unit Price"]')
output:  [9, 12]
```

**TypeScript equivalent**

```ts
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
array.map((o: any) => get(o, path))
```

- With a literal single key this is simply `array.map((o) => o.type ?? null)`.
- Yielding `null` for objects without the key is an assumption.

## PUSH

- **Summary:** append one or more items to an array
- **Signature:** `PUSH(array, item1, ...)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/push/

**Arguments**

- `array` (required): The array.
- `item1, ...` (required): One or more items to add at the end.

**Returns:** The array with the items appended.

**Porting semantics**

- An item that is itself an array is added as one nested element; nothing is flattened. CONCAT is the function that joins arrays.
- Not specified in docs: null array; whether the input array is modified (formulas return values; treat as non-mutating).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PUSH(["a"], "b", "c")
output:  ["a", "b", "c"]

# 2 - the array goes in as one element
formula: PUSH(["a"], ["b", "c"], "d")
output:  ["a", ["b", "c"], "d"]
```

**TypeScript equivalent**

```ts
[...array, item1, item2]
```

- `array.push(x)` is wrong as an expression: it mutates the input and returns the new length, not the array.
- `array.concat(item)` is wrong when the item is an array: it flattens it.

## RANDOM_ELEMENT

- **Summary:** pick a random element of an array
- **Signature:** `RANDOM_ELEMENT(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/random-element/

**Arguments**

- `array` (required): The array.

**Returns:** One randomly selected element.

**Porting semantics**

- Not specified in docs: empty array; null input; randomness source.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RANDOM_ELEMENT(["north", "south", "east"])
output:  one of the three, chosen at random
```

**TypeScript equivalent**

```ts
array[Math.floor(Math.random() * array.length)] ?? null
```

- Non-deterministic: tests comparing against a Tines run cannot expect equal output.
