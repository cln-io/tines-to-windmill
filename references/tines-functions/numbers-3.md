# Tines formula functions: Numbers (part 3 of 3: POWER to TIMES)

Independent, unofficial porting notes for the functions Tines files under "Numbers": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: POWER, RANDOM, ROUND, SIN, SQRT, TIMES

## POWER

- **Summary:** raise a number to a power
- **Signature:** `POWER(base, exponent)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/power/

**Arguments**

- `base` (required): The base.
- `exponent` (required): The exponent.

**Returns:** Number.

**Porting semantics**

- Not specified in docs: negative or fractional exponents; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: POWER(5, 3)
output:  125

# 2
formula: POWER(2, 10)
output:  1024
```

**TypeScript equivalent**

```ts
Number(base) ** Number(exponent)
```

- `^` is XOR in JS, not exponentiation.

## RANDOM

- **Summary:** random number within a range
- **Signature:** `RANDOM(min, max)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/random/

**Arguments**

- `min` (required): Lower end of the range.
- `max` (required): Upper end of the range.

**Returns:** A random number within the range.

**Porting semantics**

- Not specified in docs: whether the bounds are inclusive; whether decimals can be returned; min greater than max.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: RANDOM(20, 25)
output:  a number from 20 to 25, e.g. 23
```

**TypeScript equivalent** (APPROXIMATE: assumes whole numbers with both bounds inclusive)

```ts
Math.floor(Math.random() * (Number(max) - Number(min) + 1)) + Number(min)
```

## ROUND

- **Summary:** round a number to whole or to a given precision
- **Signature:** `ROUND(number, [precision])`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/round/

**Arguments**

- `number` (required): The number to round.
- `precision` (optional): Number of decimal places; default 0 (nearest whole number).

**Returns:** Number.

**Porting semantics**

- Not specified in docs: tie-breaking for exact halves (2.5, -2.5); negative precision; text input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: ROUND(8.4)
output:  8

# 2
formula: ROUND(8.6)
output:  9

# 3
formula: ROUND(19.8765, 2)
output:  19.88
```

**TypeScript equivalent**

```ts
// Halves round away from zero (assumption, see notes).
function round(n: number, precision = 0): number {
  const x = Number(n);
  return Math.sign(x) * Number(Math.round(Number(`${Math.abs(x)}e${precision}`)) + `e-${precision}`);
}
```

- Assumption, not specified in docs: exact halves round away from zero (`2.5` to `3`, `-2.5` to `-3`), which is how Ruby, the language Tines is built on, rounds. The docs do not show a tie. Flag it if a port depends on ties.
- Bare `Math.round` rounds halves toward +Infinity (`-2.5` gives `-2`), hence the sign handling.
- `Math.round(n * 100) / 100` and `Number(n.toFixed(2))` suffer float error (`1.005` gives `1`); the exponent form above avoids it. `n.toFixed(2)` alone returns a string.

## SIN

- **Summary:** sine of an angle in radians
- **Signature:** `SIN(x)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sin/

**Arguments**

- `x` (required): Number (radians).

**Returns:** Number between -1 and 1. (The Tines page states a different range, which looks like a slip.)

**Porting semantics**

- Not specified in docs: null or text input; the docs give no examples.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SIN(0)
output:  0

# 2
formula: SIN(1.5707963267948966)
output:  1
```

**TypeScript equivalent**

```ts
Math.sin(Number(x))
```

## SQRT

- **Summary:** square root of a number
- **Signature:** `SQRT(x)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/sqrt/

**Arguments**

- `x` (required): Number.

**Returns:** Number.

**Porting semantics**

- Not specified in docs: negative input; text or null input; the docs give no examples.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SQRT(144)
output:  12

# 2
formula: SQRT(2.25)
output:  1.5
```

**TypeScript equivalent**

```ts
Math.sqrt(Number(x))
```

- JS returns `NaN` for negative input; Tines behaviour is not specified.

## TIMES

- **Summary:** multiply two numbers
- **Signature:** `TIMES(number, number)`
- **Categories:** Numbers
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/times/

**Arguments**

- `number` (required): First number.
- `number` (required): Second number.

**Returns:** Number: the product.

**Porting semantics**

- Not specified in docs: text or null arguments.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TIMES(12, 2.5)
output:  30
```

**TypeScript equivalent**

```ts
Number(a) * Number(b)
```
