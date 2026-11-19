# Tines formulas -> TypeScript: worked translations

Companion to [tines-formula-language.md](tines-formula-language.md) (syntax) and [tines-formulas-to-ts.md](tines-formulas-to-ts.md) (function lookup tables and the helpers `text`, `isBlank`, `truthy`, `toDate`, `tinesDate`, `dateDiff`, `typeOf` used below). Ordered simple to hard. Every name, host and literal here is invented (a parcel-tracking story, then a few reporting ones); the formula shapes are ones observed in real exports. Action slugs (`fetch_scans`, `explode_parcels`, `depots`, ...) are variables holding that action's output; `resource`, `local`, `loop` hold `RESOURCE`, `LOCAL`, `LOOP`. All snippets were run under Node.

**Index:** 1 text with pills | 2 text mode vs `=`, `LOCAL`, `GET`, `IF` | 3 `REJECT` + `INDEX_OF` | 4 nested lambdas, index 0 | 5 `DATE` `%s` arithmetic | 6 pipe into `MAP_LAMBDA` | 7 `WHERE` + `FIRST` + path | 8 multi-line text | 9 `DATE` / `DATE_PARSE` chains | 10 `MAP_LAMBDA` / `SET_KEY` pipelines | 11 nested control tags

**1. Text with pills** (URL of an HTTP request; `cursor_parameter` is an upstream action whose output is a string).
```ts
// Tines: https://api.example.com/depots/<<explode_depots.id>>/scans?state=held&limit=500<<cursor_parameter>>
const url = `https://api.example.com/depots/${text(explode_depots?.id)}/scans?state=held&limit=500${text(cursor_parameter)}`;
```

**2. Text mode vs `=`; `LOCAL`; `GET` with a dynamic key; `IF` + `IS_BLANK`; `&`.** Evaluate `local` first.
```ts
// Tines: <<fetch_scans.status>>         (one pill is still text: a trigger rule compares it with "200")
const status = text(fetch_scans?.status);   // "200", a string
// Tines: =SIZE(damaged)                 (whole-value formula keeps the number)
const count = (damaged ?? []).length;
// Tines local.cursor: =GET(RESOURCE.last_scan_cursor, explode_depots.id)
// Tines payload:      =IF(IS_BLANK(LOCAL.cursor), "", "&after=" & LOCAL.cursor)
const local = { cursor: resource.last_scan_cursor?.[explode_depots?.id] ?? null };
const payload = isBlank(local.cursor) ? "" : "&after=" + text(local.cursor);
```

**3. `REJECT` + `INDEX_OF` + pipe + `IS_BLANK`.** Read inside-out: the lambda is true when `"damaged"` is NOT among the flag codes; `REJECT` drops those; so the result keeps scans that carry the flag `damaged`.
```ts
// Tines: =REJECT(fetch_scans.body.items, LAMBDA(scan, INDEX_OF(MAP(scan.flags, "code"),"damaged") |> IS_BLANK(%)))
const damaged = (fetch_scans?.body?.items ?? []).filter(
  (scan: any) => (scan?.flags ?? []).map((f: any) => f?.code ?? null).includes("damaged"),
);
```

**4. Nested lambdas where index `0` must count as true.** Inner `INDEX_OF(flag, "customs")` is a text search (index or `NULL`). Outer `INDEX_OF(codes, LAMBDA)` is the first matching index or `NULL`. Index `0` is truthy in Tines, so `REJECT` drops every scan with any flag code containing `customs`. A literal `indexOf(...)` translation gets index 0 wrong.
```ts
// Tines: =REJECT(fetch_scans.body.items, LAMBDA(scan,
//          MAP(scan.flags, "code") |> INDEX_OF(%, LAMBDA(flag, INDEX_OF(flag,"customs")))))
const not_customs = (fetch_scans?.body?.items ?? []).filter(
  (scan: any) => !(scan?.flags ?? []).some((f: any) => String(f?.code ?? "").includes("customs")),
);
```

**5. `DATE` with `%s`, `NUMBER`, `MAX`, arithmetic after `IF`.** `%s` is unix seconds as text; the `+ 30` applies to the whole `IF` result.
```ts
// Tines local.cursor_s:   =GET(RESOURCE.last_scan_cursor, explode_depots.id) |> NUMBER(%)
// Tines local.scan_s: =DATE(explode_parcels.scan.scanned_at,"%s") |> NUMBER(%)
// Tines payload.newest:  =IF(IS_BLANK(LOCAL.cursor_s), LOCAL.scan_s, MAX(LOCAL.cursor_s,LOCAL.scan_s)) + 30
const saved = resource.last_scan_cursor?.[explode_depots?.id];
const scannedAt = toDate(explode_parcels?.scan?.scanned_at);
const local = {
  cursor_s: isBlank(saved) ? null : Number(saved),   // NUMBER(NULL) is not specified in docs, so keep null
  scan_s: Math.floor(scannedAt!.getTime() / 1000),   // throws when the timestamp cannot be read
};
const newest = (local.cursor_s == null ? local.scan_s : Math.max(local.cursor_s, local.scan_s)) + 30;
```

**6. Pipe into `MAP_LAMBDA`, `&` concatenation.**
```ts
// Tines: =REJECT(request_carrier_quotes.body.quote_results.offers, LAMBDA(offer, IS_BLANK(offer.rating)))
//        |> MAP_LAMBDA(%, LAMBDA(q, q.carrier & ":"& q.rating))
const summary = (request_carrier_quotes?.body?.quote_results?.offers ?? [])
  .filter((offer: any) => !isBlank(offer?.rating))
  .map((q: any) => text(q?.carrier) + ":" + text(q?.rating));
