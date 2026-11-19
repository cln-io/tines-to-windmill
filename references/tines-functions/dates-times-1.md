# Tines formula functions: Dates/Times (part 1 of 2: DATE to MINUTE)

Independent, unofficial porting notes for the functions Tines files under "Dates/Times": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: DATE, DATE_DIFF, DATE_PARSE, DAY, DISTANCE_OF_TIME_IN_WORDS, HOUR, MINUTE

## DATE

- **Summary:** format a date as text (strftime)
- **Signature:** `DATE(date, format, timezone)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/date/

**Arguments**

- `date` (required): Date text, a whole-number unix timestamp, or an object returned by DATE_PARSE. Free-form and relative wording ("yesterday", "next friday at 9am", "now") is understood.
- `format` (optional): Ruby `strftime` pattern for the result. Omitted: ISO 8601 in UTC with milliseconds and a `Z` suffix.
- `timezone` (optional): tz database zone name in which the result is expressed.

**Returns:** The formatted date as text. Text that cannot be read as a date comes back exactly as it was passed.

**Porting semantics**

- A number is taken as unix seconds; once it has 13 or more digits it is taken as milliseconds.
- A date written with slashes whose day and month could be swapped is read day first.
- When the text names a whole period, such as a month, the result is the first instant of that period.
- Unreadable text is passed through; no error is raised.
- The result is text even when it looks like a number. `NOW()` and `TODAY()` are text too, so date arithmetic starts from `UNIX_TIMESTAMP()` (seconds) instead.
- Free-form text is interpreted by the Ruby library chronic, which can silently misread a phrase it does not know rather than reject it.
- Not specified in docs: the zone assumed when none is given (UTC here); null or blank input; an unknown zone name.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - unix seconds, shown in another zone
formula: DATE(1757340300, "%A %d %B, %H:%M", "Australia/Sydney")
output:  "Tuesday 09 September, 00:05"

# 2 - day first
formula: DATE("03/04/2025", "%-d %B")
output:  "3 April"

# 3 - unreadable text comes back unchanged
formula: DATE("sometime soonish", "%Y")
output:  "sometime soonish"
```

**TypeScript equivalent** (APPROXIMATE: natural-language parsing (chrono-node vs Ruby chronic) and uncommon strftime directives will not match exactly)

```ts
import * as chrono from "chrono-node"; // only needed for natural-language / non-ISO text input
function toDate(v: unknown): Date | null {
  if (v !== null && typeof v === "object" && "unix_timestamp_milliseconds" in v) return new Date((v as any).unix_timestamp_milliseconds);
  if (typeof v === "number" || (typeof v === "string" && /^\d{9,}$/.test(v))) {
    const n = Number(v);
    return new Date(String(Math.trunc(n)).length >= 13 ? n : n * 1000); // 13+ digits = milliseconds
  }
  if (typeof v !== "string") return null;
  if (v === "now" || v === "today") return new Date();
  // text with a time but no offset is taken as UTC (JS alone would read it as local time)
  const iso = new Date(/\d:\d/.test(v) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(v) ? v.replace(" ", "T") + "Z" : v);
  if (/^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}.*)?$/.test(v) && !isNaN(iso.getTime())) return iso;
  const r = chrono.en.GB.parse(v, { instant: new Date(), timezone: "UTC" })[0]; // GB locale: ambiguous dates are DD/MM/YYYY
  const d = r ? r.start.date() : null;
  if (d && !r.start.isCertain("hour")) d.setUTCHours(0, 0, 0, 0); // bare dates and spans start at 00:00 (chrono defaults to noon)
  return d;
}
// Takes the Ruby strftime format unchanged. Supports %Y %y %m %d %e %H %I %M %S %L %p %B %b %A %a %s %z %:z %Z %F %T %% and %-d style.
function strftime(d: Date, fmt: string, tz = "UTC"): string {
  const opts: Intl.DateTimeFormatOptions = { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "long", timeZoneName: "short" };
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", opts).formatToParts(d).map((x) => [x.type, x.value]));
  const month = new Intl.DateTimeFormat("en-US", { timeZone: tz, month: "long" }).format(d);
  const wall = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  const off = Math.round((wall - Math.floor(d.getTime() / 1000) * 1000) / 60000); // minutes east of UTC
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  const z = (sep: string) => (off < 0 ? "-" : "+") + pad(Math.floor(Math.abs(off) / 60)) + sep + pad(Math.abs(off) % 60);
  const m: Record<string, string> = {
    Y: p.year, y: p.year.slice(-2), m: p.month, d: p.day, e: p.day.replace(/^0/, " "),
    H: p.hour, I: pad(+p.hour % 12 || 12), M: p.minute, S: p.second, L: pad(d.getUTCMilliseconds(), 3),
    p: +p.hour < 12 ? "AM" : "PM", B: month, b: month.slice(0, 3), A: p.weekday, a: p.weekday.slice(0, 3),
    s: String(Math.floor(d.getTime() / 1000)), z: z(""), Z: tz === "UTC" ? "UTC" : p.timeZoneName, "%": "%",
  };
  return fmt.replace(/%F/g, "%Y-%m-%d").replace(/%T/g, "%H:%M:%S").replace(/%:z/g, z(":"))
    .replace(/%(-?)([a-zA-Z%])/g, (all, dash, c) => (c in m ? (dash ? m[c].replace(/^[0 ]+(?=.)/, "") : m[c]) : all));
}
function tinesDate(v: unknown, fmt?: string, tz = "UTC"): unknown {
  const d = toDate(v);
  if (!d) return v; // unparseable input is returned unchanged
  return fmt === undefined ? d.toISOString() : strftime(d, fmt, tz);
}
```

