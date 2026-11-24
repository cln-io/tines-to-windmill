# Tines to Windmill patterns: one recipe per shape

Find the shape you see in the outline. Open that one recipe. Copy it. Change names, URLs, fields and paths. Keep the structure.

**Status: validated structurally only.** Every `flow.yaml` and action map below passes `scripts/validate_flow.py`, and every TypeScript file passes a syntax check. **Nothing here was run on a Windmill instance.** Section 32 lists what is not verified. The outline blocks are real output of `scripts/tines_outline.py` on an invented story ("Library - desk automations"). Every name, host and value is made up.

How to read a recipe:

- Open one recipe with `python3 scripts/ref.py patterns 7`. The table below is `python3 scripts/ref.py patterns 0`.
- **Outline shows**: the lines that identify the shape. Other lines are left out.
- The outline prints `recipe N,M` at the end of an action line. `N` and `M` are section numbers of this file.
- A block that starts with `# flow.yaml` is one complete small flow. Copy its `properties` entries and its `modules` items into your flow.
- A block that starts with `// name.ts` is one complete step file. The file name is the step id.
- A block that starts with `# workflow:` holds the lines for `tines_action_map.md`.
- **Notes file**: what this shape adds to `<flow_name>.NOTES.md`.
- All recipes use the folder `f/library`. Use your own folder.
- Step ids must be unique in your flow. Rename a step if two recipes give the same id. Rename its `.ts` file too.
- Tines continues after a non-2xx HTTP response. These recipes throw instead, unless the story reads the status (recipe 7). Write each such change under "Behaviour differences".
- Starter files to copy are in `templates/`: `flow.yaml`, `http_get.ts`, `http_post.ts`, `transform.ts`, `state_read.ts`, `state_write.ts`, `send_email.ts`, `ask_approval.ts`, `preprocessor.ts`, `failure.ts`, `FLOW_NAME.schedule.yaml`, `FLOW_NAME.NOTES.md`, `PLAN.md`.

| What you see in the outline | Recipe |
|---|---|
| `ENTRY: schedule cron ...` | 1 |
| `[webhook]  ENTRY: webhook`, and later actions read only `<name>.body.x` | 2 |
| `[webhook]`, and later actions read `<name>.headers.x` or query values, or the sender must keep its own secret | 3 |
| `[page/...]  ENTRY: page` | 4 |
| `[page/...]` with `links: in aNN` (a page that is not the entry) | 5 |
| `[http_request]` followed by a `[trigger]` whose rule tests `.status` against `200` | 6 |
| A `[trigger]` that tests `.status` against `404`, `409`, ..., or a `(no-match)` link after a status trigger | 7 |
| `retry_on_status:` or `retries:` on an `[http_request]` | 8 |
| `CYCLE` on a delay, an HTTP request and a trigger | 9 |
| `disable_ssl_verification: true` | 10 |
| `[event_transform/message_only]` | 11 |
| `<%for ...%>` or `<%if ...%>` inside a `payload:` or `body:` text | 12 |
| `[event_transform/explode]`, with or without `[event_transform/implode]` | 13 |
| `(no-match)` in front of an action. `NO-MATCH FAN-OUT xN` on a trigger: all N no-match links fire | 14 |
| `FAN-OUT xN` (N match links from one action) | 15 |
| `JOIN xN` on an action that is not an implode and has no `CYCLE` | 16 |
| `[group]` and `{ inside group aNN:` | 17 |
| `[send_to_story]` with `calls: STORY.x - body embedded in this export` | 18 |
| `[event_transform/delay]` without `CYCLE` | 19 |
| `[event_transform/throttle]` | 20 |
| `[event_transform/deduplicate]` | 21 |
| `[send_email]` | 22 |
| `RESOURCE.x` on a `uses:` line, and nothing writes it | 23 |
| `RESOURCE.x` read, and a URL with `/api/v1/global_resources/` writes it | 24 |
| `CREDENTIAL.x` | 25 |
| `=META`, `META.x` or `STORY_RUN_GUID()` | 26 |
| `CALLED AS FUNCTION`, or `body NOT in this export`, or another URL of the Tines tenant | 27 |
| A delete or send action fed by `DEFAULT(<filtered list>, <full list>)` or a similar fallback | 28 |
| `DISABLED`, `UNREACHABLE`, `DEAD-END`, `NOT TRIGGERED` | 29 |
| `JOIN xN` after a `(no-match)` link, and the joined action reads the output of an action that only one side runs | 30 |
| `PAGE.x` on the `uses:` line of an action that is not that page | 31 |

Four helpers appear in several recipes. Paste the ones a step uses. They have the same names and the same behaviour in every reference file:

```ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
const truthy = (v: any): boolean => v !== false && v != null;      // Tines: 0 and "" are truthy
// text(v): what a <<pill>> or `a & b` does with a value. null gives "". An array or object gives JSON.
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
// esc(v): text(v) made safe for HTML. Every value put into an HTML body goes through esc().
const esc = (v: any): string =>
  text(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
```

Rules for values put into text:

- A `<<pill>>` and `a & b`: use `text()`. The Tines function `TEXT(x)` is different: use `textFn(x)` from `tines-formulas-to-ts.md` section 1. Never use `text()` for `TEXT()`.
- An array or object inside a pill becomes JSON. That is this skill's convention. Tines does not specify it. When a request body or a message depends on it, write it under "Not verified" in the notes.
- HTML (an email body, an HTML page): build it in the script and put every value through `esc()` (recipe 22).
- Markdown chat message: use `text()`, not `esc()`. HTML entities would show as text, and Tines did not escape either. A value from outside can still add formatting, a link or a mention. If the values come from outside the organisation, say so under "Not verified". In a Markdown table cell replace the pipe character and line breaks: `text(v).replace(/\|/g, "\\|").replace(/\r?\n/g, " ")`.
- A URL inside a message comes from a variable or is built with `encodeURIComponent` on each inserted value.

## 1. Schedule on an action

**Outline shows**
```text
a001 branch_list  "branch list"  [event_transform/message_only]  ENTRY: schedule cron 0 7 * * 1-5 (Europe/Dublin); schedule cron 30 13 * * 6 (Europe/Dublin)  recipe 1,11
  payload: ["central", "harbour", "hillside"]
a002 request_shelf_check  "Request shelf check"  [http_request]  recipe 6,25
  payload: {"branches": "=branch_list"}
```
**Write** one schedule file per cron line. Put it next to the flow folder, not inside it.
```yaml
# f/library/shelf_check.schedule.yaml
schedule: "0 0 7 * * 1-5"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/shelf_check
is_flow: true
args: {}
```
```yaml
# f/library/shelf_check_2.schedule.yaml
schedule: "0 30 13 * * 6"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/shelf_check
is_flow: true
args: {}
```
```yaml
# flow.yaml
summary: Request the shelf check
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties:
    branch_codes: {type: array, items: {type: string}, default: [central, harbour, hillside]}
value:
  modules:
    - id: request_shelf_check
      value:
        type: rawscript
        language: bun
        content: "!inline request_shelf_check.ts"
        input_transforms:
          branch_codes: {type: javascript, expr: "flow_input.branch_codes"}
          api_key: {type: static, value: "$var:f/library/catalog_key"}
```
```ts
// request_shelf_check.ts
// a002 Request shelf check
export async function main(branch_codes: string[], api_key: string) {
  const res = await fetch("https://catalog.example.org/api/v2/shelf-checks", {
    method: "POST",
    headers: { "X-Api-Key": api_key, "Content-Type": "application/json" },
    body: JSON.stringify({ branches: branch_codes }),
  });
  if (!res.ok) throw new Error(`shelf check returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w01
a001 -> flow_input.branch_codes   # branch list [event_transform/message_only]
a002 -> request_shelf_check   # Request shelf check [http_request]
```
**Goes wrong**
- The Tines cron has 5 fields. Windmill needs 6. Put `0` (seconds) in front and copy the five fields unchanged: `0 7 * * 1-5` becomes `0 0 7 * * 1-5`.
- The schedule is written inside `flow.yaml`. A flow file never holds its trigger.
- Two cron lines in one file. Write one file per cron line, each with its own file name and the same `script_path`.
- `script_path` is the flow path without `.flow`. `args` holds only the inputs that have no default.

**Notes file**
- Setup: each schedule file, with the Tines cron line it replaces and the timezone. The secret variable `f/library/catalog_key`.
- Behaviour differences: the scheduled action's constant payload is now the default of the flow input `branch_codes`.
- Not verified: a day-of-week number (`1-5`, `6`). Windmill may count week days differently from Tines. Ask the user to check the next run times in Windmill.

## 2. Webhook entry, body fields only

**Outline shows**
```text
a003 suggestion_in  "suggestion in"  [webhook]  ENTRY: webhook  recipe 2
  verbs: get,post
a004 record_suggestion  "Record suggestion"  [http_request]  recipe 6,25
  payload: {"title": "<<suggestion_in.body.title>>", "isbn": "<<suggestion_in.body.isbn>>", "member": "<<suggestion_in.body.member_id>>"}
```
**Write** one flow input per `<webhook>.body.x` that a later action reads. No trigger file: every flow has a webhook.
```yaml
# flow.yaml
summary: Record a purchase suggestion
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [title]
  properties:
    title: {type: string}
    isbn: {type: string, default: ""}
    member_id: {type: string, default: ""}
value:
  modules:
    - id: record_suggestion
      value:
        type: rawscript
        language: bun
        content: "!inline record_suggestion.ts"
        input_transforms:
          title: {type: javascript, expr: "flow_input.title"}
          isbn: {type: javascript, expr: "flow_input.isbn"}
          member_id: {type: javascript, expr: "flow_input.member_id"}
          api_key: {type: static, value: "$var:f/library/catalog_key"}
```
```ts
// record_suggestion.ts
// a004 Record suggestion
export async function main(title: string, isbn: string, member_id: string, api_key: string) {
  const res = await fetch("https://catalog.example.org/api/v2/suggestions", {
    method: "POST",
    headers: { "X-Api-Key": api_key, "Content-Type": "application/json" },
    body: JSON.stringify({ title, isbn, member: member_id }),
  });
  if (!res.ok) throw new Error(`suggestions returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w02
a003 -> flow_input.title, flow_input.isbn, flow_input.member_id   # suggestion in [webhook]
a004 -> record_suggestion   # Record suggestion [http_request]
```
**Goes wrong**
- The webhook `path` and `secret` are copied into a file. Never copy them. The Windmill webhook has its own URL and token.
- An input named `body`. The JSON body keys are the inputs: `{"title": "x"}` gives `flow_input.title`.
- `verbs: get,post` is ignored. The Windmill webhook takes POST. Say so in the notes.

**Notes file**
- Setup: the sender must call `POST <base_url>/api/w/<workspace>/jobs/run/f/f/library/record_suggestion` with the header `Authorization: Bearer <Windmill token>` and the same JSON body.
- Behaviour differences: the Tines webhook also accepted GET; the Windmill webhook takes POST. Tines answered `Ok`; Windmill answers with a job id.

## 3. Webhook entry that needs headers, query values or a secret check

**Outline shows**
```text
a005 courier_update  "courier update"  [webhook]  ENTRY: webhook  recipe 3
  secret: <redacted>
  include_headers: true
a006 update_parcel  "Update parcel"  [http_request]  recipe 6,25
  payload: {"state": "<<courier_update.body.state>>", "depot": "<<courier_update.headers.x_courier_depot>>", "trace": "<<courier_update.body.trace>>"}
```
**Write** a `preprocessor_module` beside `modules`. It gets the raw request and returns the flow inputs.
```yaml
# flow.yaml
summary: Update a parcel from a courier message
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties:
    parcel_id: {type: string}
    state: {type: string}
    depot: {type: string, default: ""}
    trace: {type: string, default: ""}
value:
  preprocessor_module:
    id: preprocessor
    value:
      type: rawscript
      language: bun
      content: "!inline preprocessor.ts"
      input_transforms: {}
  modules:
    - id: update_parcel
      value:
        type: rawscript
        language: bun
        content: "!inline update_parcel.ts"
        input_transforms:
          parcel_id: {type: javascript, expr: "flow_input.parcel_id"}
          state: {type: javascript, expr: "flow_input.state"}
          depot: {type: javascript, expr: "flow_input.depot"}
          trace: {type: javascript, expr: "flow_input.trace"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// preprocessor.ts
import * as wmill from "windmill-client";
import { timingSafeEqual } from "node:crypto";

// a005 courier update. The function must be named preprocessor, not main.
export async function preprocessor(event: {
  kind: string; body?: any; query?: Record<string, string>; headers?: Record<string, string>;
}) {
  const headers = event.headers ?? {};
  // Secret check. Keep these 4 lines only when the route has authentication_method: none.
  const expected = Buffer.from(await wmill.getVariable("f/library/courier_update_secret"));
  const given = Buffer.from(headers["x-courier-secret"] ?? "");
  if (given.length !== expected.length || !timingSafeEqual(given, expected))
    throw new Error("courier update: wrong or missing secret");
  return {
    parcel_id: event.body?.parcel_id ?? null,
    state: event.body?.state ?? null,
    depot: headers["x-courier-depot"] ?? "",                // Tines: courier_update.headers.x_courier_depot
    trace: event.body?.trace ?? event.query?.trace ?? "",   // Tines puts query values into body
  };
}
```
```ts
// update_parcel.ts
// a006 Update parcel
export async function main(parcel_id: string, state: string, depot: string, trace: string, api_token: string) {
  const res = await fetch(`https://loans.example.org/v1/parcels/${encodeURIComponent(parcel_id)}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ state, depot, trace }),
  });
  if (!res.ok) throw new Error(`parcel update returned ${res.status}`);
  return { status: res.status };
}
```
Only when the sender cannot send a Windmill token, or needs its own URL or GET, also write a route file next to the flow folder:
```yaml
# f/library/courier_update.http_trigger.yaml
script_path: f/library/update_parcel
is_flow: true
route_path: library/courier-update
http_method: post
request_type: async
authentication_method: none
is_static_website: false
workspaced_route: false
wrap_body: false
raw_string: false
```
```text
# workflow: w03
a005 -> flow_input.parcel_id, flow_input.state, flow_input.depot, flow_input.trace   # courier update [webhook]
a006 -> update_parcel   # Update parcel [http_request]
```
**Goes wrong**
- The preprocessor is put inside `modules`, or its function is named `main`, or it reads `results`.
- The returned keys differ from `schema.properties`. They must be the same names.
- Header names: Tines gives `x_courier_depot`, Windmill is expected to give `x-courier-depot`. Not verified.
- The Tines `secret` is written into a file. Use a secret variable with a new value.

**Notes file**
- Setup: the secret variable `f/library/courier_update_secret` (new value, to be given to the sender, who sends it in the header `X-Courier-Secret`). The route URL, or the webhook URL of recipe 2.
- Behaviour differences: the secret moved from the URL to a header. One route file takes one HTTP method.
- Not verified: header key spelling, and that the route URL is `<base_url>/api/r/library/courier-update`.

## 4. Page that starts a workflow

**Outline shows**
```text
a007 book_a_room  "Book a room"  [page/success_page]  ENTRY: page  recipe 4
    input room [OPTION] required: {"default_value": "Oak", "options": ["Oak", "Birch", "Studio"]}
    input day [SHORT_TEXT] required
    input attendees [SHORT_TEXT]: {"default_value": 2}
    input needs_projector [BOOLEAN]: {"default_value": false}
    button "Book" [BUTTON]: {"label": "Book"}
    button "Ask" [BUTTON]: {"label": "Ask a librarian"}
  success_message: Thank you. We will confirm by email.
    room: =FIRST(book_a_room.body.room)
    action: <<book_a_room.body.button>>
    requested_by: <<book_a_room.headers.email>>
