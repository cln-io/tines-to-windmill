# Windmill flow format (OpenFlow) reference

How to hand-write a Windmill flow as files that `wmill flow push` / `wmill sync push` accept. Field names follow `openflow.openapi.yaml` v1.876 (windmill-labs/windmill). Copy the examples and change only names, expressions and code. Anything marked **unverified** is listed in section 13.

Contents: 1 Files on disk · 2 `flow.yaml` skeleton · 3 Script files (`!inline`) · 4 Module shape and ids ·
5 Module types · 6 Expressions and `input_transforms` · 7 Per-module settings · 8 Input `schema` ·
9 Variables, resources, state · 10 Triggers · 11 Error handling · 12 Invalid-flow checklist · 13 Unverified

## 1. Files on disk

```
f/<folder>/<flow_name>.flow/      # flow path in Windmill = f/<folder>/<flow_name>
  flow.yaml                       # the flow definition
  fetch_items.ts                  # one file per rawscript step, named <step_id>.ts
  send_report.ts
f/<folder>/<flow_name>.schedule.yaml      # optional trigger files (section 10)
```

- The folder suffix is `.flow` unless the project's `wmill.yaml` has `nonDottedPaths: true`; then it is `__flow`. New projects made by `wmill init` set it to `true`. No `wmill.yaml`: use `.flow`.
- Paths start with `f/<folder>/` (shared folder) or `u/<username>/` (one user's space).
- Commands (run only when asked; never deploy on your own): `wmill lint <flow folder>` checks files offline; `wmill flow preview <flow folder> -d '{"input": "value"}'` runs local files without deploying; `wmill flow push <flow folder> f/<folder>/<flow_name>` deploys one flow; `wmill sync push` deploys the tree.

## 2. `flow.yaml` skeleton

```yaml
summary: Short title of the flow
description: |
  What the flow does and which variables/resources it needs.
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  required: [items]
  properties:
    items:
      type: array
      items: {type: string}
value:
  modules:
    - id: fetch_items
      summary: Fetch details for the items
      value:
        type: rawscript
        language: bun
        content: "!inline fetch_items.ts"
        input_transforms:
          items: {type: javascript, expr: "flow_input.items"}
```

The top level has only `summary` (required), `description`, `schema`, `value` (required). Everything else goes inside `value`. Leave out keys you do not need; do not invent keys.

| Key in `value` | Type | Meaning |
|---|---|---|
| `modules` | list, required | Steps, run in order. The flow result is the last step's result. |
| `failure_module` | one module | Error handler with `id: failure` (section 11). Not an item of `modules`. |
| `preprocessor_module` | one module | Reshapes trigger payloads, `id: preprocessor` (section 10). Not an item of `modules`. |
| `same_worker` | boolean | All steps run on one worker and can share files in `./shared/`. |
| `flow_env` | map | Constants read as `flow_env.NAME` in expressions. Values may be `"$var:<path>"` / `"$res:<path>"`. |
| `concurrent_limit`, `concurrency_time_window_s` | number | At most N runs of this flow per window of seconds. |
| `concurrency_key`, `on_concurrency_limit` | string | Grouping key; `queue` (default) or `fail` when over the limit. |
| `timeout` | integer | Wall-clock limit in seconds for the whole run. |
| `skip_expr` | JS string | If true for the flow inputs, the flow does not run. |
| `early_return` | step id | A sync webhook answers with this step's result while the flow continues. |

Rarely needed, also in `value`: `cache_ttl` (seconds), `priority` (number), `debounce_delay_s`, `debounce_key`.

## 3. Script files (`!inline`)

Confirmed in the CLI source. Put each rawscript's code in its own file in the flow folder and point
`content` at it, as in section 2: `content: "!inline fetch_items.ts"`. Always do this; do not embed code in the YAML.

- The value is a **double-quoted string**: `!inline`, one space, one path. Unquoted (`content: !inline x.ts`) is a YAML tag and `wmill lint` rejects it.
- The path is relative to the flow folder, uses `/`, and has no spaces.
- Name the file `<step_id>.<ext>`: `.ts` for `bun`, `.py` for `python3`, `.sh` for `bash`, `.go` for `go`, `.pg.sql` for `postgresql`. Do not put `.inline_script.` in the name.
- Keep `language:` in the YAML; it is not derived from the extension.
- A referenced file that does not exist makes the push fail. Write every file you reference.
- Do not write a `lock:` key; `wmill generate-metadata` adds dependency locks later.
- Works the same in `failure_module`, `preprocessor_module`, and steps nested in loops and branches.
- Embedded code (`content: |` followed by indented source) is also valid, but indentation errors are easy.

## 4. Module shape and ids

Every step, at any depth, is `id` + `value`, plus optional `summary` and the settings of section 7. Settings are siblings of `id` and `value`, never inside `value`.

- Ids are unique across the whole flow, including steps inside loops and branches.
- Use lowercase letters, digits, underscores, starting with a letter: `fetch_items`. The spec allows hyphens, but `results.my-id` is not valid JavaScript, so never use them.
- Never use these ids for normal steps: `failure`, `preprocessor`, `Input`, `Result`, `Trigger`, `state`, `ctx`, `do`, `bg`, `if`, `else`, `for`, `while`, `delete`, `new`, `in`, `as`.

## 5. Module types

Each YAML example is one or more items of a `modules:` list.

### 5.1 `rawscript`: inline code (use for most steps)

Required: `type`, `language`, `content`, `input_transforms` (write `input_transforms: {}` if `main` takes nothing).

```yaml
- id: fetch_user
  summary: Fetch one user from the API
  value:
    type: rawscript
    language: bun
    content: "!inline fetch_user.ts"
    input_transforms:
      user_id: {type: javascript, expr: "flow_input.user_id"}
      api_key: {type: static, value: "$var:f/acme/api_key"}
      limit: {type: static, value: 100}
```

```ts
// fetch_user.ts
export async function main(user_id: string, api_key: string, limit: number = 100) {
  const res = await fetch(`https://api.example.com/users/${user_id}?limit=${limit}`, {
    headers: { Authorization: `Bearer ${api_key}` },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return await res.json();
}
```

- Write exactly `export async function main(...)` with plain named parameters. Do not call it.
- Arguments are matched **by name**: each `input_transforms` key must equal a parameter name. A parameter with no entry gets `undefined` (or its default).
- The return value must be JSON-serialisable; it becomes `results.<id>`.
- To fail the step, `throw`. Do not return an error object to signal failure.
- `import` any npm package by name; it is installed automatically. `fetch` and `Buffer` are built in.
- To skip TLS certificate verification for **one** request, pass Bun's `tls` option to that `fetch`: `await fetch(url, { tls: { rejectUnauthorized: false } })`. `language: bun` only. Never switch verification off for the whole script.
- One id for the whole flow run, the same in every step: `process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID`. `WM_JOB_ID` alone is the step's own job id and changes at every step.
- `language` values: `bun` (default), `deno`, `bunnative`, `nativets`, `python3`, `go`, `bash`, `powershell`, `php`, `rust`, `csharp`, `java`, `ruby`, `nu`, `rlang`, `ansible`, `postgresql`, `mysql`, `mssql`, `oracledb`, `bigquery`, `snowflake`, `duckdb`, `graphql`.
- Parameter types become the step's input schema (they describe the form; they do not convert values): `string`/`number`/`boolean` map to the same JSON type; `bigint` to `integer`; `"x" | "y"` to a string `enum`; `T[]` to `array`; `object` or `{ k: string }` to `object`; `a?: T` or `a: T = v` makes it optional; `a: RT.Smtp` to `object` with `format: resource-smtp` (section 9).

### 5.2 `script` and 5.3 `flow`: call an existing script or flow by path

Required: `type`, `path`, `input_transforms` (keys are the parameters of that script, or the inputs of that flow).

```yaml
- id: send_email
  value:
    type: script
    path: f/acme/send_email
    input_transforms:
      to: {type: javascript, expr: "flow_input.email_to"}
      subject: {type: static, value: Daily report}