```

**7. `WHERE`, then `FIRST`, then a path on the piped result.**
```ts
// Tines: =WHERE(collect_results,"channel","sms") |> FIRST(%).payload
const sms = (collect_results ?? []).filter((o: any) => o?.channel === "sms")[0]?.payload ?? null;
```

**8. Multi-line text with function pills and an object pill** (message body, shortened).
```ts
// Tines: <p><<explode_parcels.scan.courier.name>> - <<locate_depot.body.town>></p>
//        <p><<MAP(explode_parcels.scan.flags,"code") |> JOIN(%, " / ")>></p>
//        <p>https://track.example.com/parcel/<<BASE64_ENCODE(explode_parcels.scan.tracking_ref)>>/history</p>
//        <p><<explode_parcels.scan>></p>
const scan = explode_parcels?.scan;
// HTML body: every inserted value goes through esc() (defined in tines-formulas-to-ts.md section 1).
const body = `<p>${esc(scan?.courier?.name)} - ${esc(locate_depot?.body?.town)}</p>
<p>${(scan?.flags ?? []).map((f: any) => esc(f?.code)).join(" / ")}</p>
<p>https://track.example.com/parcel/${Buffer.from(text(scan?.tracking_ref)).toString("base64")}/history</p>
<p>${esc(scan)}</p>`;   // object pill -> JSON text
```

**9. `DATE` / `DATE_PARSE` chains.** (a) Relative-date text, formatted to month and year, re-parsed to unix seconds (a month name parses to the START of that month), minus one second, then formatted as ISO: the last second of the month before. `|>` binds loosest, so the `- 1` happens before the pipe. (b) `DATE_PARSE` with an explicit format, `.iso8601` field, `DATE_DIFF`. (c) Several `DATE_PARSE(...)` fields joined with `&` collapse into one format string.
```ts
// Tines (a): <<DATE(DATE("6 weeks ago", '%b %Y'), '%s') - 1 |> DATE(%)>>
const ref = new Date(Date.now() - 42 * 86400 * 1000);                                // 6 weeks ago
const monthStart = Date.UTC(ref.getUTCFullYear(), ref.getUTCMonth(), 1) / 1000;      // start of that month, unix seconds
const cutoff = new Date((monthStart - 1) * 1000).toISOString();                      // DATE(%) with no format = ISO 8601
// Tines (b): =DATE_DIFF(DATE_PARSE(LOOP.value.opens_on, "%d%m%Y").iso8601, DATE_PARSE(LOOP.value.closes_on, "%d%m%Y").iso8601)
const dmy = (s: string) => new Date(Date.UTC(Number(s.slice(4, 8)), Number(s.slice(2, 4)) - 1, Number(s.slice(0, 2))));
const span = dateDiff(dmy(loop.value.opens_on).toISOString(), dmy(loop.value.closes_on).toISOString());
// Tines (c): <<DATE_PARSE(deadline.at).day_name & ", " & DATE_PARSE(deadline.at).day & " " & DATE_PARSE(deadline.at).month_name & " (month " & DATE_PARSE(deadline.at).month & ")">>
const label = tinesDate(deadline?.at, "%A, %-d %B (month %-m)");                     // "Thursday, 7 March (month 3)"
```

**10. `WHERE` / `MAP_LAMBDA` / `SET_KEY` / `SORT` / `REVERSE` pipelines.** (a) Inside the lambda, `box |> SET_KEY(%, ...) |> SET_KEY(%, ...)` adds keys one at a time, and `%.returned` reads from the piped value: one object spread does it. (b) `MAP_LAMBDA` to one-key objects, then `REDUCE` with `MERGE` = build an object from pairs. (c) `REDUCE` over a list of keys with `SET_KEY` and a dynamic key `record[col]` = pick and convert keys.
```ts
// Tines (a): =WHERE(lockers, "kind", "outdoor")
//            |> MAP_LAMBDA(%, LAMBDA(box, box |> SET_KEY(%, "returned_total", SIZE(%.returned)) |> SET_KEY(%, "collected_total", SIZE(%.collected))))
//            |> SORT(%, "collected_total") |> REVERSE(%)
const ranked = (lockers ?? [])
  .filter((o: any) => o?.kind === "outdoor")
  .map((box: any) => ({ ...box, returned_total: (box?.returned ?? []).length, collected_total: (box?.collected ?? []).length }))
  .sort((a: any, b: any) => a.collected_total - b.collected_total)
  .reverse();