```
**Write** one `schema` property per input field, and one `button` property when the page has several buttons. Give `button` a default only when that button's path is harmless. When a button deletes, sends or blocks something, leave the default out and put `button` under `required`.
```yaml
# flow.yaml
summary: Book a study room
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  order: [room, day, attendees, needs_projector, button]
  required: [room, day]
  properties:
    room: {type: string, enum: [Oak, Birch, Studio], default: Oak}
    day: {type: string, description: Day of the booking}
    attendees: {type: integer, default: 2}
    needs_projector: {type: boolean, default: false}
    button: {type: string, enum: [Book, Ask a librarian], default: Book, description: The button pressed on the Tines page}
value:
  modules:
    - id: create_booking
      value:
        type: rawscript
        language: bun
        content: "!inline create_booking.ts"
        input_transforms:
          room: {type: javascript, expr: "flow_input.room"}
          day: {type: javascript, expr: "flow_input.day"}
          attendees: {type: javascript, expr: "flow_input.attendees"}
          needs_projector: {type: javascript, expr: "flow_input.needs_projector"}
          button: {type: javascript, expr: "flow_input.button"}
          api_token: {type: static, value: "$var:f/library/rooms_token"}
```
```ts
// create_booking.ts
// a008 Create booking
export async function main(
  room: string, day: string, attendees: number, needs_projector: boolean, button: string, api_token: string,
) {
  const res = await fetch("https://rooms.example.org/api/bookings", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      room,                                        // =FIRST(book_a_room.body.room): the input is one value already
      day,
      attendees: Number(attendees),                // =NUMBER(book_a_room.body.attendees)
      projector: needs_projector,
      action: button,                              // book_a_room.body.button
      requested_by: process.env.WM_EMAIL ?? null,  // book_a_room.headers.email: the user who runs the flow
    }),
  });
  if (!res.ok) throw new Error(`booking returned ${res.status}`);
  return { message: "Thank you. We will confirm by email." };   // the page's success_message
}
```
```text
# workflow: w04
a007 -> flow_input.room, flow_input.day, flow_input.attendees, flow_input.needs_projector, flow_input.button   # Book a room [page/success_page]
a008 -> create_booking   # Create booking [http_request]
```
**Goes wrong**
- An `OPTION` field is a list in Tines, so the story writes `FIRST(...)`. The flow input is one string. Drop the `FIRST`.
- The buttons are forgotten. The story branches on `body.button`. Make it an input with one `enum` value per button label.
- Display elements (`text title`, `text paragraph`, a divider) become inputs. They are not inputs. Leave them out.

**Notes file**
- Setup: the users run the flow from its Windmill form. A table of page field to flow input.
- Behaviour differences: a styled or public page needs a Windmill app; the form needs a Windmill login. The success message is the flow result.
- Not verified: `WM_EMAIL` as the replacement for `headers.email`.

## 5. Page in the middle of a workflow (approval step)

**Outline shows**
```text
a010 get_fines  "Get fines"  [http_request]  recipe 6,25
  links: in a009 | out a011
a011 confirm_waiver  "Confirm waiver"  [page/success_page]  recipe 5
  links: in a010 | out a012
    text paragraph: Member <<waiver_request.body.member_id>> owes <<get_fines.body.total>>.
    input fines [TABLE]: {"content": "=get_fines.body.items"}
    input reason [LONG_TEXT] required
    button "Waive" [BUTTON]: {"label": "Waive these fines"}
  payload: {"reason": "<<confirm_waiver.body.reason>>", "approved_by": "<<confirm_waiver.headers.email>>"}
```
**Write** a step with `suspend`. Its script runs first. Then the flow waits for the form.
```yaml
# flow.yaml
summary: Waive fines after confirmation
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member_id]
  properties:
    member_id: {type: string}
value:
  modules:
    - id: confirm_waiver
      suspend:
        required_events: 1
        timeout: 86400
        resume_form:
          schema:
            type: object
            required: [reason]
            properties:
              reason: {type: string, description: Why these fines are waived}
      value:
        type: rawscript
        language: bun
        content: "!inline confirm_waiver.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: waive_fines
      value:
        type: rawscript
        language: bun
        content: "!inline waive_fines.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          reason: {type: javascript, expr: "resume?.reason ?? ''"}
          approved_by: {type: javascript, expr: "approvers?.[0] ?? null"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// confirm_waiver.ts
import * as wmill from "windmill-client";

// a010 Get fines, a011 Confirm waiver. Return what the page showed, plus the link to the form.
export async function main(member_id: string, api_token: string) {
  const res = await fetch(`https://loans.example.org/v1/members/${encodeURIComponent(member_id)}/fines`, {
    headers: { Authorization: `Bearer ${api_token}` },
  });
  if (!res.ok) throw new Error(`fines returned ${res.status}`);
  const fines: { total: number; items: any[] } = await res.json();
  const urls = await wmill.getResumeUrls("desk");   // { approvalPage, resume, cancel }
  return {
    summary: `Member ${member_id} owes ${fines.total}.`,   // the page's paragraph
    fines: fines.items ?? [],                              // the page's table
    approval_page: urls.approvalPage,                      // page with the form, Approve and Reject
  };
}
```
```ts
// waive_fines.ts
// a012 Waive fines
export async function main(member_id: string, reason: string, approved_by: string | null, api_token: string) {
  const res = await fetch(`https://loans.example.org/v1/members/${encodeURIComponent(member_id)}/fines/waive`, {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ reason, approved_by }),
  });
  if (!res.ok) throw new Error(`waive returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w05
a009 -> flow_input.member_id   # waiver request [webhook]
a010 -> confirm_waiver   # Get fines [http_request]
a011 -> confirm_waiver   # Confirm waiver [page/success_page]
a012 -> waive_fines   # Waive fines [http_request]
```
**Goes wrong**
- `suspend` is put inside `value`, or on a `type: identity` step, or the script never calls `getResumeUrls`.
- `resume` and `approvers` are read in a later step. They exist only in the step right after the suspend step.
- Nobody gets the link. If the story sent the page link in a message (`PAGE.confirm_waiver`), send `urls.approvalPage` in that message. If not, the person opens the waiting run in Windmill.
- No `timeout`. The default is 1800 seconds. On timeout or Reject the flow fails.

**Notes file**
- Setup: who approves, and how they reach the form (the waiting run in Windmill, or the link in the step result).
- Behaviour differences: the page is now an approval form. It times out after 24 hours and then the run fails; the Tines page waited without limit. Reject fails the run.
- Not verified: how the Windmill approval page shows the step result (`summary`, `fines`); the content of `approvers`.

## 6. HTTP request, status trigger, transform

**Outline shows**
```text
  a013 get_new_arrivals [http_request]  ENTRY: schedule cron */30 * * * * (Europe/Dublin)  recipe 1,6,25
    a014 _200 [trigger]  recipe 6
      a015 titles [event_transform/message_only]  recipe 11
        a016 publish_arrivals [http_request]  END  recipe 6,25
  url: https://catalog.lib.internal/api/v2/arrivals?days=1
  rules: [{"type": "field==value", "value": "200", "path": "<<get_new_arrivals.status>>"}]
  payload: =MAP(get_new_arrivals.body.items, "title")
```
**Write** one script for request + status check + transform. Return only what later steps use.
```yaml
# flow.yaml
summary: Publish new arrivals on the lobby board
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties: {}
value:
  modules:
    - id: fetch_new_arrivals
      value:
        type: rawscript
        language: bun
        content: "!inline fetch_new_arrivals.ts"
        input_transforms:
          catalog_base_url: {type: static, value: "$var:f/library/catalog_base_url"}
          api_key: {type: static, value: "$var:f/library/catalog_key"}
    - id: publish_arrivals
      value:
        type: rawscript
        language: bun
        content: "!inline publish_arrivals.ts"
        input_transforms:
          titles: {type: javascript, expr: "results.fetch_new_arrivals.titles"}
          board_key: {type: static, value: "$var:f/library/signage_key"}
```
```yaml
# f/library/publish_arrivals.schedule.yaml
schedule: "0 */30 * * * *"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/publish_arrivals
is_flow: true
args: {}
```
```ts
// fetch_new_arrivals.ts
type Arrival = { title?: string };

// a013 Get new arrivals, a014 200, a015 titles
export async function main(catalog_base_url: string, api_key: string): Promise<{ titles: (string | null)[] }> {
  // The story's URL has an internal host. The host is not copied: the base URL comes from a variable.
  const res = await fetch(`${catalog_base_url}/api/v2/arrivals?days=1`, {
    headers: { "X-Api-Key": api_key },
  });
  if (res.status !== 200) throw new Error(`arrivals returned ${res.status}`);   // a014: only 200 continues
  const body: { items?: Arrival[] } = await res.json();
  return { titles: (body.items ?? []).map((a) => a?.title ?? null) };           // =MAP(items, "title")
}
```
```ts
// publish_arrivals.ts
// a016 Publish arrivals
export async function main(titles: (string | null)[], board_key: string) {
  const res = await fetch("https://signage.example.net/api/boards/lobby", {
    method: "POST",
    headers: { "X-Board-Key": board_key, "Content-Type": "application/json" },
    body: JSON.stringify({ lines: titles }),
  });
  if (!res.ok) throw new Error(`board returned ${res.status}`);
  return { status: res.status, lines: titles.length };
}
```
```text
# workflow: w06
a013 -> fetch_new_arrivals   # Get new arrivals [http_request]
a014 -> fetch_new_arrivals   # 200 [trigger]
a015 -> fetch_new_arrivals   # titles [event_transform/message_only]
a016 -> publish_arrivals   # Publish arrivals [http_request]
```
**Goes wrong**
- One step per action: a step for the request, a `branchone` for `200`, a step for `titles`. Write one script.
- The whole response body is returned. Return the fields that later steps read.
- A GET `payload` is sent as a body. In Tines a `payload` on `method: get` is the query string.
- An internal host from the export (`catalog.lib.internal`) is copied into the script or the notes. Rule: the base URL of one of the user's own systems, and any other value that differs per environment, lives in a non-secret variable (or in a resource, recipe 23) and is listed under Setup. The path after the host stays in the code.
- A public vendor API host (`signage.example.net`) is moved to a variable too. It may stay in the code.
- How to tell: internal is a private IP address, a name with no public domain (`.internal`, `.local`, `.lan`, `.corp`) or a host under the user's own domain. If you are not sure, treat it as internal.

**Notes file**
- Setup: the secret variables `f/library/catalog_key` and `f/library/signage_key`. The variable `f/library/catalog_base_url`, not secret: "base URL of the catalogue server, with `https://` and no slash at the end". Describe the system. Do not write its host name in the notes. The schedule file.
- Behaviour differences: a status other than 200 stopped the story silently. The flow fails with the status in the error.

## 7. HTTP call whose non-2xx status is data, not a failure

**Outline shows**
```text
    a018 find_member [http_request]  recipe 6,25
      a019 member_found [trigger]  recipe 6,7,14
        a020 log_visit [http_request]  END  recipe 6,25
        (no-match) a021 _404 [trigger]  recipe 7,14
          a022 create_guest_pass [http_request]  END  recipe 6,25
  rules: [{"type": "field==value", "value": "200", "path": "<<find_member.status>>"}]
  rules: [{"type": "field==value", "value": "404", "path": "<<find_member.status>>"}]
```
**Write** a script that tests each status the story tests. Throw only for a status the story does not handle.
```yaml
# flow.yaml
summary: Log a visit or create a guest pass
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [card_no]
  properties:
    card_no: {type: string}
    branch: {type: string, default: ""}
value:
  modules:
    - id: handle_card_scan
      value:
        type: rawscript
        language: bun
        content: "!inline handle_card_scan.ts"
        input_transforms:
          card_no: {type: javascript, expr: "flow_input.card_no"}
          branch: {type: javascript, expr: "flow_input.branch"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// handle_card_scan.ts
type Result = { found: boolean; member_id: string | null; action: "visit_logged" | "guest_pass_created" };

// a018 Find member, a019 member found, a020 Log visit, a021 404, a022 Create guest pass
export async function main(card_no: string, branch: string, api_token: string): Promise<Result> {
  const base = "https://loans.example.org/v1";
  const headers = { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" };
  const post = async (path: string, payload: object) => {
    const res = await fetch(`${base}${path}`, { method: "POST", headers, body: JSON.stringify(payload) });
    if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  };
  const found = await fetch(`${base}/members/by-card/${encodeURIComponent(card_no)}`, { headers });
  if (found.status === 200) {                                   // a019 member found
    const member: { id: string } = await found.json();
    await post("/visits", { member_id: member.id, branch });    // a020
    return { found: true, member_id: member.id, action: "visit_logged" };
  }
  if (found.status === 404) {                                   // a021: 404 is an answer, not an error
    await post("/guest-passes", { card_no, branch });           // a022
    return { found: false, member_id: null, action: "guest_pass_created" };
  }
  throw new Error(`member lookup returned ${found.status}`);    // the story stopped silently here
}
```
```text
# workflow: w07
a017 -> flow_input.card_no, flow_input.branch   # card scanned [webhook]
a018 -> handle_card_scan   # Find member [http_request]
a019 -> handle_card_scan   # member found [trigger]
a020 -> handle_card_scan   # Log visit [http_request]
a021 -> handle_card_scan   # 404 [trigger]
a022 -> handle_card_scan   # Create guest pass [http_request]
```
**Goes wrong**
- `if (!res.ok) throw` is written right after the first request. The 404 path then never runs.
- `await res.json()` is called on the 404 response. An error response is often not JSON. Read the body only where the story reads it.
- A later step must branch on the status. Then return it (`return { status: found.status, ... }`) and test `results.<step>.status` in a `branchone` (recipe 14).

**Notes file**
- Behaviour differences: a status other than 200 and 404 ended the story silently. The flow fails with the status in the error.
- Mapping: all six actions are one step.

## 8. Retry settings on an HTTP request

**Outline shows**
```text
a024 renew_loan  "Renew loan"  [http_request]  recipe 6,8,25
  url: https://loans.example.org/v1/loans/<<renewal_request.body.loan_id>>/renew
  timeout: "20"
  retries: "4"
  retry_on_status: ["429", "500-599"]
```
**Write** a bounded loop in the script. Retry only the statuses in `retry_on_status`.
```yaml
# flow.yaml
summary: Renew a loan
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [loan_id]
  properties:
    loan_id: {type: string}
value:
  modules:
    - id: renew_loan
      value:
        type: rawscript
        language: bun
        content: "!inline renew_loan.ts"
        input_transforms:
          loan_id: {type: javascript, expr: "flow_input.loan_id"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// renew_loan.ts
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const MAX_RETRIES = 4;                                                        // retries: "4"
const retryable = (s: number) => s === 429 || (s >= 500 && s <= 599);         // retry_on_status

// a024 Renew loan
export async function main(loan_id: string, api_token: string) {
  let status = 0;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) await sleep(Math.min(5 * 2 ** (attempt - 1), 600) * 1000);   // Tines waits 5, 10, 20, 40 ... s
    const res = await fetch(`https://loans.example.org/v1/loans/${encodeURIComponent(loan_id)}/renew`, {
      method: "POST",
      headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ weeks: 3 }),
      signal: AbortSignal.timeout(20_000),                                    // timeout: "20"
    });
    status = res.status;
    if (retryable(status)) continue;
    if (!res.ok) throw new Error(`renew returned ${status}`);
    return { status, attempts: attempt + 1 };
  }
  throw new Error(`renew still returned ${status} after ${MAX_RETRIES} retries`);
}
```
```text
# workflow: w08
a023 -> flow_input.loan_id   # renewal request [webhook]
a024 -> renew_loan   # Renew loan [http_request]
```
**Goes wrong**
- A loop with no maximum (`while (true)`). Always count the attempts.
- `retries` without `retry_on_status`. Tines then never retries. Write no retry loop.
- `retry_on_status` without `retries`. Tines then retries 25 times, for hours. Write `MAX_RETRIES = 5` and say so in the notes.
- `"0"` in `retry_on_status` means "no response". Then wrap the `fetch` in `try/catch`, set `status = 0` in the `catch`, and add `s === 0` to `retryable`.

**Notes file**
- Behaviour differences: the number of retries and the waits, when they differ from the story. After the last retry the flow fails; Tines emitted the last response and went on.

## 9. Poll loop: trigger, delay, link back

**Outline shows**
```text
  a025 start_catalogue_export [http_request]  ENTRY: schedule cron 0 2 * * 0 (Europe/Dublin)  recipe 1,6,25
    a026 wait_for_export [event_transform/delay]  JOIN x2  CYCLE  recipe 9
      a027 get_export_status [http_request]  CYCLE  recipe 6,9,25
        a028 still_running [trigger]  CYCLE  recipe 9,14
          ^ a026 wait_for_export  (CYCLE: loops back)
          (no-match) a029 share_export [http_request]  END  recipe 6,14,25
  seconds: "20"
  rules: [{"type": "field==value", "value": "running", "path": "<<get_export_status.body.state>>"}]
