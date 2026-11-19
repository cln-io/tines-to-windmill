# Tines formulas -> TypeScript: function lookup

Use this file to translate the functions inside a Tines option value into TypeScript. All 227 functions of the official reference (tines.com/docs/formulas, Nov 2026) are in section 2. "unverified" = the docs do not settle it.

**Optional catalogue.** `python3 scripts/tines_fn.py NAME` prints a longer entry for one function (every argument, edge cases, a tested helper) from `references/tines-functions/`. That folder is local material and is not shipped with this skill: to build it, download the function pages with `python3 scripts/fetch_tines_function_docs.py <dir>` and write one `## NAME` entry per function. This table stands on its own without it; a row that mentions the catalogue still gives the safe short form.

Companion files: syntax, operators, references, lambdas, truthiness and text-mode control tags are in [tines-formula-language.md](tines-formula-language.md); eleven worked translations are in [tines-formulas-examples.md](tines-formulas-examples.md).

**Contents:** [1 Helpers](#1-helpers) | [2 Function tables](#2-function-tables) | [3 Traps](#3-traps) | [4 Legacy Liquid](#4-legacy-liquid) | [5 Unverified](#5-unverified)

**Procedure:** (1) classify the value and rewrite references, operators, pipes and tags with the language file; (2) rewrite each function with section 2, innermost first; (3) check section 3.

**Syntax recap** (details in the language file):

```text
"a <<expr>> b"        text mode: always a string          `a ${text(expr)} b`
"=expr"               formula field: keeps its type       expr
action_slug.a.b       upstream action output              action_slug?.a?.b          (missing key = null)
a = b                 equality                            a === b
a & b                 text concatenation                  text(a) + text(b)
f(x) |> g(%, y)       pipe, % = left result               g(f(x), y)
LAMBDA(a, b, body)    function                            (a, b) => body
TRUE FALSE NULL       literals                            true false null
condition             only FALSE and NULL are falsy       truthy(v)                  (0 and "" are truthy)
<%if c%> <%for x in arr%> ... <%endif%> <%endfor%>        control tags: build the text with statements
```

A table one-liner is a single expression. Anything needing a helper, an `import`, `await` or `try` must live in a script step, not in a single-expression input transform.

## 1 Helpers

Paste only the helpers a step uses. All were run against the examples in the Tines docs.

```ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
const truthy = (v: any): boolean => v !== false && v != null;
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
// Path lookup for GET / MAP / WHERE / SORT: "a.b.c", "a[0].b", 'user["User ID"]'. Escaped dots ("a\.b") are not handled.
const get = (o: any, path: string): any =>
  (path.match(/[^.\[\]"']+/g) ?? []).reduce((a: any, k: string) => a?.[k], o) ?? null;
// DATE input -> Date, or null when it cannot be read. Text without an offset is taken as UTC.
// Needs `import * as chrono from "chrono-node"` only for natural-language or non-ISO text; otherwise delete the chrono lines.
function toDate(v: any): Date | null {
  if (v !== null && typeof v === "object" && "unix_timestamp_milliseconds" in v) return new Date(v.unix_timestamp_milliseconds);
  if (typeof v === "number" || (typeof v === "string" && /^\d{9,}$/.test(v)))    // digit-only text: assumed to be a timestamp
    return new Date(Number(v) * (String(Math.trunc(Number(v))).length >= 13 ? 1 : 1000));   // 13+ digits = milliseconds
  if (typeof v !== "string") return null;
  if (v === "now" || v === "today") return new Date();
  const iso = new Date(/\d:\d/.test(v) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(v) ? v.replace(" ", "T") + "Z" : v);
  if (/^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}.*)?$/.test(v) && !isNaN(iso.getTime())) return iso;
  const r = chrono.en.GB.parse(v, { instant: new Date(), timezone: "UTC" })[0];    // GB: ambiguous dates are DD/MM/YYYY
  const d = r ? r.start.date() : null;
  if (d && !r.start.isCertain("hour")) d.setUTCHours(0, 0, 0, 0);                  // a bare date or a span starts at 00:00
  return d;
}
// DATE output. Takes the Ruby strftime text unchanged: %Y %y %m %d %e %H %I %M %S %L %p %B %b %A %a %s %z %:z %Z %F %T %% and %-d style.
function strftime(d: Date, fmt: string, tz = "UTC"): string {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "long", timeZoneName: "short" }).formatToParts(d).map((x) => [x.type, x.value]));
  const month = new Intl.DateTimeFormat("en-US", { timeZone: tz, month: "long" }).format(d);
  const wall = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  const off = Math.round((wall - Math.floor(d.getTime() / 1000) * 1000) / 60000);  // minutes east of UTC
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  const z = (sep: string) => (off < 0 ? "-" : "+") + pad(Math.floor(Math.abs(off) / 60)) + sep + pad(Math.abs(off) % 60);
  const m: Record<string, string> = {
    Y: p.year, y: p.year.slice(-2), m: p.month, d: p.day, e: p.day.replace(/^0/, " "), H: p.hour, I: pad(+p.hour % 12 || 12),
    M: p.minute, S: p.second, L: pad(d.getUTCMilliseconds(), 3), p: +p.hour < 12 ? "AM" : "PM", B: month, b: month.slice(0, 3), A: p.weekday,
    a: p.weekday.slice(0, 3), s: String(Math.floor(d.getTime() / 1000)), z: z(""), Z: tz === "UTC" ? "UTC" : p.timeZoneName, "%": "%",
  };
  return fmt.replace(/%F/g, "%Y-%m-%d").replace(/%T/g, "%H:%M:%S").replace(/%:z/g, z(":"))
    .replace(/%(-?)([a-zA-Z%])/g, (all, dash, c) => (c in m ? (dash ? m[c].replace(/^[0 ]+(?=.)/, "") : m[c]) : all));
}
// DATE(x, fmt, tz): input that cannot be read is returned unchanged; no format = ISO 8601 with milliseconds.
const tinesDate = (v: any, fmt?: string, tz = "UTC"): any =>
  ((d) => (!d ? v : fmt === undefined ? d.toISOString() : strftime(d, fmt, tz)))(toDate(v));
const isObj = (v: any): boolean => typeof v === "object" && v !== null && !Array.isArray(v);
const deepMerge = (...objs: any[]): any =>       // DEEP_MERGE(a, b, ...): last wins, arrays are replaced
  objs.reduce((acc, o) => (Object.entries(o ?? {}).forEach(([k, v]) => (acc[k] = isObj(acc[k]) && isObj(v) ? deepMerge(acc[k], v) : v)), acc), {});
const sw = (v: any, ...a: any[]) => {            // SWITCH(v, case1, result1, ..., default)
  for (let i = 0; i + 1 < a.length; i += 2) if (a[i] === v) return a[i + 1];
  return a.length % 2 ? a.at(-1) : null;
};
const escHtml = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" } as any)[c]);
const typeOf = (v: any): string =>               // TYPE returns Ruby class names
  v == null ? "NilClass" : v === true ? "TrueClass" : v === false ? "FalseClass"
  : Array.isArray(v) ? "Array" : typeof v === "object" ? "Hash"
  : typeof v === "number" ? (Number.isInteger(v) ? "Integer" : "Float") : "String";
const dateDiff = (a: any, b: any, absolute = true) => {   // DATE_DIFF totals; the calendar "units" part is in the catalogue
  const ms = new Date(b).getTime() - new Date(a).getTime(), v = Math.floor(Math.abs(ms) / 1000);
  const r = (n: number) => { const x = Math.round(n * 100) / 100; return !absolute && ms < 0 && x !== 0 ? -x : x; };
  return { seconds: r(v), minutes: r(v / 60), hours: r(v / 3600), days: r(v / 86400), weeks: r(v / 604800) };
};
const lev = (a: string, b: string, ins = 2, del = 2, sub = 1): number => {  // Tines default costs are 2, 2, 1
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j * ins);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i * del];
    for (let j = 1; j <= b.length; j++)
      cur[j] = Math.min(prev[j] + del, cur[j - 1] + ins, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : sub));
    prev = cur;
  }
  return prev[b.length];
};
const legacyStringify = (v: any): string =>      // TEXT / LEGACY_STRINGIFY on objects: {"k"=>"v"} (nested shapes assumed)
  v == null ? "nil" : Array.isArray(v) ? `[${v.map(legacyStringify).join(", ")}]`
  : typeof v === "object" ? `{${Object.entries(v).map(([k, x]) => `${JSON.stringify(k)}=>${legacyStringify(x)}`).join(", ")}}`
  : typeof v === "string" ? JSON.stringify(v) : String(v);
```

## 2 Function tables

Conventions: `x` text or any value, `n` number, `arr` array, `obj` object, `e` the translated body of a `LAMBDA`, `p` a path string. Tines never mutates its input, so the TS column never mutates either. `crypto` rows assume `import crypto from "node:crypto"`. npm packages are imported by name in a Bun script.

### 2.1 Text

| Tines | TypeScript | Notes |
|---|---|---|
| `APPEND(x, y, z)`, `PREPEND(x, pre)` | `[x, y, z].join("")`, `[pre, x].join("")` | `APPEND` is the same as `x & y & z`; `join` turns `null` into `""` (a template literal would print `null`); non-text arguments are not specified in docs |
| `UPCASE(x)`, `DOWNCASE(x)` | `x.toUpperCase()`, `x.toLowerCase()` | |
| `CAPITALIZE(x)` | `x.charAt(0).toUpperCase() + x.slice(1).toLowerCase()` | lowercases the rest |
| `CAMELIZE(x)` | `x.replace(/[_\s-]+(.)?/g, (_, c) => c ? c.toUpperCase() : "").replace(/^./, c => c.toLowerCase())` | `hello_world` -> `helloWorld`; first letter lowercased |
| `TITLEIZE(x)` | `x.replace(/([a-z\d])([A-Z])/g, "$1_$2").toLowerCase().replace(/_id$/, "").replace(/[_-]+/g, " ").replace(/(^\s*\S)/g, c => c.toUpperCase()).replace(/\s[a-z]/g, c => c.toUpperCase())` | drop the `_id` replace when `keep_id_suffix: TRUE`; words after spaces, underscores and camelCase humps are capitalised |
| `TO_SNAKE_CASE(x)` | `x.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+/, "").replace(/_+$/, "")` | `fooBar` -> `foobar`; with `from_camel_case: TRUE` first do `x.replace(/([a-z0-9])([A-Z])/g, "$1_$2")` |
| `STRIP(x)`, `LSTRIP(x)`, `RSTRIP(x)` | `x.trim()`, `x.trimStart()`, `x.trimEnd()` | |
| `STRIP_HTML(x)` | `x.replace(/<[^>]*>/g, "")` | |
| `STRIP_NEWLINES(x)` | `x.replace(/\r?\n/g, "")` | |
| `NEWLINE_TO_BR(x)` | `x.replace(/\n/g, "<br />\n")` | keeps the newline |
| `REPLACE(x, a, b)` | `x.split(a).join(b)` | every occurrence; `a` is plain text, not a regex. Not `replaceAll(a, b)`: it reads `$&` / `$1` inside `b` as patterns |
| `REPLACE_FIRST(x, a, b)`, `REMOVE_FIRST(x, a)` | `x.replace(a, () => b)`, `x.replace(a, "")` | a string pattern replaces only the first match; the function form keeps `$` in `b` literal |
| `REMOVE(x, a)` | `x.split(a).join("")` | on an array: `arr.filter(v => v !== a)` (exact items only) |
| `SPLIT(x, sep)` | `x.split(sep)` | |
| `SLICE(x, i, len)` | `x.slice(i).slice(0, len)` | third argument is a length, not an end index; negative `i` counts from the end. `SLICE(x, i)` with no length = ONE character: `x.at(i) ?? ""` |
| `SIZE(x)`, `BYTESIZE(x)` | `Array.isArray(x) ? x.length : [...x].length`, `Buffer.byteLength(x)` | `SIZE` works on text and arrays; the spread counts an emoji as one character (`x.length` counts two) |
| `STARTS_WITH(x, pre)`, `ENDS_WITH(x, suf)` | `x.startsWith(pre)`, `x.endsWith(suf)` | case-sensitive |
| `INCLUDES(x, part)` | `x.includes(part)` | text: substring. array: exact element. object: key exists (`Object.hasOwn(obj, part)`) |
| `INDEX_OF(x, part)`, `LAST_INDEX_OF(x, part)` | `x.indexOf(part) === -1 ? null : x.indexOf(part)` | miss returns `NULL`, not `-1`; `LAST_INDEX_OF` uses `lastIndexOf`; arrays: see 2.2 |
| `PAD_LEFT(x, n, pad)`, `PAD_RIGHT(x, n, pad)` | `x.padStart(n, pad)`, `x.padEnd(n, pad)` | |
| `TRUNCATE(x, n)` | `x.length > n ? x.slice(0, n - 3) + "..." : x` | `n` includes the ellipsis; `TRUNCATE(x, n, end)`: use `end` and `end.length` |
| `TRUNCATEWORDS(x, n)` | `(w => w.length > n ? w.slice(0, n).join(" ") + "..." : x)(x.split(/\s+/).filter(Boolean))` | optional third argument replaces `"..."` |
| `PLURALIZE(n, "item")` | `Number(n) === 1 ? "item" : "items"` | result has no number in it; `PLURALIZE(n, "bonus", "bonuses")` gives the plural explicitly; default plural assumed to add `s` |
| `TRANSLITERATE(x)` | `x.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^\x00-\x7f]/g, "?")` | accents dropped, anything else non-ASCII becomes `?` |
| `LEVENSHTEIN_DISTANCE(a, b)` | `lev(a, b)` | default costs: insertion 2, deletion 2, substitution 1 |
| `ESCAPE(x)`, `HTML_ENCODE(x)` | `escHtml(x)` | `ESCAPE` is HTML escaping, not URL encoding |
| `ESCAPE_ONCE(x)` | `escHtml(x).replace(/&amp;(?=#?\w+;)/g, "&")` | escapes like `ESCAPE` but leaves existing entities alone |
| `HTML_DECODE(x)` | `he.decode(x)` | npm `he` |
| `RANDOM_STRING(n)` | `Array.from({ length: n }, () => chars[crypto.randomInt(chars.length)]).join("")` | default `n` 16; `chars = [...set]`, set by mode: alphanumeric (default), letters, numbers, hex (lowercase), custom (third argument) |
| `UUID()` | `crypto.randomUUID()` | |
| `TO_MARKDOWN_BOLD(x)`, `TO_MARKDOWN_ITALIC(x)`, `TO_MARKDOWN_STRIKE(x)` | `(t => t ? "**" + t + "**" : "")(text(x).trim())`, same with `"_" + t + "_"`, same with `"~~" + t + "~~"` | trimmed; blank input returns `""` |
| `TO_MARKDOWN_HEADING(x, level)`, `TO_MARKDOWN_LIST(arr)` | `"#".repeat(level) + " " + text(x).trim().replace(/\s+/g, " ")`, `arr.map(v => "- " + String(v).trim().replace(/\s+/g, " ")).join("\n")` | level defaults to 1 and must be 1 to 6; `ordered: TRUE`: prefix `(i + 1) + ". "` instead of `"- "`; whitespace inside an item collapses to one space |
| `TO_MARKDOWN_BLOCKQUOTE(x)`, `TO_MARKDOWN_CODEBLOCK(x, lang)` | `text(x).trim() === "" ? "" : text(x).split("\n").map(l => "> " + l).join("\n")`, `fence + lang + "\n" + x + "\n" + fence` | `fence` = backticks, one more than the longest run of backticks inside `x`, at least three; `lang` defaults to `""` |
| `TO_MARKDOWN_CALLOUT(x, type)` | `["> [!" + type.toUpperCase() + "]", ...(text(x).trim() === "" ? [] : text(x).split("\n").map(l => "> " + l))].join("\n")` | type defaults to `NOTE` (one word, letters only); blank text gives the title line alone |
| `ESTIMATED_TOKEN_COUNT(x)` | `Math.ceil((typeof x === "string" ? x : JSON.stringify(x)).length / 4)` | rough approximation only; Tines raises an error above 1 million characters |

### 2.2 Arrays and lambdas

| Tines | TypeScript | Notes |
|---|---|---|
| `ARRAY(a, b)` | `[a, b]` | |
| `FIRST(arr)`, `LAST(arr)` | `arr?.[0] ?? null`, `arr?.at(-1) ?? null` | |
| `JOIN(arr, sep)` | `arr.join(sep)` | |
| `CONCAT(a, b, c)` | `[...a, ...b, ...c]` | |
| `PUSH(arr, v, w)` | `[...arr, v, w]` | an array argument is added as one element |
| `INSERT(arr, i, v)` | `arr.toSpliced(i < 0 ? arr.length + i + 1 : i, 0, v)` | negative `i` inserts AFTER that element |
| `DELETE(arr, i)` | `arr.filter((_, j) => j !== (i < 0 ? arr.length + i : i))` | by index; negative counts from the end |
| `COMPACT(arr)` | `arr.filter(v => v != null)` | removes only null (not `filter(Boolean)`) |
| `FLATTEN(arr)`, `REVERSE(arr)` | `arr.flat(Infinity)`, `arr.flat(Infinity).reverse()` | `REVERSE` also flattens nested arrays |
| `ROTATE(arr, n)` | `[...arr.slice(k), ...arr.slice(0, k)]` | `k = ((n % arr.length) + arr.length) % arr.length`; `n` defaults to 1 |
| `UNIQ(arr)` | `[...new Set(arr)]` | for objects dedupe by `JSON.stringify` |
| `SORT(arr)` | `[...arr].sort((a, b) => a < b ? -1 : a > b ? 1 : 0)` | never bare `.sort()`: it sorts numbers as text and mutates |
| `SORT(arr, p)` | `[...arr].sort((a, b) => get(a, p) < get(b, p) ? -1 : get(a, p) > get(b, p) ? 1 : 0)` | |
| `SORT_NATURAL(arr)` | `[...arr].sort((a, b) => low(a) < low(b) ? -1 : low(a) > low(b) ? 1 : 0)` | case-insensitive: `low = (v) => typeof v === "string" ? v.toLowerCase() : v`; with a path compare `low(get(a, p))` |
| `SLICE_ARRAY(arr, i, len)` | `arr.slice(i, i + len)` | third argument is a length; `SLICE_ARRAY(arr, i)` = `arr.slice(i)` (rest of the array, unlike text `SLICE`) |
| `CHUNK_ARRAY(arr, n)` | `Array.from({ length: Math.ceil(arr.length / n) }, (_, i) => arr.slice(i * n, i * n + n))` | |
| `RANGE(a, b)` | `Array.from({ length: Math.max(0, b - a + 1) }, (_, i) => a + i)` | end is inclusive |
| `SHUFFLE(arr)`, `RANDOM_ELEMENT(arr)` | `arr.map(v => [Math.random(), v]).sort((a, b) => a[0] - b[0]).map(p => p[1])`, `arr[Math.floor(Math.random() * arr.length)] ?? null` | not `sort(() => Math.random() - 0.5)`: biased, and it mutates |
| `UNION(a, b)` | `[...new Set([...a, ...b])]` | |
| `INTERSECTION(a, b)`, `DIFFERENCE(a, b)` | `a.filter(v => b.includes(v))`, `a.filter(v => !b.includes(v))` | |
| `INDEX_OF(arr, v)` | `arr.indexOf(v) === -1 ? null : arr.indexOf(v)` | miss returns `NULL`; `0` is a hit and is truthy in Tines |
| `INDEX_OF(arr, LAMBDA(v, e))` | `arr.findIndex(v => truthy(e)) === -1 ? null : arr.findIndex(v => truthy(e))` | `LAST_INDEX_OF`: same with `lastIndexOf` / `findLastIndex` |
| `MAP(arr, "a.b")` | `arr.map(o => get(o, "a.b"))` | plucks a path; it does NOT take a function |
| `MAP_LAMBDA(arr, LAMBDA(v, e))` | `arr.map(v => e)` | this is JS `.map` |
| `MAP_LAMBDA(obj, LAMBDA(k, v, e))` | `Object.entries(obj).map(([k, v]) => e)` | returns an array |
| `FILTER(arr, LAMBDA(v, e))` | `arr.filter(v => truthy(e))` | keeps matches |
| `REJECT(arr, LAMBDA(v, e))` | `arr.filter(v => !truthy(e))` | drops matches: negate |
| `FILTER(arr, ARRAY(2, 4))` | `arr.filter(v => [2, 4].includes(v))` | list of values to keep; `REJECT(arr, ARRAY(2, 4))`: negate |
| `FIND(arr, LAMBDA(v, e))` | `arr.find(v => truthy(e)) ?? null` | |
| `WHERE(arr, p, val)` | `arr.filter(o => get(o, p) === val)` | `WHERE(arr, p)` with no value, or with `NULL` as the value, keeps items where the path holds something: `arr.filter(o => !isBlank(get(o, p)) && text(get(o, p)).trim() !== "")` (whitespace-only text counts as absent here) |
| `REDUCE(arr, LAMBDA(acc, v, e), init)` | `arr.reduce((acc, v) => e, init)` | initial value is the LAST argument |
| `COUNTIF(arr, v)` | `arr.filter(i => i === v).length` | with a lambda: `arr.filter(i => truthy(e)).length` |
| `GROUP_BY(arr, "key")` | `arr.reduce((g, o) => ((g[o?.key ?? null] ??= []).push(o), g), {})` | lambda form: use `e` in place of `o?.key`; `as_array: TRUE`: `Object.entries(g).map(([key, values]) => ({ key, values }))` |
| `TALLY(arr)` | `arr.reduce((o, v) => ({ ...o, [v]: (o[v] ?? 0) + 1 }), {})` | `strict_types: TRUE` returns `[{ key, count }]` |
| `FORCE_ARRAY(x)` | `x == null ? [] : Array.isArray(x) ? x : [x]` | |
| `LAMBDA(a, b, e)` | `(a, b) => e` | |

### 2.3 Objects

| Tines | TypeScript | Notes |
|---|---|---|
| `OBJECT("k", v, "k2", v2)` | `{ k: v, k2: v2 }` | alternating key, value |
| `GET(obj, "a.b.c")` | `get(obj, "a.b.c")` | with a variable key: `obj?.[key] ?? null` |
| `KEYS(obj)`, `VALUES(obj)` | `Object.keys(obj)`, `Object.values(obj)` | |
| `MERGE(a, b)`, `DEEP_MERGE(a, b)` | `{ ...a, ...b }`, `deepMerge(a, b)` | last wins; `MERGE` is shallow |
| `SET_KEY(obj, "k", v)` | `{ ...obj, k: v }` | dotted path: work on `structuredClone(obj)`; split the path with `p.split(/(?<!\\)\./)` and turn each `\.` into `.` (a backslash-dot is a literal dot in a key), walk to the parent, assign. Full helper: catalogue `SET_KEY` |
| `REMOVE_KEY(obj, "k")` | `Object.fromEntries(Object.entries(obj).filter(([k]) => k !== "k"))` | dotted path: same clone, split and walk as `SET_KEY`, then `delete parent[last]`. Not lodash `set` / `unset`: they ignore the `\.` escape |
| `FILTER(obj, LAMBDA(k, v, e))` | `Object.fromEntries(Object.entries(obj).filter(([k, v]) => truthy(e)))` | a one-argument lambda receives the VALUE; `REJECT`: negate; `FILTER(obj, ARRAY(2, 4))` keeps entries whose value is listed |
| `INCLUDES(obj, "k")` | `Object.hasOwn(obj, "k")` | checks keys |
| `FLATTEN_JSON(obj)`, `UNFLATTEN_JSON(obj)` | `flatten(obj)`, `unflatten(obj)` | npm `flat`; custom separator: `{ delimiter: sep }`; numeric segments become array indexes; empty `{}` / `[]` values are kept as they are (Tines behaviour not specified) |
| `JSONPATH(obj, "$.a[*].b")` | `JSONPath({ path: "$.a[*].b", json: obj })` | npm `jsonpath-plus`; prefer a plain `.map` when the path is simple |
| `IS_VALID_JSON_SCHEMA(schema, v)`, `JSON_SCHEMA_VALIDATE(schema, v)` | `ajv.validate(schema, v)`, `ajv.validate(schema, v) ? "" : ajv.errorsText()` | npm `ajv` (`const ajv = new Ajv({ strict: false })`); schema is the FIRST argument; the second returns `""` when valid, else a message (wording differs) |

### 2.4 Dates and time

| Tines | TypeScript | Notes |
|---|---|---|
| `DATE(x, fmt)` | `tinesDate(x, fmt)` | `fmt` is Ruby strftime (`%Y-%m-%d`), never `YYYY-MM-DD`; result is TEXT; input that cannot be read comes back unchanged; `DATE(x)` with no format: `tinesDate(x)` (ISO 8601 with milliseconds) |
| `DATE(x, "%s")` | `String(Math.floor(toDate(x).getTime() / 1000))` | unix seconds as text; drop `String()` when used in math |
| `DATE(x, fmt, "Asia/Tokyo")` | `tinesDate(x, fmt, "Asia/Tokyo")` | `%Z` prints `GMT+9`-style names for most zones where Tines prints an abbreviation |
| `NOW()`, `TODAY()` | `new Date().toISOString().replace("Z", "+00:00")`, `new Date().toISOString().slice(0, 10)` | both are TEXT, not numbers |
| `UNIX_TIMESTAMP()` | `Math.floor(Date.now() / 1000)` | seconds, number |
| `DATE_PARSE(x).unix_timestamp` | `Math.floor(toDate(x).getTime() / 1000)` | other fields: `iso8601`, `unix_timestamp_milliseconds`, `year`, `month`, `month_name`, `day`, `day_of_week`, `day_name`, `hour`, `minute`, `second`, `millisecond`, `timezone`, `utc_offset` |
| `DATE_PARSE(x, "%d/%m/%Y")` | `fromZonedTime(parse(x, "dd/MM/yyyy", new Date(0)), "UTC")` | npm `date-fns` (`parse`) + `date-fns-tz` (`fromZonedTime`; pass the zone name when `DATE_PARSE` has a third argument); tokens: `%Y` yyyy, `%y` yy, `%m` MM, `%d` dd, `%H` HH, `%M` mm, `%S` ss, `%b` MMM, `%B` MMMM; gives a `Date`, the full field object is in the catalogue |
| `DATE_DIFF(a, b)` | `dateDiff(a, b)` | `{ seconds, minutes, hours, days, weeks, units }`; absolute unless `absolute: FALSE`; hours, days, weeks are rounded to 2 decimals; the helper omits `units` (calendar breakdown: catalogue `DATE_DIFF`, npm `date-fns`) |
| `DISTANCE_OF_TIME_IN_WORDS(x)` | `formatDistance(new Date(x), new Date(), { addSuffix: true, includeSeconds: true })` | npm `date-fns`; second argument of the Tines call replaces `new Date()`; wording is approximate |
| `YEAR(x)`, `MONTH(x)`, `DAY(x)`, `HOUR(x)`, `MINUTE(x)` | `String(new Date(x).getUTCFullYear())`, `String(new Date(x).getUTCMonth() + 1)`, then `getUTCDate()`, `getUTCHours()`, `getUTCMinutes()` | TEXT, not zero-padded; JS month is 0-based; `x` must be an ISO timestamp (UTC assumed) |
| `SECOND(x)` | `new Date(x).getUTCSeconds()` | a number, unlike the five above |

Date input rules (all built into `toDate` / `tinesDate`): numbers with 13+ digits are milliseconds, shorter are seconds; text made only of 9+ digits is treated the same way (assumption, not specified in docs); `"01/02/2023"` is DD/MM (JS `new Date` reads MM/DD); text without an offset is UTC (JS reads many such strings as local time); a bare date or a span such as a month starts at 00:00; input that cannot be read is returned unchanged; phrases like `"yesterday"` or `"tomorrow at 10am"` need npm `chrono-node`.

### 2.5 Math

| Tines | TypeScript | Notes |
|---|---|---|
| `ABS(n)` | `Math.abs(Number(n))` | numeric text is accepted by all math functions |
| `CEIL(n)`, `FLOOR(n)` | `Math.ceil(Number(n))`, `Math.floor(Number(n))` | |
| `ROUND(n)` | `Math.sign(n) * Math.round(Math.abs(n))` | halves round away from zero (`-2.5` -> `-3`): assumed from Ruby, not specified in docs; bare `Math.round(-2.5)` is `-2`. `ROUND(n, d)`: ``Math.sign(n) * Number(Math.round(Number(`${Math.abs(n)}e${d}`)) + `e-${d}`)`` (`toFixed` mis-rounds `1.005`) |
| `PLUS(a, b)`, `MINUS(a, b)`, `TIMES(a, b)` | `Number(a) + Number(b)`, `Number(a) - Number(b)`, `Number(a) * Number(b)` | |
| `DIVIDED_BY(a, b)` | `Number.isInteger(b) ? Math.floor(a / b) : a / b` | whole-number divisor = result rounded down (`5 / 3` -> `1`); a divisor written `3.0` or `x * 1.0` in the formula is NOT whole: use `a / b`; check `b === 0` first and throw (assumed; JS gives `Infinity`) |
| `MODULO(a, b)` | `((a % b) + b) % b` | result takes the sign of `b` (`MODULO(-7, 3)` -> `2`): assumed from Ruby, not specified in docs; plain `a % b` gives `-1` there |
| `POWER(a, b)` | `a ** b` | |
| `SQRT(n)`, `SIN(n)`, `COS(n)`, `ASIN(n)`, `ACOS(n)` | `Math.sqrt(n)`, `Math.sin(n)`, `Math.cos(n)`, `Math.asin(n)`, `Math.acos(n)` | radians |
| `MIN(a, b)`, `MAX(a, b)` | `Math.min(a, b)`, `Math.max(a, b)` | array form `MAX(arr)`: `Math.max(...arr)` |
| `SUM(arr)`, `AVERAGE(arr)` | `arr.reduce((a, b) => a + Number(b), 0)`, the same sum `/ arr.length` | `AVERAGE(a, b, c)`: put them in an array |
| `MEDIAN(arr)` | `((s, h) => s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2)([...arr].sort((a, b) => a - b), arr.length >> 1)` | |
| `AT_LEAST(n, min)`, `AT_MOST(n, max)` | `Math.max(n, min)`, `Math.min(n, max)` | the JS name is the opposite word |
| `CLAMP(n, lo, hi)` | `n < lo ? lo : n > hi ? hi : n` | works for numbers and for text (alphabetical order) |
| `RANDOM(a, b)` | `Math.floor(Math.random() * (b - a + 1)) + a` | integer, both ends inclusive (unverified) |
| `NUMBER(x)` | `Number(x)` | |

### 2.6 Logic

| Tines | TypeScript | Notes |
|---|---|---|
| `IF(c, a, b)` | `truthy(c) ? a : b` | `IF(c, a)` with no else: `truthy(c) ? a : null` |
| `AND(a, b, c)`, `OR(a, b, c)` | `truthy(a) && truthy(b) && truthy(c)`, `truthy(a) ? true : truthy(b) ? true : truthy(c)` | lazy, left to right, like Tines; both return a boolean (`OR` does not return the first truthy value) |
| `NOT(a)` | `!truthy(a)` | |
| `SWITCH(v, c1, r1, c2, r2, dflt)` | `sw(v, c1, r1, c2, r2, dflt)` | or chained `v === c1 ? r1 : v === c2 ? r2 : dflt` |
| `DEFAULT(v, fb)` | `isBlank(v) ? fb : v` | not `v ?? fb`: `""`, `false`, `[]`, `{}` also fall back, `0` does not. Several fallbacks: first non-blank; all blank returns the FIRST fallback (the LAST one with `{use_last_fallback: TRUE}` as final argument) |
| `IS_BLANK(v)`, `IS_PRESENT(v)` | `isBlank(v)`, `!isBlank(v)` | |
| `IS_EMPTY(v)` | `typeof v === "string" ? v === "" : Array.isArray(v) ? v.length === 0 : Object.keys(v).length === 0` | text, array or object only; other types are not specified in docs: throw for `null`, booleans and numbers rather than guess |
| `IF_ERROR(e, fb)` | `(() => { try { return e; } catch { return fb; } })()` | |
| `ERROR("msg")` | `(() => { throw new Error("msg"); })()` | |

### 2.7 Encoding, hashing, crypto, archives

| Tines | TypeScript | Notes |
|---|---|---|
| `BASE64_ENCODE(x)`, `BASE64_DECODE(x)` | `Buffer.from(typeof x === "string" ? x : JSON.stringify(x)).toString("base64")`, `Buffer.from(x, "base64").toString("utf8")` | not `btoa` / `atob` (break on non-Latin1); objects are JSON-encoded first; binary decode result: keep the `Buffer`; `strict: FALSE` on encode adds a line break every 72 characters and at the end; Node never rejects sloppy input on decode |
| `BASE64URL_ENCODE(x)`, `BASE64URL_DECODE(x)` | `Buffer.from(x).toString("base64url")`, `Buffer.from(x, "base64url").toString("utf8")` | |
| `TO_HEX(x)`, `HEX_PARSE(x)` | `Buffer.from(x).toString("hex")`, `Buffer.from(x, "hex").toString("utf8")` | |
| `MD5(x)`, `SHA1(x)`, `SHA256(x)`, `SHA512(x)`, `MD5_BASE64(x)`, `SHA256_BASE64(x)` | `crypto.createHash("sha256").update(x).digest("hex")` | algorithm name: `"md5"`, `"sha1"`, `"sha256"`, `"sha512"`; the `_BASE64` variants use `.digest("base64")` |
| `HMAC_SHA1(x, secret)`, `HMAC_SHA256(x, secret)`, `HMAC_SHA1_BASE64(x, secret)`, `HMAC_SHA256_BASE64(x, secret)` | `crypto.createHmac("sha256", secret).update(x).digest("hex")` | `"sha1"` or `"sha256"`; `_BASE64` variants use `.digest("base64")`. Tines: text first, secret second. Node: secret first |
| `CONST_EQUALS(a, b)` | `((p, q) => p.length === q.length && crypto.timingSafeEqual(p, q))(buf(a), buf(b))` | `buf = (v) => Buffer.from(typeof v === "string" ? v : JSON.stringify(v))`; compare BYTE lengths first or `timingSafeEqual` throws |
| `JWT_SIGN(claims, key, alg, headers)` | `h + "." + crypto.createHmac("sha256", key).update(h).digest("base64url")` | HS256 form, with `b = (v) => Buffer.from(JSON.stringify(v)).toString("base64url")` and `h = b({ alg: "HS256", ...headers }) + "." + b(claims)`. Tines adds no `iat` and no `typ` by itself, so not `jsonwebtoken.sign` (it adds both). Default algorithm is `RS256`; RSA / ECDSA signing: catalogue `JWT_SIGN` |
| `JWT_DECODE(token, key, alg)` | `({ payload: jwt.verify(token, key, { algorithms: [alg] }), header: jwt.decode(token, { complete: true }).header, verified: true })` | npm `jsonwebtoken`; `verify` throws on a bad signature (what Tines does then is not specified); with `verify: FALSE`: `payload` and `header` from `jwt.decode(token, { complete: true })`, `verified: false` |
| `JWK_TO_PEM(jwk)`, `PEM_TO_JWK(pem)` | `crypto.createPublicKey({ key: jwk, format: "jwk" }).export({ type: "spki", format: "pem" })`, `crypto.createPublicKey(pem).export({ format: "jwk" })` | public key only unless `include_private: TRUE` (then `createPrivateKey`) |
| `GENERATE_RSA_KEYS()` | `crypto.generateKeyPairSync("rsa", { modulusLength: 2048, publicKeyEncoding: { type: "spki", format: "pem" }, privateKeyEncoding: { type: "pkcs8", format: "pem" } })` | Tines returns `[public, private]` |
| `RSA_ENCRYPT(x, key)`, `RSA_DECRYPT(x, key)` | `crypto.publicEncrypt({ key, padding: crypto.constants.RSA_PKCS1_PADDING }, Buffer.from(x)).toString("base64")`, `crypto.privateDecrypt({ key, padding: crypto.constants.RSA_PKCS1_PADDING }, Buffer.from(x, "base64")).toString("utf8")` | default padding PKCS1; base64 as the text form of the ciphertext is assumed (not specified in docs) |
| `RSA_SIGN(x, key)` | `crypto.sign("sha256", Buffer.from(x), key).toString("base64")` | `digest:` SHA256 (default), SHA384, SHA512; output encoding unverified |
| `RSA_AES_HYBRID_ENCRYPT(x, key)`, `RSA_AES_HYBRID_DECRYPT(arr, key)` | no equivalent | Tines-specific 3-element format; data cannot cross between Tines and the port. If both sides are ported, the catalogue has a self-made pair; flag it |
| `OPENSSL_ENCRYPT(x, alg, key)`, `OPENSSL_DECRYPT(x, alg, key, iv)` | `crypto.createCipheriv(alg, key, iv)`, `crypto.createDecipheriv(alg, key, iv)` | encrypt makes a fresh random `iv` and returns `{ encrypted, iv, auth_tag }`, values base64 (`iv` only when the algorithm has one, `auth_tag` only for GCM; key encoding not specified in docs); algorithms: aes-128-cbc, aes-256-cbc, aes-256-gcm, aes-128-ecb, aes-256-ecb |
| `AES_ENCRYPT`, `AES_DECRYPT`, `TINES_ENCRYPT`, `TINES_DECRYPT` | no equivalent | proprietary ciphertext format; data encrypted by Tines cannot be read outside Tines. If both sides are ported, re-encrypt with `crypto` (the catalogue has an AES-256-GCM pair with expiry) and flag it |
| `ZSCALER_OBFUSCATE_API_KEY(key, now)` | `[...n].map(c => key[+c]).join("") + [...r].map(c => key[+c + 2]).join("")` | `n = String(now).slice(-6)`, `r = String(Number(n) >> 1).padStart(6, "0")`; from the Zscaler docs, unverified against Tines |
| `GZIP(x)`, `GUNZIP(x)` | `zlib.gzipSync(Buffer.from(x))`, `zlib.gunzipSync(buf).toString("utf8")` | `import zlib from "node:zlib"`; gzip result is binary (a `Buffer`); `buf` must be the raw bytes, e.g. `Buffer.from(b64, "base64")` |
| `ZIP(contents, name, password)`, `UNZIP(x)` | `zipSync({ [name]: strToU8(contents) })`, `unzipSync(x)` | npm `fflate`; password-protected zips need another package (unverified); Tines `UNZIP` returns file objects |
| `TAR(files)`, `UNTAR(x)` | npm `tar-stream` | no one-liner |

### 2.8 JSON, CSV, XML, YAML and other parsing

| Tines | TypeScript | Notes |
|---|---|---|
| `JSON_PARSE(x)` | `JSON.parse(x)` | |
| `TO_JSON(x)`, `NEAT_JSON(x)` | `JSON.stringify(x)`, `JSON.stringify(x, null, 2)` | |
| `IS_JSON(x)`, `IS_YAML(x)` | `(() => { try { JSON.parse(x); return true; } catch { return false; } })()` | for YAML use `YAML.parse(x)` in the same pattern; `strict: TRUE` also requires the parsed value to be an object with keys |
| `CSV_PARSE(x)`, `CSV_PARSE_TO_OBJECTS(x)` | `Papa.parse(x.trim(), { skipEmptyLines: true }).data.map(r => r.map(c => c.trim()))`, `Papa.parse(x.trim(), { header: true, skipEmptyLines: true, transformHeader: h => h.trim(), transform: v => v.trim() }).data` | npm `papaparse` (detects the delimiter, as Tines does); array of arrays, or objects keyed by the first row; all values stay text |
| `TO_CSV(rows)`, `OBJECTS_TO_CSV(objs, headers)` | `rows.map(r => r.map(cell).join(",")).join("\n") + "\n"`, the same over `[headers, ...objs.map(o => headers.map(h => o[h]))]` | `cell = (v) => /[",\n]/.test(String(v ?? "")) ? '"' + String(v ?? "").replace(/"/g, '""') + '"' : String(v ?? "")`; headers default to the keys of the first object; the Tines docs show `", "` between fields (not verified), this writes a bare comma |
| `OBJECTS_TO_MARKDOWN_TABLE(objs)` | `[h, h.map(() => "---"), ...objs.map(o => h.map(k => String(o[k] ?? "").replaceAll(bar, "\\" + bar)))].map(r => bar + " " + r.join(" " + bar + " ") + " " + bar).join("\n")` | `h = Object.keys(objs[0])` (or the second argument), `bar = String.fromCharCode(124)` (the pipe character); a pipe inside a value is backslash-escaped |
| `COMBINE_COLUMNS_AND_ROWS(cols, rows)` | `rows.map(r => Object.fromEntries(cols.map((c, i) => [c, r[i] ?? null])))` | values pass through unchanged |
| `XML_PARSE(x)`, `IS_XML(x)` | `new XMLParser({ parseTagValue: false }).parse(x)`, `XMLValidator.validate(x) === true` | npm `fast-xml-parser`; `parseTagValue: false` keeps `"10"` as text; attribute handling differs |
| `TO_XML(obj, root)` | no one-liner: build the text | layout: `<?xml version="1.0" encoding="UTF-8"?>`, root element (default `hash`), one two-space-indented child per key, underscores in key names written as dashes, `type="integer"` on whole numbers, trailing newline. Helper: catalogue `TO_XML`; arrays and nesting are not specified in docs |
| `YAML_PARSE(x)`, `TO_YAML(obj)` | `YAML.parse(x)`, `"---\n" + YAML.stringify(obj)` | npm `yaml` (`import YAML from "yaml"`); Tines output starts with a `---` line, the package omits it |
| `EML_PARSE(x)` | `await simpleParser(x)` | npm `mailparser`; map its fields to the Tines shape: `subject`, `from` (text), `to` / `cc` (arrays of addresses), `date` (ISO text), `message_id` (no angle brackets), `headers` (object), `attachments`, `body` = HTML part or else text part (`single_body: FALSE`: `body_html` + `body_text`). Mapping helper: catalogue `EML_PARSE` |
| `MSG_PARSE(x)` | `new MsgReader(buf).getFileData()` | npm `@kenjiuno/msgreader` |
| `MIME_HEADER_DECODE(x)` | `libmime.decodeWords(x)` | npm `libmime` |
| `LDIF_PARSE(x)`, `HCL_PARSE(x)` | hand parser, `hcl.parseToObject(x)[0]` | LDIF: one object per blank-line-separated entry, attribute names lowercased, each value an array of text, the `dn` line left out (helper: catalogue `LDIF_PARSE`); HCL: npm `hcl2-parser`, output shape not specified in docs; flag both for a human |

### 2.9 Regex

Tines regexes are Ruby regexes passed as text. Build with `new RegExp(re, flags)`.

| Tines | TypeScript | Notes |
|---|---|---|
| `MATCH(x, re)` | `new RegExp(re).test(x)` | boolean; `MATCH(x, re, "i")`: `new RegExp(re, "i")`; Ruby modifier `m` (dot matches newline) = JS flag `s` |
| `REGEX_EXTRACT(x, re)` | `[...x.matchAll(new RegExp(re, "g"))].map(m => m.length > 1 ? m.slice(1) : m[0])` | ALL matches; with capture groups each item is an array of the groups; no-match result unverified |
| `REGEX_EXTRACT(x, re)[0][0]` | `x.match(new RegExp(re))?.[1] ?? null` | first match, first group |
| `REGEX_REPLACE(x, re, rep)` | `x.replace(new RegExp(re, "g"), rep)` | every match; rewrite the replacement: `\1` -> `$1`, `\k<name>` -> `$<name>` |

Ruby -> JS pattern differences: `\A` -> `^`, `\z` / `\Z` -> `$`; Ruby `^` `$` always match at line breaks (add JS flag `m`); `\h` -> `[0-9a-fA-F]`; `(?i)` inline -> flag `i`. A backslash in a JS string literal must be doubled (`"\\d+"`), or use a regex literal `/\d+/`.

### 2.10 URL and network

| Tines | TypeScript | Notes |
|---|---|---|
| `URL_ENCODE(x)` | `encodeURIComponent(x).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase()).replace(/%20/g, "+")` | default is FORM encoding: space -> `+`; with `encoding: "uri"` drop the last `.replace` (space stays `%20`); exact safe-character set not specified in docs |
| `URL_DECODE(x)` | `decodeURIComponent(x.replace(/\+/g, " "))` | `+` -> space |
| `PARSE_URL(x)` | `new URL(x)` | field mapping below |
| `IS_URL(x)` | `URL.canParse(x)` | `strict: TRUE`: also require protocol `http:`, `https:` or `ftp:` |
| `CONTAINS_URL(x)` | `["http://", "https://", "ftp://"].some(p => x.toLowerCase().includes(p))` | exact pattern not specified in docs; this only looks for a scheme prefix |
| `IS_EMAIL(x)` | `/^[^@\s]+@[^@\s]+$/.test(x)` | `john@smith` is true unless `strict_tld: TRUE` |
| `IS_IPV4(x)`, `IS_IPV6(x)` | `net.isIPv4(x)`, `net.isIPv6(x)` | `import net from "node:net"` |
| `IS_IP_ADDRESS(x)` | `net.isIP(x.split("/")[0]) !== 0` | non-strict accepts a CIDR suffix (this short form does not check that the suffix is a valid prefix length; the catalogue helper does); `strict: TRUE`: `net.isIP(x) !== 0`; one value at a time, not a list |
| `IN_CIDR(ip, cidr)` | `[ip].flat().every(a => ipaddr.parse(a).match(ipaddr.parseCIDR(cidr)))` | npm `ipaddr.js`; a list is true only when every address is inside; throws on text that is not an IP |

`PARSE_URL` fields from `const u = new URL(x)`: `scheme` = `u.protocol.slice(0, -1)`; `host` = `u.hostname`; `port` = `Number(u.port)` or 80 / 443 when empty (JS leaves default ports empty); `path` = `u.pathname`, but `""` when the URL has no path at all (JS gives `"/"`); `fragment` = `u.hash.slice(1)`, or `null` when there is none; `query` = object, repeated keys become arrays (`u.searchParams.getAll(k)`), or `null` when there is no query string; `domain` and `tld` need npm `tldts` (`parse(u.hostname).domain`, `parse(u.hostname).publicSuffix`).

### 2.11 Type conversion and story metadata

| Tines | TypeScript | Notes |
|---|---|---|
| `TEXT(x)` | `isObj(x) ? legacyStringify(x) : text(x)` | numbers and text: plain `String(x)`; on objects Tines gives Ruby style `{"k"=>"v"}`, not JSON (use `TO_JSON` for JSON) |
| `LEGACY_STRINGIFY(obj)` | `legacyStringify(obj)` | `{"k"=>"v"}` text; only the flat one-pair shape is documented, nested values are assumed; almost never wanted |
| `TYPE(x)` | `typeOf(x)` | `"String"`, `"Integer"`, `"Float"`, `"Array"`, `"Hash"`, `"TrueClass"`, `"FalseClass"`, `"NilClass"`; rewrite tests such as `TYPE(x) = "Array"` to `Array.isArray(x)` |
| `STORY_RUN_GUID()` | `process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID` | one id shared by every event of a story run; nearest Windmill notion is the root flow job id |
| `STORY_RUN_LINK()`, `WORKBENCH_LINK()` | no equivalent | Tines UI links; drop or replace with a link to the run |
| `PROMPT("status")` | no formula equivalent | URL that resumes the story when visited: an approval / suspend step, not an expression |

## 3 Traps

| Tines | Wrong TypeScript | Right TypeScript |
|---|---|---|
| `IF(qty, "some", "zero")` with `qty = 0` | `qty ? "some" : "zero"` | `truthy(qty) ? "some" : "zero"` (0 and `""` are truthy) |
| `IS_BLANK(arr)` | `!arr` | `isBlank(arr)` (`[]` and `{}` are blank) |
| `IS_BLANK(INDEX_OF(arr, v))` | `!arr.indexOf(v)` | `!arr.includes(v)` (miss is `NULL`; index 0 is not blank) |
| `REJECT(arr, LAMBDA(v, cond))` | `arr.filter(v => cond)` | `arr.filter(v => !truthy(cond))` |
| `MAP(arr, "id")` | `arr.map("id")` | `arr.map(o => o?.id)` |
| `a & b` | `a & b` | `text(a) + text(b)` |
| `DATE(x, "%Y-%m-%d")` | `format(x, "%Y-%m-%d")` with date-fns / dayjs | `tinesDate(x, "%Y-%m-%d")` |
| `DATE(1647712411, fmt)` | `new Date(1647712411)` | `new Date(1647712411 * 1000)` (seconds) |
| `SLICE(x, 6)` | `x.slice(6)` | `x.at(6)` (one character) |
| `SORT(nums)` | `nums.sort()` | `[...nums].sort((a, b) => a < b ? -1 : a > b ? 1 : 0)` |
| `DEFAULT(v, "x")` | `v ?? "x"` | `isBlank(v) ? "x" : v` |
| `<<obj>>` inside text | `` `${obj}` `` (gives `[object Object]`) | `` `${JSON.stringify(obj)}` `` |
| `a.b.c` where `b` may be missing | `a.b.c` (throws) | `a?.b?.c` (Tines yields `NULL`) |

## 4 Legacy Liquid

Older exports use Liquid instead of formulas (mapping taken from archived Tines docs, no longer in the current docs). A filter is the formula function of the same name in uppercase, with the piped value as its FIRST argument (`x | replace: "a", "b"` = `REPLACE(x, "a", "b")`). Rewrite to the formula form, then use section 2.

```text
Liquid                                                Formula form                      TypeScript
{{ .action.field }}   {{ action.field }}              <<action.field>>                  text(action?.field)     (leading dot = event root: drop it)
{{ x | upcase }}                                      <<UPCASE(x)>>                     x.toUpperCase()
{{ x | replace: "a", "b" | append: "!" }}             <<REPLACE(x, "a", "b") & "!">>    x.split("a").join("b") + "!"
{{ arr | size | times: 10 }}                          <<SIZE(arr) * 10>>                String(arr.length * 10)
{{ .a.items | where: "k", "v" | as_object }}          =WHERE(a.items, "k", "v")         a?.items.filter(o => o?.k === "v")
{{ x | json_parse | as_object }}                      =JSON_PARSE(x)                    JSON.parse(x)
{{ "now" | date: "%Y%m%d" }}                          <<DATE("now", "%Y%m%d")>>         strftime(new Date(), "%Y%m%d")
{{ "now" | date: "%s" | minus: 86400 | date: "%F" }}  <<DATE(DATE("now", "%s") - 86400, "%F")>>
                                                      strftime(new Date((Math.floor(Date.now() / 1000) - 86400) * 1000), "%F")
{% if a == "x" %}A{% elsif b contains "y" %}B{% else %}C{% endif %}
                                                      IF(a = "x", "A", IF(INCLUDES(b, "y"), "B", "C"))
                                                      a === "x" ? "A" : b?.includes("y") ? "B" : "C"
{% for p in items %}{{ p.title }} {% endfor %}        <<for p in items>>...<<endfor>>   items.map(p => text(p?.title) + " ").join("")
{% assign v = 2 | minus: 1 %}                         LOCAL.v                           const v = 2 - 1;   (declare before the value that uses it)
{% capture v %}...{% endcapture %}                    LOCAL.v                           const v = `...`;
{% random 1-10 %}                                     RANDOM(1, 10)                     Math.floor(Math.random() * 10) + 1
{% credential name %}  {% global_resource name %}     CREDENTIAL.name  RESOURCE.name    credential.name  resource.name   (unverified, from memory)
{% line_break %}                                      newline                           "\n"                             (unverified, from memory)
```

Rules: without `as_object` the result is always text; a value that is exactly one `{{ ... | as_object }}` keeps its type (same as `=`). Liquid operators: `==`, `!=`, `>`, `<`, `and`, `or`, `contains`. Liquid truthiness matches formulas (only `nil` and `false` are falsy). `forloop.index` etc. map like `FORLOOP`, and Liquid `if` / `for` tags use the same `let out` recipe as formula control tags (language file, section 8).

## 5 Unverified

The official docs do not settle these. Translate as shown, and say so in the port's notes when a formula depends on one.

- Language-level gaps (operator operand types and precedence, `=` across types, text rendering of `NULL`, tag whitespace) are listed in [tines-formula-language.md](tines-formula-language.md), section 11.
- `MODULO` on negative numbers and `ROUND` on exact halves: Ruby behaviour assumed (sign of the divisor; halves away from zero). The docs examples agree with it but do not test either case.
- Whether whitespace-only text (`"  "`) is blank for `IS_BLANK` / `DEFAULT`. Assumed: not blank.
- `NUMBER(NULL)`, `NUMBER("")`, `SIZE(NULL)`, `SIZE(object)`, negative array indexes in paths (`arr[-1]`), `IS_EMPTY` on anything but text, arrays and objects, `DIVIDED_BY` with a zero divisor (the port throws).
- `REGEX_EXTRACT` with no match (`[]` or `NULL`); `RANDOM(a, b)` bounds and integer-ness; the patterns behind `CONTAINS_URL` and `IS_EMAIL`; whether digit-only text passed to `DATE` is a timestamp (assumed yes for 9+ digits).
- `TYPE(x)` on an object: the docs say `"Hash"`, but a real export compares it with `"Object"`. If a formula tests `TYPE(x) = "Object"`, translate it as "is a plain object" and flag it.
- `COUNT(...)` and `DAYS(...)` appear in docs examples but are not in the function list. Assumed: `COUNT` is `SIZE`, `DAYS(n)` is `n * 86400` seconds. Flag either in the port notes.
- Docs example outputs treated here as documentation typos: `SIZE` returning `"4"`, `STARTS_WITH` / `ENDS_WITH` returning `"true"`, `LAST_INDEX_OF` miss returning `"NULL"` (assumed number, boolean, `null`).
- Output encodings of `RSA_ENCRYPT`, `RSA_SIGN`, `OPENSSL_ENCRYPT`; password-protected `ZIP`; the npm package choices for `LDIF_PARSE`, `HCL_PARSE`, `MSG_PARSE`; the `ZSCALER_OBFUSCATE_API_KEY` algorithm (taken from Zscaler's docs).
- Legacy Liquid tags `credential`, `global_resource`, `line_break`.
