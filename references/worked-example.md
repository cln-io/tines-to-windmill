# Worked example: "Cold chain - review excursions" (Tines) -> Windmill flow

One port, walked through in the order you should work: read the graph, decide per cluster, map
credentials and state, report differences. The story is invented for teaching; every name, host
and value in it is made up, and the outline excerpts are in the format `scripts/tines_outline.py`
prints. The story has 42 top-level actions plus 25 inside two groups; the flow has 13 modules.
Most of the work is deciding what *disappears*.

The export and the finished flow are in `examples/cold-chain/` (`story.json` and `f/cold_chain/`).
You can run the scripts on them to see the real output.

What the story does: every 20 minutes, for each of three depots, fetch the open temperature
excursions raised since the last run, drop those caused by a defrost cycle, look up the carrier of
each remaining one, then ask a lab, a claims register, a sensor-audit service and a chart service
about it, and email a report with a chart attached when the lab results are bad.

## 1. Read the story as a graph

Never open the export itself. `tines_outline.py S --index` lists one workflow, `w01`, so `PLAN.md`
gets one line: `w01 | review_excursions | schedule */20 * * * * America/Toronto | 60 actions | TODO`.
Under `NOT TRIGGERED` the index also lists `a06 door_open DISABLED > a07 not_empty DISABLED >
a08 rows DISABLED`, a second chain `a39 > a40 > a41` of the same form, and a lone `a42`.
`--workflow w01 --graph` then gives the shape. Answer five questions before translating anything.

**Q1. Where does it start?** The action marked `ENTRY`: `a01 depots`, on a schedule. The index
says `webhooks: none | pages: none`, so that is the only entry point.

**Q2. What is disabled or unreachable?** Everything under `NOT TRIGGERED`: two disabled chains
(filter -> trigger -> rename) and `a42`, which has no links at all. They are not part of `w01`,
get no line in the action map and are not ported. Say so in the notes.

**Q3. Where does it end?** `END` is a leaf with an outside effect: keep it. Here: `a34` (email),
`a38` (state write) and the group `a23` (it requests an audit; the parent never reads its output).
`DEAD-END` is a trigger or transform that nothing reads: drop it. Here: `a21 claim_summary` and
`a22 event_transform_action` (the default placeholder payload).

**Q4. Which names are ambiguous?** The digest ends with a `DUPLICATE REFERENCE NAMES` block:
`_200: a04, a19, a25, a27` and `tag_for_join: a28, a29`. `not empty` and `rows` exist three times
each across the story. `<<rows>>` means the one *upstream of the action using it*. Trust the ids
on each action's `uses:` line, never a name search.

**Q5. Which shapes recur?** Mark them on the graph; each has a standard translation (section 2).

```
a01 depots [event_transform/message_only]  ENTRY: schedule cron */20 * * * * (America/Toronto)
  a02 explode_depots [event_transform/explode]
    a35 since_parameter [event_transform/message_only]          <- reads RESOURCE.excursion_cursor
      a03 get_excursions [http_request]
        a04 _200 [trigger]
          a05 not_defrost [event_transform/message_only]        <- filter formula
            a09 not_empty [trigger]                             <- guard: SIZE(not_defrost) > 0
              a10 rows [event_transform/message_only]           <- rename only
                a11 explode_excursions [event_transform/explode]  FAN-OUT x2
                  a12 look_up_carrier [http_request]  FAN-OUT x4
                    a13 get_batch_report_from_lab [http_request]  FAN-OUT x3  JOIN x2  CYCLE
                      a14 _404 [trigger]  CYCLE
                        a15 wait_for_lab [event_transform/delay]  CYCLE
                          ^ a13 get_batch_report_from_lab  (CYCLE: loops back)
                      a16 failed_tests_above_0 [trigger]
                        a28 tag_for_join [event_transform/message_only]  JOIN x2
                          a30 join_parts [event_transform/implode]  JOIN x2
                            a31 message [event_transform/message_only]
                              a32 chart [event_transform/message_only]
                                a33 message_present [trigger]
                                  a34 send_excursion_report [send_email]  END
                      a17 borderline_tests_above_2 [trigger]
                        ^ a28 tag_for_join  (JOIN: shown above)
                    a18 check_claims_register [http_request]
                      a19 _200 [trigger]  FAN-OUT x2
                        a20 open_claims_is_greater_than_0 [trigger]
                          a21 claim_summary [event_transform/message_only]  DEAD-END
                        (no-match) a22 event_transform_action [event_transform/message_only]  DEAD-END
                    a23 sensor_audit [group]  END               <- 14 inner actions, a23.01 - a23.14
                    a24 find_or_render_chart [group]            <- 11 inner actions, a24.01 - a24.11
                      a25 _200 [trigger]
                        a26 retrieve_chart_image [http_request]
                          a27 _200 [trigger]
                            a29 tag_for_join [event_transform/message_only]
                              ^ a30 join_parts  (JOIN: shown above)
                  a36 slow_down [event_transform/throttle]
                    a37 latest_seen [event_transform/message_only]
                      a38 save_cursor [http_request]  END       <- HTTP to the Tines API
```

