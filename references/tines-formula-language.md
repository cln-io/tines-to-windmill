# Tines formula language -> TypeScript

The syntax and semantics of Tines formulas, each construct with its TypeScript rendering. This is the offline stand-in for the Tines "Formulas" docs pages: language, operators, referencing data, and the formulas overview (read Nov 2026).

Evidence labels used below:
- **[docs]** stated on those pages.
- **[fn docs]** stated on a function reference page, not on the language or operators page.
- **[export]** not in the docs, but observed in real story exports.
- **not specified in docs** nothing above settles it. Translate as shown and flag it in the port's notes if the formula depends on it.

Function lookup tables and the helpers (`text`, `truthy`, `isBlank`, `get`, ...) are in [tines-formulas-to-ts.md](tines-formulas-to-ts.md). Worked translations are in [tines-formulas-examples.md](tines-formulas-examples.md).

**Contents:** [1 Where formulas appear](#1-where-formulas-appear) | [2 Literals and types](#2-literals-and-types) | [3 References and paths](#3-references-and-paths) | [4 Operators](#4-operators) | [5 Function calls, pipe, lazy evaluation](#5-function-calls-pipe-lazy-evaluation) | [6 Lambdas](#6-lambdas) | [7 Truthiness, blank, coercion](#7-truthiness-blank-coercion) | [8 Text mode: pills and control tags](#8-text-mode-pills-and-control-tags) | [9 Comments and escaping](#9-comments-and-escaping) | [10 No clean TypeScript equivalent](#10-no-clean-typescript-equivalent) | [11 Not specified in docs](#11-not-specified-in-docs)

## 1 Where formulas appear

An option value in an export is a string. Classify it first.

| The option value looks like | Tines meaning | Result type | TypeScript shape |
|---|---|---|---|
| `"plain text"` | literal | string | `"plain text"` |
| `"Ticket <<ticket.id>> is open"` | text mode: each `<<expr>>` value pill is evaluated, converted to text and joined with the surrounding text [docs] | always string | `` `Ticket ${text(ticket?.id)} is open` `` |
| `"<<ticket.count>>"` (one pill, nothing else) | still text mode | string (`7` becomes `"7"`) | `text(ticket?.count)` |
| `"=ticket.tags"` (starts with `=`) | formula field, also called single value mode: one formula, its result is returned as is [docs]; the leading `=` is how the export stores it [export] | type of the result (array, object, number, ...) | `ticket?.tags` |
| `"<%if c%>a<%endif%>"`, `"<%for x in arr%>...<%endfor%>"` | text mode with control tags (section 8) | always string | template-building code |
| `"<<>>"` | empty pill [export] | `""` | `""` |
| `"{{ .a.b }}"`, `"{% if %}"` | legacy Liquid | see the lookup file | see the lookup file |

The language inside `<<...>>`, inside `<%...%>` conditions, and after `=` is the same. Formulas may span several lines [export]; line breaks and spaces between tokens carry no meaning.

Converting a value to text in text mode (a `<<pill>>`, and `a & b`): use the `text()` helper. Text and numbers stay as written. `null` is assumed to become `""`. An array or an object becomes JSON text: that is this skill's convention. The current Tines docs do not specify it (an archived docs page said JSON). The function `TEXT(x)` is a different construct with a different result for objects: use `textFn(x)` (lookup file, section 1), never `text()`.

## 2 Literals and types

The types are the JSON types [docs].

| Tines | Rule | TypeScript |
|---|---|---|
| `"open"`, `'open'` | text; double and single quotes behave the same [docs] | `"open"` |
| `"say \"hi\""` | a backslash escapes a quote inside text [docs] | `"say \"hi\""` |
| `"a\nb"`, `"a\tb"`, `"C:\\dir"` | `\n` newline, `\t` tab, `\\` one backslash; any other sequence such as `\d` is kept as written [fn docs: REPLACE] | `"a\nb"`, `"a\tb"`, `"C:\\dir"`; write `\d` as `"\\d"` |
| `TRUE`, `FALSE` | booleans; uppercase only, case matters [docs] | `true`, `false` |
| `NULL` | null; uppercase; falsy [docs] | `null` |
| `42`, `4.25`, `-3` | numbers in plain notation [docs]; exponent or hex notation: not specified in docs | `42`, `4.25`, `-3` |
| `[1, "b", TRUE]` | array literal; same as `ARRAY(1, "b", TRUE)` [docs] | `[1, "b", true]` |
| `tags[0]` | element access with square brackets; the first item is position 0 [docs]; negative positions: not specified in docs | `tags?.[0]` |
| `{id: 7, "full name": "Ada"}` | object literal; same as `OBJECT("id", 7, "full name", "Ada")`; a key needs quotes only when it must, e.g. it contains a space [docs] | `{ id: 7, "full name": "Ada" }` |
| `{}`, `[]` | empty object / array [export] | `{}`, `[]` |

Inside `OBJECT(k, v, ...)` and `{...}` a key can be computed: `OBJECT(row.period, row.score)` -> `{ [row.period]: row.score }`.

## 3 References and paths

A bare lowercase name refers to the output (event) of an upstream action, addressed by the action's **slug** [docs]. Slug rule: lowercase the name; replace each run of characters that are not letters or digits with one `_` when it is in the middle, delete such runs at the start and end; if the result starts with a digit, put `_` in front. Examples: `Get Open Tickets` -> `get_open_tickets`, `Lookup (v2) host!` -> `lookup_v2_host`, `2nd pass` -> `_2nd_pass`. If two actions on the path share a slug, the nearer (more downstream) one is the one referenced [docs].

| Tines | TypeScript | Notes |
|---|---|---|
| `get_open_tickets.body.items` | `get_open_tickets?.body?.items` | dot path into the action's output [docs]. A missing key gives `null` rather than an error [fn docs: DEFAULT, FORCE_ARRAY examples]: always use `?.` |
| `orders[1].price` | `orders?.[1]?.price` | zero-based index [docs] |
| `row["Team Name"]` | `row?.["Team Name"]` | key with spaces [docs] |
| `RESOURCE[cfg.resource_key]`, `entry[key]` | `resource?.[cfg?.resource_key]`, `entry?.[key]` | computed key [docs]; same as `GET(RESOURCE, cfg.resource_key)` |
| `F(x).field`, `F(x)[0]`, `%.field` | `F(x)?.field`, `F(x)?.[0]`, piped value `?.field` | a path may follow a call or the pipe placeholder [fn docs, export] |
| `"a.b.c"` passed to `GET`, `MAP`, `WHERE`, `SORT` ... | `get(o, "a.b.c")` | path given as text [fn docs] |
| `'["Team Name"]'`, `'owner["Full Name"]'` passed as a path | `o?.["Team Name"]`, `o?.owner?.["Full Name"]` | keys with spaces inside a path text [docs] |

Uppercase keywords are not actions [docs]. Here each is assumed to be a variable already in scope (binding them is covered by the other references).

| Keyword | Holds | Variable used here |
|---|---|---|
| `CREDENTIAL.name` | a secret; never shown in previews | `credential.name` |
| `RESOURCE.name` | shared data stored for the team (text or JSON) | `resource.name` |
| `LOCAL.name` | values from the same action's `local` option, computed first, top to bottom | `const local = {...}` |
| `INPUT.name` | inputs of an action template / group / send-to-story | `input.name` |
| `LOOP.value`, `LOOP.index`, `LOOP.key`, `LOOP.previous_result` | the current iteration when an action or group loops | loop variable |
| `META.tenant`, `META.team`, `META.story`, `META.action`, `META.event`, `META.story_run.id` | environment info (`META.story.name`, `META.story.is_draft`, `META.tenant.url`, ...) | constants / runtime info |
| `PAGINATE.index`, `PAGINATE.previous_response` | HTTP pagination: 0-based page counter; previous page's response (`null` on the first request) | loop counter / previous response |
| `OUTPUT` | this action's own output, for post-processing it | the step's own result |
| `INFO`, `PAGE`, `STORY`, `team_case`, `FORM` (deprecated name of `PAGE`) | Tines platform objects: ids and metadata, page URLs, story ids, the current case | no TS equivalent; flag for a human |

## 4 Operators

The operators page lists 14 operators. All 14 are below.

```text
#   Tines         Also written   What the docs say                                   TypeScript rendering
1   a = b                        "equal to" comparison; returns TRUE or FALSE        a === b
2   a != b                       "not equal to" comparison; returns TRUE or FALSE    a !== b
3   a > b                        "greater than"; returns TRUE or FALSE               a > b
4   a >= b                       "greater than or equal to"; returns TRUE or FALSE   a >= b
5   a < b                        "less than"; returns TRUE or FALSE                  a < b
6   a <= b                       "less than or equal to"; returns TRUE or FALSE      a <= b
7   a && b        a AND b        "logical and"; returns TRUE or FALSE                truthy(a) && truthy(b)
8   a || b        a OR b         "logical or"; returns TRUE or FALSE                 truthy(a) || truthy(b)
9   a * b                        multiplication; returns the product                 a * b
10  a / b                        division; returns a divided by b                    a / b
11  a + b                        addition; returns the sum                           a + b
12  a - b                        subtraction; returns a minus b                      a - b
13  a & b                        concatenation; returns ONE text value:              text(a) + text(b)
                                 the text of a followed by the text of b
14  f() |> g(%)                  pipeline; the output of the left side is            g(f())
                                 available as % on the right side
```

For every one of the 14 the page states only what is in the third column. Operand types, behaviour on mixed types, behaviour when an operand is `NULL`, precedence and associativity are **not specified in docs**. Consequences for the translator:

| Operator (by name) | Same spelling in JS does what | Use instead | Not specified in docs |
|---|---|---|---|
| `=` equal | assignment | `a === b` | text vs number (`"1" = 1`); arrays / objects (by content or by identity); `NULL = NULL` |
| `!=` not equal | loose inequality with coercion | `a !== b` | same as `=` |
| `>` `>=` `<` `<=` | compare, coercing mixed operands | `a > b` when both are numbers; `Number(a) > Number(b)` when an operand is numeric text | text vs text ordering; a `NULL` operand |
| `&&`, `AND` | returns one of the OPERANDS (`0 && "x"` is `0`) and treats `0`, `""` as false | `truthy(a) && truthy(b)`: a real boolean, Tines truthiness | whether the right side is skipped when the left is false (documented only for the `AND(...)` function) |
| two vertical bars, `OR` | returns one of the OPERANDS and treats `0`, `""` as false | `truthy(a) ? true : truthy(b)`: a real boolean | whether the right side is skipped (documented only for `OR(...)`) |
| `*` `-` | numeric; `NaN` on bad input | `a * b`, `a - b`; wrap numeric text in `Number()` | text or `NULL` operands |
| `/` | always float division; `1 / 0` is `Infinity` | `a / b`; wrap numeric text in `Number()` | integer vs float result for two whole numbers; `[fn docs]` only: the `DIVIDED_BY` function floors for a whole-number divisor, and an `IF_ERROR` example shows `x / 0` raising an error |
| `+` | adds numbers but JOINS when either side is text (`"5" + 1` is `"51"`) | `Number(a) + Number(b)` unless both are known numbers | what `+` does with non-numeric text (text is joined with `&`) |
| `&` concatenation | bitwise AND on integers (`"a" & "b"` is `0`) | `text(a) + text(b)` | how numbers, `NULL`, arrays, objects are turned into text (assumed: as in text mode) |
| pipeline, written as a vertical bar followed by `>` | does not exist in JS | nest the calls, or one `const` per stage (section 5) | precedence against other operators |

Other evidence about operators (none of it from the operators page):
- Numeric text in comparisons and arithmetic works in practice: a docs example compares the text returned by `DATE("now", "%H")` with a number using `>=` [docs, language page], and function-page examples subtract a number from `DATE(x, "%s")` [fn docs]. The same language page also says formulas do not coerce types (said about truthiness). So: wrap in `Number(...)` when an operand is numeric text, and do not rely on any other mixed-type behaviour.
- Parentheses group sub-expressions: `(a.count * b.size) + 1`, `(row.kind = "x")` [export].
- The pipeline binds loosest: in `DATE(x, "%s") - 1 |> DATE(%)` the whole subtraction is piped [export].
- An operator can follow a call: `IF(c, a, b) + 30` adds 30 to whichever branch was chosen [export].
- There is no unary `!` in the docs or in the exports; negation is the function `NOT(x)`. `==` does not occur either.
- When precedence between different operators matters and the formula has no parentheses, do not guess: keep the formula's own grouping visible in the TS with parentheses and flag it.

## 5 Function calls, pipe, lazy evaluation

| Tines | Rule | TypeScript |
|---|---|---|
| `UPCASE(user.role)` | a function is its uppercase name followed by parentheses; all function names are uppercase [docs] | look the name up in the lookup file |
| `JOIN(SPLIT(csv_line, ","), " / ")` | calls nest; arguments are separated by commas [docs] | `csv_line.split(",").join(" / ")` |
| `IS_EMAIL(x, strict_tld: TRUE)` | some functions take named options after the positional arguments [fn docs] | see the function's row |
| `AND(a, b,)` | a trailing comma before `)` appears in docs examples; drop it | `truthy(a) && truthy(b)` |

Chaining with the pipe operator: the left result is available on the right as `%`, which may be placed anywhere in the right-hand expression [docs].

```text
Tines                                        TypeScript
SPLIT(line, ";") |> FIRST(%)                 line.split(";")[0] ?? null
get_users.body |> WHERE(%, "active", TRUE) |> SIZE(%)
                                             const s1 = get_users?.body;
                                             const s2 = s1.filter((o) => o?.active === true);
                                             const n = s2.length;
u |> SET_KEY(%, "n", SIZE(%.groups))         { ...u, n: u?.groups.length }      "%" used twice, and with a path   [export]
WHERE(list, "kind", "x") |> FIRST(%).name    list.filter((o) => o?.kind === "x")[0]?.name ?? null   path after the call   [export]
```

Evaluation order [docs]: arguments are normally all evaluated first (left to right), then the function runs. The exceptions are `IF`, `AND` and `OR`, whose arguments are evaluated only when needed, so `IF(IS_PRESENT(u), u.name, ERROR("no user"))` only raises when `u` is blank. In TypeScript a ternary and `&&` / `||` are lazy in the same way; do not move a lazily evaluated argument into a `const` that is computed unconditionally if it can throw or has a side effect.

## 6 Lambdas

`LAMBDA(p1, p2, ..., body)` creates a function: every argument except the last is a parameter name, the last is the expression to evaluate [docs]. Parameters shadow action slugs of the same name inside the body.

| Use [docs] | Tines | TypeScript |
|---|---|---|
| definition | `LAMBDA(w, h, w * h)` | `(w, h) => w * h` |
| immediately invoked (to name a value and reuse it) | `LAMBDA(n, IF(n > 99, "many", n & " items"))(SIZE(cart.items))` | `((n) => n > 99 ? "many" : n + " items")(cart.items.length)`, or simply `const n = cart.items.length;` first |
| argument of a lambda-taking function: `MAP_LAMBDA`, `FILTER`, `FIND`, `REDUCE` (also `REJECT`, `COUNTIF`, `INDEX_OF`, `GROUP_BY` [fn docs]) | `FILTER(cart.items, LAMBDA(it, it.qty > 0))` | `cart.items.filter((it) => it?.qty > 0)` |
| stored in `LOCAL` or a `RESOURCE`, called from elsewhere | `RESOURCE.shared_fns.shorten(item.name, 30)`, `LOCAL.fmt(x)` | a named function: `shorten(item?.name, 30)` |

**Lambda stored in a resource.** The resource value is the formula text of a `LAMBDA(...)` (stored in single value mode [docs]). Resource values are not part of a story export, so the body cannot be read from it.
1. Do not guess the body from the function's name. Ask the user for the resource's value, e.g. `{"shorten": "=LAMBDA(s, max, IF(SIZE(s) > max, SLICE(s, 0, max - 3) & \"...\", s))"}`.
2. Port that `LAMBDA` as an ordinary named function and call it: `const shorten = (s: any, max: number) => text(s).length > max ? text(s).slice(0, max - 3) + "..." : text(s);`
3. Until the user answers, emit a stub that fails loudly and list it as an open question: `const shorten = (..._args: any[]): never => { throw new Error("TODO: port LAMBDA from RESOURCE.shared_fns.shorten"); };`

A lambda stored in `LOCAL` is in the same action's `local` option, so it IS in the export: port it directly.

## 7 Truthiness, blank, coercion

[docs]: formulas do not coerce values to booleans the way JS does. Every value is truthy except `FALSE` and `NULL`. An empty array is NOT false. To test for "nothing there" use `IS_BLANK` / `IS_PRESENT`.

| Value | Tines truthy? | JS truthy? | `IS_BLANK` [fn docs] | `IS_EMPTY` [fn docs] |
|---|---|---|---|---|
| `NULL` / missing key | no | no | true | not specified (text, array, object only); the port throws |
| `FALSE` | no | no | true | not specified; the port throws |
| `""` | **yes** | no | true | true |
| `0` | **yes** | no | false | not specified; the port throws |
| `[]`, `{}` | yes | yes | **true** | true |
| `"x"`, `1`, `[1]`, `{a: 1}` | yes | yes | false | false |

- Condition position (`IF`, `AND`, `OR`, `NOT`, the `&&` and OR operators, `<%if%>`, a lambda result in `FILTER` / `REJECT` / `FIND` / `COUNTIF`): use `truthy(v)`, i.e. `v !== false && v != null`. Not needed when the expression is already a real boolean (`a > 1`, `a === "x"`).
- Numeric text in math or comparison: wrap in `Number(...)` (see section 4).
- A value placed inside text (`<<v>>`, `a & b`): use `text(v)`. The function call `TEXT(v)`: use `textFn(v)`. A value placed inside an HTML body: use `esc(v)`.

## 8 Text mode: pills and control tags

Text mode has two kinds of insert [docs]: **value pills** `<<expr>>`, replaced by the text of their result, and **tags**, which control what is emitted. Tags exist only in text mode, can be nested, and every opening tag needs its matching end tag [docs]. The docs show tags only as editor screenshots; the spelling below is how exports store them [export].

| Tines | Meaning | TypeScript |
|---|---|---|
| `<%if cond%>` ... `<%elseif cond2%>` ... `<%else%>` ... `<%endif%>` | conditional output; any number of `elseif`, optional `else` [docs]; `cond` is any formula, judged with Tines truthiness | `if (truthy(cond)) { ... } else if (truthy(cond2)) { ... } else { ... }` |
| `<%for x in expr%>` ... `<%endfor%>` | repeats the body once per item of an array [docs]; `expr` may be any formula (`report.items`, `REVERSE(months)`, `MAP(WHERE(a, "k", v), "id")`) [export]; `x` exists only inside the body | `for (const x of expr ?? []) { ... }` |
| `FORLOOP.index0`, `FORLOOP.index`, `FORLOOP.first`, `FORLOOP.last` | inside a `for`: zero-based position, one-based position, true on the first pass, true on the last pass [docs] | `i`, `i + 1`, `i === 0`, `i === arr.length - 1` with `for (const [i, x] of arr.entries())` |
| `<% if cond %>`, `<% endif %>` | spaces inside the delimiters occur [export] | same as above |
| `raw` ... `endraw` tag pair | the content is emitted literally with no interpolation, so text containing `<<` can be written [docs]; assumed spelling `<%raw%>` ... `<%endraw%>` (not seen in exports) | a plain string literal |

**A pill that holds an array or an object** (`<<rows>>`, `<<fetch_item.body>>`): how Tines renders it is not specified in the docs. The skill's convention: it becomes JSON text, which is what `text()` gives. When a request body or a message depends on it (a list of rows inserted into a CSV body, an object inserted into a chat message), do two things: translate it with `text()`, or build the format the receiver needs in code, and record it under "Not verified" in the notes file.

How to turn a text value with tags into code:

```ts
// Tines text (3 lines):
//   Open items:
//   <%for item in report.items%>- <<item.title>><%if item.count > 1%> (x<<item.count>>)<%endif%>
//   <%endfor%><%if SIZE(report.items) = 0%>none<%endif%>
let out = "Open items:\n";
for (const item of report?.items ?? []) {
  out += `- ${text(item?.title)}`;
  if (Number(item?.count) > 1) out += ` (x${text(item.count)})`;
  out += "\n";                        // the newline before <%endfor%> is inside the loop body
}
if ((report?.items ?? []).length === 0) out += "none";
```

1. Start with `let out = ""` and walk the text left to right: literal text -> `out += "..."`, pill -> `out += text(expr)`, `<%if%>` / `<%for%>` -> a block that stays open until its `<%endif%>` / `<%endfor%>`. Nested tags become nested blocks, one to one.
2. Copy literal text exactly, including newlines and spaces that touch a tag. Whether tags trim adjacent whitespace is not specified in docs; real templates are written as if they do not: a row loop puts the newline before `<%endfor%>` (one line per item), a column loop puts `<%endfor%>` right after the cell (same line) [export]. Do not tidy blank lines.
3. The loop variable shadows any action with the same slug inside the body. Each `for` has its own `FORLOOP`.
4. A simple loop with no inner tags may be written `arr.map((x) => ...).join("")`; use the `let out` form whenever tags are nested.

## 9 Comments and escaping

- **Comments:** the docs describe no comment syntax for formulas, and none occurs in the exports. (Lines starting with `#` in the docs' code samples are annotations of the sample, not formula syntax.) If something that looks like a comment appears inside a formula, flag it; do not silently drop it.
- **Quotes inside text:** backslash, as in section 2 [docs].
- **A literal `<<` in text mode:** the only documented mechanism is the `raw` tag (section 8) [docs]. No escape sequence for `<<`, `>>`, `<%` or `%>` is documented.
- **A literal `=` at the start of a plain text value:** not specified in docs (a leading `=` means formula field in exports).
- **Dots in keys:** in path text passed to `SET_KEY` / `REMOVE_KEY`, a dot inside a key is written `\.` [fn docs]. For other keys with special characters use bracket access (section 3).

## 10 No clean TypeScript equivalent

| Tines construct | Why | What to do |
|---|---|---|
| pipe with `%` placeholder | JS has no pipeline operator | nest the calls or use one `const` per stage |
| Tines truthiness (`0`, `""` truthy) | JS conditions disagree | `truthy()` helper in every condition that is not already boolean |
| automatic text conversion in text mode and `&` | JS template literals print `[object Object]` and `null` | `text()` helper |
| missing path yields `NULL` | JS throws on a property of `undefined` | `?.` on every step |
| named function options (`strict: TRUE`) | no named arguments in JS | pick the right variant from the function's row |
| control tags and `FORLOOP` | templating language, not expressions | the `let out` recipe; needs statements, so it cannot be a single expression |
| `raw` tag | escaping device only | plain string literal |
| lambda stored in a `RESOURCE` | code loaded from data at run time | ask the user for the definition and port it as a static function |
| keywords `INFO`, `PAGE`, `STORY`, `team_case`, `META.*` | Tines platform state | flag for a human; replace with constants where the value is known |
| uppercase-only `TRUE` / `FALSE` / `NULL`, `=` for equality, `&` for joining text | same spelling means something else in JS | always rewrite; never copy an operator through unchanged except `*`, `-`, `<`, `>`, `<=`, `>=`, `!=` -> `!==` |

## 11 Not specified in docs

- Operators: operand types, mixed-type behaviour, `NULL` operands, precedence and associativity (section 4). Pipe-binds-loosest and grouping parentheses are from exports only.
- Whether the infix `&&` / OR operators skip their right side (the functions `AND` / `OR` do).
- `/` on two whole numbers (integer or float result).
- `=` across types and on arrays / objects.
- Number notation beyond plain, decimal and negative; negative array positions.
- How `NULL`, booleans and decimal numbers are rendered as text (assumed `""`, `"true"` / `"false"`, plain JS number text).
- How an array or an object inside a `<<pill>>` or next to `&` is rendered as text. Skill convention: JSON (`text()`). Record it under "Not verified" in the notes when a request body or a message depends on it (section 8).
- Whether control tags trim surrounding whitespace; the export spelling of the `raw` tag.
- Comment syntax; escaping of `<<` outside the `raw` tag; a literal leading `=` in plain text.
- Scope rules when a lambda parameter, a loop variable and an action slug share a name (assumed: innermost wins).
