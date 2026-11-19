# Tines formula functions: Arrays (part 3 of 4: RANGE to TALLY)

Independent, unofficial porting notes for the functions Tines files under "Arrays": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: RANGE, REVERSE, ROTATE, SHUFFLE, SLICE_ARRAY, SORT, SORT_NATURAL, SUM, TALLY

## RANGE

- **Summary:** array of numbers from start to end inclusive
- **Signature:** `RANGE(start, end)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/range/

**Arguments**

- `start` (required): First value.
- `end` (required): Last value (included).

**Returns:** Array of consecutive numbers: `RANGE(7, 10)` is `[7, 8, 9, 10]`.

**Porting semantics**

- Both ends are inclusive.
- Not specified in docs: start greater than end; non-integer bounds; step size other than 1.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - both ends included
formula: RANGE(3, 6)
output:  [3, 4, 5, 6]

# 2
formula: RANGE(-1, 1)
output:  [-1, 0, 1]
```

**TypeScript equivalent**

```ts
Array.from({ length: Math.max(0, end - start + 1) }, (_, i) => start + i)
```

- Off-by-one trap: the end is included, unlike most JS/Python range helpers.

## REVERSE

- **Summary:** reverse an array (and flatten nested arrays)
- **Signature:** `REVERSE(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/reverse/

**Arguments**

- `array` (required): The array.

**Returns:** Array in reverse order.

**Porting semantics**

- Nested arrays are flattened completely before the order is reversed.
- Text cannot be reversed directly; split it into characters, reverse, and join again.
- Not specified in docs: null input; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REVERSE(["a", "b", "c"])
output:  ["c", "b", "a"]

# 2 - flattened, then reversed
formula: REVERSE([["a", "b"], ["c", ["d"]]])
output:  ["d", "c", "b", "a"]
```

**TypeScript equivalent**

```ts
array.flat(Infinity).reverse()
```

- Plain `array.reverse()` is wrong twice: it mutates the input in place, and it does not flatten nested arrays.
- Text reversal: `[...text].reverse().join("")`.

## ROTATE

- **Summary:** rotate array elements by a number of steps
- **Signature:** `ROTATE(array, steps)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/rotate/

**Arguments**

- `array` (required): The array.
- `steps` (optional): How many positions to rotate; 1 when omitted. A negative number rotates the other way.

**Returns:** The rotated array. Positive steps move elements from the front to the back; negative steps move elements from the back to the front.

**Porting semantics**

- Not specified in docs: steps larger than the array length (presumably wraps); empty array.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ROTATE(["a", "b", "c", "d"])
output:  ["b", "c", "d", "a"]

# 2
formula: ROTATE(["a", "b", "c", "d"], 3)
output:  ["d", "a", "b", "c"]

# 3
formula: ROTATE(["a", "b", "c", "d"], -1)
output:  ["d", "a", "b", "c"]
```

**TypeScript equivalent**

```ts
function rotate<T>(array: T[], steps = 1): T[] {
  if (array.length === 0) return [];
  const n = ((steps % array.length) + array.length) % array.length;
  return [...array.slice(n), ...array.slice(0, n)];
}
```

## SHUFFLE

- **Summary:** randomly reorder an array
- **Signature:** `SHUFFLE(array)`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/shuffle/

**Arguments**

- `array` (required): The array.

**Returns:** An array with the same elements in random order.

**Porting semantics**

- Not specified in docs: randomness source; whether the input is modified (treat as non-mutating).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SHUFFLE([1, 2, 3, 4, 5])
output:  the same five numbers in a random order, e.g. [4, 1, 5, 3, 2]
```

**TypeScript equivalent**

```ts
array.map((v: unknown) => [Math.random(), v] as const).sort((a, b) => a[0] - b[0]).map((p) => p[1])
```

- Each element gets a random sort key, so the result is unbiased and the input is not touched.
- `array.sort(() => Math.random() - 0.5)` is biased and mutates the input.

## SLICE_ARRAY

- **Summary:** sub-array from a start index, optionally limited in length
- **Signature:** `SLICE_ARRAY(array, start_index, [length])`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/slice-array/

**Arguments**

- `array` (required): The array.
- `start_index` (required): 0-based index to start at.
- `length` (optional): Number of elements to return. If omitted, the remainder of the array is returned.

**Returns:** A new array. A length that runs beyond the end simply stops at the end.

**Porting semantics**

- The third argument is a length, not an end index: `SLICE_ARRAY(a, 1, 2)` returns 2 elements starting at index 1.
- Not specified in docs: negative start_index (SLICE documents it for text; not stated here); start beyond the end.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - three elements from position 1
formula: SLICE_ARRAY(["a", "b", "c", "d", "e"], 1, 3)
output:  ["b", "c", "d"]

# 2 - no length: the rest
formula: SLICE_ARRAY(["a", "b", "c", "d", "e"], 3)
output:  ["d", "e"]
```

**TypeScript equivalent**

```ts
length === undefined ? array.slice(start) : array.slice(start, start + length)
```

- JS `slice(start, end)` takes an end index; passing the Tines length straight through is the classic bug.
- With a negative start and a length, `start + length` can reach 0 and return `[]`; convert the start first: `const s = start < 0 ? Math.max(0, array.length + start) : start`.

## SORT

