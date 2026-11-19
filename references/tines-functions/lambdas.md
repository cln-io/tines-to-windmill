# Tines formula functions: Lambdas

Independent, unofficial porting notes for the functions Tines files under "Lambdas": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: FILTER, FIND, LAMBDA, MAP_LAMBDA, REDUCE, REJECT

## FILTER

- **Summary:** keep array/object items matching a lambda or value list
- **Signature:** `FILTER(array | object, values_to_keep | LAMBDA(arg1, [arg2], expr))`
- **Categories:** Lambdas, Arrays, Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/filter/

**Arguments**

- `array | object` (required): The array or object to filter.
- `values | LAMBDA` (required): Either an array listing the values to keep, or a LAMBDA deciding per item.

**Returns:** For an array: a new array of the kept items. For an object: a new object with the kept key/value pairs.

**Porting semantics**

- On an array the lambda receives one argument, the element.
- On an object a one-parameter lambda receives the value; a two-parameter lambda receives the key and the value.
- With a value list, an entry stays when its value equals one of the listed values; on an object it is the values, not the keys, that are compared.
- Tines truthiness applies to the lambda result: only `FALSE` and `NULL` drop an item, so a lambda returning `0` or `""` keeps it.
- Not specified in docs: whether the lambda result must be exactly TRUE or merely truthy; null target; equality rules for objects.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FILTER([3, 18, 7, 42], LAMBDA(n, n > 5))
output:  [18, 7, 42]

# 2
formula: FILTER({mon: 4, tue: 0, wed: 9}, LAMBDA(day, hours, hours > 0 && day != "wed"))
output:  {"mon": 4}

# 3
formula: FILTER(["x", "y", "x", "z"], ["x", "z"])
output:  ["x", "x", "z"]
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
function filter(target: any, by: any[] | ((...a: any[]) => unknown)): any {
  const keep = (k: string, v: any, isObj: boolean): boolean =>
    typeof by === "function" ? truthy(isObj && by.length >= 2 ? by(k, v) : by(v)) : by.includes(v);
  return Array.isArray(target)
    ? target.filter((v) => keep("", v, false))
    : Object.fromEntries(Object.entries(target).filter(([k, v]) => keep(k, v, true)));
}
```

- For the common array + lambda case this is just `array.filter((item) => truthy(expr))`.
- Plain `array.filter((x) => x.count)` drops items where the lambda yields `0` or `""`; Tines keeps them.
- The helper uses the arrow function's declared arity (`by.length`) to choose `(value)` vs `(key, value)`; port `LAMBDA(key, value, ...)` as a two-parameter arrow.

## FIND

- **Summary:** first array element for which a lambda is true
- **Signature:** `FIND(array, LAMBDA(item, [expr]))`
- **Categories:** Lambdas, Arrays
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/find/

**Arguments**

- `array` (required): The array to search.
- `LAMBDA(item, expr)` (required): Lambda taking one item.

**Returns:** The first matching element, or `NULL` when no element matches.

**Porting semantics**

- Not specified in docs: null/non-array input; whether the lambda result must be exactly TRUE or merely truthy.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FIND([{id: 1, ok: FALSE}, {id: 2, ok: TRUE}, {id: 3, ok: TRUE}], LAMBDA(r, r.ok))
output:  {"id": 2, "ok": true}

# 2
formula: FIND([4, 8], LAMBDA(n, n > 10))
output:  null
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
array.find((item: any) => truthy(/* lambda body */ item.type === "mammal")) ?? null
```

- JS `find` returns `undefined` on no match; add `?? null` so the step output matches Tines' `null`.

## LAMBDA

- **Summary:** define an anonymous function
- **Signature:** `LAMBDA([parameter1, parameter2, …,] calculation)`
- **Categories:** Lambdas
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/lambda/

**Arguments**

- `parameter1, parameter2, ...` (optional): Parameter names.
- `calculation` (required): The last argument: the expression to evaluate; it can reference the parameters.

**Returns:** A function value. Use it as an argument to MAP_LAMBDA, FILTER, FIND, REDUCE, REJECT, COUNTIF, INDEX_OF, LAST_INDEX_OF, GROUP_BY; invoke it immediately (`LAMBDA(a, b, a + b)(1, 2)`); or store it in LOCAL / a RESOURCE and call it later (`RESOURCE.my_lambdas.defang(url)`).

**Porting semantics**

- The calculation can also read data from outside the lambda, such as upstream action output.
- Not specified in docs: behaviour when called with the wrong number of arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - defined and called at once
formula: LAMBDA(w, h, w * h)(3, 4)
output:  12