- id: enrich_item
  value:
    type: flow
    path: f/acme/enrich_item
    input_transforms:
      sku: {type: javascript, expr: "results.pick_item.sku"}
```

- `type: flow` runs another flow as a subflow; its result is the subflow's result.
- Hub scripts use `path: hub/<version_id>/<app>/<name>`. Never invent a Hub path or its parameters; use one only if it was given to you. Otherwise write a `rawscript`.

### 5.4 `forloopflow`: run steps once per array element

Required: `type`, `iterator`, `skip_failures`, `modules`.

```yaml
- id: loop_users
  value:
    type: forloopflow
    iterator: {type: javascript, expr: "results.list_users"}
    skip_failures: false
    parallel: false
    modules:
      - id: process_user
        value:
          type: rawscript
          language: bun
          content: "!inline process_user.ts"
          input_transforms:
            user: {type: javascript, expr: "flow_input.iter.value"}
            position: {type: javascript, expr: "flow_input.iter.index"}
```

- `iterator.expr` must return an array. An empty array runs nothing and gives `[]`.
- `results.loop_users` is an array, one entry per iteration, in iterator order. Each entry is the result of the **last** step of that iteration. To keep several values, make the last step return one object.
- `skip_failures: false`: a failed iteration fails the loop and the flow. `true`: the loop carries on and succeeds; the failed iteration's entry is `null` or `{error: ...}` (**unverified** which), so later code must tolerate both.
- `parallel: true` runs iterations concurrently; cap with `parallelism: {type: static, value: 5}`.

### 5.5 `whileloopflow`: repeat until a condition is true

Required: `type`, `skip_failures`, `modules`. No iterator. The stop condition is `stop_after_if` on the loop **module** (sibling of `value`); there `result` is the latest iteration's result.

```yaml
- id: poll_until_done
  stop_after_if: {expr: "result.done === true", skip_if_stopped: false}
  value:
    type: whileloopflow
    skip_failures: false
    max_iterations: 20
    modules:
      - id: check_status
        sleep: {type: static, value: 15}
        value:
          type: rawscript
          language: bun
          content: "!inline check_status.ts"
          input_transforms:
            job_id: {type: javascript, expr: "results.start_job.id"}
            attempt: {type: javascript, expr: "flow_input.iter.index"}