```
**Write** a counted loop in one script. Find the exit condition (here: the trigger does not match). Add a maximum.
```yaml
# flow.yaml
summary: Export the catalogue and share the link
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties: {}
value:
  modules:
    - id: export_catalogue
      value:
        type: rawscript
        language: bun
        content: "!inline export_catalogue.ts"
        input_transforms:
          api_key: {type: static, value: "$var:f/library/catalog_key"}
    - id: share_export
      value:
        type: rawscript
        language: bun
        content: "!inline share_export.ts"
        input_transforms:
          download_url: {type: javascript, expr: "results.export_catalogue.download_url"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
```
```yaml
# f/library/export_catalogue.schedule.yaml
schedule: "0 0 2 * * 0"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/export_catalogue
is_flow: true
args: {}
```
```ts
// export_catalogue.ts
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const MAX_POLLS = 30;   // the story has no limit. 30 polls x 20 s = 10 minutes.

// a025 Start catalogue export, a026 wait for export, a027 Get export status, a028 still running
export async function main(api_key: string) {
  const headers = { "X-Api-Key": api_key, "Content-Type": "application/json" };
  const start = await fetch("https://catalog.example.org/api/v2/exports", {
    method: "POST", headers, body: JSON.stringify({ format: "csv" }),
  });
  if (!start.ok) throw new Error(`export start returned ${start.status}`);
  const id: string = (await start.json()).id;
  for (let poll = 1; poll <= MAX_POLLS; poll++) {
    await sleep(20_000);                                              // a026: the wait comes before each check
    const res = await fetch(`https://catalog.example.org/api/v2/exports/${encodeURIComponent(id)}`, { headers });
    const body: any = res.ok ? await res.json() : null;
    if (body?.state !== "running")                                    // a028 no-match: leave the loop
      return { state: body?.state ?? null, download_url: body?.download_url ?? null, polls: poll };
  }
  throw new Error(`export ${id} still running after ${MAX_POLLS} polls`);
}
```
```ts
// share_export.ts
// a029 Share export
export async function main(download_url: string | null, api_token: string) {
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: "collections-team", text: `Catalogue export: ${download_url ?? ""}` }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w09
a025 -> export_catalogue   # Start catalogue export [http_request]
a026 -> export_catalogue   # wait for export [event_transform/delay]
a027 -> export_catalogue   # Get export status [http_request]
a028 -> export_catalogue   # still running [trigger]
a029 -> share_export   # Share export [http_request]
```
**Goes wrong**
- The loop has no maximum, because the story has none. Always add one and throw when it is reached.
- The loop guard is misread. A rule such as `IS_BLANK(<trigger>.rule_matched)` lets the loop run once only: write an `if`, not a loop.
- The wait is put after the check. Keep the story's order: here delay, then request.

**Notes file**
- Behaviour differences: the poll loop stops after 30 polls (10 minutes) and the flow fails; the story polled without limit.
- Not verified: what the service answers when the export fails. The story shares the link for any state that is not `running`, and so does the flow.

## 10. HTTP request with TLS verification disabled

**Outline shows**
```text
  a030 get_kiosk_status [http_request]  ENTRY: schedule cron */10 * * * * (Europe/Dublin)  recipe 1,6,10
    a031 not_ok [trigger]
      a032 report_kiosk [http_request]  END  recipe 6,25
  url: https://kiosk.harbour.example.net:8443/status
  disable_ssl_verification: true
  rules: [{"type": "field!=value", "value": "ok", "path": "<<get_kiosk_status.body.state>>"}]
```
**Write** the request with certificate checks **on**, and a `skip_tls_verify` argument that is `false` in `flow.yaml`. Only when the user sets it to `true` does that one `fetch` get `tls: { rejectUnauthorized: false }`. The story switched the check off; the port does not copy that silently, because the request usually carries a token.
```yaml
# flow.yaml
summary: Report a kiosk that is not ok
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties: {}
value:
  modules:
    - id: check_kiosk
      value:
        type: rawscript
        language: bun
        content: "!inline check_kiosk.ts"
        input_transforms:
          facilities_token: {type: static, value: "$var:f/library/facilities_token"}
          skip_tls_verify: {type: static, value: false}   # the story had disable_ssl_verification: true
```
```yaml
# f/library/check_kiosk.schedule.yaml
schedule: "0 */10 * * * *"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/check_kiosk
is_flow: true
args: {}
```
```ts
// check_kiosk.ts
// a030 Get kiosk status, a031 not ok, a032 Report kiosk
export async function main(facilities_token: string, skip_tls_verify: boolean = false) {
  const res = await fetch("https://kiosk.harbour.example.net:8443/status", {
    signal: AbortSignal.timeout(10_000),          // timeout: "10"
    // disable_ssl_verification: true in the story. Off here unless skip_tls_verify is set. Bun only. This host only.
    ...(skip_tls_verify ? { tls: { rejectUnauthorized: false } } : {}),
  });
  const state: string | null = res.ok ? ((await res.json())?.state ?? null) : null;
  if (state === "ok") return { state, reported: false };          // a031 does not match: nothing to do
  const report = await fetch("https://facilities.example.org/api/tickets", {   // normal TLS here
    method: "POST",
    headers: { "X-Token": facilities_token, "Content-Type": "application/json" },
    body: JSON.stringify({ kiosk: "harbour", state }),
  });
  if (!report.ok) throw new Error(`ticket returned ${report.status}`);
  return { state, reported: true };
}
```
```text
# workflow: w10
a030 -> check_kiosk   # Get kiosk status [http_request]
a031 -> check_kiosk   # not ok [trigger]
a032 -> check_kiosk   # Report kiosk [http_request]
```
**Goes wrong**
- `tls: { rejectUnauthorized: false }` is written unconditionally, or stored as `insecure: true` in a resource the flow creates. Checks stay on unless the user switches them off.
- TLS checks are switched off for the whole script (`NODE_TLS_REJECT_UNAUTHORIZED=0`) or for every request. The switch covers the one request that has the option.
- `language: deno` or a Node `https.Agent`. The `tls` option of `fetch` works in `language: bun` only.
- The option comes from a resource (`disable_ssl_verification: =RESOURCE.x.disable_ssl_verification`). Then read the flag from that resource: `...(api.disable_ssl_verification ? { tls: { rejectUnauthorized: false } } : {})`.

**Notes file**
- Setup: the secret variable `f/library/facilities_token`. The schedule file. `skip_tls_verify` is `false`: if the kiosk request fails on its certificate, add the kiosk's certificate authority to the Windmill workers; setting `skip_tls_verify` to `true` is the last resort.
- Behaviour differences: deliberate. The story had TLS verification off for `kiosk.harbour.example.net`; the flow keeps it on unless `skip_tls_verify` is set. A failed status request is reported as state `null`, as in the story.
- Not verified: the `tls` option of Bun's `fetch` was not run.

## 11. Message-only transform

**Outline shows**
```text
    a034 clean_isbn [event_transform/message_only]  recipe 11
      a035 shelf_label [event_transform/message_only]  FAN-OUT x2  recipe 11,15
        a036 print_shelf_label [http_request]  END  recipe 6,25
        a037 add_to_display_list [http_request]  END  recipe 6,25
  payload: =REPLACE(new_copy.body.isbn, "-", "") |> UPCASE(%)
  payload: {"isbn": "=clean_isbn", "line": "<<new_copy.body.title>> (<<new_copy.body.year>>)", "shelf": "=DEFAULT(new_copy.body.shelf, \"unsorted\")"}
```
**Write** a transform that one action reads as a line of code in that step (`clean_isbn`). Give a transform its own step only when several later steps read it (`shelf_label`).
```yaml
# flow.yaml
summary: Label a new copy
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [isbn, title]
  properties:
    isbn: {type: string}
    title: {type: string}
    year: {type: string, default: ""}
    shelf: {type: string, default: ""}
value:
  modules:
    - id: shelf_label
      value:
        type: rawscript
        language: bun
        content: "!inline shelf_label.ts"
        input_transforms:
          isbn: {type: javascript, expr: "flow_input.isbn"}
          title: {type: javascript, expr: "flow_input.title"}
          year: {type: javascript, expr: "flow_input.year"}
          shelf: {type: javascript, expr: "flow_input.shelf"}
    - id: print_shelf_label
      value:
        type: rawscript
        language: bun
        content: "!inline print_shelf_label.ts"
        input_transforms:
          label: {type: javascript, expr: "results.shelf_label"}
          printer_key: {type: static, value: "$var:f/library/printer_key"}
    - id: add_to_display_list
      value:
        type: rawscript
        language: bun
        content: "!inline add_to_display_list.ts"
        input_transforms:
          label: {type: javascript, expr: "results.shelf_label"}
          board_key: {type: static, value: "$var:f/library/signage_key"}
```
```ts
// shelf_label.ts
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));

