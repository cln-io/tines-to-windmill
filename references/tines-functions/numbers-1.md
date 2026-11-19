# Tines formula functions: Numbers (part 1 of 3: ABS to COS)

Independent, unofficial porting notes for the functions Tines files under "Numbers": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: ABS, ACOS, ASIN, AT_LEAST, AT_MOST, AVERAGE, CEIL, CLAMP, COS

## ABS

- **Summary:** absolute value of a number
- **Signature:** `ABS(number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/abs/

**Arguments**

- `number` (required): A number, or numeric text.

**Returns:** Number (the absolute value).

**Porting semantics**

- Numeric text is converted first, so text such as `"-7.25"` works like the number.
- Not specified in docs: null/blank input; text that is not a number.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ABS(-12)
output:  12

# 2
formula: ABS("-7.25")
output:  7.25
```

**TypeScript equivalent**

```ts
Math.abs(Number(number))
```

- JS `Number(null)` and `Number("")` are `0` and `Number("abc")` is `NaN`; the docs do not say what Tines does for those inputs.

## ACOS

- **Summary:** arc cosine in radians
- **Signature:** `ACOS(x)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/acos/

**Arguments**

- `x` (required): Number.

**Returns:** Number between 0 and π (radians).

**Porting semantics**

- Not specified in docs: input outside [-1, 1]; null or text input; the docs give no examples.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ACOS(1)
output:  0

# 2
formula: ACOS(-1)
output:  3.141592653589793
```

**TypeScript equivalent**

```ts
Math.acos(Number(x))
```

- JS returns `NaN` outside [-1, 1]; Tines behaviour there is not specified.

## ASIN

- **Summary:** arc sine in radians
- **Signature:** `ASIN(x)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/asin/

**Arguments**

- `x` (required): Number.

**Returns:** Number between -π/2 and π/2 (radians).

**Porting semantics**

- Not specified in docs: input outside [-1, 1]; null or text input; the docs give no examples.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ASIN(0)
output:  0

# 2
formula: ASIN(1)
output:  1.5707963267948966
```

**TypeScript equivalent**

```ts
Math.asin(Number(x))
```

- JS returns `NaN` outside [-1, 1]; Tines behaviour there is not specified.

## AT_LEAST

- **Summary:** limit a number to a minimum
- **Signature:** `AT_LEAST(number, minimum)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/at-least/

**Arguments**

- `number` (required): The number to limit.
- `minimum` (required): Lower bound.

**Returns:** `number` if it is >= `minimum`, otherwise `minimum`.

**Porting semantics**

- Not specified in docs: null or text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: AT_LEAST(3, 10)
output:  10

# 2
formula: AT_LEAST(42, 10)
output:  42
```

**TypeScript equivalent**

```ts
Math.max(Number(number), Number(minimum))
```

- Naming trap: AT_LEAST is `Math.max`, AT_MOST is `Math.min`.

## AT_MOST

- **Summary:** limit a number to a maximum
- **Signature:** `AT_MOST(number, maximum)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/at-most/

**Arguments**

- `number` (required): The number to limit.
- `maximum` (required): Upper bound.

**Returns:** `number` if it is <= `maximum`, otherwise `maximum`.

**Porting semantics**

- Not specified in docs: null or text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: AT_MOST(250, 100)
output:  100

# 2
formula: AT_MOST(-5, 100)
output:  -5
```

**TypeScript equivalent**

```ts
Math.min(Number(number), Number(maximum))
```

- Naming trap: AT_MOST is `Math.min`, AT_LEAST is `Math.max`.

## AVERAGE

- **Summary:** mean of an array or of the arguments
- **Signature:** `AVERAGE(array) or AVERAGE(number1, number2, ...)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/average/

**Arguments**

- `array` (required): Either a single array of numbers, or
- `number1, number2, ...` (required): multiple numeric arguments (alternative form).

**Returns:** Number: the arithmetic mean.

**Porting semantics**

- Not specified in docs: empty array; non-numeric or null members.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: AVERAGE([10, 20, 60])
output:  30

# 2
formula: AVERAGE(4, 5)
output:  4.5
```

**TypeScript equivalent**

```ts
function average(...args: any[]): number {
  const xs: number[] = (args.length === 1 && Array.isArray(args[0]) ? args[0] : args).map(Number);
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}
```

- This returns `NaN` for an empty array; Tines behaviour is not specified.

## CEIL

- **Summary:** round up to a whole number
- **Signature:** `CEIL(number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/ceil/

**Arguments**

- `number` (required): A number, or numeric text.

**Returns:** Whole number.

**Porting semantics**

- Numeric text is converted first.
- Not specified in docs: null/blank input; non-numeric text; negative numbers (no example).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CEIL(7.01)
output:  8

# 2
formula: CEIL("2.5")
output:  3
```

**TypeScript equivalent**

```ts
Math.ceil(Number(number))
```

## CLAMP

- **Summary:** restrict a value to a min..max range
- **Signature:** `CLAMP(input, min, max)`
- **Categories:** Numbers, Text
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/clamp/

**Arguments**

- `input` (required): Number or text.
- `min` (required): Lower boundary.
- `max` (required): Upper boundary.

**Returns:** The lower boundary when the input is below it, the upper boundary when the input is above it, otherwise the input unchanged.

**Porting semantics**

- Text is compared in dictionary (lexicographic) order.
- Not specified in docs: mixed types; lower boundary above the upper one; null input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: CLAMP(140, 0, 100)
output:  100

# 2
formula: CLAMP(37, 0, 100)
output:  37

# 3
formula: CLAMP("zebra", "kiwi", "plum")
output:  "plum"
```

**TypeScript equivalent**

```ts
input < min ? min : input > max ? max : input
```

- JS `<` on two strings is lexicographic by UTF-16 code unit, which matches for ASCII; do not wrap strings in `Number()`.

## COS

- **Summary:** cosine of an angle in radians
- **Signature:** `COS(x)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/cos/

**Arguments**

- `x` (required): Number (radians).

**Returns:** Number between -1 and 1.

**Porting semantics**

- Not specified in docs: null or text input; the docs give no examples.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: COS(0)
output:  1

# 2
formula: COS(3.141592653589793)
output:  -1
```

**TypeScript equivalent**

```ts
Math.cos(Number(x))
```