```

- In a while loop `flow_input.iter.value` equals `flow_input.iter.index` (0, 1, 2, ...). It never carries state.
- `results.poll_until_done` is the array of all iteration results. A later step takes the last one: `expr: "results.poll_until_done[results.poll_until_done.length - 1]"`.
- Always set `max_iterations` (or `max_duration_secs`). Reaching it fails the loop with error name `LoopExhausted`.
- To carry state between iterations a step reads its own previous result (`expr: "results.check_status ?? flow_input.start"`); then put `stop_after_if` on that inner step instead.
- `sleep` on the body step pauses between iterations without holding a worker.

### 5.6 `branchone`: if / else-if / else

Required: `type`, `branches`, `default`. Each branch requires `expr` and `modules`.

```yaml
- id: route_by_severity
  value:
    type: branchone
    branches:
      - summary: High severity
        expr: "results.assess.score >= 8"
        modules:
          - id: page_oncall
            value:
              type: rawscript
              language: bun
              content: "!inline page_oncall.ts"
              input_transforms:
                report: {type: javascript, expr: "results.assess"}
    default: []
```

- Branches are tested in order; the first true `expr` runs. If none is true, `default` runs. `default: []` means "do nothing"; the key must still be present.
- `results.route_by_severity` is the result of the last step of the branch that ran. Give all branches the same result shape if a later step reads it.

### 5.7 `branchall`: run every branch

Required: `type`, `branches`. Each branch requires `modules`.

```yaml
- id: enrich
  value:
    type: branchall
    parallel: true
    branches:
      - summary: Price service
        skip_failure: true
        modules:
          - id: price_check
            value:
              type: rawscript
              language: bun
              content: "!inline price_check.ts"
              input_transforms:
                sku: {type: javascript, expr: "flow_input.sku"}
      - summary: stock_check
        skip_failure: true
        modules:
          - id: stock_check
            value:
              type: rawscript
              language: bun
              content: "!inline stock_check.ts"
              input_transforms:
                sku: {type: javascript, expr: "flow_input.sku"}