Four things in this graph decide the whole port, so check them twice:
- `a11 explode_excursions` has **two** children. The throttle `a36` is on the cursor branch only;
  the lookup branch under `a12` is not throttled.
- `a16` and `a17` both feed `a28`: two triggers into one action is an **OR**.
- A `(no-match)` link (`a19 -> a22`, and three inside group `a24`) is the trigger's *else* path.
- The cursor is read at the start (`a35`) and written at the end of a side branch (`a38`).

Ids follow the position in the export, not the flow of data: `a35` runs third. A group's inner
actions are `a23.01`, `a23.02`, ...; print them with `--group a23`. A group built from a template
has `options: {}`. Its inputs live in the export's top-level `integrations`, and the digest prints
them under the group:

```
a24 find_or_render_chart  "Find or Render Chart"  [group]
  inputs (read as INPUT.x here, GROUP_INPUT.x inside a group):
    sensor_id: <<explode_excursions.alert.sensor_id>>
    resolution: {"value": "", "type": "OPTION", "choices": ["hour", "minute", "raw"]}
    chart_service_credential: {"value": "=CREDENTIAL.chart_service", "required": true, "type": "CREDENTIAL"}
```

The same line explains `<<INPUT.job_id>>` in `a26`. Also read the `AUTHOR NOTES` block: these are
the author's comments. Here one says defrost excursions are ignored on purpose, and one names the
resource behind the numeric id in the URL that `a38` posts to (`.../global_resources/4410/replace`).

## 2. Decisions, cluster by cluster

The rule behind every decision: a Tines action receives one event and emits one; a Windmill step is
code with real control flow. So (a) fan-out and fan-in become loops and branches, (b) "request,
check status, transform" becomes one script, and (c) actions that only move or rename data between
other actions have no equivalent and are deleted. Resulting flow:

```
loop_depots (forloopflow)
  fetch_excursions    script
  loop_excursions (forloopflow)
    lookup_carrier    script
    lookups (branchall, parallel): lab_report | claims | sensor_audit | chart
    decide            script
    send_if_bad (branchone): send_report
  save_cursor         script
```

### 2.1 Constant + explode -> flow input + for-loop

`a01 depots` has `payload: ["north-quay", "ridgeway", "old-mill"]`; `a02 explode_depots` has
`path: =depots` and `to: code`.

```yaml
# flow.yaml: one entry of schema.properties, then the first item of value.modules
depot_codes: {type: array, items: {type: string}, default: [north-quay, ridgeway, old-mill]}
- id: loop_depots
  value:
    type: forloopflow
    iterator: {type: javascript, expr: "flow_input.depot_codes"}
    skip_failures: true
    parallel: false
    modules: []   # the steps of 2.2 to 2.9
```

Why: a hardcoded list is configuration, so it becomes a flow input with the story's values as the
default. Explode becomes `forloopflow`; everything downstream of the explode goes *inside* the
loop, and `explode_depots.code` becomes `flow_input.iter.value`. `skip_failures: true` because in
Tines one failing event never stops its siblings.

### 2.2 Cursor read + HTTP + status trigger + filter -> one script