// Tines (b): =MAP_LAMBDA(quarters, LAMBDA(q, OBJECT(q.label, q.volume)))
//            |> REDUCE(%, LAMBDA(merged, pair, MERGE(merged, pair)), OBJECT())
const by_label = Object.fromEntries((quarters ?? []).map((q: any) => [q?.label, q?.volume]));
// Tines (c): =MAP_LAMBDA(rows, LAMBDA(record, REDUCE(column_keys, LAMBDA(out, col,
//              SET_KEY(out, col, IF(TYPE(record[col]) = "Hash", TO_JSON(record[col]) |> BASE64_ENCODE(%), record[col]))), OBJECT())))
const flat = (rows ?? []).map((record: any) =>
  Object.fromEntries(column_keys.map((col: string) => {
    const v = record?.[col] ?? null;
    return [col, typeOf(v) === "Hash" ? Buffer.from(JSON.stringify(v)).toString("base64") : v];
  })));
```

**11. Text template with nested control tags** (a Markdown table: header loop, row loop with an inner cell loop, `FORLOOP.index`, `if` / `elseif` / `else`). Follow the `let out` recipe in section 8 of [tines-formula-language.md](tines-formula-language.md); every literal character, including each newline, is copied.
```ts
// Tines text (4 lines; line 3 ends with a newline before <%endfor%>):
//   | # | Depot |<%for q in REVERSE(quarters)%> <<DATE(q.start, "%b %y")>> |<%endfor%> total |
//   |--|--|<%for q in REVERSE(quarters)%>--|<%endfor%>--|
//   <%for row in depots%>| <<FORLOOP.index>> | <<row.name>> |<%for cell in row.cells%> <<cell.volume>> |<%endfor%> <<row.total>> |
//   <%endfor%><%if SIZE(depots) > 10%>Showing <<SIZE(depots)>> depots.<%elseif SIZE(depots) = 0%>No depots yet.<%else%><%endif%>
const cols = (quarters ?? []).flat(Infinity).reverse();        // REVERSE(quarters), evaluated once
let out = "| # | Depot |";
for (const q of cols) out += ` ${tinesDate(q?.start, "%b %y")} |`;
out += " total |\n|--|--|";
for (const q of cols) out += "--|";
out += "--|\n";
for (const [i, row] of (depots ?? []).entries()) {
  out += `| ${i + 1} | ${text(row?.name)} |`;                   // FORLOOP.index is 1-based
  for (const cell of row?.cells ?? []) out += ` ${text(cell?.volume)} |`;
  out += ` ${text(row?.total)} |\n`;
}
if ((depots ?? []).length > 10) out += `Showing ${(depots ?? []).length} depots.`;
else if ((depots ?? []).length === 0) out += "No depots yet.";
```