// a034 clean isbn, a035 shelf label. No network call: a transform step only computes.
export async function main(isbn: string, title: string, year: string, shelf: string) {
  const clean_isbn = text(isbn).split("-").join("").toUpperCase();   // =REPLACE(isbn, "-", "") |> UPCASE(%)
  return {
    isbn: clean_isbn,
    line: `${text(title)} (${text(year)})`,
    shelf: isBlank(shelf) ? "unsorted" : shelf,                      // =DEFAULT(shelf, "unsorted")
  };
}
```
```ts
// print_shelf_label.ts
// a036 Print shelf label
export async function main(label: { isbn: string; line: string; shelf: string }, printer_key: string) {
  const res = await fetch("https://printer.example.net/jobs", {
    method: "POST",
    headers: { "X-Printer-Key": printer_key, "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error(`printer returned ${res.status}`);
  return { status: res.status };
}
```
```ts
// add_to_display_list.ts
// a037 Add to display list
export async function main(label: { isbn: string; line: string; shelf: string }, board_key: string) {
  const res = await fetch("https://signage.example.net/api/lists/new-copies", {
    method: "POST",
    headers: { "X-Board-Key": board_key, "Content-Type": "application/json" },
    body: JSON.stringify({ entry: label }),
  });
  if (!res.ok) throw new Error(`display list returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w11
a033 -> flow_input.isbn, flow_input.title, flow_input.year, flow_input.shelf   # new copy [webhook]
a034 -> shelf_label   # clean isbn [event_transform/message_only]
a035 -> shelf_label   # shelf label [event_transform/message_only]
a036 -> print_shelf_label   # Print shelf label [http_request]
a037 -> add_to_display_list   # Add to display list [http_request]
```
**Goes wrong**
- One step per transform. A transform read by one action belongs in that action's script.
- `DEFAULT(v, x)` written as `v ?? x`. In Tines `""`, `[]` and `{}` also fall back. Use `isBlank`.
- `IF(x, a, b)` written as `x ? a : b`. In Tines `0` and `""` are truthy. Use `truthy(x)`.
- A long formula in an `expr`. An `expr` is one expression with no helpers. Put formulas in a script.

**Notes file**
- Mapping: name the step that holds each folded transform.
- Behaviour differences: the two requests ran side by side in Tines; here the second runs after the first, and a failed print stops the flow before the display list.

## 12. Text built with `<%for%>` and `<%if%>` tags

**Outline shows**
```text
a039 notice_text  "notice text"  [event_transform/message_only]  recipe 11,12
  payload: |-
    Hello <<due_list.body.member.first_name>>,
    <%if SIZE(due_list.body.loans) = 0%>You have nothing due.
    <%else%>Due soon:
    <%for loan in due_list.body.loans%>- <<loan.title>><%if loan.days_left < 0%> (OVERDUE)<%elseif loan.days_left = 0%> (today)<%endif%>
    <%endfor%><%endif%>Thank you.
```
**Write** a function that builds the string with `let out`, ordinary `if` and `for`. Walk the text left to right.
```yaml
# flow.yaml
summary: Send a due-date notice
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member]
  properties:
    member: {type: object, properties: {id: {type: string}, first_name: {type: string}}}
    loans: {type: array, items: {type: object}, default: []}
value:
  modules:
    - id: send_notice
      value:
        type: rawscript
        language: bun
        content: "!inline send_notice.ts"
        input_transforms:
          member: {type: javascript, expr: "flow_input.member"}
          loans: {type: javascript, expr: "flow_input.loans"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
```
```ts
// send_notice.ts
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
type Loan = { title?: string; days_left?: number | null };

// a039 notice text
function noticeText(first_name: string, loans: Loan[]): string {
  let out = `Hello ${text(first_name)},\n`;
  if (loans.length === 0) {                              // <%if SIZE(due_list.body.loans) = 0%>
    out += "You have nothing due.\n";
  } else {                                               // <%else%>
    out += "Due soon:\n";
    for (const loan of loans) {                          // <%for loan in due_list.body.loans%>
      out += `- ${text(loan?.title)}`;
      const days = loan?.days_left == null ? NaN : Number(loan.days_left);
      if (days < 0) out += " (OVERDUE)";                 // <%if loan.days_left < 0%>
      else if (days === 0) out += " (today)";            // <%elseif loan.days_left = 0%>
      out += "\n";                                       // the newline before <%endfor%> is inside the loop
    }
  }
  return out + "Thank you.";                             // `|-`: no newline at the end
}

// a040 Send notice
export async function main(member: { id: string; first_name: string }, loans: Loan[], api_token: string) {
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member.id, text: noticeText(member.first_name, loans ?? []) }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w12
a038 -> flow_input.member, flow_input.loans   # due list [webhook]
a039 -> send_notice   # notice text [event_transform/message_only]
a040 -> send_notice   # Send notice [http_request]
```
**Goes wrong**
- The tags are left in a string, or turned into one long `expr`. Tags need statements: write a function in a script.
- Line breaks are tidied. Copy every literal character, also the newline that touches a tag.
- The block marker is ignored. `|-` means the text has no newline at the end. `|` means it has one.
- A condition uses JavaScript truthiness. `<%if x%>` is true for `0` and `""`. Use `truthy(x)` for a bare value.
- A pill holds an array or an object (`<<rows>>` in a CSV or JSON body). Tines does not specify how that renders. This skill's convention is JSON: `text(rows)`. If the receiver needs another format (CSV lines), build that format in code and say so in the notes.
- The text is HTML (an email body, a table with `<tr>` tags). Then every inserted **data value** goes through `esc()`, not `text()`. Text that the story itself wrote is never escaped: a separator such as `JOIN(list, " &nbsp;&middot;&nbsp; ")`, a heading, a style attribute. Escape each item, then join with the literal separator. Copy every literal piece of the template: when you move repeated markup into a helper, check that no heading or style text was lost. For a Markdown chat message use `text()`; in a table cell also replace the pipe character and line breaks.

**Notes file**
- Mapping: the text action is a function inside the step that sends the text.
- Not verified, when a request body or a message depends on it: "`<<name>>` holds an array (or object). Tines does not document how a pill renders it. The flow sends JSON."
- Not verified: whether Tines trims white space next to a tag. The function keeps every character of the template.

## 13. Explode, work per item, implode

**Outline shows**
```text
    a042 explode_items [event_transform/explode]  recipe 13
      a043 place_hold [http_request]  recipe 6,25
        a044 build_row [event_transform/message_only]  recipe 11
          a045 collect_rows [event_transform/implode]  recipe 13
            a046 send_summary [http_request]  END  recipe 6,25
  path: =reserve_items.body.items
  to: item
  payload: {"item": "<<explode_items.item.id>>", "hold": "<<place_hold.body.hold_id>>", "ok": "=place_hold.status = 201"}
  payload: {"to": "<<reserve_items.body.member_id>>", "rows": "=collect_rows"}
```
**Write** a `forloopflow`. Put the work between explode and implode inside it. The loop result is the list.
```yaml
# flow.yaml
summary: Place holds for a list of items
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [items, member_id]
  properties:
    items: {type: array, items: {type: object}}
    member_id: {type: string}
value:
  modules:
    - id: loop_items
      value:
        type: forloopflow
        iterator: {type: javascript, expr: "flow_input.items"}
        skip_failures: true
        parallel: false
        modules:
          - id: place_hold
            value:
              type: rawscript
              language: bun
              content: "!inline place_hold.ts"
              input_transforms:
                item: {type: javascript, expr: "flow_input.iter.value"}
                member_id: {type: javascript, expr: "flow_input.member_id"}
                api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: send_summary
      value:
        type: rawscript
        language: bun
        content: "!inline send_summary.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          rows: {type: javascript, expr: "results.loop_items"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
```
```ts
// place_hold.ts
// a043 Place hold, a044 build row. The return value is this item's entry in results.loop_items.
export async function main(item: { id: string }, member_id: string, api_token: string) {
  const res = await fetch("https://loans.example.org/v1/holds", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: item.id, member_id }),
  });
  const body: any = res.status === 201 ? await res.json() : null;
  return { item: item.id, hold: body?.hold_id ?? null, ok: res.status === 201 };   // the story reads the status: no throw
}
```
```ts
// send_summary.ts
// a046 Send summary. a045 collect rows is gone: results.loop_items is the list.
export async function main(member_id: string, rows: any[], api_token: string) {
  const done = (rows ?? []).filter((r) => r && !r.error);   // a failed iteration leaves null or {error: ...}
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member_id, rows: done }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status, rows: done.length };
}
```
```text
# workflow: w13
a041 -> flow_input.items, flow_input.member_id   # reserve items [webhook]
a042 -> loop_items   # explode items [event_transform/explode]
a043 -> place_hold   # Place hold [http_request]
a044 -> place_hold   # build row [event_transform/message_only]
a045 -> DROPPED: implode plumbing; results.loop_items is the list   # collect rows [event_transform/implode]
a046 -> send_summary   # Send summary [http_request]
```
**Goes wrong**
- A step outside the loop reads `results.place_hold`. Steps inside a loop are not visible outside. Read `results.loop_items`.
- Steps for the explode, the row builder and the implode. They are plumbing. The loop replaces them.
- `flow_input.iter.value` is used outside the loop, or `<explode>.item` is kept. Inside the loop the item is `flow_input.iter.value`.
- `skip_failures: false`. In Tines one failing item never stops the others. Use `true`, and filter failed entries afterwards.

**Notes file**
- Behaviour differences: if one item failed, the Tines implode waited for it and the summary was never sent. The flow sends the summary without that item.
- Not verified: the explode `limit` (500) is not applied. Say what happens to a longer list if it matters.

## 14. Trigger with a no-match link (if / else)

**Outline shows**
```text
    a048 is_reference [trigger]  NO-MATCH FAN-OUT x2  recipe 14,15
      a049 book_reading_room_slot [http_request]  END  recipe 6,25
      (no-match) a050 place_hold_for_pickup [http_request]  END  recipe 6,14,25
      (no-match) a108 add_desk_log_entry [http_request]  END  recipe 6,14,25
  rules: [{"type": "field==value", "value": "reference", "path": "<<desk_request.body.collection>>"}]
```
**Write** a `branchone`. The rules become the branch `expr`. The `(no-match)` side becomes `default`. Here the trigger has two no-match links (`NO-MATCH FAN-OUT x2`). When the rules do not match, both fire. So `default` holds both steps.
```yaml
# flow.yaml
summary: Route a desk request
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [item_id, member_id]
  properties:
    collection: {type: string, default: ""}
    item_id: {type: string}
    member_id: {type: string}
value:
  modules:
    - id: route_request
      value:
        type: branchone
        branches:
          - summary: Reference collection
            expr: "flow_input.collection === 'reference'"
            modules:
              - id: book_reading_room_slot
                value:
                  type: rawscript
                  language: bun
                  content: "!inline book_reading_room_slot.ts"
                  input_transforms:
                    item_id: {type: javascript, expr: "flow_input.item_id"}
                    member_id: {type: javascript, expr: "flow_input.member_id"}
                    api_token: {type: static, value: "$var:f/library/rooms_token"}
        default:
          - id: place_hold_for_pickup
            value:
              type: rawscript
              language: bun
              content: "!inline place_hold_for_pickup.ts"
              input_transforms:
                item_id: {type: javascript, expr: "flow_input.item_id"}
                member_id: {type: javascript, expr: "flow_input.member_id"}
                api_token: {type: static, value: "$var:f/library/loans_token"}
          - id: add_desk_log_entry
            value:
              type: rawscript
              language: bun
              content: "!inline add_desk_log_entry.ts"
              input_transforms:
                item_id: {type: javascript, expr: "flow_input.item_id"}
                loans_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// book_reading_room_slot.ts
// a049 Book reading room slot
export async function main(item_id: string, member_id: string, api_token: string) {
  const res = await fetch("https://rooms.example.org/api/reading-room/slots", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item_id, member_id }),
  });
  if (!res.ok) throw new Error(`reading room returned ${res.status}`);
  return { route: "reading_room", status: res.status };
}
```
```ts
// place_hold_for_pickup.ts
// a050 Place hold for pickup
export async function main(item_id: string, member_id: string, api_token: string) {
  const res = await fetch("https://loans.example.org/v1/holds", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item_id, member_id }),
  });
  if (!res.ok) throw new Error(`holds returned ${res.status}`);
  return { route: "pickup", status: res.status };
}
```
```ts
// add_desk_log_entry.ts
// a108 Add desk log entry: the second no-match link of a048. It runs whenever a050 runs.
export async function main(item_id: string, loans_token: string) {
  const entry = { kind: "pickup-hold", item_id };
  const res = await fetch("https://loans.example.org/v1/desk-log", {
    method: "POST",
    headers: { Authorization: `Bearer ${loans_token}`, "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`desk log entry was not written: ${res.status}`);
  return { logged: true };
}
```
```text
# workflow: w14
a047 -> flow_input.collection, flow_input.item_id, flow_input.member_id   # desk request [webhook]
a048 -> route_request   # is reference [trigger]
a049 -> book_reading_room_slot   # Book reading room slot [http_request]
a050 -> place_hold_for_pickup   # Place hold for pickup [http_request]
a108 -> add_desk_log_entry   # Add desk log entry [http_request]
```
**Goes wrong**
- `default` is left out. It is required. A trigger with no `(no-match)` link gets `default: []`.
- Several `(no-match)` links are read as "one of them". All of them fire. Put all of them in `default`, one after another. Use a `branchall` inside `default` only if a later step needs all their results (recipe 15).
- Several match links from one trigger (`FAN-OUT xN` on the trigger) all fire too. Put all of them in the branch.
- A step after the branch reads `results.book_reading_room_slot`. Read `results.route_request`, and give both sides the same result keys.
- Several rules: without `must_match` all rules must hold (`&&`). `must_match: "1"` means any rule (`||`).
- A rule of type `formula` has its formula in `path`. Ignore its `value`.

**Notes file**
- Mapping: the trigger is the `branchone`; say which side is `default`.
- Behaviour differences: the two no-match actions ran side by side in Tines. Here `add_desk_log_entry` runs after `place_hold_for_pickup`, and not at all if that step fails.
- Not verified: Tines compares rule values loosely (`"200"` equals `200`). If the types can differ, compare text: `String(x) === 'reference'`.

## 15. One action linking to several actions (fan-out)

**Outline shows**
```text
  a051 title_lookup [webhook]  ENTRY: webhook  FAN-OUT x2  recipe 2,15
    a052 check_shelf [http_request]  recipe 6,25
      a054 tag_for_join [event_transform/message_only]  recipe 11
        a056 join_sources [event_transform/implode]  JOIN x2  recipe 13
          a057 send_answer [http_request]  END  recipe 6,25
    a053 check_ebook [http_request]  recipe 6,25
      a055 tag_for_join [event_transform/message_only]  recipe 11
        ^ a056 join_sources  (JOIN: shown above)
    shelf_copies: =WHERE(join_sources, "part", "shelf") |> FIRST(%).data
```
**Write** a `branchall` when a later step needs all the results. If no later step reads them, write the steps one after another instead.
```yaml
# flow.yaml
summary: Answer a title lookup
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [isbn, member_id]
  properties:
    isbn: {type: string}
    member_id: {type: string}
value:
  modules:
    - id: lookups
      value:
        type: branchall
        parallel: true
        branches:
          - summary: Shelf copies
            skip_failure: true
            modules:
              - id: check_shelf
                value:
                  type: rawscript
                  language: bun
                  content: "!inline check_shelf.ts"
                  input_transforms:
                    isbn: {type: javascript, expr: "flow_input.isbn"}
                    api_key: {type: static, value: "$var:f/library/catalog_key"}
          - summary: Ebook licences
            skip_failure: true
            modules:
              - id: check_ebook
                value:
                  type: rawscript
                  language: bun
                  content: "!inline check_ebook.ts"
                  input_transforms:
                    isbn: {type: javascript, expr: "flow_input.isbn"}
                    api_key: {type: static, value: "$var:f/library/ebooks_key"}
    - id: send_answer
      value:
        type: rawscript
        language: bun
        content: "!inline send_answer.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          lookups: {type: javascript, expr: "results.lookups"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
```
```ts
// check_shelf.ts
// a052 Check shelf, a054 tag for join. "source" replaces the tag.
export async function main(isbn: string, api_key: string) {
  const res = await fetch(`https://catalog.example.org/api/v2/copies?isbn=${encodeURIComponent(isbn)}`, {
    headers: { "X-Api-Key": api_key },
  });
  const body: any = res.ok ? await res.json() : null;
  return { source: "shelf", data: body?.available ?? null };
}
```
```ts
// check_ebook.ts
// a053 Check ebook, a055 tag for join
export async function main(isbn: string, api_key: string) {
  const res = await fetch(`https://ebooks.example.com/api/titles/${encodeURIComponent(isbn)}`, {
    headers: { "X-Api-Key": api_key },
  });
  const body: any = res.ok ? await res.json() : null;
  return { source: "ebook", data: body?.licences_free ?? null };
}
```
```ts
// send_answer.ts
// a057 Send answer. a056 join sources is gone: results.lookups holds one entry per branch.
export async function main(member_id: string, lookups: any[], api_token: string) {
  const by = (source: string) => (lookups ?? []).find((r) => r?.source === source)?.data ?? null;
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member_id, shelf_copies: by("shelf"), ebook_licences: by("ebook") }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w15
a051 -> flow_input.isbn, flow_input.member_id   # title lookup [webhook]
a052 -> check_shelf   # Check shelf [http_request]
a053 -> check_ebook   # Check ebook [http_request]
a054 -> check_shelf   # tag for join [event_transform/message_only]
a055 -> check_ebook   # tag for join [event_transform/message_only]
a056 -> DROPPED: join plumbing; send_answer reads results.lookups   # join sources [event_transform/implode]
a057 -> send_answer   # Send answer [http_request]
```
**Goes wrong**
- Results are read by position (`results.lookups[0]`). A failed branch leaves `null` or an error object. Find entries by `source`.
- `skip_failures` (loop key) is written on a branch. The branch key is `skip_failure`, without `s`.
- A step after the `branchall` reads `results.check_shelf`. It must read `results.lookups`.
- Two actions have the same name (`tag_for_join`). Trust the ids on the `uses:` line, not the name.

**Notes file**
- Behaviour differences: the implode waited at most 30 seconds, then went on with what it had. The `branchall` waits until both branches end. A failed branch gives `null` in the answer.

## 16. Several links leading into the same action (join)

**Outline shows**
```text
    a059 is_damaged [trigger]  recipe 14
      a060 open_repair_ticket [http_request]  recipe 6,25
        a061 mark_returned [http_request]  JOIN x2  END  recipe 6,14,16,25
      (no-match) ^ a061 mark_returned  (JOIN: shown above)
  links: in a060,a059(no-match) | out -
```
**Write** the shared work once, after the branch. Only the part that differs goes inside the `branchone`.
```yaml
# flow.yaml
summary: Take back a returned item
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [item_id]
  properties:
    item_id: {type: string}
    condition: {type: string, default: ""}
value:
  modules:
    - id: repair_if_damaged
      value:
        type: branchone
        branches:
          - summary: Item is damaged
            expr: "flow_input.condition === 'damaged'"
            modules:
              - id: open_repair_ticket
                value:
                  type: rawscript
                  language: bun
                  content: "!inline open_repair_ticket.ts"
                  input_transforms:
                    item_id: {type: javascript, expr: "flow_input.item_id"}
                    facilities_token: {type: static, value: "$var:f/library/facilities_token"}
        default: []
    - id: mark_returned
      value:
        type: rawscript
        language: bun
        content: "!inline mark_returned.ts"
        input_transforms:
          item_id: {type: javascript, expr: "flow_input.item_id"}
          condition: {type: javascript, expr: "flow_input.condition"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// open_repair_ticket.ts
// a060 Open repair ticket
export async function main(item_id: string, facilities_token: string) {
  const res = await fetch("https://facilities.example.org/api/tickets", {
    method: "POST",
    headers: { "X-Token": facilities_token, "Content-Type": "application/json" },
    body: JSON.stringify({ kind: "book-repair", item_id }),
  });
  if (!res.ok) throw new Error(`ticket returned ${res.status}`);
  return { status: res.status };
}
```
```ts
// mark_returned.ts
// a061 Mark returned: reached from a060 and from the no-match side of a059. Written once.
export async function main(item_id: string, condition: string, api_token: string) {
  const res = await fetch("https://loans.example.org/v1/returns", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item_id, condition }),
  });
  if (!res.ok) throw new Error(`returns returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w16
a058 -> flow_input.item_id, flow_input.condition   # return scanned [webhook]
a059 -> repair_if_damaged   # is damaged [trigger]
a060 -> open_repair_ticket   # Open repair ticket [http_request]
a061 -> mark_returned   # Mark returned [http_request]
```
**Goes wrong**
- One copy of the shared step per incoming link (`mark_returned` in the branch and again in `default`). Never do that.
- One `.ts` file used by two steps. Each step id has its own file, and each piece of work has one step.
- The shared step needs a value from the branch. Then end every side, `default` too, with a step that returns the same keys, and read `results.repair_if_damaged`. Do not rely on the result of an empty `default`.
- Three or more links join. It is the same pattern: one script decides and returns what differs, the shared step follows.

**Notes file**
- Mapping: say that the joined action is one step after the branch.
- Behaviour differences: none if every incoming link is one side of the branch. If two links can fire for the same event, Tines ran the shared action twice; the flow runs it once. Say so.

## 17. Group action

**Outline shows**
```text
    a063 extend_at_desk [group]  recipe 17
      { inside group a063:
        a063.01 input [group_input]
          a063.02 get_loan [http_request]  recipe 6,25
            a063.03 renewable [trigger]
              a063.04 extend_loan [http_request]  recipe 6,25
                a063.05 output [group_output]  END
      }
      a064 tell_member [http_request]  END  recipe 6,25
  payload: {"loan_id": "<<renew_at_desk.body.loan_id>>"}
    payload: {"due": "<<extend_loan.body.due_date>>"}
```
**Write** the inside of the group as one script. The group payload is its parameters. The output payload is its return value.
```yaml
# flow.yaml
summary: Extend a loan at the desk
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [loan_id, member_id]
  properties:
    loan_id: {type: string}
    member_id: {type: string}
value:
  modules:
    - id: extend_at_desk
      value:
        type: rawscript
        language: bun
        content: "!inline extend_at_desk.ts"
        input_transforms:
          loan_id: {type: javascript, expr: "flow_input.loan_id"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: tell_if_extended
      value:
        type: branchone
        branches:
          - summary: The group reached its output
            expr: "results.extend_at_desk.extended === true"
            modules:
              - id: tell_member
                value:
                  type: rawscript
                  language: bun
                  content: "!inline tell_member.ts"
                  input_transforms:
                    member_id: {type: javascript, expr: "flow_input.member_id"}
                    due: {type: javascript, expr: "results.extend_at_desk.due"}
                    api_token: {type: static, value: "$var:f/library/notify_token"}
        default: []
```
```ts
// extend_at_desk.ts
// a063 Extend at desk: a063.02 Get loan, a063.03 renewable, a063.04 Extend loan
export async function main(loan_id: string, api_token: string) {
  const url = `https://loans.example.org/v1/loans/${encodeURIComponent(loan_id)}`;   // input.payload.loan_id
  const headers = { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" };
  const loan = await fetch(url, { headers });
  if (!loan.ok) throw new Error(`loan returned ${loan.status}`);
  if (!(Number((await loan.json())?.renewals_left) > 0)) return { extended: false, due: null };   // a063.03: output not reached
  const ext = await fetch(`${url}/extend`, { method: "POST", headers, body: JSON.stringify({ weeks: 2 }) });
  if (!ext.ok) throw new Error(`extend returned ${ext.status}`);
  return { extended: true, due: (await ext.json())?.due_date ?? null };               // a063.05 Output payload
}
```
```ts
// tell_member.ts
// a064 Tell member
export async function main(member_id: string, due: string | null, api_token: string) {
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member_id, text: `Renewed until ${due ?? ""}` }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w17
a062 -> flow_input.loan_id, flow_input.member_id   # renew at desk [webhook]
a063 -> extend_at_desk   # Extend at desk [group]
a063.01 -> DROPPED: group plumbing   # Input [group_input]
a063.02 -> extend_at_desk   # Get loan [http_request]
a063.03 -> extend_at_desk   # renewable [trigger]
a063.04 -> extend_at_desk   # Extend loan [http_request]
a063.05 -> DROPPED: group plumbing   # Output [group_output]
a064 -> tell_member   # Tell member [http_request]
```
**Goes wrong**
- The group is skipped because its options are empty. Print its inside with `--group a063` and port it.
- The actions after the group run although the group never reached its output. If a trigger inside can stop the group, return a flag and branch on it.
- A big group is forced into one script. A group with its own loops or branches becomes several steps of this flow, in place.
- A separate flow is made for a group used once. Make a separate flow, called with `type: flow`, only when several workflows use the same group.

**Notes file**
- Mapping: the group and its inner actions, by step.
- Behaviour differences: a failed `Get loan` now fails the flow; in the story the group ended silently.

## 18. Send to story (sub-story in the export, ported or not yet ported)

**Outline shows**
```text
a066 send_pickup_message  "Send pickup message"  [send_to_story]  recipe 18
  calls: STORY.send_member_message - body embedded in this export as s1 (print it with --story s1)
    s1 reads these keys of the payload: channel, member_id, subject, text
    sent here but never read by s1: none
    read by s1 but not sent here (NULL there): none
  payload:
    member_id: <<hold_ready.body.member_id>>
    subject: Your hold is ready
    text: <<hold_ready.body.title>> is waiting at <<hold_ready.body.branch>>.
    channel: sms
  payload: {"delivery": "<<send_pickup_message.delivery_id>>"}
```
**Write** a `type: flow` step. `path` is the sub-story's path from `PLAN.md`, also when it is not ported yet. The inputs are the payload keys, unchanged.
```yaml
# flow.yaml
summary: Tell a member that a hold is ready
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [hold_id, member_id]
  properties:
    hold_id: {type: string}
    member_id: {type: string}
    title: {type: string, default: ""}
    branch: {type: string, default: ""}
value:
  modules:
    - id: send_pickup_message
      value:
        type: flow
        path: f/library/send_member_message
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          subject: {type: static, value: Your hold is ready}
          text: {type: javascript, expr: "`${flow_input.title} is waiting at ${flow_input.branch}.`"}
          channel: {type: static, value: sms}
    - id: log_delivery
      value:
        type: rawscript
        language: bun
        content: "!inline log_delivery.ts"
        input_transforms:
          hold_id: {type: javascript, expr: "flow_input.hold_id"}
          delivery_id: {type: javascript, expr: "results.send_pickup_message?.delivery_id ?? null"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// log_delivery.ts
// a067 Log delivery
export async function main(hold_id: string, delivery_id: string | null, api_token: string) {
  const res = await fetch(`https://loans.example.org/v1/holds/${encodeURIComponent(hold_id)}/notices`, {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ delivery: delivery_id }),
  });
  if (!res.ok) throw new Error(`notices returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w18
a065 -> flow_input.hold_id, flow_input.member_id, flow_input.title, flow_input.branch   # hold ready [webhook]
a066 -> send_pickup_message   # Send pickup message [send_to_story]
a067 -> log_delivery   # Log delivery [http_request]
```
The line in `PLAN.md` for the sub-story is: `s1 | send_member_message | f/library/send_member_message | called by 1 workflow | TODO`

**Goes wrong**
- A `MISSING` stub is written because the sub-story is not ported yet. A sub-story that is in the export is a dependency, not missing logic. Use its planned path.
- The payload keys are renamed. The sub-story reads `<entry>.body.<key>`, so its flow inputs will have exactly these names. The line `s1 reads these keys of the payload` lists them.
- A key under `read by s1 but not sent here` is `NULL` in the sub-story. Do not invent a value for it. A key under `sent here but never read` is still passed.
- The sub-story is copied into every caller. It is one shared flow.
- The outline says `body NOT in this export`. That is missing logic: use recipe 27.
- The validator prints `WARN [path-missing]` for this step. That is expected until the sub-story is ported. Do not remove the step.

**Notes file**
- Setup: dependency `f/library/send_member_message` (Tines sub-story `send_member_message`, s1), not ported yet. Its inputs must be `member_id`, `subject`, `text`, `channel`. Its result must have `delivery_id`, the key of its exit action.
- Not verified: the caller cannot run until that flow exists.

## 19. Delay

**Outline shows**
```text
    a069 send_welcome [http_request]  recipe 6,25
      a070 wait_a_day [event_transform/delay]  recipe 19
        a071 create_follow_up_task [http_request]  END  recipe 6,25
  seconds: "86400"
```
**Write** `sleep` on the step before the delay. `sleep` waits after its step and holds no worker.
```yaml
# flow.yaml
summary: Welcome a new member, then create a follow-up task
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member_id]
  properties:
    member_id: {type: string}
value:
  modules:
    - id: send_welcome
      sleep: {type: static, value: 86400}
      value:
        type: rawscript
        language: bun
        content: "!inline send_welcome.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
    - id: create_follow_up_task
      value:
        type: rawscript
        language: bun
        content: "!inline create_follow_up_task.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          loans_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// send_welcome.ts
// a069 Send welcome
export async function main(member_id: string, api_token: string) {
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member_id, template: "welcome" }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```ts
// create_follow_up_task.ts
// a071 Create follow-up task: runs one day after send_welcome
export async function main(member_id: string, loans_token: string) {
  const task = { kind: "first-visit-call", member_id };
  const res = await fetch("https://loans.example.org/v1/tasks", {
    method: "POST",
    headers: { Authorization: `Bearer ${loans_token}`, "Content-Type": "application/json" },
    body: JSON.stringify(task),
  });
  if (!res.ok) throw new Error(`task was not created: ${res.status}`);
  return { created: true };
}
```
```text
# workflow: w19
a068 -> flow_input.member_id   # new member [webhook]
a069 -> send_welcome   # Send welcome [http_request]
a070 -> send_welcome   # wait a day [event_transform/delay]
a071 -> create_follow_up_task   # Create follow-up task [http_request]
```
**Goes wrong**
- `sleep: 86400` as a bare number, or `sleep` inside `value`. It is `sleep: {type: static, value: 86400}`, beside `id` and `value`.
- A long `setTimeout` in a script. That holds a worker. Use step `sleep` for a wait between steps.
- The delay is the first action after the entry. Then put `sleep` on a `type: identity` step in front.
- The delay has `CYCLE` in the graph. That is a poll loop: use recipe 9.
- A computed delay (`seconds: "<<30 * NUMBER(x)>>"`): `sleep: {type: javascript, expr: "30 * Number(flow_input.x)"}`.

**Notes file**
- Mapping: the delay action maps to the step that carries the `sleep`.
- Not verified: a `sleep` of a day was not run.

## 20. Throttle

**Outline shows**
```text
    a073 explode_labels [event_transform/explode]  recipe 13
      a074 slow_printer [event_transform/throttle]  recipe 20
        a075 print_spine_label [http_request]  END  recipe 6,25
  capacity: "6"
  interval: minute
```
First find what the throttle limits. It limits only the actions after it on its own branch.

**Write, when the main work comes after the throttle:** a loop with `parallel: false` and a `sleep` on its step. 6 per minute is one every 10 seconds.
```yaml
# flow.yaml
summary: Print a batch of spine labels
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [labels]
  properties:
    labels: {type: array, items: {type: object}}
value:
  modules:
    - id: loop_labels
      value:
        type: forloopflow
        iterator: {type: javascript, expr: "flow_input.labels"}
        skip_failures: true
        parallel: false
        modules:
          - id: print_spine_label
            sleep: {type: static, value: 10}
            value:
              type: rawscript
              language: bun
              content: "!inline print_spine_label.ts"
              input_transforms:
                label: {type: javascript, expr: "flow_input.iter.value"}
                printer_key: {type: static, value: "$var:f/library/printer_key"}
```
```ts
// print_spine_label.ts
// a075 Print spine label (a074 slow printer is the sleep on this step)
export async function main(label: object, printer_key: string) {
  const res = await fetch("https://printer.example.net/jobs", {
    method: "POST",
    headers: { "X-Printer-Key": printer_key, "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error(`printer returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w20
a072 -> flow_input.labels   # label batch [webhook]
a073 -> loop_labels   # explode labels [event_transform/explode]
a074 -> print_spine_label   # slow printer [event_transform/throttle]
a075 -> print_spine_label   # Print spine label [http_request]
```
**Write, when the throttle is on a side branch:** nothing. Example (outline of w24): the throttle `a088` sits beside the main work `a087`, in front of a state write only.
```text
    a086 explode_returns [event_transform/explode]  FAN-OUT x2  recipe 13,15
      a087 request_reshelving [http_request]  END  recipe 6,25
      a088 ease_off [event_transform/throttle]  recipe 20
        a089 save_cursor [http_request]  END  recipe 24,25
```
The flow writes the state once, after the loop (recipe 24). Nothing is left to slow down. Map the throttle to the step that writes the state.

**Goes wrong**
- A `sleep` or a limit is put on the main loop although the throttle is on a side branch. The story never slowed the main work.
- The throttle is dropped without a word. Always say in the notes what you did with it.
- A throttle right after the entry, with no explode, limits whole runs. Use `concurrent_limit: 1` and `concurrency_time_window_s: 10` in `value`, beside `modules`. This may need an Enterprise licence.

**Notes file**
- Behaviour differences: the Tines throttle is shared by all runs of the story. The `sleep` spaces the items of one run only. Two runs at the same time are not slowed against each other.
- Side branch: "`ease off` (a088) limited the state writes to 2 per minute. The flow writes the state once per run, so no limit is needed. The main work was never throttled."

## 21. Deduplicate

**Outline shows**
```text
  a076 get_ready_holds [http_request]  ENTRY: schedule cron */15 * * * * (Europe/Dublin)  recipe 1,6,25
    a077 explode_holds [event_transform/explode]  recipe 13
      a078 only_new [event_transform/deduplicate]  recipe 21
        a079 text_member [http_request]  END  recipe 6,25
  path: <<explode_holds.hold.id>>
  lookback: "500"
```
**Write** the filter in the step that produces the list, before the loop. Keep the seen keys with `getState` / `setState`.
```yaml
# flow.yaml
summary: Text members whose hold is ready
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties: {}
value:
  modules:
    - id: fetch_new_holds
      value:
        type: rawscript
        language: bun
        content: "!inline fetch_new_holds.ts"
        input_transforms:
          api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: loop_holds
      value:
        type: forloopflow
        iterator: {type: javascript, expr: "results.fetch_new_holds.holds"}
        skip_failures: true
        parallel: false
        modules:
          - id: text_member
            value:
              type: rawscript
              language: bun
              content: "!inline text_member.ts"
              input_transforms:
                hold: {type: javascript, expr: "flow_input.iter.value"}
                api_token: {type: static, value: "$var:f/library/notify_token"}
```
```yaml
# f/library/text_ready_holds.schedule.yaml
schedule: "0 */15 * * * *"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/text_ready_holds
is_flow: true
args: {}
```
```ts
// fetch_new_holds.ts
import * as wmill from "windmill-client";

type Hold = { id: string; member_id: string; title: string };
const LOOKBACK = 500;                                          // lookback: "500"

// a076 Get ready holds, a078 only new
export async function main(api_token: string): Promise<{ holds: Hold[] }> {
  const res = await fetch("https://loans.example.org/v1/holds?state=ready", {
    headers: { Authorization: `Bearer ${api_token}` },
  });
  if (!res.ok) throw new Error(`holds returned ${res.status}`);
  const holds: Hold[] = (await res.json())?.holds ?? [];
  const seen: string[] = (await wmill.getState()) ?? [];       // empty on the first run only. No try/catch.
  const fresh: Hold[] = [];
  for (const hold of holds) {
    const key = String(hold.id);                               // path: <<explode_holds.hold.id>>
    if (seen.includes(key)) continue;                          // duplicate: Tines emits nothing
    seen.push(key);
    fresh.push(hold);
  }
  await wmill.setState(seen.slice(-LOOKBACK));                 // keep the last 500 keys
  return { holds: fresh };
}
```
```ts
// text_member.ts
// a079 Text member
export async function main(hold: { member_id: string; title: string }, api_token: string) {
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: hold.member_id, text: `Ready for pickup: ${hold.title}` }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w21
a076 -> fetch_new_holds   # Get ready holds [http_request]
a077 -> loop_holds   # explode holds [event_transform/explode]
a078 -> fetch_new_holds   # only new [event_transform/deduplicate]
a079 -> text_member   # Text member [http_request]
```
**Goes wrong**
- `getState` is called in one step and `setState` in another. State belongs to one step. Read and write it in the same step.
- The state call sits inside the loop. Filter the whole list once, before the loop.
- The state read is wrapped in `try/catch`. A permission error then looks like a first run and everything is sent again.
- The seen list grows without limit. Cut it to the story's `lookback`. For `period` (seconds), store `{key, at}` pairs and drop the old ones.

**Notes file**
- Behaviour differences: a key is remembered when it is seen, as in Tines. If the text fails, that hold is not tried again.
- Not verified: Windmill keeps state per step and per trigger. A manual run may not share the memory of the scheduled runs.

## 22. Send email

**Outline shows**
```text
a081 email_branch_staff  "Email branch staff"  [send_email]  recipe 22
  recipients: =closure_notice.body.recipients
  reply_to: desk@example.org
  subject: Closure: <<closure_notice.body.branch>> on <<closure_notice.body.day>>
```
**Write** a script with `nodemailer` and an `smtp` resource. Windmill has no built-in mail step.
```yaml
# flow.yaml
summary: Email branch staff about a closure
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [recipients, branch, day]
  properties:
    recipients: {type: array, items: {type: string}}
    branch: {type: string}
    day: {type: string}
    reason: {type: string, default: ""}
value:
  modules:
    - id: email_branch_staff
      value:
        type: rawscript
        language: bun
        content: "!inline email_branch_staff.ts"
        input_transforms:
          smtp: {type: static, value: "$res:f/library/smtp"}
          recipients: {type: javascript, expr: "flow_input.recipients"}
          branch: {type: javascript, expr: "flow_input.branch"}
          day: {type: javascript, expr: "flow_input.day"}
          reason: {type: javascript, expr: "flow_input.reason"}
```
```ts
// email_branch_staff.ts
import nodemailer from "nodemailer";

type Smtp = { host: string; port: number; user?: string; password?: string };
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
// Every value put into an HTML body goes through esc(). Otherwise a value that contains tags changes the email.
const esc = (v: any): string =>
  text(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

// a081 Email branch staff
export async function main(smtp: Smtp, recipients: string[], branch: string, day: string, reason: string) {
  const transport = nodemailer.createTransport({
    host: smtp.host,
    port: smtp.port,
    auth: smtp.user ? { user: smtp.user, pass: smtp.password } : undefined,
  });
  const info = await transport.sendMail({
    from: smtp.user,                                      // Tines sent from the tenant's own address
    to: recipients,                                       // one address or a list
    replyTo: "desk@example.org",
    subject: `Closure: ${text(branch)} on ${text(day)}`,
    html: `<p>The <b>${esc(branch)}</b> branch is closed on ${esc(day)}.</p><p>${esc(reason)}</p>`,
  });
  return { message_id: info.messageId };
}
```
```text
# workflow: w22
a080 -> flow_input.recipients, flow_input.branch, flow_input.day, flow_input.reason   # closure notice [webhook]
a081 -> email_branch_staff   # Email branch staff [send_email]
```
**Goes wrong**
- A Hub script path is invented. Write the script.
- The subject or the body is rewritten. Copy both from the story. Replace only the pills.
- A plain-text body is sent as `html`, or the other way round. A body with tags is `html`. A body without tags is `text`.
- A value is put into an `html` body without `esc()`. Data from a webhook, a page or an API can contain tags. Escape every value. If the story inserts a value that is meant to be HTML, leave that one value unescaped and say so in the notes.
- The `html` string is built in an input transform in `flow.yaml`. Build it in the script, where `esc()` exists.
- Attachments: a Tines attachment `{filename, base64encodedcontents}` becomes `attachments: [{ filename, content: <base64>, encoding: "base64" }]`.

**Notes file**
- Setup: the resource `f/library/smtp` of type `smtp` (host, port, user, password).
- Behaviour differences: the sender address is now the SMTP user. Tines sent from the tenant's address.
- Not verified: the field names of the `smtp` resource type.

## 23. Resource that is only read: settings or a lookup table

**Outline shows**
```text
a083 get_stock  "Get stock"  [http_request]  recipe 6,23,25
  uses: a082 stock_query, RESOURCE.inventory_api, CREDENTIAL.inventory_key
  url: <<RESOURCE.inventory_api.url>>/stock/<<stock_query.body.isbn>>
  timeout: =RESOURCE.inventory_api.timeout
  payload: {"to": "=GET(RESOURCE.branch_contacts, stock_query.body.branch)", "text": "Copies in stock: <<get_stock.body.copies>>"}
```
**Write** a Windmill resource for connection settings and a non-secret variable holding JSON for a lookup table. The flow reads them at run time. Do not write a stub. Do not invent their content.

Which one:
- A Tines resource that is an object with named keys, above all connection settings (`RESOURCE.x.url`, `.timeout`, `.retries`): a Windmill **resource**. Pass it as `"$res:<path>"`. The step gets an object.
- A Tines resource that is one string (a user name, a channel id, one base URL): a non-secret **variable**. Pass it as `"$var:<path>"`. The step gets the string.
- A Tines resource used as data (a lookup table, a list): a non-secret **variable holding JSON**. Pass it as `"$var:<path>"` and `JSON.parse` it in the step.
- A secret is never in a non-secret variable: that is a credential (recipe 25).
```yaml
# flow.yaml
summary: Tell a branch how many copies are in stock
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [isbn, branch]
  properties:
    isbn: {type: string}
    branch: {type: string}
value:
  modules:
    - id: notify_branch_stock
      value:
        type: rawscript
        language: bun
        content: "!inline notify_branch_stock.ts"
        input_transforms:
          isbn: {type: javascript, expr: "flow_input.isbn"}
          branch: {type: javascript, expr: "flow_input.branch"}
          inventory_api: {type: static, value: "$res:f/library/inventory_api"}
          branch_contacts: {type: static, value: "$var:f/library/branch_contacts"}
          inventory_key: {type: static, value: "$var:f/library/inventory_key"}
          notify_token: {type: static, value: "$var:f/library/notify_token"}
```
```ts
// notify_branch_stock.ts
// a083 Get stock, a084 Notify branch
export async function main(
  isbn: string, branch: string,
  inventory_api: { url: string; timeout?: number | string },   // RESOURCE.inventory_api: an object
  branch_contacts: string,                                     // RESOURCE.branch_contacts: JSON text of a variable
  inventory_key: string, notify_token: string,
) {
  const contacts: Record<string, string> = JSON.parse(branch_contacts);
  const stock = await fetch(`${inventory_api.url}/stock/${encodeURIComponent(isbn)}`, {
    headers: { "X-Api-Key": inventory_key },
    signal: AbortSignal.timeout(Number(inventory_api.timeout ?? 30) * 1000),   // timeout: =RESOURCE.inventory_api.timeout
  });
  if (!stock.ok) throw new Error(`stock returned ${stock.status}`);
  const copies = (await stock.json())?.copies ?? null;
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${notify_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: contacts[branch] ?? null, text: `Copies in stock: ${copies ?? ""}` }),   // GET(RESOURCE.branch_contacts, branch)
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { copies, notified: contacts[branch] ?? null };
}
```
```text
# workflow: w23
a082 -> flow_input.isbn, flow_input.branch   # stock query [webhook]
a083 -> notify_branch_stock   # Get stock [http_request]
a084 -> notify_branch_stock   # Notify branch [http_request]
```
**Goes wrong**
- A stub that throws `MISSING` is written for the resource. The value is data that the user creates. A stub is only for missing logic (recipe 27).
- The content is guessed and written into the script (a host, a table of contacts). Only the keys that the story reads are known: `url`, `timeout`.
- A host is written into the code. A base URL of one of the user's own systems, and any other value that differs per environment, lives in a variable or resource and is listed under Setup. That is also true when the story has the internal host as plain text in a `url:` (recipe 6). Never copy an internal host name from the export into the flow or the notes. A public vendor API host may stay in the code.
- `"$res:..."` or `"$var:..."` is built inside a longer string. It must be the whole static value.
- The Tines name is changed. Keep it as the last part of the path: `RESOURCE.inventory_api` is `f/library/inventory_api`.

**Notes file**
- Setup: resource `f/library/inventory_api` (custom type, for example `c_inventory_api`), not secret, keys `url` and `timeout`: was `RESOURCE.inventory_api`. Variable `f/library/branch_contacts`, not secret, JSON object of branch code to contact: was `RESOURCE.branch_contacts`.
- Not verified: the content of both resources is not in the export.

## 24. State shared by a read at the start and a write at the end

**Outline shows**
```text
  a085 get_returns [http_request]  ENTRY: schedule cron */20 * * * * (Europe/Dublin)  recipe 1,6,24,25
    a086 explode_returns [event_transform/explode]  FAN-OUT x2  recipe 13,15
      a087 request_reshelving [http_request]  END  recipe 6,25
      a088 ease_off [event_transform/throttle]  recipe 20
        a089 save_cursor [http_request]  END  recipe 24,25
  url: https://loans.example.org/v1/returns?after=<<RESOURCE.returns_cursor.last_id>>
  url: https://tenant.example.com/api/v1/global_resources/<<INFO.resource.returns_cursor.id>>
  payload: {"value": {"last_id": "=MAX(RESOURCE.returns_cursor.last_id, explode_returns.item.id)"}}
```
**Write** one non-secret variable holding JSON. The first step reads it. A last step, after the loop, writes it once. The call to the Tines API and its credential are not ported.
```yaml
# flow.yaml
summary: Request reshelving for new returns
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  properties: {}
value:
  modules:
    - id: fetch_returns
      value:
        type: rawscript
        language: bun
        content: "!inline fetch_returns.ts"
        input_transforms:
          api_token: {type: static, value: "$var:f/library/loans_token"}
          cursor_var: {type: static, value: f/library/returns_cursor}
    - id: loop_returns
      value:
        type: forloopflow
        iterator: {type: javascript, expr: "results.fetch_returns.returns"}
        skip_failures: true
        parallel: false
        modules:
          - id: request_reshelving
            value:
              type: rawscript
              language: bun
              content: "!inline request_reshelving.ts"
              input_transforms:
                item: {type: javascript, expr: "flow_input.iter.value"}
                api_key: {type: static, value: "$var:f/library/catalog_key"}
    - id: save_returns_cursor
      value:
        type: rawscript
        language: bun
        content: "!inline save_returns_cursor.ts"
        input_transforms:
          max_id: {type: javascript, expr: "results.fetch_returns.max_id"}
          cursor_var: {type: static, value: f/library/returns_cursor}
```
```yaml
# f/library/reshelve_returns.schedule.yaml
schedule: "0 */20 * * * *"
timezone: Europe/Dublin
enabled: false   # turned on by a person after the flow was reviewed and tested
script_path: f/library/reshelve_returns
is_flow: true
args: {}
no_flow_overlap: true
```
```ts
// fetch_returns.ts
import * as wmill from "windmill-client";

// a085 Get returns (reads RESOURCE.returns_cursor)
export async function main(api_token: string, cursor_var: string) {
  // No try/catch: a missing variable or a permission error must fail, not look like a first run.
  const cursor: { last_id?: number } = JSON.parse(await wmill.getVariable(cursor_var));
  const res = await fetch(`https://loans.example.org/v1/returns?after=${cursor.last_id ?? ""}`, {
    headers: { Authorization: `Bearer ${api_token}` },
  });
  if (!res.ok) throw new Error(`returns returned ${res.status}`);
  const returns: { id: number; item_id: string; branch: string }[] = (await res.json())?.returns ?? [];
  return { returns, max_id: returns.length ? Math.max(...returns.map((r) => Number(r.id))) : null };
}
```
```ts
// request_reshelving.ts
// a087 Request reshelving
export async function main(item: { item_id: string; branch: string }, api_key: string) {
  const res = await fetch("https://catalog.example.org/api/v2/reshelve", {
    method: "POST",
    headers: { "X-Api-Key": api_key, "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: item.item_id, branch: item.branch }),
  });
  if (!res.ok) throw new Error(`reshelve returned ${res.status}`);
  return { status: res.status };
}
```
```ts
// save_returns_cursor.ts
import * as wmill from "windmill-client";

// a088 ease off, a089 Save cursor: the Tines API call becomes one variable write per run
export async function main(max_id: number | null, cursor_var: string) {
  if (max_id === null) return { saved: null };                          // nothing fetched: the story wrote nothing
  const cursor: { last_id?: number } = JSON.parse(await wmill.getVariable(cursor_var));
  cursor.last_id = Math.max(Number(cursor.last_id ?? 0), max_id);       // =MAX(RESOURCE.returns_cursor.last_id, item.id)
  await wmill.setVariable(cursor_var, JSON.stringify(cursor));
  return { saved: cursor.last_id };
}
```
```text
# workflow: w24
a085 -> fetch_returns   # Get returns [http_request]
a086 -> loop_returns   # explode returns [event_transform/explode]
a087 -> request_reshelving   # Request reshelving [http_request]
a088 -> save_returns_cursor   # ease off [event_transform/throttle]
a089 -> save_returns_cursor   # Save cursor [http_request]
```
**Goes wrong**
- `getState` / `setState` in two different steps. Each step has its own state. Two steps share a variable instead.
- The cursor is written inside the loop, once per item, with a `sleep` for the throttle. Write it once, after the loop.
- The work is capped (first 10 items) but the cursor still moves to the newest id. The skipped items are then lost.
- The HTTP call to `tenant.example.com/api/v1/global_resources` is ported as a `fetch`. It is a state write: use `setVariable`.
- One step both reads and writes the state and no other step needs it. Then use `wmill.getState()` / `wmill.setState()` in that step instead of a variable.

**Notes file**
- Setup: variable `f/library/returns_cursor`, not secret, created with the value `{}`: was `RESOURCE.returns_cursor`. The schedule file, with `no_flow_overlap: true` so that two runs never write the cursor at the same time.
- Behaviour differences: the cursor is written once per run, not once per item. `ease off` (a088) only limited those writes, so no limit is left. As in the story, an item whose reshelving fails is not tried again.
- Not ported: `CREDENTIAL.tines_api_key`, used only to call the Tines API.

## 25. Credentials

**Outline shows**
```text
a091 record_payment  "Record payment"  [http_request]  recipe 6,23,25
  uses: a090 fine_paid, RESOURCE.payments_api, CREDENTIAL.payments_api
  url: <<RESOURCE.payments_api.url>>/payments
  headers: {"Authorization": "Bearer <<CREDENTIAL.payments_api>>"}
  basic_auth: ["<<CREDENTIAL.receipts_user>>", "<<CREDENTIAL.receipts_password>>"]
```
**Write** one secret variable per credential, at `f/<folder>/<credential name>`. Pass it as a static `"$var:<path>"`. Here a credential and a resource share the name `payments_api`, so the credential's path gets `_secret`.
```yaml
# flow.yaml
summary: Record a fine payment and send the receipt
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member_id, amount]
  properties:
    member_id: {type: string}
    amount: {type: number}
value:
  modules:
    - id: record_payment
      value:
        type: rawscript
        language: bun
        content: "!inline record_payment.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          amount: {type: javascript, expr: "flow_input.amount"}
          payments_api: {type: static, value: "$res:f/library/payments_api"}
          payments_token: {type: static, value: "$var:f/library/payments_api_secret"}
          receipts_user: {type: static, value: "$var:f/library/receipts_user"}
          receipts_password: {type: static, value: "$var:f/library/receipts_password"}
```
```ts
// record_payment.ts
// a091 Record payment, a092 Send receipt
export async function main(
  member_id: string, amount: number, payments_api: { url: string },
  payments_token: string, receipts_user: string, receipts_password: string,
) {
  const pay = await fetch(`${payments_api.url}/payments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${payments_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ member_id, amount }),
  });
  if (!pay.ok) throw new Error(`payments returned ${pay.status}`);
  const payment_id: string = (await pay.json())?.id;
  const basic = Buffer.from(`${receipts_user}:${receipts_password}`).toString("base64");   // basic_auth: [user, password]
  const receipt = await fetch("https://receipts.example.com/send", {
    method: "POST",
    headers: { Authorization: `Basic ${basic}`, "Content-Type": "application/json" },
    body: JSON.stringify({ member_id, payment_id }),
  });
  if (!receipt.ok) throw new Error(`receipts returned ${receipt.status}`);
  return { payment_id };                                    // never return a secret
}
```
```text
# workflow: w25
a090 -> flow_input.member_id, flow_input.amount   # fine paid [webhook]
a091 -> record_payment   # Record payment [http_request]
a092 -> record_payment   # Send receipt [http_request]
```
**Goes wrong**
- A secret is a flow input, or is written into a file, or is returned in a result, or is put into an error message.
- The name is changed. Keep the Tines name as the last part of the path, so the user can match them one to one.
- `CREDENTIAL.x` is left in a string. Every `<<CREDENTIAL.x>>` becomes a parameter of `main`.
- A credential that is used only in calls to the Tines API (`x-user-token`, `/api/v1/global_resources`) gets a variable. It is dropped with those calls.
- The paths differ per environment. Then make the path a flow input with a default, and read it in the script with `wmill.getVariable(path)`.

**Notes file**
- Setup: variables `f/library/payments_api_secret` (secret, was `CREDENTIAL.payments_api`), `f/library/receipts_user` and `f/library/receipts_password` (secret). Resource `f/library/payments_api` (not secret, key `url`, was `RESOURCE.payments_api`).
- Behaviour differences: the credential `payments_api` has the path suffix `_secret`, because a resource has the same name.
- The action has both `basic_auth` and an `Authorization` header (or two other ways to log in). A request has one `Authorization` header. Which one Tines sends is **not verified**: do not invent a second header name such as `Basic-Auth`. Send the explicit `Authorization` header, keep the basic-auth values as unused arguments, and write the choice under **Not verified** in the notes so the user can confirm it.

## 26. `META` passed on as an object, and the story run id

**Outline shows**
```text
a094 write_audit_entry  "Write audit entry"  [http_request]  recipe 6,25,26
  uses: a093 desk_note, META, META.story, CREDENTIAL.audit_key
  payload: {"note": "<<desk_note.body.note>>", "run": "=STORY_RUN_GUID()", "origin": "=META", "story": "<<META.story.name>>"}
```
**Write** a small object in the script. Give it only the keys that are read later, in the shape Tines gave them (`story.name`, `story_run.id`).
```yaml
# flow.yaml
summary: Write a desk note to the audit log
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [note]
  properties:
    note: {type: string}
value:
  modules:
    - id: write_audit_entry
      value:
        type: rawscript
        language: bun
        content: "!inline write_audit_entry.ts"
        input_transforms:
          note: {type: javascript, expr: "flow_input.note"}
          audit_key: {type: static, value: "$var:f/library/audit_key"}
```
```ts
// write_audit_entry.ts
const STORY_NAME = "Library - desk automations";   // META.story.name: the STORY line of the index

// a094 Write audit entry
export async function main(note: string, audit_key: string) {
  // =STORY_RUN_GUID() and META.story_run.id: one id for the whole run. WM_JOB_ID alone changes at every step.
  const run_id = process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID ?? null;
  // =META: not the whole Tines object. Only what the receiver reads.
  const origin = { story: { name: STORY_NAME }, story_run: { id: run_id } };
  const res = await fetch("https://audit.example.org/v1/entries", {
    method: "POST",
    headers: { "X-Audit-Key": audit_key, "Content-Type": "application/json" },
    body: JSON.stringify({ note, run: run_id, origin, story: STORY_NAME }),
  });
  if (!res.ok) throw new Error(`audit returned ${res.status}`);
  return { run_id };
}
```
```text
# workflow: w26
a093 -> flow_input.note   # desk note [webhook]
a094 -> write_audit_entry   # Write audit entry [http_request]
```
**Goes wrong**
- `META` or `STORY_RUN_GUID()` is left in the code, or `META` is sent as an empty object.
- `process.env.WM_JOB_ID` alone is used as the run id. Each step has another job id. Two steps would then report two runs.
- Values are invented for `META.tenant`, `META.action.id`, `META.event.id`. If nothing reads a key, leave it out. If something reads it and there is no Windmill value, send `null` and say so.
- The receiver is a sub-story that **checks** a `META` field (for example it stops with "missing parameter" when the tenant name is empty), and the caller sends `null` for it. Look at the sub-story's first triggers before you decide what callers send. Decide the values once, when the sub-story is ported, write them in `PLAN.md`, and make every caller send the same.
- `META` goes to a sub-story (`my_meta: =META` in a send-to-story payload). Print the sub-story (`--story s1`), find the `my_meta.x` paths it reads, and build the object with those keys.

**Notes file**
- Behaviour differences: `origin` holds `story.name` and `story_run.id` only. The other `META` keys (tenant, team, action, event) are not sent. The run id is a Windmill job id, not a Tines run id.
- Not verified: which `META` keys the receiver reads. The environment variable names were not checked on an instance.

## 27. Missing logic: stored lambda, story not in the export, other Tines API call

**Outline shows**
```text
a096 short_title  "short title"  [event_transform/message_only]  recipe 11,27
  uses: a095 new_title, RESOURCE.text_tools()
  payload: =RESOURCE.text_tools.shorten(new_title.body.title, 40)
  calls: STORY.print_shelf_label - body NOT in this export (separate story; port or ask for it)
  RESOURCE.text_tools: a096  CALLED AS FUNCTION: shorten - lambda body not in export, ask the user for it
```
**Write** a stub that throws, after you asked the user and got no answer. The message starts with `MISSING:` and names what is missing. Keep the stub's inputs, so the real code can be dropped in.
```yaml
# flow.yaml
summary: Print a shelf label for a new title
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [title]
  properties:
    title: {type: string}
value:
  modules:
    - id: short_title
      value:
        type: rawscript
        language: bun
        content: "!inline short_title.ts"
        input_transforms:
          title: {type: javascript, expr: "flow_input.title"}
    - id: print_label_via_story
      value:
        type: rawscript
        language: bun
        content: "!inline print_label_via_story.ts"
        input_transforms:
          text: {type: javascript, expr: "results.short_title"}
          copies: {type: static, value: 1}
```
```ts
// short_title.ts
// RESOURCE.text_tools.shorten(value, length): a lambda stored in a resource. Its body is not in the export.
function shorten(value: string, length: number): string {
  throw new Error(`MISSING: Tines resource text_tools.shorten - definition not in export (called with length ${length})`);
}

// a096 short title
export async function main(title: string) {
  return shorten(title, 40);
}
```
```ts
// print_label_via_story.ts
// a097 Print label via story: STORY.print_shelf_label is not in the export.
// When it is ported, replace this step by a `type: flow` step with the inputs text and copies.
export async function main(text: string, copies: number) {
  throw new Error(`MISSING: Tines story print_shelf_label - not in export (payload keys: text, copies; copies=${copies})`);
}
```
```text
# workflow: w27
a095 -> flow_input.title   # new title [webhook]
a096 -> short_title   # short title [event_transform/message_only]
a097 -> print_label_via_story   # Print label via story [send_to_story]
```
**Goes wrong**
- The body is guessed from the name (`shorten` becomes `value.slice(0, length)`). Never guess. A wrong guess runs silently; a stub fails loudly.
- The action is marked `DROPPED`. A stub is mapped to its step. The work is still owed.
- A stub is written for a credential or for a resource that is only read. Those are data: recipes 23 and 25.
- The error is caught later so that the flow goes on. Let it fail.
- A call to the Tines API that is not a resource write (events, actions, cases, records: any other `/api/v1/...` URL of the tenant) has no Windmill equivalent. Write the same kind of stub: `MISSING: Tines API call <method> <path>`.

**Notes file**
- Not ported: every stub, word for word: "`short_title` throws `MISSING: Tines resource text_tools.shorten`. Needed: the lambda's definition."
- Setup: nothing for the stubs. The flow fails at the first stub until the missing logic is supplied.

## 28. A story bug with a destructive effect

**Outline shows**
```text
a100 matching  [event_transform/message_only]  recipe 11
  payload: =FILTER(get_expired_holds.body.holds, LAMBDA(h, MATCH(h.title, purge_request.body.pattern)))
a101 explode_targets  "explode targets"  [event_transform/explode]  recipe 13
  path: =DEFAULT(matching, get_expired_holds.body.holds)
a102 delete_hold  "Delete hold"  [http_request]  recipe 6,25
  outside effect: HTTP DELETE
```
`DEFAULT` treats an empty list as blank. When the pattern matches nothing, the story deletes every expired hold.

**Write** the safe behaviour: no match deletes nothing. Do not port the fallback. Say so in the code and in the notes.
```yaml
# flow.yaml
summary: Delete expired holds whose title matches a pattern
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [pattern]
  properties:
    pattern: {type: string, description: Regular expression tested on the hold title}
value:
  modules:
    - id: select_holds
      value:
        type: rawscript
        language: bun
        content: "!inline select_holds.ts"
        input_transforms:
          pattern: {type: javascript, expr: "flow_input.pattern"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: loop_targets
      value:
        type: forloopflow
        iterator: {type: javascript, expr: "results.select_holds.targets"}
        skip_failures: true
        parallel: false
        modules:
          - id: delete_hold
            value:
              type: rawscript
              language: bun
              content: "!inline delete_hold.ts"
              input_transforms:
                hold: {type: javascript, expr: "flow_input.iter.value"}
                api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// select_holds.ts
type Hold = { id: string; title?: string };

// a099 Get expired holds, a100 matching, and the path of a101 explode targets
export async function main(pattern: string, api_token: string) {
  if (!pattern) throw new Error("pattern is empty: nothing is deleted");
  const res = await fetch("https://loans.example.org/v1/holds?state=expired", {
    headers: { Authorization: `Bearer ${api_token}` },
  });
  if (!res.ok) throw new Error(`holds returned ${res.status}`);
  const holds: Hold[] = (await res.json())?.holds ?? [];
  const re = new RegExp(pattern);                                            // MATCH(h.title, pattern)
  const matching = holds.filter((h) => re.test(String(h?.title ?? "")));
  // Story: =DEFAULT(matching, get_expired_holds.body.holds). An empty match fell back to ALL holds.
  // Deliberate change: an empty match deletes nothing.
  return { targets: matching, matched: matching.length, expired: holds.length };
}
```
```ts
// delete_hold.ts
// a102 Delete hold
export async function main(hold: { id: string }, api_token: string) {
  const res = await fetch(`https://loans.example.org/v1/holds/${encodeURIComponent(hold.id)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${api_token}` },
  });
  if (!res.ok) throw new Error(`delete of hold ${hold.id} returned ${res.status}`);
  return { deleted: hold.id };
}
```
```text
# workflow: w28
a098 -> flow_input.pattern   # purge request [webhook]
a099 -> select_holds   # Get expired holds [http_request]
a100 -> select_holds   # matching [event_transform/message_only]
a101 -> loop_targets   # explode targets [event_transform/explode]
a102 -> delete_hold   # Delete hold [http_request]
```
**Goes wrong**
- The fallback is ported faithfully (`matching.length ? matching : holds`). That keeps the bug.
- The change is made silently. The user must be told: in the notes and in your message.
- Every odd thing is called a bug. Change behaviour only when the effect destroys or sends something by accident. Port everything else as it is and list it under "Not verified".
- The intended fallback is kept by mistake. `DEFAULT(x, y)` where `x` can be missing but not an empty list is normal: port it with `isBlank`.

**Notes file**
- Behaviour differences, marked deliberate: "`explode targets` (a101) used `DEFAULT(matching, all expired holds)`. `DEFAULT` treats `[]` as blank, so a pattern with no match deleted every expired hold. The flow deletes nothing in that case. An empty pattern fails the run. To get the story's behaviour back, change `select_holds.ts`."
- Not verified: Tines regular expressions are Ruby; the flow uses JavaScript `RegExp`.

## 29. Disabled, unreachable and dead-end actions

**Outline shows**
```text
  a103 shelf_sensor [webhook]  ENTRY: webhook  FAN-OUT x3  recipe 2,15
    a104 record_reading [http_request]  END  recipe 6,25
    a105 debug_copy [event_transform/message_only]  DEAD-END  recipe 11,29
    a106 old_alert [http_request]  DISABLED  END  recipe 29
NOT TRIGGERED in main (no entry point: never runs unless started by hand; `;` separates unconnected pieces; print with --actions ID)
  a107 event_transform_action
```
**Write** nothing for them. Keep their lines in the map with `DROPPED:` and a reason. `END` is kept: it has an outside effect.
```yaml
# flow.yaml
summary: Record a shelf sensor reading
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [shelf]
  properties:
    shelf: {type: string}
    weight_g: {type: number, default: 0}
value:
  modules:
    - id: record_reading
      value:
        type: rawscript
        language: bun
        content: "!inline record_reading.ts"
        input_transforms:
          shelf: {type: javascript, expr: "flow_input.shelf"}
          weight_g: {type: javascript, expr: "flow_input.weight_g"}
          api_key: {type: static, value: "$var:f/library/catalog_key"}
```
```ts
// record_reading.ts
// a104 Record reading
export async function main(shelf: string, weight_g: number, api_key: string) {
  const res = await fetch("https://catalog.example.org/api/v2/shelf-readings", {
    method: "POST",
    headers: { "X-Api-Key": api_key, "Content-Type": "application/json" },
    body: JSON.stringify({ shelf, weight_g }),
  });
  if (!res.ok) throw new Error(`shelf readings returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w29
a103 -> flow_input.shelf, flow_input.weight_g   # shelf sensor [webhook]
a104 -> record_reading   # Record reading [http_request]
a105 -> DROPPED: dead end; nothing reads its output and it has no outside effect   # debug copy [event_transform/message_only]
a106 -> DROPPED: disabled in Tines   # Old alert [http_request]
```
**Goes wrong**
- A map line is deleted. Never delete a line. `--map-template` fills in `DROPPED` for disabled and unreachable actions: leave those lines as they are.
- A `DEAD-END` is ported "to be safe". Nothing reads it. Drop it.
- An `END` is dropped. `END` means the last action of a branch with an outside effect. Port it.
- An action is marked `DROPPED` only to make the validator pass. `DROPPED` needs a true reason.
- Actions under `NOT TRIGGERED` (here `a107`) are not part of any workflow. They have no map line. Mention them once in the notes.
- A whole workflow marked `NO-EFFECT` in the index is not ported: plan it as `SKIP: no effect` and tell the user.

**Notes file**
- Not ported: "`debug copy` (a105): dead end. `Old alert` (a106): disabled in Tines. `Event Transform Action` (a107): not linked to anything."

## 30. Early exit, then a shared final step

**Outline shows**
```text
    a110 has_overdue_items [trigger]  recipe 14
      a111 suspend_borrowing [http_request]  recipe 6,25
        a112 write_account_log [http_request]  JOIN x2  END  recipe 6,14,16,25,30
      (no-match) ^ a112 write_account_log  (JOIN: shown above)
  payload: {"member_id": "<<account_check.body.member_id>>", "checked": true, "suspension_id": "<<suspend_borrowing.body.id>>"}
```
One side skips `a111`. Both sides end in `a112`. `a112` reads the output of `a111`, which is `NULL` on the skipping side.

**Write, option A (use this one here):** a guard inside the script. On the skipping side the script returns early with the same keys. The final step can always read them.
```yaml
# flow.yaml
summary: Suspend borrowing for overdue items and log the check
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member_id]
  properties:
    member_id: {type: string}
    overdue_count: {type: integer, default: 0}
value:
  modules:
    - id: suspend_borrowing
      value:
        type: rawscript
        language: bun
        content: "!inline suspend_borrowing.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          overdue_count: {type: javascript, expr: "flow_input.overdue_count"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
    - id: write_account_log
      value:
        type: rawscript
        language: bun
        content: "!inline write_account_log.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          suspension_id: {type: javascript, expr: "results.suspend_borrowing.suspension_id"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
```ts
// suspend_borrowing.ts
type Result = { suspended: boolean; suspension_id: string | null };

// a110 has overdue items, a111 Suspend borrowing
export async function main(member_id: string, overdue_count: number, api_token: string): Promise<Result> {
  // a110 does not match: nothing to do. Return the SAME keys as the normal path.
  if (!(Number(overdue_count) > 0)) return { suspended: false, suspension_id: null };
  const res = await fetch(`https://loans.example.org/v1/members/${encodeURIComponent(member_id)}/suspensions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "overdue items" }),
  });
  if (!res.ok) throw new Error(`suspension returned ${res.status}`);
  return { suspended: true, suspension_id: (await res.json())?.id ?? null };
}
```
```ts
// write_account_log.ts
// a112 Write account log: the shared final step. It runs on both sides, once.
export async function main(member_id: string, suspension_id: string | null, api_token: string) {
  const res = await fetch("https://loans.example.org/v1/account-log", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ member_id, checked: true, suspension_id }),   // null when nothing was suspended, as in Tines
  });
  if (!res.ok) throw new Error(`account log returned ${res.status}`);
  return { logged: true };
}
```
```text
# workflow: w30
a109 -> flow_input.member_id, flow_input.overdue_count   # account check [webhook]
a110 -> suspend_borrowing   # has overdue items [trigger]
a111 -> suspend_borrowing   # Suspend borrowing [http_request]
a112 -> write_account_log   # Write account log [http_request]
```
**Option B:** a `branchone` with an empty `default`, in place of the step `suspend_borrowing`. Later steps see nothing of it: they cannot read `results.suspend_borrowing` (it is inside the branch), and they must not read `results.suspend_if_overdue` (the result of an empty `default` is not verified). Right when no later step reads anything from the skipped work, or when the skipped work is several steps, a sub-flow or an approval. Wrong here, because `write_account_log` needs `suspension_id`.
```yaml
# flow.yaml, option B: replaces the step suspend_borrowing
    - id: suspend_if_overdue
      value:
        type: branchone
        branches:
          - summary: Has overdue items
            expr: "Number(flow_input.overdue_count) > 0"
            modules:
              - id: suspend_borrowing
                value:
                  type: rawscript
                  language: bun
                  content: "!inline suspend_borrowing.ts"
                  input_transforms:
                    member_id: {type: javascript, expr: "flow_input.member_id"}
                    overdue_count: {type: javascript, expr: "flow_input.overdue_count"}
                    api_token: {type: static, value: "$var:f/library/loans_token"}
        default: []
```
**Option C:** a step setting. Use one of the two lines, not both.
```yaml
# flow.yaml, option C: replaces the step suspend_borrowing
    - id: suspend_borrowing
      skip_if: {expr: "!(Number(flow_input.overdue_count) > 0)"}
      stop_after_if: {expr: "result.suspended === false", skip_if_stopped: true}
      value:
        type: rawscript
        language: bun
        content: "!inline suspend_borrowing.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          overdue_count: {type: javascript, expr: "flow_input.overdue_count"}
          api_token: {type: static, value: "$var:f/library/loans_token"}
```
- `skip_if`: the step does not run and the next steps do run. `results.suspend_borrowing` is then not this step's result: it is the result of the step before it. Later steps that read `results.suspend_borrowing.suspension_id` get `undefined` or a wrong value. Right only when no later step reads this step's result. Wrong here.
- `stop_after_if`: the whole flow ends after this step, as a success. The shared final step does **not** run. Right only for a pure early exit: nothing after it has to run (a trigger near the start with no `(no-match)` link). Wrong here.

**Goes wrong**
- `skip_if` on the step, and a later step reads its result. Use option A.
- `results.suspend_borrowing?.suspension_id ?? null` is written to hide the problem. Make the step return the keys on every path instead.
- The shared final step is copied into both sides. Write it once, after the differing part (recipe 16).
- The early-exit side returns other keys (`{ skipped: true }`). Return the same keys with `null` values.

**Notes file**
- Mapping: the trigger is the guard at the top of `suspend_borrowing`.
- Behaviour differences: none. On the skipping side Tines gave `NULL` for `suspend_borrowing.body.id`; the flow sends `null`.
- Not verified, if you used option C: what later steps see for a skipped step, and the status of a run ended by `stop_after_if`.

## 31. Link to a Tines page that belongs to another workflow

**Outline shows**
```text
a114 answer_with_booking_link  "Answer with booking link"  [http_request]  recipe 6,25,31
  uses: a113 room_question, PAGE.book_a_room, CREDENTIAL.notify_token
  payload: {"to": "<<room_question.body.member_id>>", "text": "You can book a study room here: <<PAGE.book_a_room>>"}
```
`PAGE.book_a_room` is the URL of the Tines page `book_a_room`. That page is the entry of another workflow (here w04).

**Write** a non-secret variable that holds the URL of whatever replaces that page: the run form of the flow that ports it, or a Windmill app. The user fills it in. It is data, so no stub.
```yaml
# flow.yaml
summary: Answer a room question with the booking link
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [member_id]
  properties:
    member_id: {type: string}
value:
  modules:
    - id: answer_with_booking_link
      value:
        type: rawscript
        language: bun
        content: "!inline answer_with_booking_link.ts"
        input_transforms:
          member_id: {type: javascript, expr: "flow_input.member_id"}
          booking_page_url: {type: static, value: "$var:f/library/book_a_room_url"}
          api_token: {type: static, value: "$var:f/library/notify_token"}
```
```ts
// answer_with_booking_link.ts
// a114 Answer with booking link
export async function main(member_id: string, booking_page_url: string, api_token: string) {
  // PAGE.book_a_room: the URL comes from a variable. Fail loudly if nobody has set it yet.
  if (!/^https?:\/\//.test(booking_page_url ?? "")) throw new Error("variable f/library/book_a_room_url does not hold a URL");
  const res = await fetch("https://notify.example.net/v1/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ to: member_id, text: `You can book a study room here: ${booking_page_url}` }),
  });
  if (!res.ok) throw new Error(`notify returned ${res.status}`);
  return { status: res.status };
}
```
```text
# workflow: w31
a113 -> flow_input.member_id   # room question [webhook]
a114 -> answer_with_booking_link   # Answer with booking link [http_request]
```
**Goes wrong**
- A Tines URL is written into the code (`https://<tenant>/pages/...`), or the page's `url_identifier` is copied from the export. Never do that. The Tines page will not exist after the port.
- A Windmill URL is guessed from the flow path. Do not build it. The user knows where the form or the app lives.
- A `MISSING` stub is written. A URL is data that the user supplies: a variable under Setup.
- The link is left out, or `PAGE.x` is left in the text.
- The page belongs to this same workflow and comes later in it. That is an approval step: send `urls.approvalPage` (recipe 5).
- The URL must differ per run. Then make it a flow input with the variable's value as the documented default.

**Notes file**
- Setup: variable `f/library/book_a_room_url`, not secret: "URL that replaces the Tines page `Book a room`: the run form of the flow that ports workflow w04, or an app". Was `PAGE.book_a_room`.
- Depends on: the flow that ports the page's workflow (its line in `PLAN.md`). Until it exists the link has no target.
- Behaviour differences: the Tines page could be opened by anyone the page allowed. A Windmill run form needs a Windmill login.

## 32. What these recipes rely on that is not verified

Nothing in this file was run on a Windmill instance. Copy these points into "Not verified" in the notes file when a flow uses them.

- Approval steps (recipe 5): how the approval page shows the step result; what `approvers` holds; that `resume` holds the form values.
- Preprocessor (recipe 3): the spelling of header keys in `event.headers`; that query values are in `event.query`; the URL of an HTTP route.
- `WM_EMAIL` as the user who runs a flow (recipe 4). `WM_ROOT_FLOW_JOB_ID`, `WM_FLOW_JOB_ID`, `WM_JOB_ID` (recipe 26).
- `fetch(url, { tls: { rejectUnauthorized: false } })` in Bun, behind `skip_tls_verify` (recipe 10). `AbortSignal.timeout` as the request timeout (recipes 8, 10, 23).
- `sleep` on a step inside a loop (recipe 20) and a `sleep` of many hours (recipe 19).
- The entry of a failed iteration or branch in a result list: `null` or `{error: ...}`. The recipes accept both (recipes 13, 15).
- The result of a `branchone` whose empty `default` ran. The recipes never read it (recipes 16, 17).
- `concurrent_limit` may need an Enterprise licence (recipe 20).
- The field names of the `smtp` resource type: `host`, `port`, `user`, `password` (recipe 22).
- State from `getState` is kept per step and per trigger (recipe 21).
- Day-of-week numbers in a schedule (recipe 1): Windmill may count week days differently from Tines.
- Every `if (!res.ok) throw` is a choice: Tines went on after an error response. The recipes fail the step instead.
- How a pill renders an array or an object (recipe 12). The recipes use JSON.
- `skip_if` reading `results`, and what `results.<id>` holds for a skipped step (recipe 30). The recipes do not read it.
- The URL of a flow's run form or of an app (recipe 31). The user supplies it in a variable.