```
a35 since_parameter
  payload: =IF(IS_BLANK(LOCAL.last),"","&since="&LOCAL.last)
  local: {"last": "=GET(RESOURCE.excursion_cursor, explode_depots.code)"}
a03 get_excursions
  url: https://tracker.example.com/v2/depots/<<explode_depots.code>>/excursions?state=open&limit=200<<since_parameter>>
  headers: {"X-Auth-Token": "<<CREDENTIAL.tracker_api_token>>"}
a04 _200
  rules: [{"type": "field==value", "value": "200", "path": "<<get_excursions.status>>"}]
a05 not_defrost
  payload: |
    =REJECT(get_excursions.body.items,
      LAMBDA(item,
        FILTER(MAP(item.causes, "code"), LAMBDA(code, INDEX_OF(code, "defrost")))
        |> SIZE(%) > 0))
```
```ts
// fetch_excursions.ts (trimmed): main(depot, api_token, cursor_var)
const cursor = JSON.parse(await wmill.getVariable(cursor_var));                        // a35
const last = cursor[depot];
const since = last === undefined || last === null ? "" : `&since=${last}`;
const res = await fetch(
  `https://tracker.example.com/v2/depots/${depot}/excursions?state=open&limit=200${since}`,
  { headers: { "X-Auth-Token": api_token } });                                         // a03
if (res.status !== 200) throw new Error(`tracker returned ${res.status}`);             // a04
const items = (await res.json())?.items ?? [];
const alerts = items.filter((item) =>                                                  // a05
  !(item.causes ?? []).some((c) => String(c?.code ?? "").includes("defrost")));
const seconds = alerts.map((a) => Math.floor(new Date(a.raised_at).getTime() / 1000));
return { depot, alerts, latest_s: seconds.length ? Math.max(...seconds) : null };
```

- **A status trigger with a single path** means "stop this event otherwise". In a script that is
  `throw`; the loop's `skip_failures` then stops this depot only, as in Tines.
- **A transform that only builds a string or filters a list** for the next action is a line of code
  in that step, not a step of its own.
- **The formula** uses `INDEX_OF` as a condition. In Tines a miss is `NULL` (falsy) and a hit is a
  position, where `0` is truthy. JavaScript `indexOf` is wrong on both ends (`0` falsy, `-1`
  truthy), so translate the intent, which the author note confirms: drop items where any cause code
  contains `defrost`. When a formula is oddly built, say in the notes how you read it.
- `a10 rows` (`payload: =not_defrost`) only renames a value. `a09 not_empty` guards against an
  empty list, and a for-loop over `[]` does nothing. Both deleted.
- Do not wrap the cursor read in `try/catch`: a missing variable or a permission error would then
  look like a first run and refetch everything. The user creates the variable with `{}` (section 3).

### 2.3 Second explode -> nested for-loop

`a11 explode_excursions` becomes `loop_excursions`, nested in `loop_depots`, with
`iterator: {type: javascript, expr: "results.fetch_excursions.alerts"}` and the same
`skip_failures: true`. `explode_excursions.alert` becomes `flow_input.iter.value` (inside the
inner loop this is the alert, not the depot).

Two pitfalls belong to this shape. Both look reasonable, and neither is in the flow above:

- **A throttle on a side branch is not a throttle on the main work.** The graph shows `a36` under
  `a11` next to `a12`, not above it: the story looks up every alert at full speed. Do not turn that
  throttle into a `sleep` or a limit on `loop_excursions`.
- **A cap on per-run work loses data when the cursor moves on.** With a limit such as "at most 10
  alerts per depot per run", and a cursor that still jumps to the latest timestamp of the batch,
  the alerts beyond the cap are never fetched again. A cursor may only advance to the last item
  that was processed. Report any cap, and anything else the story does not do (deduplicating
  alerts, for example), with its consequence.

### 2.4 Throttle + compare + HTTP to the Tines API -> one cursor-write step

```
a36 slow_down     capacity: "4"    interval: minute
a37 latest_seen
  payload: {"next": "=MAX(LOCAL.cursor_s, LOCAL.alert_s) + 1"}
  local:
    cursor_s: =GET(RESOURCE.excursion_cursor, explode_depots.code) |> DEFAULT(%, 0) |> NUMBER(%)
    alert_s: =DATE(explode_excursions.alert.raised_at, "%s") |> NUMBER(%)
a38 save_cursor
  url: https://tenant.example.com/api/v1/global_resources/4410/replace
  payload: {"key": "=explode_depots.code", "value": "<<latest_seen.next>>"}
  headers: {"x-user-token": "<<CREDENTIAL.tenant_api_token>>"}