```

- `results.enrich` is an array, one entry per branch in branch order: `[price_check result, stock_check result]`.
- `skip_failure: true` (singular, per branch) lets the other branches and the flow continue when that branch fails. Without it, one failed branch fails the step.
- Make each branch return a field such as `source: "price_check"` so the next step finds entries by name, not position; a failed branch's entry will not have it.

### 5.8 `identity`: pass the previous result through

```yaml
- id: wait_a_minute
  sleep: {type: static, value: 60}
  value:
    type: identity
```

Returns the previous step's result unchanged. Use it only to carry a `sleep` or as a placeholder.

### 5.9 `aiagent`: LLM step

Required: `type`, `input_transforms`. `provider` is an object, not a resource path.

```yaml
- id: summarise
  value:
    type: aiagent
    input_transforms:
      provider:
        type: static
        value: {kind: openai, resource: "$res:f/ai/openai", model: gpt-4o}
      output_type: {type: static, value: text}
      system_prompt: {type: static, value: You summarise security alerts in two sentences.}
      user_message: {type: javascript, expr: "JSON.stringify(results.assess)"}
    tools: []
```

- `kind`: `openai`, `azure_openai`, `anthropic`, `mistral`, `deepseek`, `googleai`, `groq`, `openrouter`, `togetherai`, `customai` (any OpenAI-compatible endpoint), `aws_bedrock`.
- Structured output: add `output_schema: {type: static, value: <JSON Schema object>}`. Tools (modules with `value.tool_type: flowmodule`) and `type: aidecision` also exist; use them only if asked.

## 6. Expressions and `input_transforms`

Two kinds: `{type: static, value: <any YAML value>}` and `{type: javascript, expr: "<JavaScript>"}`.

```yaml
input_transforms:
  channel: {type: static, value: "#alerts"}
  options:
    type: static
    value: {retries: 3, tags: [a, b]}
  text: {type: javascript, expr: "`Found ${results.count_hits.total} hits for ${flow_input.sku}`"}
  payload: {type: javascript, expr: "({ id: flow_input.id, rows: results.fetch_rows.filter((r) => r.ok) })"}
```

In scope inside any `expr`:

| Name | Value | Where |
|---|---|---|
| `flow_input.<name>` | A flow input | Everywhere, also inside loops and branches |
| `results.<step_id>` | Result of an earlier step | See scope rules below |
| `previous_result` | Result of the step just before this one | Any step |
| `flow_input.iter.value` | Current element | Inside a `forloopflow` |
| `flow_input.iter.index` | Current index from 0 | Inside a for or while loop |
| `flow_input.iter_parent.value` | Element of the outer loop | Inside a loop nested in a loop |
| `flow_env.<NAME>` | Value from `value.flow_env` | Everywhere |
| `variable('f/x/name')`, `resource('f/x/name')` | Variable value (string), resource value (object) | Everywhere; no `await` needed |
| `result` | This step's own result | Only `stop_after_if`, `stop_after_all_iters_if`, `retry_if` |
| `error` | Error of the failed step | Only `failure_module` inputs and `retry_if` |
| `resume`, `resumes`, `approvers` | Approval payload(s) | Only the step right after a `suspend` step |

Scope rules for `results.<step_id>`:

- Only steps that have **already run** are visible. Never reference a later step.
- A step inside a loop or branch may read earlier steps outside it and earlier steps in its own body.
- A step **outside** a loop or branch must not read ids of steps inside it. Read `results.<loop_id>` (array) or `results.<branch_id>` instead.
- A step in one branch cannot read steps of a sibling branch.
- `preprocessor_module` cannot read `results`; `failure_module` reads `error`.

Writing `expr`:

- **Always put `expr` in double quotes**, and use single quotes or backticks for JavaScript strings inside it: `expr: "results.a.kind === 'email'"`. This avoids every YAML quoting problem.
- One JavaScript expression. For several statements, end with `return`: `expr: "const xs = results.a.items; return xs.filter((x) => x.ok).length"`.
- Predicates (`stop_after_if`, `skip_if`, branch `expr`) must be a single expression.
- Wrap an object literal in parentheses: `"({ a: 1 })"`.
- Guard values that may be missing: `"results.lookup?.city ?? 'unknown'"`.
- A static string that is exactly `"$res:<path>"` or `"$var:<path>"` is replaced at run time by the resource object or the variable value. It must be the whole string.

## 7. Per-module settings

All are siblings of `id` and `value`. The example is valid as written; keep only what you need.

```yaml
- id: call_api
  retry:
    constant: {attempts: 3, seconds: 10}
    exponential: {attempts: 3, multiplier: 2, seconds: 3, random_factor: 20}
    retry_if: {expr: "error.message.includes('429')"}
  timeout: {type: static, value: 120}
  sleep: {type: static, value: 30}
  skip_if: {expr: "flow_input.dry_run === true"}
  stop_after_if: {expr: "result.items.length === 0", skip_if_stopped: true}
  continue_on_error: false
  cache_ttl: 300
  priority: 10
  delete_after_secs: 3600
  mock: {enabled: false, return_value: {items: []}}
  value:
    type: rawscript
    language: bun
    content: "!inline call_api.ts"
    input_transforms: {}