- **Summary:** sort an array (case-sensitive), optionally by a path
- **Signature:** `SORT(array, path, [include_json_paths: FALSE])`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sort/

**Arguments**

- `array` (required): The array.
- `path` (optional): Property (or dot-separated path) of each element to sort by.
- `include_json_paths` (optional): Keyword argument, off by default. The docs turn it on in their example that sorts by a dotted path.

**Returns:** A sorted array in ascending order. Letter case matters: uppercase letters come before lowercase ones.

**Porting semantics**

- There is no descending option; combine with REVERSE (which also flattens nested arrays).
- Not specified in docs: ordering of numbers (numeric vs text), mixed types and nulls; whether a dotted path works without `include_json_paths: TRUE`; stability.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - capitals first
formula: SORT(["pear", "Apple", "fig", "Banana"])
output:  ["Apple", "Banana", "fig", "pear"]

# 2
formula: SORT(["b", "a", "C"])
output:  ["C", "a", "b"]

# 3
formula: SORT([{n: "Bo", dept: {floor: 3}}, {n: "Ada", dept: {floor: 1}}], "dept.floor", include_json_paths: TRUE)
output:  [{"n": "Ada", "dept": {"floor": 1}}, {"n": "Bo", "dept": {"floor": 3}}]
```

**TypeScript equivalent**

```ts
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
function sort<T>(array: T[], path?: string): T[] {
  const key = (v: any) => (path ? get(v, path) : v);
  return [...array].sort((a, b) => { const x = key(a), y = key(b); return x < y ? -1 : x > y ? 1 : 0; });
}
```

- Bare `array.sort()` is wrong twice: it mutates the input, and it compares everything as text (`[10, 9, 1]` sorts to `[1, 10, 9]`).
- `localeCompare` is case-insensitive-ish and would give SORT_NATURAL-like ordering; the `<`/`>` comparator above keeps uppercase first.

## SORT_NATURAL

- **Summary:** sort an array case-insensitively, optionally by a path
- **Signature:** `SORT_NATURAL(array, path, [include_json_paths: FALSE])`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sort-natural/

**Arguments**

- `array` (required): The array.
- `path` (optional): Property (or dot-separated path) of each element to sort by.
- `include_json_paths` (optional): Keyword argument, default `FALSE`. (SORT's nested-key example passes `include_json_paths: TRUE`.)

**Returns:** A sorted array in ascending order, ignoring letter case.

**Porting semantics**

- Not specified in docs: ordering of numbers, mixed types and nulls; whether "natural" also means numeric-aware ordering of digits inside text; stability.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SORT_NATURAL(["pear", "Apple", "fig", "Banana"])
output:  ["Apple", "Banana", "fig", "pear"]
```

**TypeScript equivalent** (APPROXIMATE: case-insensitive comparison only; any digit-aware ordering is not specified in the docs and not implemented)

```ts
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
function sortNatural<T>(array: T[], path?: string): T[] {
  const key = (v: any) => { const k = path ? get(v, path) : v; return typeof k === "string" ? k.toLowerCase() : k; };
  return [...array].sort((a, b) => { const x = key(a), y = key(b); return x < y ? -1 : x > y ? 1 : 0; });
}
```

- `array.sort()` mutates the input; copy first.

## SUM

- **Summary:** sum of an array of numbers
- **Signature:** `SUM(array)`
- **Categories:** Arrays, Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sum/

**Arguments**

- `array` (required): Array of numbers.

**Returns:** Number: the sum of the elements.

**Porting semantics**

- Not specified in docs: empty array (presumably 0); numeric text or null members; multiple-argument form (the syntax shows only an array).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SUM([4, 9.5, -2])
output:  11.5
```

**TypeScript equivalent**

```ts
array.reduce((a: number, b: unknown) => a + Number(b), 0)
```

- Keep the `Number()`: with string members a bare `a + b` concatenates.
- Always pass the `0` initial value or an empty array throws.

## TALLY

- **Summary:** count occurrences of each unique element in an array
- **Signature:** `TALLY(array, [strict_types: FALSE])`
- **Categories:** Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/tally/

**Arguments**

- `array` (required): The array.
- `strict_types` (optional): Keyword argument, default `FALSE`.

**Returns:** By default an object whose keys are the distinct elements and whose values are their counts. With `strict_types: TRUE`, an array of objects with the fields `key` and `count`, in which a number and the same digits as text are counted separately.

**Porting semantics**

- Case-sensitive (`"Dog"` and `"dog"` are different).
- Not specified in docs: with the default setting, whether `404` and `"404"` are merged into one key (implied by the option's name, not stated); order of the result.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TALLY(["ok", "fail", "ok", "ok"])
output:  {"ok": 3, "fail": 1}

# 2
formula: TALLY([7, "7", 7], strict_types: TRUE)
output:  [{"key": 7, "count": 2}, {"key": "7", "count": 1}]
```

**TypeScript equivalent**

```ts
function tally(array: any[], strictTypes = false): any {
  const m = new Map<any, number>();
  for (const v of array) { const k = strictTypes ? v : String(v); m.set(k, (m.get(k) ?? 0) + 1); }
  return strictTypes ? [...m].map(([key, count]) => ({ key, count })) : Object.fromEntries(m);
}
```

- JS objects list integer-like keys first, so the key order of the default form can differ from first-occurrence order.