```
```ts
// save_cursor.ts (trimmed): the step after loop_excursions, still inside loop_depots.
// Its latest_s input is {type: javascript, expr: "results.fetch_excursions.latest_s"}.
if (latest_s === null) return { depot, saved: null };     // no alert: the story wrote nothing either
const cursor = JSON.parse(await wmill.getVariable(cursor_var));
cursor[depot] = Math.max(Number(cursor[depot] ?? 0), latest_s) + 1;                    // a37
await wmill.setVariable(cursor_var, JSON.stringify(cursor));                           // a38
```

Why: the story writes the resource once per alert event, and the throttle only rate-limits those
writes. Per-event writes exist because Tines has no "after the loop" point. Windmill has one, so
the latest timestamp is computed once in `fetch_excursions` and written once per depot, and the
throttle has nothing left to protect. An HTTP request to the Tines tenant's own API is platform
plumbing: replace it with the Windmill equivalent and drop its credential. Keep the formula's
arithmetic (`max(stored, alert) + 1`) exactly.

Check what the write depends on. In the story the cursor branch is a sibling of the lookup
branch, so the cursor advances even when a lookup fails. Here `loop_excursions` has
`skip_failures: true`, so `save_cursor` also runs after a failed alert. That keeps the story's
behaviour, and it means a failed alert is not retried: write it in the notes. If
`fetch_excursions` throws, the iteration stops and the cursor stays, as in the story.

### 2.5 Parallel fan-out -> `branchall`

`a12 look_up_carrier` links to four actions. Its result is needed later and the four lookups are
independent, so `lookup_carrier` is a plain step followed by:

```yaml
- id: lookups
  value:
    type: branchall
    parallel: true
    branches:
      - summary: Lab report
        skip_failure: true
        modules:
          - id: lab_report
            value:
              type: rawscript
              language: bun
              content: "!inline lab_report.ts"
              input_transforms:
                alert: {type: javascript, expr: "flow_input.iter.value"}
                api_key: {type: static, value: "$var:f/cold_chain/lab_api_key"}
      # claims, sensor_audit, chart: three more branches of the same shape
```

`skip_failure: true` on each branch because in Tines a failed branch does not stop its siblings.
Each branch script returns an object with a `source` field (`"lab"`, `"claims"`, ...) so the next
step finds results by name, not by array position.

### 2.6 HTTP + 404 -> delay -> back-link -> retry inside the script

```
a14 _404   (both rules must match)
  rules:
    - {"type": "formula", "value": null, "path": "=IS_BLANK(_404.rule_matched)"}
    - {"type": "field==value", "value": "404", "path": "<<get_batch_report_from_lab.status>>"}
a15 wait_for_lab   seconds: "45"      links: in a14 | out a13
```
```ts
// lab_report.ts (trimmed)
let res = await call();
if (res.status === 404) { await sleep(45_000); res = await call(); }
const counts = (res.status === 200 ? await res.json() : null)?.result?.counts ?? {};
return { source: "lab", status: res.status,
         failed: counts.failed ?? null, borderline: counts.borderline ?? null };
```

Read the loop guard first. `IS_BLANK(_404.rule_matched)` is true only while this trigger has not
yet fired for the event, so the loop runs **at most once**: an `if`, not a `while`. A `CYCLE` in
the graph is always a retry or poll loop; find its exit condition and its bound, and add a bound
when the story has none. Return only the fields later steps use, not the whole response body.

### 2.7 HTTP + trigger chain feeding nothing -> fold in or drop

`a18 check_claims_register` -> `a19 _200` -> `a20` -> `a21 claim_summary`, and `claim_summary` is
never read. The placeholder `a22` on the no-match link is never read either. So `claims` is one
script that returns `open_claims`; `a20`, `a21` and `a22` are dropped.

Why keep the request at all? Because the message built in `a28` contains
`<<check_claims_register.body.summary.open_claims>>`, and the digest of `a28` marks that reference
on its `uses:` line: `a18 check_claims_register (NOT UPSTREAM of this action)`. `a18` is on a
sibling branch, so in Tines the pill most likely renders empty. In Windmill `results.lookups` holds
every branch, so `decide` can print the number. That is a behaviour difference: list it, and list
the Tines behaviour as not verified.

### 2.8 Group action -> one script

A group is a sub-story with one input and one output: a function. `--group a24` prints:

```
a24.09 input [group_input]
  a24.01 search_charts_for_sensor [http_request]
    a24.03 chart_found [trigger]  FAN-OUT x2
      a24.02 get_chart_job [http_request]
        a24.10 output [group_output]  JOIN x3  END
      (no-match) a24.04 no_chart [trigger]
        a24.05 submit_render_job [http_request]
          a24.11 accepted [trigger]  FAN-OUT x2
            a24.06 wait_for_render [event_transform/delay]  JOIN x2  CYCLE
              a24.07 get_chart_job [http_request]  CYCLE
                a24.08 still_rendering [trigger]  FAN-OUT x2  CYCLE
                  ^ a24.06 wait_for_render  (CYCLE: loops back)
                  (no-match) ^ a24.10 output  (JOIN: shown above)
            (no-match) ^ a24.10 output  (JOIN: shown above)
