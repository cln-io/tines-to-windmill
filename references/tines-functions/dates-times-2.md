# Tines formula functions: Dates/Times (part 2 of 2: MONTH to YEAR)

Independent, unofficial porting notes for the functions Tines files under "Dates/Times": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: MONTH, NOW, SECOND, TODAY, UNIX_TIMESTAMP, YEAR

## MONTH

- **Summary:** month of the year of a date
- **Signature:** `MONTH(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/month/

**Arguments**

- `date` (required): Date text in year-month-day order, with or without a time part.

**Returns:** The month number, 1-based, shown as text without zero padding in the docs example (`"3"` for March).

**Porting semantics**

- The docs show the result as text rather than a number, without a leading zero; SECOND is the one date-part function shown returning a number.
- Not specified in docs: which time zone is used when the input has a non-UTC offset; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MONTH("2025-09-08T14:05:00Z")
output:  "9"

# 2
formula: MONTH("2024-12-31T23:59:59Z")
output:  "12"
```

**TypeScript equivalent** (APPROXIMATE: assumes UTC and an ISO-parseable input)

```ts
String(new Date(date).getUTCMonth() + 1)
```

- JS months are 0-based: forgetting the `+ 1` gives February for a March date.

## NOW

- **Summary:** current UTC date-time as ISO 8601 text
- **Signature:** `NOW()`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/now/

**Arguments**

- None.

**Returns:** A timestamp for the present instant: ISO 8601 text, UTC, millisecond precision, written with a `+00:00` offset.

**Porting semantics**

- The result is text, not a number: it cannot be used directly in arithmetic. For date arithmetic use UNIX_TIMESTAMP() (seconds).
- A docs example on another page adds a duration to NOW(); that contradicts this page, which is the one to follow.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: NOW()
output:  text shaped like "2031-07-04T08:15:42.117+00:00" (the current time)
```

**TypeScript equivalent**

```ts
new Date().toISOString().replace("Z", "+00:00")
```

- `toISOString()` ends in `Z`; Tines shows `+00:00`. Both are valid ISO 8601, but the text differs if it is compared or stored.

## SECOND

- **Summary:** second of the minute of a date
- **Signature:** `SECOND(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/second/

**Arguments**

- `date` (required): Date/time text (the example uses a full ISO 8601 timestamp).

**Returns:** The second, shown as the number `1` in the docs example (not text, unlike DAY/MONTH/YEAR/HOUR/MINUTE whose examples show text).

**Porting semantics**

- Not specified in docs: accepted formats; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: SECOND("2025-09-08T14:05:37Z")
output:  37
```

**TypeScript equivalent** (APPROXIMATE: assumes an ISO-parseable input)

```ts
new Date(date).getUTCSeconds()
```

## TODAY

- **Summary:** current UTC date as YYYY-MM-DD text
- **Signature:** `TODAY()`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/today/

**Arguments**

- None.

**Returns:** Today's UTC calendar date, as text laid out year-month-day.

**Porting semantics**

- The result is text, not a number. For date arithmetic use UNIX_TIMESTAMP() (seconds).

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: TODAY()
output:  text shaped like "2031-07-04" (today's date in UTC)
```

**TypeScript equivalent**

```ts
new Date().toISOString().slice(0, 10)
```

- Do not build it from `getFullYear()`/`getMonth()`/`getDate()`: those use the worker's local zone.

## UNIX_TIMESTAMP

- **Summary:** current unix timestamp in seconds
- **Signature:** `UNIX_TIMESTAMP()`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/unix-timestamp/

**Arguments**

- None.

**Returns:** Number: whole seconds elapsed since the start of 1970 (UTC).

**Porting semantics**

- Takes no arguments; to convert a given date use `DATE(x, "%s")` or `DATE_PARSE(x).unix_timestamp`.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: UNIX_TIMESTAMP()
output:  the current time as a whole number of seconds, e.g. 1940000000
```

**TypeScript equivalent**

```ts
Math.floor(Date.now() / 1000)
```

- `Date.now()` is milliseconds; forgetting the division is a factor-1000 bug.

## YEAR

- **Summary:** year of a date
- **Signature:** `YEAR(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/year/

**Arguments**

- `date` (required): Date text (the example uses a full ISO 8601 timestamp).

**Returns:** The year, shown as text in the docs example (`"2022"`).

**Porting semantics**

- The docs show the result as text rather than a number; SECOND is the one date-part function shown returning a number.
- Not specified in docs: accepted formats; which time zone is used when the input has a non-UTC offset; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: YEAR("2025-09-08T14:05:00Z")
output:  "2025"
```

**TypeScript equivalent** (APPROXIMATE: assumes UTC and an ISO-parseable input)

```ts
String(new Date(date).getUTCFullYear())
```

- Use `getUTCFullYear()`, never `getYear()`.
