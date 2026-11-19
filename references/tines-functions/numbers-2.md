# Tines formula functions: Numbers (part 2 of 3: DIVIDED_BY to PLUS)

Independent, unofficial porting notes for the functions Tines files under "Numbers": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: DIVIDED_BY, FLOOR, MAX, MEDIAN, MIN, MINUS, MODULO, NUMBER, PLUS

## DIVIDED_BY

- **Summary:** divide a number by another (floors when the divisor is whole)
- **Signature:** `DIVIDED_BY(number, denominator)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/divided-by/

**Arguments**

- `number` (required): The numerator.
- `denominator` (required): The number to divide by.

**Returns:** Number.

**Porting semantics**

- A whole-number divisor makes the result a whole number, rounded down. The rule is stated for the divisor, so it applies whatever the numerator is.
- A divisor with decimals gives a result with decimals; writing the divisor as `4.0`, or multiplying it by `1.0`, is the way to force that.
- The `/` operator raises an error when dividing by zero.
- Not specified in docs: DIVIDED_BY with a zero denominator (this helper throws, by analogy with the `/` operator); rounding direction for negative results ("rounded down" is taken as floor); text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DIVIDED_BY(14, 4)
output:  3

# 2 - the formula writes a decimal divisor
formula: DIVIDED_BY(14, 4.0)
output:  3.5

# 3
formula: DIVIDED_BY(9, 2.5)
output:  3.6
```

**TypeScript equivalent**

```ts
// wholeDivisor: true when the divisor is a whole number in the formula (no `3.0`, no `* 1.0`)
function dividedBy(n: number, d: number, wholeDivisor = Number.isInteger(d)): number {
  if (d === 0) throw new Error("divided by 0"); // assumption: not specified in docs for DIVIDED_BY
  return wholeDivisor ? Math.floor(n / d) : n / d;
}
```

- Plain `a / b` is wrong for a whole divisor: JS gives `3.5` where Tines gives `3`.
- JS cannot tell `4.0` from `4` (and JSON `4.0` parses to `4`). When the formula writes the divisor with a decimal point or multiplies it by `1.0`, pass `wholeDivisor = false` explicitly.
- JS division by zero yields `Infinity`/`NaN` and never throws, so an `IF_ERROR(a / b, ...)` port needs an explicit zero check.

## FLOOR

- **Summary:** round down to a whole number
- **Signature:** `FLOOR(number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/floor/

**Arguments**

- `number` (required): A number, or numeric text.

**Returns:** Whole number.

**Porting semantics**

- Numeric text is converted first.
- Not specified in docs: null/blank input; non-numeric text; negative numbers (no example).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: FLOOR(7.99)
output:  7

# 2
formula: FLOOR("12.5")
output:  12
```

**TypeScript equivalent**

```ts
Math.floor(Number(number))
```

## MAX

- **Summary:** highest numeric value of an array or of the arguments
- **Signature:** `MAX(array) or MAX(number1, number2, ...)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/max/

**Arguments**

- `array` (required): Either a single array, or
- `number1, number2, ...` (required): multiple arguments (alternative form).

**Returns:** The largest of the values.

**Porting semantics**

- Not specified in docs: empty array; numeric text members; null members.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MAX([4, 19, 7])
output:  19

# 2
formula: MAX(2.5, -1)
output:  2.5
```

**TypeScript equivalent**

```ts
function max(...args: any[]): number {
  const xs: any[] = args.length === 1 && Array.isArray(args[0]) ? args[0] : args;
  return Math.max(...xs.map(Number));
}
```

- `Math.max()` of an empty list is `-Infinity`; Tines behaviour is not specified.
- `Math.max(array)` without spreading gives `NaN`.

## MEDIAN

- **Summary:** median of an array or of the arguments
- **Signature:** `MEDIAN(array) or MEDIAN(number1, number2, ...)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/median/

**Arguments**

- `array` (required): Either a single array of numbers, or
- `number1, number2, ...` (required): multiple numeric arguments (alternative form).

**Returns:** Number: the median. For an even count, the mean of the two middle values (`[1, 2, 3, 4]` gives `2.5`).

**Porting semantics**

- Not specified in docs: empty array; non-numeric members.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MEDIAN([9, 1, 5])
output:  5

# 2 - even count: mean of the two middle values
formula: MEDIAN(10, 2, 8, 4)
output:  6
```