```

In `chart.ts` this is straight-line code: search; `if (results.length > 0)` get the job, `else`
submit a render job, `if (submit.status !== 200) return`, then `do { sleep(10_000); get the job }
while (job.status === 404)`. The story's poll loop has no limit; the script stops after 30 polls
and throws. The actions after the group, `a25 _200 -> a26 retrieve_chart_image -> a27 _200`, use
only the group's output, so they are folded into the same script, which returns
`{ source: "chart", filename, base64 }`. Check inner HTTP options too: `a24.05` has
`retry_on_status: ["429"]`, which a faithful script must also handle.

`a23 sensor_audit` is the same with two triggers on one field: `a23.02 no_audit_yet` (status `204`)
and `a23.10 audit_exists` (status `200`) are an if / else-if. Each mid-chain `200` trigger is an
early return. A `delay` action is a `sleep`. The parent never reads the group's output, but the
group sends a `POST`, so the step stays for its outside effect.

### 2.9 Trigger pair + tag + implode + untag + guard -> `decide` + `branchone`

The largest deletion: eight actions (two triggers, two tags, the implode, two untags and a guard)
become one boolean and one branch.

```
a16 / a17: both link to a28
  rules: [{"type": "field>value", "value": "0", "path": "=get_batch_report_from_lab.body.result.counts.failed"}]
  rules: [{"type": "field>value", "value": "2", "path": "=get_batch_report_from_lab.body.result.counts.borderline"}]
a28 and a29 tag_for_join: tag each side
  payload: {"data": "<h2>Temperature excursion on shipment ...", "part": "message"}
  payload: {"data": "=retrieve_chart_image.body", "part": "chart"}
a30 join_parts: wait for both sides
  item_path: =tag_for_join   guid_path: =explode_excursions.alert.id   size_path: =2   seconds: 40
a31 message, a32 chart: untag
  payload: =WHERE(join_parts,"part","message") |> FIRST(%).data
a33 message_present: only send when the lab side arrived
  rules: [{"path": "=SIZE(message)", "type": "field>value", "value": "0"}]
```
```yaml
# decide: a rawscript like lab_report in 2.5. Its input_transforms, besides alert:
#   carrier: {type: javascript, expr: "results.lookup_carrier"}
#   lookups: {type: javascript, expr: "results.lookups"}
- id: send_if_bad
  value:
    type: branchone
    branches:
      - summary: Lab results are bad
        expr: "results.decide.send === true"
        modules: []   # one step: send_report
    default: []
```
```ts
// decide.ts (trimmed)
const by = (name: string) => (lookups ?? []).find((r) => r?.source === name) ?? null;
const lab = by("lab"), claims = by("claims"), chart = by("chart");
const send = Number(lab?.failed ?? 0) > 0 || Number(lab?.borderline ?? 0) > 2;        // a16 OR a17
return { send, subject: "Cold chain: excursion needs review", html,       // html: the text of a28
         attachment: chart?.base64 ? { filename: chart.filename, base64: chart.base64 } : null };