- npm package: `chrono-node`, needed only for natural-language or non-ISO text. If the story only passes ISO timestamps, unix numbers or the word "now", delete the import and the chrono block in `toDate` (return null instead).
- Pass the Tines pattern as it is. Do not hand it to date-fns or dayjs: their tokens (`yyyy`, `YYYY`) are a different language.
- The directive meanings implemented in `strftime` are Ruby's (the Tines page only links to Ruby's docs); directives not listed in the comment are left in the output untouched.
- `%Z` prints `UTC` for UTC but names like `GMT+9` for most other zones, where Tines prints an abbreviation; hard-code the abbreviation if the text matters.
- Assumption, not specified in docs: text made only of digits (9 or more) is read as a unix timestamp like a number would be.
- A pattern of `%s` gives unix seconds as text; wrap the result in `Number()` when the formula does arithmetic with it.
- JS `new Date("03/04/2025")` reads month first (US style), the opposite of Tines. Never use it for slash dates.
- Text without an offset is read as UTC.

## DATE_DIFF

- **Summary:** difference between two times as an object
- **Signature:** `DATE_DIFF(start_time, end_time, [absolute: TRUE])`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/date-diff/

**Arguments**

- `start_time` (required): Start time (examples use ISO 8601 text with offsets).
- `end_time` (required): End time.
- `absolute` (optional): Keyword argument, default `TRUE`. With `absolute: FALSE`, values are negative when start is after end.

**Returns:** Object with five totals (`seconds`, `minutes`, `hours`, `days`, `weeks`) and a nested `units` object that breaks the difference down by calendar unit, from `years` to `seconds`.

**Porting semantics**

- The five top-level fields each express the whole difference in that unit; hours, days and weeks are rounded to two decimals.
- `units` splits the same difference calendar-wise, so month lengths and leap years are respected.
- Offsets in the inputs are honoured.
- By default all values are positive whichever date comes first; with `absolute: FALSE` they are negative when the start is later than the end.
- Not specified in docs: accepted input forms other than ISO 8601 text; input that cannot be read; how `minutes` is rounded.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - crosses a leap day
formula: DATE_DIFF("2024-02-28T08:00:00Z", "2024-03-01T20:30:00Z")
output:  {"seconds": 217800, "minutes": 3630, "hours": 60.5, "days": 2.52, "weeks": 0.36, "units": {"years": 0, "months": 0, "weeks": 0, "days": 2, "hours": 12, "minutes": 30, "seconds": 0}}

# 2
formula: DATE_DIFF("2024-03-01T20:30:00Z", "2024-02-28T08:00:00Z", absolute: FALSE).hours
output:  -60.5
```

**TypeScript equivalent** (APPROXIMATE: calendar breakdown via date-fns may differ from Tines at month-end edge cases)

```ts
import { intervalToDuration } from "date-fns";
function dateDiff(start: string | number, end: string | number, absolute = true) {
  let a = new Date(start).getTime(), b = new Date(end).getTime();
  const sign = !absolute && a > b ? -1 : 1;
  if (a > b) [a, b] = [b, a];
  const secs = Math.floor((b - a) / 1000);
  const r2 = (n: number) => Math.round(n * 100) / 100;
  const s = (n: number) => (n === 0 ? 0 : sign * n);
  const d = intervalToDuration({ start: a, end: b });
  const days = d.days ?? 0;
  return {
    seconds: s(secs), minutes: s(r2(secs / 60)), hours: s(r2(secs / 3600)), days: s(r2(secs / 86400)), weeks: s(r2(secs / 604800)),
    units: { years: s(d.years ?? 0), months: s(d.months ?? 0), weeks: s(Math.floor(days / 7)), days: s(days % 7),
      hours: s(d.hours ?? 0), minutes: s(d.minutes ?? 0), seconds: s(d.seconds ?? 0) },
  };
}
```

- npm package: `date-fns`. `intervalToDuration` does calendar math in the runtime's local zone; run workers in UTC.
- If the story only reads `.seconds`, skip the helper and the package: `Math.floor(Math.abs(new Date(end).getTime() - new Date(start).getTime()) / 1000)`.

## DATE_PARSE

- **Summary:** parse a date into an object of fields
- **Signature:** `DATE_PARSE(date, format, timezone)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/date-parse/

