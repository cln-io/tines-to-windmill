# Tines formula functions: Logic

Independent, unofficial porting notes for the functions Tines files under "Logic": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: AND, DEFAULT, ERROR, IF, IF_ERROR, NOT, OR, SWITCH

## AND

- **Summary:** true only when every argument is truthy
- **Signature:** `AND(value1, value2, ...)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/and/

**Arguments**

- `arg1, arg2, ...` (required): Any expressions.

**Returns:** Boolean `TRUE` or `FALSE` (never one of the operands).

**Porting semantics**

- Tines truthiness: only `FALSE` and `NULL` count as false. `0`, `""`, `[]` and `{}` count as true.
- Arguments are evaluated lazily, left to right; evaluation stops at the first falsy one.
- Not specified in docs: result when called with zero arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: AND(4 > 1, 4 < 9)
output:  true

# 2 - both are truthy in Tines
formula: AND(0, "")
output:  true

# 3
formula: AND("ready", NULL)
output:  false
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
truthy(value1) && truthy(value2) // extend with && for more arguments
```

- Plain JS `a && b` is subtly wrong twice: it returns an operand instead of a boolean, and it treats `0`, `""` and `NaN` as falsy while Tines treats them as truthy.

## DEFAULT

- **Summary:** first value that is not blank
- **Signature:** `DEFAULT(value, fallback1, fallback2, ..., [{use_last_fallback: FALSE}])`
- **Categories:** Logic, Arrays, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/default/

**Arguments**

- `value` (required): The value to test.
- `alt1, alt2, ...` (required): One or more alternatives, tried in order.
- `{use_last_fallback: TRUE}` (optional): Options object given as the final argument; off by default.

**Returns:** The value itself when it is not blank, otherwise the first alternative that is not blank. When everything is blank: the first alternative, or the last one when `use_last_fallback` is on.

**Porting semantics**

- Blank covers `NULL`, `FALSE`, empty text, an empty array and an empty object.
- A reference to a key that does not exist is blank too.
- `0` is not blank, so it is kept.
- When all arguments are blank the result is still one of the alternatives, blank as it is - the first by default.
- Not specified in docs: whether whitespace-only text counts as empty.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - where order has no note key
formula: DEFAULT(order.note, "n/a")
output:  "n/a"

# 2 - all blank: first alternative
formula: DEFAULT("", {}, FALSE)
output:  {}

# 3
formula: DEFAULT("", {}, FALSE, {use_last_fallback: TRUE})
output:  false
```

**TypeScript equivalent**

```ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
// pass [value, fallback1, fallback2, ...]
function tinesDefault(args: unknown[], useLastFallback = false): unknown {
  const hit = args.find((a) => !isBlank(a));
  if (hit !== undefined) return hit;
  return (useLastFallback ? args[args.length - 1] : args[1]) ?? null;
}
```

- `value ?? alt` is wrong: it keeps `""`, `false`, `[]` and `{}`.
- `value || alt` is wrong: it replaces `0` and keeps `[]` and `{}`.

## ERROR

- **Summary:** raise an error with a message
- **Signature:** `ERROR(message)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/error/

**Arguments**

- `message` (optional): Error message. Default message: "Explicit error raised".

**Returns:** Never returns; raises an error carrying the message.

**Porting semantics**

- Typically placed in one branch of IF to reject bad input.
- Can be caught with IF_ERROR.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ERROR("quota exceeded")
output:  an error is raised with the message "quota exceeded"

# 2
formula: ERROR()
output:  an error is raised with the default message
```

**TypeScript equivalent**

```ts
const raise = (message = "Explicit error raised"): never => { throw new Error(message); };
```

- `throw` is a statement in JS, so use the `raise(...)` helper where the formula uses ERROR inside an expression (e.g. the else branch of IF).
- In Windmill an uncaught throw fails the step (and the flow, unless an error handler or `continue on error` is configured).

## IF

- **Summary:** conditional: second argument if condition is true, else third
- **Signature:** `IF(condition, value_if_true, [value_if_false])`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/if/

**Arguments**

- `condition` (required): The condition.
- `then` (required): Result when the condition holds.
- `otherwise` (optional): Result when it does not; `NULL` when left out.

**Returns:** The second argument when the condition holds; otherwise the third argument, or `NULL` if there is none.

**Porting semantics**

- Arguments are evaluated lazily: only the chosen branch is evaluated.
- Tines truthiness: only `FALSE` and `NULL` count as false.
- A branch value keeps its type; text stays text even when it reads like a boolean.
- Not specified in docs: whether a condition that is not a boolean, such as `0` or `""`, selects the first branch (by the truthiness rule it would).

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - no third argument
formula: IF(18 >= 21, "adult")
output:  null

# 2
formula: IF(SIZE("abc") = 3, "three", "other")
output:  "three"
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
truthy(condition) ? valueIfTrue : valueIfFalse   // use `: null` when the formula has no third argument
```