```

| Setting | Behaviour |
|---|---|
| `retry.constant` | Retry `attempts` times, `seconds` apart. |
| `retry.exponential` | Then `attempts` more; retry n waits `multiplier × seconds^n` s; `random_factor` is jitter 0-100 %. |
| `retry.retry_if` | Optional. Retry only when true; sees `error` and `result`. |
| `timeout` | Seconds before the step is cancelled and fails. |
| `sleep` | Seconds to wait **after** this step, before the next. Holds no worker. |
| `skip_if` | Checked before the step. If true the step does not run; its result is the previous step's result. |
| `stop_after_if` | Checked after the step with `result`. If true: a top-level step stops the flow there as a success; a step in a for loop breaks that loop only; on a while-loop module it ends the loop. |
| `skip_if_stopped` | `true` labels the stopped run "skipped" in the runs list. A label only. |
| `stop_after_if.error_message` | A string makes the stop a **failure** with that message. Not with `skip_if_stopped: true`. |
| `stop_after_all_iters_if` | Same shape; on a loop module only; checked once after all iterations. |
| `continue_on_error` | `true`: if the step fails the flow continues and `results.<id>` is `{error: {...}}`. |
| `cache_ttl` | Seconds to reuse the result for identical inputs. |
| `mock` | `enabled: true` returns `return_value` without running the step. Keep `false` in delivered flows. |
| `priority` | Higher runs first. Leave out unless asked. |
| `delete_after_secs` | Delete the step's args, result and logs N seconds after it ends. The older boolean `delete_after_use` is not in the spec. |

`timeout`, `sleep` and `parallelism` take a transform object (static or javascript), never a bare number.

### Approval and wait-for-callback steps (`suspend`)

A step with `suspend` runs its script, then the flow pauses until `required_events` resume requests arrive. The script must create the resume URLs and send or return them. Never use `type: identity` here.

```yaml
- id: ask_approval
  suspend:
    required_events: 1
    timeout: 86400
    resume_form:
      schema:
        type: object
        properties:
          comment: {type: string}
  value:
    type: rawscript
    language: bun
    content: "!inline ask_approval.ts"
    input_transforms:
      subject: {type: javascript, expr: "results.assess.subject"}
```

```ts
// ask_approval.ts
import * as wmill from "windmill-client";

export async function main(subject: string) {
  const urls = await wmill.getResumeUrls("approver");
  // urls.approvalPage = page with the form; urls.resume / urls.cancel = request these to continue / reject.
  // Send them by email, Slack, etc. here.
  return { subject, ...urls };
}
```

- `suspend.timeout` is in seconds (default 1800). On timeout or cancel the flow fails, unless `continue_on_disapprove_timeout: true`; then the next step sees `resume.error.name` equal to `SuspendedTimedOut` or `SuspendedDisapproved`.
- The JSON body POSTed to `urls.resume` (or the form values) is `resume` in the **next** step's transforms: `expr: "resume?.comment ?? ''"`. The approver's name is `expr: "approvers[0]"`.
- To wait for an external callback, give `urls.resume` to the other system.

## 8. Input `schema`

Standard JSON Schema for an object. Every `flow_input.<name>` you use must be a property here.

```yaml
schema:
  $schema: https://json-schema.org/draft/2020-12/schema
  type: object
  order: [sku, mode, max_items, recipients, smtp]
  required: [sku, smtp]
  properties:
    sku: {type: string, description: SKU to check}
    mode: {type: string, enum: [fast, full], default: fast}
    max_items: {type: integer, default: 10}
    recipients: {type: array, items: {type: string}, default: []}
    smtp: {type: object, format: resource-smtp, description: SMTP resource used to send mail}