**TypeScript equivalent**

```ts
function median(...args: any[]): number {
  const xs: number[] = (args.length === 1 && Array.isArray(args[0]) ? args[0] : args).map(Number).sort((a: number, b: number) => a - b);
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
}
```

- Sort with a numeric comparator; the default JS sort is lexicographic (`[10, 9]` stays `[10, 9]`).

## MIN

- **Summary:** lowest numeric value of an array or of the arguments
- **Signature:** `MIN(array) or MIN(number1, number2, ...)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/min/

**Arguments**

- `array` (required): Either a single array, or
- `number1, number2, ...` (required): multiple arguments (alternative form).

**Returns:** The smallest of the values.

**Porting semantics**

- Not specified in docs: empty array; numeric text members; null members.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MIN([4, 19, 7])
output:  4

# 2
formula: MIN(2.5, -1)
output:  -1
```

**TypeScript equivalent**

```ts
function min(...args: any[]): number {
  const xs: any[] = args.length === 1 && Array.isArray(args[0]) ? args[0] : args;
  return Math.min(...xs.map(Number));
}
```

- `Math.min()` of an empty list is `Infinity`; Tines behaviour is not specified.
- `Number(null)` is `0`, so a null member silently becomes the minimum - filter nulls first if they can occur.

## MINUS

- **Summary:** subtract one number from another
- **Signature:** `MINUS(number, number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/minus/

**Arguments**

- `number` (required): The number to subtract from.
- `number` (required): The number to subtract.

**Returns:** Number (first minus second).

**Porting semantics**

- Not specified in docs: text or null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MINUS(20, 7.5)
output:  12.5
```

**TypeScript equivalent**

```ts
Number(a) - Number(b)
```

## MODULO

- **Summary:** remainder of a division
- **Signature:** `MODULO(numerator, denominator)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/modulo/

**Arguments**

- `numerator` (required): The number to divide.
- `denominator` (required): The number to divide by.

**Returns:** Number: what is left over after dividing the first argument by the second.

**Porting semantics**

- Not specified in docs: sign of the result for negative operands; zero denominator; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MODULO(29, 6)
output:  5

# 2
formula: MODULO(7.5, 2)
output:  1.5
```

**TypeScript equivalent**

```ts
((Number(numerator) % Number(denominator)) + Number(denominator)) % Number(denominator)
```

- Assumption, not specified in docs: for negative operands the result takes the sign of the denominator (`MODULO(-7, 3)` is `2`), which is how Ruby, the language Tines is built on, defines modulo. The docs only show positive operands. Bare JS `a % b` gives `-1` there. For positive operands the two forms agree.
- Float noise: with decimal operands JS can return a value such as `1.2999999999999998` where exact arithmetic gives `1.3`. Round if the value is displayed or compared: `Number(result.toFixed(10))`.
- A zero denominator gives `NaN` in JS; Tines behaviour is not specified.

## NUMBER

- **Summary:** convert a value to a number
- **Signature:** `NUMBER(value)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/number/

**Arguments**

- `value` (required): Value to convert, typically numeric text.

**Returns:** Number; whole or decimal, positive or negative, according to the text.

**Porting semantics**

- Not specified in docs: non-numeric text; blank text; null; booleans; text with surrounding spaces or units.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: NUMBER("250")
output:  250

# 2
formula: NUMBER("-0.75")
output:  -0.75
```

**TypeScript equivalent**

```ts
Number(value)
```

- JS specifics not covered by the docs: `Number("")` and `Number(null)` are `0`, `Number("abc")` is `NaN`, `Number("12px")` is `NaN`. Validate the input if those cases can occur.
- Do not use `parseInt` (drops decimals, accepts trailing garbage).

## PLUS

- **Summary:** add two numbers
- **Signature:** `PLUS(number, number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/plus/

**Arguments**

- `number` (required): First number.
- `number` (required): Second number.

**Returns:** Number: the sum.

**Porting semantics**

- Not specified in docs: text or null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PLUS(19, 2.5)
output:  21.5

# 2
formula: PLUS(-3, 10)
output:  7
```

**TypeScript equivalent**

```ts
Number(a) + Number(b)
```

- Bare `a + b` concatenates when either operand is a string (`"4" + 2` is `"42"`). Event data often carries numbers as text, so keep the `Number()` calls. The same applies when porting the Tines `+` operator; Tines concatenation is the separate `&` operator.