# 2 - with rate = 10 from surrounding data
formula: MAP_LAMBDA([1, 2, 3], LAMBDA(n, n * rate))
output:  [10, 20, 30]
```

**TypeScript equivalent**

```ts
(parameter1: any, parameter2: any) => /* calculation */ parameter1 + parameter2
```

- Port an immediately-invoked lambda as a `const` plus the expression, or as an IIFE: `((a, b) => a + b)(1, 2)`.
- A lambda stored in a Tines RESOURCE has no Windmill equivalent as data: port it as a shared helper function in the script (or a Windmill shared script).
- Operators inside the body follow Tines rules: `=` is equality (`===`), `&` is text concatenation, `/` on whole numbers - see DIVIDED_BY.

## MAP_LAMBDA

- **Summary:** map each array element or object entry through a lambda
- **Signature:** `MAP_LAMBDA(array_or_object, lambda)`
- **Categories:** Lambdas
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/map-lambda/

**Arguments**

- `array_or_object` (required): An array, or an object.
- `lambda` (required): For an array: `LAMBDA(element, expr)`. For an object: `LAMBDA(key, value, expr)`.

**Returns:** An array of the lambda results (also when the input is an object).

**Porting semantics**

- The function passes values through unchanged apart from what the lambda does (one docs example shows an altered value that the lambda did not produce; it is a slip on the page).
- Not specified in docs: null input; empty input (presumably an empty array).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MAP_LAMBDA([{n: "Ada", h: 6}, {n: "Bo", h: 8}], LAMBDA(p, p.n & ":" & p.h * 2))
output:  ["Ada:12", "Bo:16"]

# 2
formula: MAP_LAMBDA({mon: 4, tue: 9}, LAMBDA(day, hours, UPCASE(day) & "=" & hours))
output:  ["MON=4", "TUE=9"]
```

**TypeScript equivalent**

```ts
Array.isArray(x) ? x.map((elem: any) => fn(elem)) : Object.entries(x).map(([key, value]) => fn(key, value))
```

- For the usual array case just write `array.map((elem) => expr)`.
- `null.map` throws; use `(x ?? []).map(...)` if the input may be missing (Tines behaviour for null is not specified).

## REDUCE

- **Summary:** fold an array into one value with a lambda
- **Signature:** `REDUCE(array, LAMBDA(previous_value, current_value, [expr]), initial_value)`
- **Categories:** Lambdas
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/reduce/

**Arguments**

- `array` (required): The array to fold.
- `LAMBDA(previous_value, current_value, expr)` (required): Lambda taking the running result and the current element and returning the new running result.
- `initial_value` (required): Starting value of the running result.

**Returns:** The final accumulator value.

**Porting semantics**

- Not specified in docs: empty array (presumably the initial value); omitting the initial value.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REDUCE([4, 9, 2], LAMBDA(total, n, total + n), 100)
output:  115

# 2
formula: REDUCE(["a", "b"], LAMBDA(acc, k, SET_KEY(acc, k, TRUE)), OBJECT())
output:  {"a": true, "b": true}
```

**TypeScript equivalent**

```ts
array.reduce((previousValue: any, currentValue: any) => /* lambda body */ previousValue + currentValue, initialValue)
```

- Argument order differs: Tines is `(array, lambda, initial)`; JS is `array.reduce(fn, initial)`. Always pass the initial value.

## REJECT

- **Summary:** drop array/object items matching a lambda or value list
- **Signature:** `REJECT(array | object, values_to_remove | LAMBDA(arg1, [arg2], expr))`
- **Categories:** Lambdas, Arrays, Objects
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/reject/

**Arguments**

- `array | object` (required): The array or object to filter.
- `values | LAMBDA` (required): Either an array listing the values to drop, or a LAMBDA deciding per item.

**Returns:** For an array: a new array without the rejected items. For an object: a new object without the rejected key/value pairs.

**Porting semantics**

- The inverse of FILTER: an item is removed when the lambda accepts it.
- On an array the lambda receives one argument, the element.
- On an object a one-parameter lambda receives the value; a two-parameter lambda receives the key and the value.
- With a value list, an entry is removed when its value equals one of the listed values; on an object it is the values, not the keys, that are compared.
- Tines truthiness applies to the lambda result: only `FALSE` and `NULL` keep an item, so a lambda returning `0` or `""` removes it.
- Not specified in docs: whether the lambda result must be exactly TRUE or merely truthy; null target; equality rules for objects.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: REJECT([3, 18, 7, 42], LAMBDA(n, n > 5))
output:  [3]

# 2
formula: REJECT({mon: 4, tue: 0, wed: 9}, [0])
output:  {"mon": 4, "wed": 9}

# 3
formula: REJECT(["a", "", "b"], LAMBDA(s, IS_BLANK(s)))
output:  ["a", "b"]
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
function reject(target: any, by: any[] | ((...a: any[]) => unknown)): any {
  const drop = (k: string, v: any, isObj: boolean): boolean =>
    typeof by === "function" ? truthy(isObj && by.length >= 2 ? by(k, v) : by(v)) : by.includes(v);
  return Array.isArray(target)
    ? target.filter((v) => !drop("", v, false))
    : Object.fromEntries(Object.entries(target).filter(([k, v]) => !drop(k, v, true)));
}
```

- For the common array + lambda case this is `array.filter((item) => !truthy(expr))`.
- `REJECT(array, LAMBDA(x, IS_BLANK(x)))` is not `array.filter(Boolean)`: that would also drop `0` (see IS_BLANK).