```

- Types: `string`, `number`, `integer`, `boolean`, `array` (with `items`), `object` (with `properties`).
- `default` is used when the caller omits the input. Give every non-required input a default.
- `order` is optional and only sets the form layout.
- `type: object` + `format: resource-<type>` makes a resource picker. Callers pass the string `"$res:<path>"`; steps receive the resource's **value object**. `<type>` must exist in the workspace.
- String `format` values the form understands: `email`, `uri`, `uuid`, `ipv4`, `date-time`, `yaml`, `sql`.
- No inputs: `schema: {$schema: "https://json-schema.org/draft/2020-12/schema", type: object, properties: {}, required: []}`.

## 9. Variables, resources, state

| Thing | Holds | Path | File in the sync tree |
|---|---|---|---|
| Variable | One string; `is_secret: true` encrypts it | `f/<folder>/<name>` or `u/<user>/<name>` | `<path>.variable.yaml` |
| Resource | A JSON object of one `resource_type` | same | `<path>.resource.yaml` |

```yaml
# f/acme/api.resource.yaml
value:
  base_url: https://api.example.com
  token: "$var:f/acme/api_token"
resource_type: c_acme_api
description: Acme API connection
```

- Never write a secret's value into any file. Reference it by path and tell the user to create it: `wmill variable add '<value>' f/acme/api_token` (secret by default). Custom resource types are named `c_<name>`.

Three ways to give a step a credential, best first:

1. A flow input with `format: resource-<type>` (section 8), passed on with `expr: "flow_input.smtp"`.
2. A static reference in the step: `value: "$res:f/acme/api"` (object) or `value: "$var:f/acme/api_token"` (string).
3. Reading it in code with `windmill-client` (this example also keeps a polling cursor in state):

```ts
import * as wmill from "windmill-client";