- Plain `cond ? a : b` treats `0`, `""` and `NaN` as false; Tines treats them as truthy. When the condition is a comparison (`>`, `=`, IS_BLANK, ...) it is already a boolean and the plain ternary is fine.
- The Tines `=` operator is equality: port as `===`, not as assignment.

## IF_ERROR

- **Summary:** return a fallback if an expression errors
- **Signature:** `IF_ERROR(expression, fallback_expression)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/if-error/

**Arguments**

- `expression` (required): Expression to evaluate.
- `fallback_expression` (required): Result to return if `expression` produces an error.

**Returns:** The result of `expression`, or the result of `fallback_expression` if `expression` raised an error.

**Porting semantics**

- Dividing by zero with the `/` operator is one way to get an error.
- Errors raised with ERROR() are caught too.
- Not specified in docs: whether the fallback is evaluated lazily; which other conditions count as errors.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: IF_ERROR(JSON_PARSE("{oops"), "bad json")
output:  "bad json"

# 2
formula: IF_ERROR(6 * 7, "failed")
output:  42
```

**TypeScript equivalent**

```ts
const ifError = <T, F>(expr: () => T, fallback: () => F): T | F => { try { return expr(); } catch { return fallback(); } };
// usage: ifError(() => riskyExpression, () => "fallback")
```

- JS throws in different places than Tines. `a / 0` gives `Infinity` (no throw), `JSON.parse` throws, reading a property of `null` throws (Tines path access on a missing key gives null). Add explicit checks so the same inputs take the same branch.

## NOT

- **Summary:** logical opposite of a value
- **Signature:** `NOT(any)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/not/

**Arguments**

- `any` (required): Any value.

**Returns:** Boolean: the logical opposite of the argument.

**Porting semantics**

- Tines truthiness (language docs): only `FALSE` and `NULL` are falsy, so `NOT(0)` and `NOT("")` would be false.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: NOT(3 > 8)
output:  true

# 2 - empty text is truthy in Tines
formula: NOT("")
output:  false

# 3
formula: NOT(NULL)
output:  true
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
!truthy(value)
```

- Plain `!value` is only safe when the operand is already a boolean (a comparison, IS_BLANK, INCLUDES, ...).

## OR

- **Summary:** true if any argument is truthy
- **Signature:** `OR(value1, value2, ...)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/or/

**Arguments**

- `value1, value2, ...` (required): Any values / expressions.

**Returns:** Boolean true or false (never one of the operands).

**Porting semantics**

- Tines truthiness (language docs): every value is truthy except `FALSE` and `NULL`. So `0`, `""`, `[]` and `{}` are truthy.
- Arguments are evaluated lazily (language docs: IF, AND and OR are the exceptions to eager evaluation).
- Not specified in docs: result when called with zero arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: OR(3 > 8, 2 < 5)
output:  true

# 2
formula: OR(FALSE, NULL)
output:  false

# 3 - zero is truthy, and the result is TRUE rather than 0
formula: OR(FALSE, 0)
output:  true
```

**TypeScript equivalent**

```ts
const truthy = (v: unknown): boolean => v !== false && v !== null && v !== undefined;
truthy(value1) || truthy(value2) // extend with || for more arguments
```

- Plain JS `a || b` returns an operand instead of a boolean and treats `0`, `""` and `NaN` as falsy. In particular `OR(x, "default")` is not a defaulting idiom in Tines - it returns TRUE. Use DEFAULT for fallbacks.

## SWITCH

- **Summary:** return the result paired with the first matching value
- **Signature:** `SWITCH(expression, value_to_compare, value_to_return, ..., default_value)`
- **Categories:** Logic
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/switch/

**Arguments**

- `expression` (required): The value to compare.
- `value_to_compare, value_to_return, ...` (required): Pairs: a candidate value followed by the result to return when the expression equals it.
- `default_value` (required): Final argument, returned when no candidate matches.

**Returns:** The result for the first matching candidate, otherwise the default value.

**Porting semantics**

- Not specified in docs: result when no default is supplied and nothing matches; equality rules across types (`1` vs `"1"`); whether results are evaluated lazily.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SWITCH("high", "low", "P4", "high", "P1", "P3")
output:  "P1"

# 2 - nothing matches: the last argument
formula: SWITCH("unknown", "low", "P4", "high", "P1", "P3")
output:  "P3"
```

**TypeScript equivalent**

```ts
function tinesSwitch(expr: unknown, ...rest: unknown[]): unknown {
  for (let i = 0; i + 1 < rest.length; i += 2) if (rest[i] === expr) return rest[i + 1];
  return rest.length % 2 === 1 ? rest[rest.length - 1] : null;
}
```

- With literal cases an object lookup is clearer: `({ low: "P4", high: "P1" } as Record<string, string>)[level] ?? "P3"`.
- Returning `null` when there is no default is an assumption.