**Arguments**

- `date` (required): Date text, a unix timestamp in seconds or milliseconds, or the words "now" / "today".
- `format` (optional): Ruby `strptime` pattern describing how the text is laid out. Without it the layout is guessed.
- `timezone` (optional): tz database zone name; the text is read as local time in that zone.

**Returns:** Object with the fields `iso8601`, `iso8601_milliseconds`, `unix_timestamp`, `unix_timestamp_milliseconds`, `year`, `month`, `month_name`, `day`, `day_of_week`, `day_name`, `hour`, `minute`, `second`, `millisecond`, `timezone`, `utc_offset`, `utc_offset_seconds`.

**Porting semantics**

- `month` counts from 1. `day_of_week` is a number in which Monday is 1 and Saturday is 6.
- `timezone` is a zone abbreviation, `utc_offset` is text in `+hh:mm` form, `utc_offset_seconds` is a number.
- Without a zone argument the result is in UTC.
- The object can be handed to DATE, and single fields can be read with dot notation directly on the call.
- Free-form text is interpreted by the Ruby library chronic.
- Not specified in docs: result for text that cannot be read; the `day_of_week` number for Sunday.

**Examples (illustrative, not from the Tines docs)**

```text
# 1 - selected fields
formula: DATE_PARSE("08.09.2025", "%d.%m.%Y")
output:  {"iso8601": "2025-09-08T00:00:00+00:00", "unix_timestamp": 1757289600, "month": 9, "month_name": "September", "day": 8, "day_name": "Monday", "day_of_week": 1}

# 2
formula: DATE_PARSE("2025-06-14 09:30", "%Y-%m-%d %H:%M", "Europe/Paris").utc_offset_seconds
output:  7200
```

**TypeScript equivalent** (APPROXIMATE: format guessing and natural-language parsing cannot be matched exactly; translate the fixed strptime format by hand)

```ts
import { parse } from "date-fns";
import { formatInTimeZone, fromZonedTime, getTimezoneOffset } from "date-fns-tz";
// 1) Turn the input into a Date. For a known format translate strptime to date-fns tokens (table below):
//    DATE_PARSE("17.03.2024", "%d.%m.%Y")  ->  fromZonedTime(parse("17.03.2024", "dd.MM.yyyy", new Date(0)), "UTC")
//    numbers: new Date(n >= 1e12 ? n : n * 1000);   "now": new Date()
// 2) Build the Tines-shaped object:
function dateParts(d: Date, tz = "UTC") {
  const f = (p: string) => formatInTimeZone(d, tz, p);
  return {
    iso8601: f("yyyy-MM-dd'T'HH:mm:ssxxx"), iso8601_milliseconds: f("yyyy-MM-dd'T'HH:mm:ss.SSSxxx"),
    unix_timestamp: Math.floor(d.getTime() / 1000), unix_timestamp_milliseconds: d.getTime(),
    year: +f("yyyy"), month: +f("M"), month_name: f("MMMM"), day: +f("d"),
    day_of_week: +f("i") % 7, day_name: f("EEEE"),
    hour: +f("H"), minute: +f("m"), second: +f("s"), millisecond: +f("SSS"),
    timezone: f("zzz"), utc_offset: f("xxx"), utc_offset_seconds: getTimezoneOffset(tz, d) / 1000,
  };
}
```