export async function main(smtp: RT.Smtp) {
  const token: string = await wmill.getVariable("f/acme/api_token");
  const api = await wmill.getResource("f/acme/api"); // the value object
  const state = (await wmill.getState()) ?? { cursor: 0 };
  const res = await fetch(`${api.base_url}/events?since=${state.cursor}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const events: { ts: number }[] = await res.json();
  await wmill.setState({ cursor: events.reduce((m, e) => Math.max(m, e.ts), state.cursor) });
  return { events, mail_host: smtp.host };
}
```

- `getVariable(path)` returns a string. `setVariable(path, value)` takes a string and creates the variable (non-secret) if missing. `getResource(path)` returns the object; `setResource(value, path)` writes one.
- `RT.<TypeName>` marks a resource parameter (`RT.Smtp` is type `smtp`, `RT.CAcmeApi` is `c_acme_api`). It is only a type hint; the value is a plain object. If you do not know the fields, use an inline type such as `{ host: string; port: number }`.
- State for polling cursors ("only items newer than the last run"): `getState()` / `setState(value)` keep one JSON value **per step and per trigger**. Another step sees a different state, so read and write the cursor in the same step.
- If two steps must share the cursor (read first, write last after processing succeeded), use a non-secret variable holding JSON: `JSON.parse(await wmill.getVariable(path))` in the first step, `wmill.setVariable(path, JSON.stringify(x))` in the last. Tell the user to create it with the value `{}`.

## 10. Triggers

A flow file never contains its trigger. Triggers are separate files in the sync tree, deployed by
`wmill sync push`. The file name gives the trigger's own path. The block below shows three separate files.

| Starts the flow | File | Flow receives |
|---|---|---|
| Schedule (cron) | `<path>.schedule.yaml` | `args` from the file, as flow inputs |
| Webhook (built in for every flow) | none | JSON body keys, as flow inputs |
| HTTP route (custom URL or auth) | `<path>.http_trigger.yaml` | JSON body keys, as flow inputs |
| Incoming email | `<path>.email_trigger.yaml` | `parsed_email`, `raw_email` |

```yaml
# f/acme/process_orders.schedule.yaml     (cron has 6 fields; seconds come first)
schedule: "0 */15 * * * *"
timezone: Europe/Amsterdam
enabled: true
script_path: f/acme/process_orders
is_flow: true
args: {max_items: 10, smtp: "$res:f/acme/smtp"}
no_flow_overlap: true
---
# f/acme/alerts_in.http_trigger.yaml    (all ten keys are required)
script_path: f/acme/process_alert
is_flow: true
route_path: acme/alerts
http_method: post
request_type: async
authentication_method: none
is_static_website: false
workspaced_route: false
wrap_body: false
raw_string: false
---
# f/acme/inbox.email_trigger.yaml       (mail to <local_part>@<instance email domain> runs the flow)
script_path: f/acme/process_email
is_flow: true
local_part: acme-alerts
```

- HTTP route: `route_path` has no leading `/`; `http_method` is lowercase; `request_type` is `sync`, `async` or `sync_sse`; `authentication_method` is `none`, `windmill`, `api_key`, `basic_http`, `custom_script` or `signature`.
- Email: `parsed_email` is `{headers, text_body, html_body, attachments}`; `raw_email` is a string.
- Webhooks take **POST** and need a Windmill token (`Authorization: Bearer <token>`). `<flow_path>` keeps its prefix, e.g. `.../run/f/f/acme/process_orders`. A caller that can only send GET needs an HTTP route with `http_method: get`.
  - Async, returns a job UUID at once: `POST <base_url>/api/w/<workspace>/jobs/run/f/<flow_path>`
  - Sync, waits and returns the flow result: `POST <base_url>/api/w/<workspace>/jobs/run_wait_result/f/<flow_path>`
  - Result of an async run: `GET <base_url>/api/w/<workspace>/jobs_u/completed/get_result/<uuid>`
- Payload: body `{"sku": "A-100"}` gives `flow_input.sku`. A non-object body arrives as `flow_input.body`. Headers arrive only when requested with `?include_header=X-Signature`; `?raw=true` adds the unparsed body as `raw_string`.

Preprocessor: when the flow inputs differ from the raw trigger payload, add `value.preprocessor_module`. It runs only for trigger-started runs (not form runs or schedules), gets one `event`, and returns the flow inputs. The function is named `preprocessor`, not `main`. In `flow.yaml` it has the same shape and position as `failure_module` in section 11, with `id: preprocessor` and `input_transforms: {}`.

```ts
// preprocessor.ts  (webhook: body, raw_string, query, headers; http adds route, path, method, params; email: parsed_email, raw_email)
export async function preprocessor(event: { kind: "webhook" | "http" | "email"; [key: string]: any }) {
  if (event.kind === "email") return { text: event.parsed_email.text_body, source: "email" };
  if (!event.body?.text) throw new Error("payload has no 'text' field");
  return { text: event.body.text, source: event.headers?.["x-source"] ?? event.kind };
}
```

## 11. Error handling

A step fails when its script throws. Its result is then `{error: {name, message, stack}}`. The step's
`retry` runs first; if it still fails and `continue_on_error` is not set, this table applies, and finally `failure_module` runs.

| Where the step fails | What happens |
|---|---|
| Top-level step | The flow stops and fails. Later steps do not run. |
| In `forloopflow` with `skip_failures: false` | The loop stops at that iteration; the flow fails. |
| In `forloopflow` with `skip_failures: true` | The rest of that iteration is skipped; the loop continues and succeeds. |
| In `branchall`, branch has `skip_failure: true` | Other branches finish; the step succeeds. |
| In `branchall`, branch without it, or in `branchone` | The branch step fails; the flow fails. |
| Step has `continue_on_error: true` | The next step runs; `results.<id>.error` is set. |

`failure_module` is a key of `value`, has `id: failure`, must be `rawscript` or `script`, and reads `error`:

```yaml
value:
  modules: []
  failure_module:
    id: failure
    value:
      type: rawscript
      language: bun
      content: "!inline failure.ts"
      input_transforms:
        message: {type: javascript, expr: "error.message"}
        name: {type: javascript, expr: "error.name"}
        step_id: {type: javascript, expr: "error.step_id"}
        notify: {type: javascript, expr: "flow_input.email_to"}
```

`failure.ts` is an ordinary script: `export async function main(message: string, name: string, step_id: string, notify: string)`.

- `error` fields: `message`, `name`, `stack`, `step_id` (the id of the failed step).
- The flow still ends as **failed** after the handler. Returning `{recover: true, ...}` makes it end as a success; it never resumes the remaining steps.
- To react to a failure inside the flow instead, set `continue_on_error: true` on the step and follow it with a `branchone` whose `expr` is `"results.<id>?.error != null"`.

## 12. Invalid-flow checklist

Check every item before finishing.

1. Two modules share an id (ids inside loops and branches count), or an id has spaces, hyphens or a reserved word.
2. A `main` parameter has no `input_transforms` entry, or the key is spelled differently from the parameter.
3. `input_transforms` is missing on a `rawscript`, `script` or `flow` (write `{}` if empty).
4. A transform lacks `type`, or pairs `value` with `type: javascript`, or `expr` with `type: static`.
5. `results.x` names a later step, a step inside a loop/branch read from outside it, or a step in a sibling branch.
6. `flow_input.x` is used but `x` is not in `schema.properties`.
7. `flow_input.iter` is used outside a loop, or `flow_input.iter.value.<field>` in a while loop.
8. Missing required keys: `skip_failures` on a loop, `default` on `branchone`, `modules` on a branch, `expr` on a `branchone` branch.
9. `iterator`, `sleep`, `timeout` or `parallelism` written as a bare value instead of a transform object.
10. `retry`, `sleep`, `suspend`, `stop_after_if` or `skip_if` placed inside `value` instead of beside it.
11. A while loop with no `stop_after_if` (it never ends). Always add `max_iterations` as well.
12. `failure_module` / `preprocessor_module` put inside `modules`, given another id, or given a loop/branch type.
13. `content: !inline x.ts` unquoted, a file name with spaces, or a referenced file that was never written.
14. `skip_failure` (branch) and `skip_failures` (loop) swapped.
15. A script that does not export `main` (`preprocessor` for the preprocessor), or that calls `main()` itself.
16. A resource passed as `{"$res": "path"}` or a bare path instead of the string `"$res:path"`.
17. A schedule cron with 5 fields instead of 6.
18. An unquoted `expr` that YAML misreads (contains `: ` or ` #`, or starts with `{`, `[` or a backtick), or a bare object literal without parentheses.
19. `suspend` on an `identity` step, or on a script that never calls `getResumeUrls`.

## 13. Unverified

- The entry for a failed iteration (`skip_failures: true`) or failed branch (`skip_failure: true`) in the result array: the spec says `null`; the worker appears to keep the error object. Accept both.
- The result of a `branchone` whose empty `default` ran (probably the previous result or `null`).
- The flow's result and status after a top-level `stop_after_if` (docs only say "the flow stops").
- `concurrent_limit`, `priority`, `debounce_*`, `cache_ttl` may need an Enterprise licence when self-hosted.
- Whether `flow_env` values reach scripts as environment variables. Read them through expressions only.
- The HTTP route URL (believed `<base_url>/api/r/<route_path>`) and the fields of the `smtp` resource type (believed `host`, `port`, `user`, `password`).
- `error.stack` and `error.step_id` come from the spec; the docs page lists `message`, `name`, `step_id`.
- The Bun `tls` option of `fetch`, and the environment variables `WM_ROOT_FLOW_JOB_ID`, `WM_FLOW_JOB_ID`, `WM_JOB_ID` (section 5.1): not in the OpenFlow spec, and not run.
- That the webhook endpoints of section 10 accept POST only: the sync endpoint may also accept GET with the inputs in the query string.
- No example was run against a Windmill instance or `wmill lint`; the flow YAML was checked against the OpenFlow spec only.