```

Why: the lab result and the chart image ran in parallel in Tines and had to be re-joined, so the
author tagged each side, imploded them, untagged them, then checked the message side was present.
In Windmill `results.lookups` already holds every branch's result, so the join is free. What
survives is the *decision* (`failed > 0 OR borderline > 2`) and the *content*: keep the subject of
`a34` and the text of `a28` as they are. A failed branch leaves `null` or an error object in its
slot, which is why `decide` searches by `source`. `a34` (send email) has no built-in equivalent; it
becomes `send_report`, a script using `nodemailer` and an `smtp` resource, with the story's
`recipients` as the default of the `report_to` flow input.

## 3. Credentials, resources and state

The `GLOBALS` block of the digest lists every `CREDENTIAL.` and `RESOURCE.` with the actions that
use it, groups and action inputs included.

| In the story | In Windmill | How the step gets it |
|---|---|---|
| `CREDENTIAL.tracker_api_token` (a03) | secret variable `f/cold_chain/tracker_api_token` | `fetch_excursions`: `api_token` |
| `CREDENTIAL.carrier_directory_key` (a12) | secret variable `f/cold_chain/carrier_directory_key` | `lookup_carrier`: `api_key` |
| `CREDENTIAL.lab_api_key` (a13) | secret variable `f/cold_chain/lab_api_key` | `lab_report`: `api_key` |
| `CREDENTIAL.claims_register_key` (a18) | secret variable `f/cold_chain/claims_register_key` | `claims`: `api_key` |
| `CREDENTIAL.sensor_audit_key` (a23.01, ...) | secret variable `f/cold_chain/sensor_audit_key` | `sensor_audit`: `api_key` |
| `CREDENTIAL.chart_service` (only in the inputs of a24) | secret variable `f/cold_chain/chart_service` | `chart`: `api_key` |
| `CREDENTIAL.tenant_api_token` (a38) | **nothing**: only used to call the Tines API | - |
| `RESOURCE.excursion_cursor` (a35, a37; written by a38) | non-secret variable `f/cold_chain/excursion_cursor`, JSON `{depot_code: epoch_seconds}` | `fetch_excursions` and `save_cursor`: `cursor_var` |
| built-in email sender (a34) | an `smtp` resource | flow input `smtp` (`format: resource-smtp`) |

The pattern for every secret: the step's transform is a static `"$var:<path>"`, which Windmill
replaces with the value at run time. The secret is never a flow input and is never returned in a
step result. Keep the Tines credential name as the last path segment so the user can match them
one to one. If the paths differ per environment, make the path a flow input with a default instead
and read it in the script with `wmill.getVariable`.

```yaml
api_key: {type: static, value: "$var:f/cold_chain/lab_api_key"}       # the value: read only
cursor_var: {type: static, value: f/cold_chain/excursion_cursor}      # the path: the script writes it
```

State: a resource read with `GET(RESOURCE.x, key)` and written through the Tines API is a key-value
store. Two steps share it (read first, write last), so step state (`getState`) does not fit; it is
one JSON variable, read in `fetch_excursions` and written in `save_cursor`. It must be non-secret,
and the user must be told to create it with the value `{}`. A whole-map read-modify-write is only
safe while nothing else writes it: `loop_depots` is `parallel: false`, and the schedule sets
`no_flow_overlap: true`.

Hardcoded values that became inputs: the depot codes and the recipient. The schedule is not part
of the flow: write `f/cold_chain/review_excursions.schedule.yaml` next to the flow folder. The
Tines cron has 5 fields and Windmill needs 6, seconds first: `schedule: "0 */20 * * * *"`, with
`timezone: America/Toronto` kept and `args: {smtp: "$res:f/cold_chain/smtp"}`.

## 4. What was not ported or was changed, and how to report it

Two files carry this. The first is `tines_action_map.md` in the flow folder: one line per action
of the workflow, created with `--map-template` and filled in while writing the flow (excerpt):

```
# workflow: w01
a01 -> flow_input.depot_codes   # depots [event_transform/message_only]
a02 -> loop_depots   # explode depots [event_transform/explode]
a03 -> fetch_excursions   # get excursions [http_request]
a04 -> fetch_excursions   # 200 [trigger]
a09 -> DROPPED: guard against an empty list; a loop over [] does nothing   # not empty [trigger]
a10 -> DROPPED: only renames not_defrost   # rows [event_transform/message_only]
a16 -> decide   # failed tests above 0 [trigger]
a22 -> DROPPED: default placeholder on the no-match link   # Event Transform Action [event_transform/message_only]
a23.13 -> DROPPED: group plumbing   # Input [group_input]
a24.07 -> chart   # Get chart job [http_request]
a30 -> DROPPED: join plumbing; decide reads results.lookups   # join parts [event_transform/implode]
a36 -> save_cursor   # slow down [event_transform/throttle]
```

An action whose work moved into a step is mapped to that step, even when little of it is left
(`a36`). `DROPPED` is for actions with nothing left, and always has a reason.
`validate_flow.py <flow folder> --story S --workflow w01` then reports `47 mapped, 9 dropped,
0 not accounted for (of 56)` and ends with `RESULT: OK`.

The second file is `review_excursions.NOTES.md`, with the five parts SKILL.md step 8 asks for.
Every deletion and every change in behaviour goes into it. Two entries, as they should be written:

> - **`join parts` (a30)** waited for 2 of 2 parts, at most 40 s. The parallel `lookups` step
>   replaces it and waits until the `chart` branch ends (up to 30 polls). The email can therefore
>   be later than in Tines, and it is still sent, without an attachment, when the chart fails.
> - **`slow down` (a36)** limited cursor writes to 4 per minute. The flow writes the cursor once
>   per depot per run, so there is no rate limit. The lookups were never throttled in the story.

Copy the form: name the Tines action and its id, say what the story did, say what the flow does
instead, and state the consequence the user will notice. For this story the notes cover:

- **Setup:** the seven variables of section 3 (secret or not, initial value), the `smtp` resource,
  the schedule file.
- **Mapping:** steps and the actions each one replaces, taken from the map.
- **Behaviour differences:** the join and the throttle (above); the cursor written once per depot
  instead of once per alert event; a failed tracker call now fails that depot's iteration visibly
  instead of silently stopping; the open-claims number now appears in the email (2.7); the chart
  poll loop is bounded. Kept from the story and worth saying: a failed alert is not retried.
- **Not ported:** the six disabled actions (the `door open` and `power loss` chains); the unlinked
  `Event Transform Action` (a42); `a20`, `a21`, `a22`; `CREDENTIAL.tenant_api_token`.
- **Not verified:** the flow has not been run; how Tines renders a pill that points at a sibling
  branch; the reading of the `INDEX_OF` filter in `a05`.

Anything capped, bounded or retried differently needs its consequence: what is skipped, and is it
picked up on a later run? Do not write "same as the story" unless you checked it against the links.

## 5. Checklist for any story

1. Which action is marked `ENTRY` (schedule, webhook, page, send-to-story entry)? Note every cron
   line with its timezone.
2. Which actions are `DISABLED`, `UNREACHABLE` or under `NOT TRIGGERED`? List them; do not port them.
3. For each leaf: `END` with an outside effect, or `DEAD-END` whose output nobody reads?
4. Which actions are `FAN-OUT` (several children) or `JOIN` (several parents: OR, or an implode)?
5. Are there `(no-match)` links? `CYCLE` markers? For each cycle: exit condition and bound.
6. Are there duplicate reference names? Resolve each reference by the ids on the `uses:` line.
7. Is a reference marked `NOT UPSTREAM`? Decide what the step should see, and report it.
8. For each group: print its inside, and read its `inputs` line if its options are empty.
9. Explode (with or without implode) -> `forloopflow`. What belongs inside the loop?
10. HTTP + status trigger(s) + transform -> one script. Single-path trigger = throw or early return;
    two triggers on one field = if/else.
11. Fan-out to independent actions -> `branchall` with `skip_failure`; give each result a `source`.
12. Tag + implode + untag -> delete; read the branch results directly.
13. Trigger(s) before a side effect -> a boolean from a script + `branchone`.
14. Delay or throttle: which branch is it on, what does it protect, and does that reason still exist?
15. Resource read, and written through the Tines API -> a non-secret variable; write once, after
    the work. Never let a cap or an early stop move a cursor past items that were not processed.
16. Does an action only rename, guard against empty, or build a string? Delete it and inline.
17. Does each script return only what later steps use?
18. Every `CREDENTIAL.` -> a secret variable; every `RESOURCE.` -> a variable or resource; values the
    user will want to change -> flow inputs with the story's value as default.
19. Is every action of the workflow in `tines_action_map.md`, mapped or `DROPPED` with a reason,
    and does `validate_flow.py` end with `RESULT: OK`?
20. Does the notes file list every behaviour difference with its consequence, and the full setup:
    variables (secret or not, initial value), resources, schedule?