- npm packages: `date-fns`, `date-fns-tz`. Natural-language input needs `chrono-node` (see DATE).
- strptime to date-fns tokens (my mapping; the Tines page only links to Ruby's docs): `%Y` yyyy, `%y` yy, `%m` MM, `%d` dd, `%H` HH, `%I` hh, `%M` mm, `%S` ss, `%L` SSS, `%p` a, `%b` MMM, `%B` MMMM, `%a` EEE, `%A` EEEE, `%z` xx, `%Z` zzz, `%s` t.
- `date-fns` `parse` reads the text in the runtime's local zone; wrap with `fromZonedTime(..., tz)` as shown so the result does not depend on the worker's zone.
- The `timezone` field comes out as `UTC` for UTC but as an offset like `GMT+2` for most other zones, where Tines gives an abbreviation.
- `+f("i") % 7` assumes Sunday is 0; the docs do not show a Sunday.

## DAY

- **Summary:** day of the month of a date
- **Signature:** `DAY(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/day/

**Arguments**

- `date` (required): Date text in year-month-day order, with or without a time part.

**Returns:** The day of the month, shown as text in the docs example (`"19"`).

**Porting semantics**

- The docs show the result as text rather than a number; SECOND is the one date-part function shown returning a number.
- Not specified in docs: zero padding for days below 10; which time zone is used when the input has a non-UTC offset; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DAY("2025-09-18T14:05:00Z")
output:  "18"

# 2
formula: DAY("2024-12-31T23:59:59Z")
output:  "31"
```

**TypeScript equivalent** (APPROXIMATE: assumes UTC and an ISO-parseable input)

```ts
String(new Date(date).getUTCDate())
```

- Use `getUTCDate()`, not `getDate()` (local zone) and not `getDay()` (day of week).

## DISTANCE_OF_TIME_IN_WORDS

- **Summary:** human-readable distance between two times
- **Signature:** `DISTANCE_OF_TIME_IN_WORDS(date, [from])`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/distance-of-time-in-words/

**Arguments**

- `date` (required): The date/time to describe.
- `from` (optional): The moment to measure from; the current time when omitted.

**Returns:** A phrase such as "3 days ago" or "in about 2 hours".

**Porting semantics**

- A moment in the past ends with "ago"; a moment in the future starts with "in".
- Below a minute and a half the wording moves in coarse steps (a few seconds, then half a minute, then about a minute) instead of giving an exact count.
- Not specified in docs: the full wording table above 90 seconds; accepted input formats; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: DISTANCE_OF_TIME_IN_WORDS("2025-09-11T12:00:00Z", "2025-09-08T12:00:00Z")
output:  "in 3 days"

# 2
formula: DISTANCE_OF_TIME_IN_WORDS("2025-09-08T11:59:30Z", "2025-09-08T12:00:00Z")
output:  "half a minute ago"
```

**TypeScript equivalent** (APPROXIMATE: date-fns wording is close to, but not guaranteed identical to, Tines' wording)

```ts
import { formatDistance } from "date-fns";
formatDistance(new Date(date), from ? new Date(from) : new Date(), { addSuffix: true, includeSeconds: true })
```

- npm package: `date-fns`.

## HOUR

- **Summary:** hour of the day of a date
- **Signature:** `HOUR(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/hour/

**Arguments**

- `date` (required): A time or a date-time: a bare clock time, a clock time with a leading `T` and an offset, or a full ISO 8601 timestamp.

**Returns:** The hour, shown as text in the docs example (`"17"`).

**Porting semantics**

- The docs show the result as text rather than a number; SECOND is the one date-part function shown returning a number.
- Not specified in docs: zero padding for hours below 10; which time zone is used when the input has a non-UTC offset; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: HOUR("2025-09-08T14:05:00Z")
output:  "14"
```

**TypeScript equivalent** (APPROXIMATE: assumes UTC and a full ISO timestamp; time-only inputs need a date prefix)

```ts
String(new Date(date).getUTCHours())
// time-only input such as "17:49:01": String(new Date(`1970-01-01T${time.replace(/^T/, "")}`).getUTCHours())  (add "Z" if it has no offset)
```

## MINUTE

- **Summary:** minute of the hour of a date
- **Signature:** `MINUTE(date)`
- **Categories:** Dates/Times
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/minute/

**Arguments**

- `date` (required): A time or a date-time: a bare clock time, a clock time with a leading `T` and an offset, or a full ISO 8601 timestamp.

**Returns:** The minute, shown as text in the docs example (`"49"`).

**Porting semantics**

- The docs show the result as text rather than a number; SECOND is the one date-part function shown returning a number.
- Not specified in docs: zero padding for minutes below 10; time zone handling for offsets that are not whole hours; unparseable input.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: MINUTE("2025-09-08T14:25:00Z")
output:  "25"
```

**TypeScript equivalent** (APPROXIMATE: assumes a full ISO timestamp; time-only inputs need a date prefix)

```ts
String(new Date(date).getUTCMinutes())
```
