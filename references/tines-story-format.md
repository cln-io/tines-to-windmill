# Tines story export format

How to read an exported Tines story (JSON). Checked against tines.com/docs (Nov 2026) and two real exports (`schema_version` 30), one small and one large (about 1,000 actions).

- Structures seen in an export are marked *(observed)*. Each snippet keeps the exact shape of the export (same keys, option names and value forms), but **all names and values are invented**.
- Many snippets use one invented story, "Cold chain - review excursions". [worked-example.md](worked-example.md) ports that story to Windmill.

Statements marked **(unverified)** are settled by neither the docs nor the exports.

## Contents

1. [Mental model](#1-mental-model)
2. [Top-level keys](#2-top-level-keys)
3. [Agent object](#3-agent-object)
4. [Links and the event model](#4-links-and-the-event-model)
5. [Reference syntax in option values](#5-reference-syntax-in-option-values)
6. [Options common to all types](#6-options-common-to-all-types)
7. Agent types: [HTTPRequestAgent](#71-httprequestagent) · [EventTransformationAgent](#72-eventtransformationagent) · [TriggerAgent](#73-triggeragent-condition) · [WebhookAgent](#74-webhookagent) · [EmailAgent](#75-emailagent-send-email) · [SendToStoryAgent](#76-sendtostoryagent) · [GroupAgent](#77-groupagent-groupinputagent-groupoutputagent) · [FormAgent / pages](#78-formagent--pages) · [Other types](#79-other-types)
8. [One export, many workflows](#8-one-export-many-workflows)
9. [Unverified items](#9-unverified-items)

Rarely needed, in [tines-story-format-extras.md](tines-story-format-extras.md): IMAPAgent (Receive Email), LLMAgent (AI Agent), RunScriptAgent, RecordAgent, Case / MCP server, page element details, Tines API calls that write resources.

## 1. Mental model

- Tines calls a step an **action**. The export calls it an **agent**. They are the same thing.
- A story is a directed graph: `agents` are nodes, `links` are edges. **Cycles are allowed** (used for poll/retry loops).
- An action runs when (a) it receives an event from a linked source, (b) its `schedule` fires, or (c) it is an entry point (webhook, received email, page submit).
- Each run emits **zero, one or many events**. Every receiver runs **once per event**.
- There is no "start" node. Entry points are agents that are scheduled or are WebhookAgent / IMAPAgent / FormAgent.
- One export usually holds **several independent workflows** (section 8).

## 2. Top-level keys

| Key | Use | Meaning |
|---|---|---|
| `name`, `description`, `slug` | yes | Story name, description, snake_cased name. |
| `agents` | **yes** | Array of actions. **Array position is the index used by `links`.** |
| `links` | **yes** | Edges between agents (section 4). |
| `pages` (older: `forms`, `form`) | **yes** | One object per FormAgent, matched by `agent_guid`. Holds the page's elements (7.8). |
| `send_to_stories` | **yes** | List of **full exports of called sub-stories** (same keys as a story, minus `send_to_stories`). May be incomplete: *(observed)* an export that calls several stories and embeds only one of them. |
| `send_to_story_enabled` | yes | `true` = this story is a callable sub-story. |
| `entry_agent_guid` | yes | `guid` of the WebhookAgent that receives the caller's input (sub-story entry). |
| `exit_agent_guids` | yes | `guid`s of the message-only agents whose output is returned to the caller. |
| `api_entry_action_guids`, `api_exit_action_guids`, `synchronous_webhooks_enabled` | yes | "Workflow as API": the HTTP caller of the entry webhook gets the payload of the first exit action to run (30 s limit). Exit payload may be `{status, headers, body}` to shape the HTTP response. Exact mapping of these three keys to that feature is **(unverified)**. |
| `integrations` | yes | Input values for templated actions and groups. Each item: `action_guid` + `action_inputs[]` (`name`, `type`, `required`, `value`). `value` is a JSON-encoded string. Read by the action as `INPUT.<slug of name>` (in a group: `GROUP_INPUT.<slug>`). |
| `send_to_story_timeout_enabled`, `send_to_story_timeout_duration_seconds` | maybe | Timeout when called as a tool by Workbench / AI agent. |
| `recipients`, `monitor_failures` | maybe | Who is notified on monitored failures. No effect on data flow. |
| `diagram_notes` | maybe | Sticky notes: `{content, position, guid, width}`. `content` may explain intent. |
| `keep_events_for` | no | Event retention in seconds. |
| `diagram_layout`, `sections`, `icon`, `tags` | no | Canvas layout and decoration. |
| `schema_version`, `standard_lib_version`, `action_runtime_version`, `guid`, `origin_story_identifier`, `exported_at`, `story_library_metadata`, `reporting_status`, `time_saved_*`, `integration_product`, `integration_vendor`, `llm_product_instructions`, `send_to_story_access*`, `send_to_story_skill_use_requires_confirmation`, `parent_only_send_to_story`, `start_reference`, `app_endpoints` | no | Metadata. |

**Credentials and resources are not in the export.** Only references appear inside option values (`CREDENTIAL.x`, `RESOURCE.x`). To list what a story needs, search every string in `agents`, `pages` and `send_to_stories` for those two prefixes (section 8).

## 3. Agent object

```json
{ "type": "Agents::EventTransformationAgent", "name": "depots", "disabled": false, "description": null,
  "guid": "b23e6bb9d09a953542a91bea06584c7b",
  "options": { "mode": "message_only", "loop": false, "payload": ["north-quay", "ridgeway", "old-mill"] },
  "schedule": [ { "cron": "*/20 * * * *", "timezone": "America/Toronto" } ],
  "monitoring": { "monitor_all_events": false, "monitor_failures": false, "monitor_no_events_emitted": null } }
```
*(observed, trimmed)*

| Key | Use | Meaning |
|---|---|---|
| `type` | **yes** | Action type (section 7). |
| `name` | **yes** | Display name. Its **slug** is how other actions reference its output. |
| `options` | **yes** | Type-specific configuration. Values may contain references (section 5). |
| `disabled` | **yes** | `true` = the action does not run and emits nothing, so everything reachable only through it is dead. |
| `schedule` | **yes** | `null`, or a list of `{cron, timezone}` (5-field cron). **The list can hold several entries** *(observed: 1 to 3)*; each one starts a run with **no incoming event**. |
| `guid` | yes | Stable id. Used by `entry_agent_guid`, `exit_agent_guids`, `pages[].agent_guid`, `integrations[].action_guid`. |
| `description` | maybe | Human note. |
| `group` | yes | Only on GroupAgent: the nested sub-graph (7.7). |
| `record_type`, `record_writers` | yes | Only on RecordAgent (extras file). |
| `monitoring` | no | Notifications only: `monitor_failures` (notify on error), `monitor_all_events` (notify on every event), `monitor_no_events_emitted` (seconds of silence before notifying). No effect on data flow. |
| `template` | no | `created_from_template_guid` non-null = created from a template. If it uses `INPUT.x`, look up the values in top-level `integrations`. |
| `reporting`, `width`, `origin_story_identifier` | no | Metadata. |

- The `schedule` key is absent on types that cannot be scheduled *(observed)*: TriggerAgent, WebhookAgent, FormAgent, GroupInputAgent, GroupOutputAgent, and EventTransformationAgent in delay / throttle mode. Every other type has it (`null` or a list).
- The usual scheduled entry point is a message-only EventTransformationAgent (often with a constant payload) whose only job is to start the chain.
- Docs say actions inside a group cannot be scheduled, but one scheduled HTTPRequestAgent inside a group was *(observed)*. Check `schedule` at every depth.

## 4. Links and the event model

### Links

`"links": [ {"source": 0, "receiver": 1}, {"source": 18, "receiver": 21, "link_type": "secondary"} ]` *(observed)*

- `source` and `receiver` are **0-based indices into the `agents` array of the same object**. A group and an embedded sub-story each have their own `agents` and `links`; indices never cross those boundaries.
- No `link_type` = normal link: receiver gets every event the source emits.
- `"link_type": "secondary"` = the **no-match** link of a TriggerAgent: the receiver gets the event only when the rules did **not** match. In both exports every `secondary` link starts at a TriggerAgent (the API calls this type `NO_MATCH`).
- An action can also have a **failure path** link (API type `FAILURE`): the receiver gets the event when the run logged an error. Its `link_type` value in exports is **(unverified)**; neither export uses one.

### Event rules

| Rule | Detail |
|---|---|
| R1. Output key | An action's output is stored under its slug. Action `get excursions` → `get_excursions`. |
| R2. Events accumulate | The event an action emits contains its own output **plus everything in the event it received**. A downstream action can read any action upstream on its path: `get_excursions.body`, `explode_depots.code`. |
| R3. Once per event | A receiver runs once for each event it receives. If the source emits 10 events (explode), the whole downstream chain runs 10 times, independently. |
| R4. Fan-out | One source with several receivers: each receiver gets its own copy and the branches run independently. Branches never re-join automatically. |
| R5. Multiple inbound links = OR | An action with several sources runs separately for each event from any source. It does **not** wait for all sources. Only `implode` (7.2) merges events. |
| R6. Missing path | A reference to an action that is not on the current event's path evaluates to null **(unverified)**. |
| R7. Zero events stops the branch | No match, non-array explode, duplicate, fatal error → nothing emitted → nothing downstream runs for that event. |
| R8. Story run | All events descending from one trigger share one story run id (`META.story_run.id`). |

R5 *(observed)*: two agents that are both named `tag for join` (indices 27 and 28, on different branches) link to the implode agent `join parts` (29). Each event reaching `join parts` carries only one `tag_for_join` key.

### Slug rule (action name → reference key)

1. Lowercase everything.
2. Replace each run of characters that are not letters or digits with one `_`; drop such runs at the start and end.
3. If the result starts with a digit, prefix `_`.

Examples: `get excursions` → `get_excursions`; `Request to claims.example.org (v2)` → `request_to_claims_example_org_v2`; `200` → `_200`.

If two actions on one path have the same slug, the one nearest the reader (most downstream) wins. Duplicate names are common *(observed: four top-level agents named `200` in one story)*. The same rule turns page field names, resource names, credential names and story names into slugs.

## 5. Reference syntax in option values

Any string anywhere inside `options` (also nested in objects and arrays) and inside page elements can be one of:

| Form | Example | Evaluation |
|---|---|---|
| Plain text | `"method": "get"` | Literal. |
| Text with pills `<<expr>>` | `"url": "https://carriers.example.net/v1/vehicles/<<explode_excursions.alert.vehicle_id>>"` | Each pill is evaluated, converted to text and joined with the surrounding text. |
| One pill only | `"path": "<<get_excursions.status>>"` | The value of the expression. Docs pass arrays this way (`"path": "<<numbers>>"`), so the type is kept. |
| Formula field `=expr` | `"path": "=depots"` | String starts with `=`: the whole string is one expression. Returns the typed value (array, object, number...). |

- Inside `<<...>>` and after `=` the language is identical: a path or a formula (functions in UPPERCASE, `|>` pipes the left result into `%` on the right).
- Formulas may span lines. `<<>>` (empty pill) yields nothing; `"<<STORY.x>><<>>"` equals `"<<STORY.x>>"`.
- Path syntax: `action_slug.key.sub`, `list[0]`, `obj["key with spaces"]`.
- Numbers and booleans are often stored as strings (`"limit": "500"`, `"must_match": "2"`, `"timeout": "45"`). Treat them as numbers.

### Control tags in text values `<% ... %>`

*(observed; names invented)*

```json
"body": "Open items:\n<%for t in get_items.body.items%>- <<t.title>><%if t.priority > 2%> URGENT<%elseif t.priority = 2%> soon<%else%> later<%endif%>\n<%endfor%>"
```

| Tag | Meaning |
|---|---|
| `<%if expr%>` ... `<%elseif expr%>` ... `<%else%>` ... `<%endif%>` | Keep the text of the first branch whose formula is truthy (everything except `FALSE` and `NULL` is truthy). |
| `<%for item in expr%>` ... `<%endfor%>` | Repeat the enclosed text once per element of the list `expr`. `item` is usable in pills and tags inside the block. |
| `FORLOOP.index0`, `FORLOOP.index`, `FORLOOP.first`, `FORLOOP.last` | Inside a `for` block: 0-based index, 1-based index, is-first, is-last. |

- `expr` is any formula: `<%if SIZE(found.matches) > 0%>`, `<%for r in REVERSE(rows)%>`, `<%if MODULO(FORLOOP.index, 2) = 0%>`.
- Spaces inside the delimiters are allowed: `<% endif %>`. Tags nest. Tags only work in text values, not in `=formula` fields. Most often seen in message-only `payload` strings that build a message, an email or an HTML table.
- A `raw` / `endraw` pair (docs) stops interpolation of the enclosed text. Its written form is **(unverified)**, by analogy `<%raw%>` ... `<%endraw%>`.

### Namespaces (UPPERCASE = built in, lowercase = action slug)

| Reference | Meaning |
|---|---|
| `some_action.x` | Output of the upstream action with that slug. |
| `CREDENTIAL.name` | Secret stored in the tenant, by slug. Dynamic: `CREDENTIAL[expr]`. |
| `RESOURCE.name` | Shared stored value (text, JSON or file), by slug. A global variable; other stories or API calls may change it. Dynamic: `RESOURCE[expr]` or `GET(RESOURCE.name, key)`. |
| `RESOURCE.name.fn(args)` | Call of a **lambda stored in a resource** (see below). |
| `LOCAL.key` | Value from this action's own `local` option (section 6). |
| `LOOP.value`, `LOOP.index`, `LOOP.key`, `LOOP.previous_result` | Current element when the action has `loop`. `key` only when looping an object. |
| `META` | Environment: `META.tenant.{domain,name,url}`, `META.team.{id,name}`, `META.story.{id,name,key,is_draft}`, `META.action.{id,name,key}`, `META.event.{id,payload}`, `META.story_run.id`. |
| `INPUT.name` | Templated action input. Values are in top-level `integrations`. |
| `GROUP_INPUT.name` | Same, inside a group built from a template *(observed; not in the docs keyword list)*. |
| `OUTPUT` | The action's own raw output. Only valid in `customize_output` and `log_error_if`. |
| `PAGINATE.index`, `PAGINATE.previous_response` | HTTP pagination state (7.1). |
| `STORY.name` | Id of another story, for SendToStoryAgent `story`. |
| `PAGE.name` (old: `FORM.name`) | URL of the page (FormAgent) with that slug in this story. Typically put in a message or email. |
| `INFO.resource.name.id`, `INFO.record.name.id`, `INFO.record.name.fields.field.id`, `INFO.credential.x`, `INFO.cases.x` | Numeric ids and metadata of tenant objects. Used to build Tines API URLs (extras file). |
| `team_case` | Current case (Cases feature). |

There is **no `STORY_RUN` namespace**. Use `META.story_run.id` or the function `STORY_RUN_GUID()` (in a sub-story the function returns the caller's run id).

```json
"payload": "=IF(IS_BLANK(LOCAL.last),\"\",\"&since=\"&LOCAL.last)",
"local": { "last": "=GET(RESOURCE.excursion_cursor, explode_depots.code)" }
```
*(observed: `LOCAL`, `RESOURCE` and an action slug together)*

### How resources are used *(observed; names invented)*

| Pattern | Example | What the reader must know |
|---|---|---|
| Lookup table | `=GET(RESOURCE.owner_by_team, get_item.body.team)` | The table content is not in the export. |
| Shared connection settings | `"url": "<<RESOURCE.inventory_api.url>>/items"`, `"timeout": "=RESOURCE.inventory_api.timeout"`, `"retries": "=RESOURCE.inventory_api.retries"` | One JSON resource per external system; its keys are not in the export. |
| Stored lambda | `<<RESOURCE.text_tools.shorten(get_item.body.text, 30)>>` | The resource is an object whose key `shorten` holds a `LAMBDA(...)`. **The function body is not in the export.** |
| State between runs | read with `RESOURCE.poll_cursor`, written by an HTTP call to the Tines API | See extras file. Values change while stories run. |

Never guess the content of a resource or the body of a stored lambda. List them and ask the user.

## 6. Options common to all types

| `options` key | Meaning |
|---|---|
| `local` | Object evaluated once per run, before the other options. Read with `LOCAL.key`. A key can use keys defined above it. (UI name "Local values"; some docs lists say `local_values`.) |
| `customize_output` | A string, normally an `=formula` over `OUTPUT`, that **replaces** the emitted output. *(observed)* `"customize_output": "=OUTPUT.body.items"`. Event data and `LOCAL` are not available here. |
| `log_error_if` | Formula over `OUTPUT`; when true an error is logged for the run. |
| `emit_failure_event` | Always / Never / Error-response-only (HTTP default). With "always", a fatal error (for example a crashing formula) still emits an event `{"failed": true}`. JSON values **(unverified)**. |
| `include_metadata` | Adds `meta` (`duration`, `pending_duration`) to the output. On by default for HTTP. |
| `loop` | See below. |
| `rules`, `must_match` | On HTTPRequestAgent and EventTransformationAgent: the action only runs when the rules match (same rule format as 7.3). No match = no event. |

**Error logged ≠ branch stopped.** An error log stops the branch only if no event is emitted. With a failure path, the event goes to the failure link.

### `loop`

- `"loop": false` or absent → no loop. Otherwise it is a reference to a list or object: `"loop": "=numbers"`, `"loop": "=RESOURCE.team_list"`.
- Supported on: message-only EventTransformationAgent, SendToStoryAgent, GroupAgent (list only for the last two; HTTPRequestAgent support **(unverified)**).
- The action body is evaluated once per element with `LOOP` set. **Exactly one event is emitted**; its output is a **list** of the per-element results (may contain nulls).
- Order is kept (group loops are serial unless set to parallel). One failing element stops the loop. Max 20,000 elements.
- `loop` ≠ `explode`: loop gives one event holding a list; explode gives N events. Docs example: `{ "mode": "message_only", "loop": "=numbers", "payload": "value=<<LOOP.value>>" }` → a list with one string per element.

## 7. Agent types

Table columns: **Sched** = can have `schedule`; **In** = can receive events.

| `type` | UI name | Sched | In | One-line behaviour |
|---|---|---|---|---|
| `Agents::HTTPRequestAgent` | HTTP Request | yes | yes | Sends one HTTP request, emits the response. |
| `Agents::EventTransformationAgent` | Event Transform | most modes | yes | Builds/reshapes data or controls flow, by `mode`. |
| `Agents::TriggerAgent` | Condition (was Trigger) | no | yes | Filter / branch on rules. |
| `Agents::WebhookAgent` | Webhook | no | no | Entry point: emits each incoming HTTP request. |
| `Agents::EmailAgent` | Send Email | yes | yes | Sends an email. |
| `Agents::SendToStoryAgent` | Send to Story | yes | yes | Calls another story, emits its result. |
| `Agents::GroupAgent` | Group | ? | yes | Inline sub-graph with one input and one output. |
| `Agents::GroupInputAgent`, `Agents::GroupOutputAgent` | (inside a group) | no | - | Entry and exit of a group. |
| `Agents::FormAgent` | Page | no | yes | Web page/form; emits the submission. |
| `Agents::IMAPAgent`, `Agents::LLMAgent`, `Agents::RunScriptAgent`, `Agents::RecordAgent` | Receive Email, AI Agent, Run Script, Record | | | See the extras file. |

### 7.1 HTTPRequestAgent

Both blocks *(observed)*, from two different stories:

```json
{ "url": "https://tracker.example.com/v2/depots/<<explode_depots.code>>/excursions?state=open&limit=200<<since_parameter>>",
  "content_type": "application_json", "method": "get",
  "headers": { "X-Auth-Token": "<<CREDENTIAL.tracker_api_token>>" } }
```
```json
{ "url": "<<RESOURCE.inventory_api.url>>/items/<<explode_items.item.id>>", "method": "put", "content_type": "json",
  "payload": { "state": "closed" }, "basic_auth": ["<<CREDENTIAL.inventory_user>>", "<<CREDENTIAL.inventory_password>>"],
  "timeout": "45", "retries": 5, "retry_on_status": ["0", "429", "500-599"], "log_error_on_status": ["400-499", "500"],
  "disable_ssl_verification": true }
```

| Option | Meaning |
|---|---|
| `url` | Target URL, scheme included. |
| `method` | `get`, `post`, `put`, `patch`, `delete`. **Default `post`.** |
| `payload` | Object, or a string (often an `=formula` giving the whole body). On `get` it is sent as **query parameters** (unless `send_get_payload_as_body`); otherwise it is the body, encoded per `content_type`. |
| `content_type` | `json` → `application/json`; `form` → `application/x-www-form-urlencoded`; `xml` → `text/xml`; `data` → `multipart/form-data`. Exports also contain `application_json` and `application/json` (both = json). |
| `headers` | Object of request headers. `user_agent` (string) sets the User-Agent *(observed)*. |
| `query_params` | Extra query parameters. `params_encoder`: `nested` (default, arrays as `key[]=`) or `flat` (repeated keys). |
| `basic_auth` | `["user", "password"]` *(observed)* or `"user:password"`. |
| `timeout` | Seconds, default 30. Number, numeric string or reference. |
| `retry_on_status` | List of codes or ranges as strings (`["0", "429", "500-599"]`). **Retries happen only if this is set**; `retries` alone does nothing. |
| `retries` | Max retries, default 25. Backoff `min(5 * 2^n, 600)` seconds plus jitter (5, 10, 20 ... 600). |
| `log_error_on_status` | Codes that log an error. Default `[0, 400-499, 500-599]`. `[]` = never. |
| `parse_response_as` | `text`, `json`, `xml`, `file`. Default: from the response `Content-Type`. |
| `pagination` | Repeats the request while `has_more` is true (max 100 requests; first request always sent). Default `has_more` is `PAGINATE.index < 10`. Emits one event per page, or one combined event if `output_as_single_event`. The docs example uses the key `pagination_options` with `enabled: true`; accept both names. |
| `disable_ssl_verification`, `disable_redirect_follow`, `disable_url_encoding`, `https_only`, `http_proxy_url`, `use_tunnel`, `mutual_tls`, `use_ntlm_authentication`, `redirect_authorization`, `custom_certificate_authority_name`, `send_get_payload_as_body` | Transport details. |

- Status code `0` in these lists appears next to real codes in both exports; presumably it stands for "no HTTP response" (connection failure) **(unverified)**.
- Unknown option keys can occur (leftovers typed by the author). Ignore keys that are not in this table.
- Multipart file upload (`content_type: "data"`): any payload key whose value is `{ "contents": ..., "filename": ... }` is sent as a file part.

**Output** (one event per request): `{ "body": ..., "headers": { ... }, "status": 200, "meta": { "response_time": 0.08 } }`

- `body` is parsed JSON when the response is JSON, otherwise text. With `parse_response_as: file` it is a file object: `body.filename`, `body.base64encodedcontents` (other keys **(unverified)**).
- Reference pattern: `<slug>.status`, `<slug>.body.<field>`, `<slug>.headers.<Name>`.

**Non-2xx behaviour (default):** the event **is still emitted** with the real `status` (404, 500...) and an error is logged. The story continues. Stories therefore test the status themselves with TriggerAgents *(observed: agent `404` after `Get batch report from lab`, agent `200` after `get excursions`)*. Connection failures (timeout, DNS) emit **no** event by default. With `retry_on_status`, one event is emitted after the last retry.

### 7.2 EventTransformationAgent

`options.mode` selects the behaviour.

| `mode` | Options | Emits |
|---|---|---|
| `message_only` | `payload` (any JSON; strings may be references), `loop` | **Output = evaluated `payload` itself** (object, list, string, number). With `loop`: list of per-element payloads. |
| `explode` | `path` (reference to a list), `to` (key name), `limit` (default 500; *observed* values in the thousands, stored as strings) | **One event per element**: `{ "<to>": element, "index": i, "guid": "<same for all elements>", "size": n }`. Not a list → no event. |
| `implode` | `item_path`, `guid_path`, `size_path`, `seconds` | Collects incoming events with the same `guid_path` value. Emits **one** event when `size_path` events have arrived **or** `seconds` after the first one, whichever is first. Output = list of the `item_path` values (whole events if `item_path` is absent). `guid_path` may be absent *(observed)*: all events then form one batch. List order **(unverified)**. |
| `deduplicate` | `path` (value to test), `lookback` (number of past events, max 100,000) or `period` (seconds), `emit_duplicates`, `tolerance` | Unique → `{ "unique_event": true }`. Duplicate → no event (or `unique_event: false` if `emit_duplicates`). **Memory spans story runs.** |
| `delay` | `seconds` (number, string or pill: `"<<30 * NUMBER(x)>>"`) or `until` (date/time text such as `"7 days from now"`) | Waits, then emits `{ "seconds": n }`. Upstream data stays readable. |
| `throttle` | `interval` (`minute` / `hour` / `day`), `capacity`, `events_per_run` (1-10, default 1), `throttle_key` | Queues events and releases them at a fixed rate, in order, **shared across all story runs**. `capacity` is the export key for what the docs call "runs per interval" (docs option name: `runs_per_interval`; equivalence inferred). Released per interval = `capacity` × `events_per_run`. Adds `capacity_per_minute` to the output. Queue above 20,000 drops events. |
| `extract` | `matchers`: list of `{path, regexp, to}`; `emit_no_match` | `{ "<to>": [all matches] }` per matcher (Ruby regex). No match at all → no event unless `emit_no_match`. |
| `automatic` | `input`, `guidance` (plain English) | Runs a Python script generated at build time from `guidance`. Docs example output: `{ "output": ... }`. Whether the script is in the export is **(unverified)**; if absent, re-implement from `guidance`. |

*(observed)* An explode, and an implode that joins two parallel branches:

```json
{ "mode": "explode", "path": "=rows", "to": "alert", "limit": "500" }
{ "mode": "implode", "item_path": "=tag_for_join", "guid_path": "=explode_excursions.alert.id", "size_path": "=2", "seconds": 40 }
```
- The explode action is named `explode excursions`; downstream reads `explode_excursions.alert.sensor_id`.
- The implode action is named `join parts`. It waits for 2 events or 40 s and emits a list; downstream reads the list by the implode's slug: `=WHERE(join_parts,"part","message") |> FIRST(%).data`.

*(observed)* The standard explode → work → implode pair, plus other modes:

```json
{ "mode": "explode", "path": "=get_items.body.items", "to": "item", "limit": "500" }
{ "mode": "implode", "item_path": "=build_row", "guid_path": "=explode_items.guid", "size_path": "=explode_items.size" }
{ "mode": "deduplicate", "path": "<<explode_items.item.id>>", "lookback": "50" }
{ "mode": "throttle", "capacity": 10, "interval": "minute", "events_per_run": 1 }
```
To join parallel branches instead (first block): `guid_path` = a value all branches share, such as an id of the exploded item or `STORY_RUN_GUID()`, and a fixed `size_path`.

### 7.3 TriggerAgent (Condition)

`{ "rules": [ { "type": "field==value", "value": "200", "path": "<<get_excursions.status>>" } ] }` *(observed)*

Each rule compares `path` (left side, the incoming value) with `value` (right side, the test value).

| `type` | Meaning |
|---|---|
| `field==value`, `field!=value` | Equal / not equal. |
| `field<value`, `field<=value`, `field>value`, `field>=value` | Numeric comparison. |
| `regex`, `!regex` | `path` matches / does not match the regex in `value`. |
| `in`, `not in` | `path` **contains** / does not contain `value`. `path` list → `value` must equal an item (if `value` is a list: any item). `path` text → substring. |
| `formula`, `not formula` | The formula is true / false. **The formula is in `path`** (`"path": "=SIZE(get_items.body) > 0"`); ignore `value` (null or a leftover) *(observed)*. |
| `field!=null` | "Is not null": `path` is neither null nor empty. **The rule has no `value` key** *(observed)*. |
| `field==null` | "Is null". Inferred from `field!=null`; not observed. |

| Option | Meaning |
|---|---|
| `must_match` | Absent → **all** rules must match (AND). `1` → any rule (OR). `N` → at least N. Stored as a string *(observed: `"1"`, `"2"`, `"3"`)*. |
| `emit_no_match` | `true` → an event is also emitted on the normal links when rules do not match (`rule_matched: false`). `false` or absent → not. |

**Behaviour:**

| Case | Result |
|---|---|
| Rules match | Emits the event on normal links. Own output: `{ "rule_matched": true, "rule_results": [...], "path_results": [...] }`. All upstream data passes through. |
| No match, no `secondary` link | **Nothing emitted. The branch ends for this event.** |
| No match, with `secondary` link | Event goes only to the `"link_type": "secondary"` receivers (if/else). |
| No match, `emit_no_match: true` | Event goes down the normal links with `rule_matched: false`; no-match link unused. |

- Several TriggerAgents on one source = a switch: each tests the same event independently, so zero, one or several branches may continue *(observed: `failed tests above 0`, `404`, `borderline tests above 2` all hang off one HTTP action)*.
- Rule values are strings (`"value": "200"`) compared with numbers (`status` 200) and match, so comparison is loosely typed. Exact coercion and regex anchoring/case rules are **(unverified)**.
- **Paths** (docs, Nov 2026): a Condition can hold up to 10 named Paths, each with its own rules and outgoing link, evaluated top to bottom, **first match wins**; the no-match branch is used only when no Path matches. How Paths appear in `options` and `links` is **(unverified)**; neither export uses them. If a TriggerAgent has option keys other than `rules`, `must_match`, `emit_no_match`, or its links carry extra keys, treat it as a first-match multi-branch.

### 7.4 WebhookAgent

Entry point. Emits one event per accepted HTTP request. URL: `https://<tenant>/webhook/<path>/<secret>`.

`{ "path": "0123456789abcdef0123456789abcdef", "secret": "fedcba9876543210fedcba9876543210", "verbs": "get,post" }` *(observed shape; values invented)*. **`secret` is a credential in clear text: never copy it into output.**

| Option | Meaning |
|---|---|
| `path`, `secret` | URL parts. `secret` may also arrive as `Authorization: Bearer`. |
| `verbs` | Accepted methods, comma-separated (`"get,post"`). |
| `include_headers` | Default `true`. See output below. |
| `response`, `response_code`, `response_headers` | Immediate HTTP reply. Defaults: `"Ok"`, `201`. `response` may reference `body.x` and `headers.x` of the request. A `302` code with a URL in `response` redirects. |
| `rules` (docs also say `match_rules`), `must_match` | Request filter over `body.x` / `headers.x`. No match → no event; caller gets "No Rules Matched". |
| `access_control`, `rate_limit` (`{key, count, period}`, excess gets 429), `capture_raw_body` | Who may call (public / secret (default) / team / tenant / OAuth), rate limit, also emit the raw body. |

**Output:**

| `include_headers` | Shape | Reference |
|---|---|---|
| `true` or absent (default) | `{ "body": { request params/JSON }, "headers": { ... } }` | `my_webhook.body.field` |
| `false` | Request params at top level | `my_webhook.field` |

- A non-object JSON body is wrapped: `body._json`.
- Header keys are lowercased with `-` → `_` (`X-Example-Id` → `x_example_id`).
- As sub-story entry (7.6): `body` holds the caller's payload and `meta` describes the caller.

### 7.5 EmailAgent (Send Email)

| Option | Meaning |
|---|---|
| `recipients` | Address, list of addresses, or a reference giving either. `cc`, `bcc` likewise. |
| `subject`, `body` | `body` may be HTML (wrapped in `<html><body>` automatically). |
| `reply_to`, `sender_name`, `content_type` (`text/plain` / `text/html`) | Optional. |
| `advanced_html` | Boolean *(observed, not documented)*. Rendering setting; no effect on data flow. |
| `attachments` | List of `{ "filename", "base64encodedcontents", "content_type" }` (`content_type` default `"auto"`), or one `=formula` returning such a list. |

Output: `{ "status": "Success", "mail": { "to", "reply_to", "cc", "bcc", "subject", "body", "attachments", ... } }`. The email is sent from the tenant's own sender address.

### 7.6 SendToStoryAgent

Calls another story (sub-story) and waits for its result.

```json
{ "story": "<<STORY.archive_document>>", "payload": { "folder": "invoices", "title": "<<build_title.text>>" } }
```
*(observed; names invented. `"story": "=STORY.archive_document"` is equivalent.)*

| Option | Meaning |
|---|---|
| `story` | `<<STORY.sub_story_slug>>` / `=STORY.sub_story_slug`, or a numeric story id. The slug is the sub-story's top-level `slug`. |
| `payload` | Object or string sent to the sub-story. If the sub-story defines inputs, the action carries those input values instead and `payload` is ignored. |
| `send_payload_as_body` | Absent or `true` (default): the sub-story's entry webhook sees the data under `body`. `false`: not nested under `body`. |
| `loop` | One call per list element, serial; emits one event with the list of results. |
| `send_to_draft` | Call a draft version. |

**How to resolve a call** *(confirmed by the observed export)*:

1. Take the slug after `STORY.`. Find the element of top-level `send_to_stories` whose `slug` equals it. If none: the sub-story is not in the export; ask the user for its export.
2. In that element, the agent whose `guid` = `entry_agent_guid` is a WebhookAgent. Inside the sub-story the caller's data is read as `<entry slug>.body.<payload key>`.
3. The agents listed in `exit_agent_guids` are message-only. **The SendToStoryAgent's output = the `payload` of the exit action that was reached.** The caller reads `<sts slug>.<exit payload key>`.
4. The entry event also has `meta`: `{ "story_id", "action_id", "story_run_guid", "event_id", "team_id", ... }` of the caller.

- An embedded sub-story is a complete story: it can contain its own groups, SendToStoryAgents and other types. Its nested calls are resolved against the same top-level `send_to_stories` list (it has no list of its own).
- Missing required inputs → the call fails. All actions of a sub-story must be connected to its entry.
- A SendToStoryAgent whose output nobody reads is a fire-and-forget call (for example "write a log entry").

### 7.7 GroupAgent, GroupInputAgent, GroupOutputAgent

A group is an inline sub-graph. The GroupAgent holds it under `group`:

```json
{ "type": "Agents::GroupAgent", "name": "Sensor audit",
  "options": { "payload": { "explode_excursions": "=explode_excursions" } },
  "group": { "agents": [ ...14 agents... ], "links": [ {"source": 12, "receiver": 0}, {"source": 11, "receiver": 13} ] } }
```
*(observed, trimmed)*

| Part | Meaning |
|---|---|
| `group.agents`, `group.links` | Same format as a story. **Link indices are local to `group.agents`.** Groups can nest (a GroupAgent inside `group.agents`), though both exports only nest one level. |
| `Agents::GroupInputAgent` (exactly one, named `Input`) | Entry of the group. `options.options` lists declared inputs: `{name, type, description, required}`; usually one input named `Payload` of type `OBJECT`. Follow its outgoing links to find the first inner actions. |
| `Agents::GroupOutputAgent` (exactly one, named `Output`) | `options.payload` = what the group returns: an object or an `=formula`. *(observed)* `{ "payload": "=findings" }`. |
| GroupAgent `options` | `payload`: object or string passed in, evaluated in the **parent** context. **`"payload": {}` is common** *(observed)*: the group takes no input and is just a container for one workflow (section 8). Optional `loop` (top-level groups only; serial unless parallel is set). |

Data rules:

| Direction | Rule | Example *(observed)* |
|---|---|---|
| Parent → group | Inner actions read inputs through the Input agent's slug: `input.payload.<key>...` | `<<input.payload.explode_excursions.alert.sensor_id>>` |
| Parent → group (templated group) | `GROUP_INPUT.<input slug>`; values are in top-level `integrations` under the group's `guid`. | `<<GROUP_INPUT.sensor_id>>` |
| Inside the group | Normal slug references between inner actions. | `<<submit_render_job.body.job_url>>` |
| Group → parent | The parent sees **only** the Output payload, under the GroupAgent's slug. Inner outputs are not visible outside. | `find_or_render_chart.body.job.id` |

- Whether inner actions can read the parent's upstream actions directly by slug is **(unverified)**; in both exports data is passed in through `payload` or not needed.
- Output reached → the GroupAgent emits one event. Output never reached (inner branch ended) → nothing emitted. Output reached several times (inner explode) → behaviour **(unverified)**.
- Docs: groups cannot contain webhooks, pages or receive-email actions.
- Inner poll loop *(observed)*: `Wait for render` (delay 10 s) → `Get chart job` → `Still rendering` (status == 404) → normal link back to `Wait for render`, `secondary` link to `Output`.

### 7.8 FormAgent / pages

A Page is a web page with input fields and/or display elements. A page is described in **two places**, joined by guid:

| Where | Holds |
|---|---|
| Agent of type `Agents::FormAgent` in `agents` | Position in the graph (links), `name` (→ slug), behaviour `options`. Its `options.fields` is an empty string. |
| Element of top-level `pages` with `agent_guid` = that agent's `guid` | The elements: `fields`, `containers`, `conditions`. |

```json
{ "type": "Agents::FormAgent", "name": "Order form", "guid": "aaaa1111aaaa1111aaaa1111aaaa1111",
  "options": { "mode": "story_run", "fields": "", "visibility": "tenant", "anonymize": false, "auto_submit": false,
               "url_identifier": "0123456789abcdef0123456789abcdef", "loading_message": "One moment..." } }
```
```json
{ "agent_guid": "aaaa1111aaaa1111aaaa1111aaaa1111", "visibility": "tenant", "success_message": "", "conditions": [],
  "containers": [ { "guid": "c1", "name": "Container", "layout": "vertical", "ranking": 0, "loop": "" } ],
  "fields": [
    { "name": "Heading", "type": "TITLE", "content": "Order form", "container_guid": "c1", "ranking": 0 },
    { "name": "Product name", "type": "SHORT_TEXT", "required": true, "default_value": null, "container_guid": "c1", "ranking": 1 },
    { "name": "Level", "type": "OPTION", "options": ["read", "write"], "multi_select": false, "default_value": "read", "container_guid": "c1", "ranking": 2 },
    { "name": "Submit", "type": "BUTTON", "content": "Place order", "default_value": null, "style": "primary", "container_guid": "c1", "ranking": 3 } ] }
```
*(observed shape, trimmed; names and values invented)*

| FormAgent `options` key | Meaning |
|---|---|
| `mode` | What the visitor sees after submitting. `success_page` = show a message (`submissionMessage`; also in `pages[].success_message`). `redirect` = go to the URL in `redirect` (may contain pills). `story_run` = wait (showing `loading_message`) until the run reaches the next page, then show it; presumably the UI's "Move to next page" (name mapping inferred). |
| `visibility` | Who may open it: `world` (anyone with the link), `tenant` (signed-in members). Other values **(unverified)**. |
| `url_identifier` | Last part of the page URL (`https://<tenant>/pages/<url_identifier>`). |
| `anonymize` | `true` = `headers` of the submission is `{}`. |
| `auto_submit`, `auto_submit_time` | Submit automatically after a delay (*observed* `"five_seconds"`), used on display-only pages. |
| `auto_close_tab_on_submit`, `page_logo`, `page_width`, `pages_action_color`, `pages_appearance_mode`, `pages_background_color` | Appearance; ignore. `page_logo.contents` and `pages[].logo_contents` are base64 images: skip them. |

**Role of a page in the graph** *(observed)*:

| Inbound links | Outbound links | Role |
|---|---|---|
| 0 | ≥ 1 | **Entry point**: a form opened by URL; each submit starts a run. |
| ≥ 1 | ≥ 1 | Mid-flow step: shows upstream data (pills in element `content`), waits for the human to submit, then continues. |
| ≥ 1 | 0 | Final display page (results, confirmation, redirect). |

**Output on submit:** `{ "body": { "<field slug>": value, ..., "button": "<label or submission value>" }, "headers": { "email": "...", "request_ip": "...", ... } }`

- Input field key = slug of the field's `name` *(confirmed)*: field `Product name` → `order_form.body.product_name`.
- `body.button` = the pressed button's label, or its custom submission value if one is set (docs). The label is the BUTTON's `content`; that `default_value` holds the submission value is inferred. Stories branch on `body.button` when a page has several buttons.
- Input field types: `SHORT_TEXT`, `LONG_TEXT`, `OPTION` (value is a list of selected options per the docs sample), `BOOLEAN`, and per docs email, web URL, date/time, number, file upload (`{name, type, contents}`), password. Display types: `TITLE`, `PARAGRAPH`, `DIVIDER`, `TABLE`, `BUTTON`, and per docs image, map.
- Element strings (`content`, `default_value`, `options`) use section 5 syntax, including `=formula` (`"options": "=RESOURCE.team_list"`, TABLE `"content": "=build_rows"`) and control tags.
- Other actions get the page URL with `PAGE.<page slug>`.
- Field, container and condition keys in detail: extras file.

### 7.9 Other types

| Item | What is known |
|---|---|
| IMAPAgent, LLMAgent, RunScriptAgent, RecordAgent, Case tool, MCP server | See [tines-story-format-extras.md](tines-story-format-extras.md). |
| Templated action | A normal agent (usually HTTPRequestAgent) with `template.created_from_template_guid` set and often `INPUT.x` references. Treat as its base type; resolve `INPUT.x` through top-level `integrations` (worked example in the extras file). |
| Unknown `type` | Do not guess. Report the type and its `options` to the user. |

## 8. One export, many workflows

A story is a canvas, not a single program. *(observed)* One export held **more than 40 unconnected sub-graphs** at top level: about half started by a schedule, the rest by a webhook, by a page, or by nothing at all. More than half of them were just "trigger → one GroupAgent", with the actual work (from a handful to more than 150 actions) inside the group.

**Procedure to split an export into workflows:**

1. Build the undirected graph of top-level `agents` and `links`. Each connected component is one candidate workflow.
2. Find each component's entry points:

| Entry point | How to recognise it |
|---|---|
| Schedule | Agent with a non-empty `schedule` list. Several cron entries = several schedules for the same workflow. |
| Webhook | `Agents::WebhookAgent`. |
| Page | `Agents::FormAgent` with no inbound link. |
| Email | `Agents::IMAPAgent`. |
| Sub-story call | Agent whose `guid` = top-level `entry_agent_guid`. |

3. A component with **no entry point** only runs when a person clicks "run" in Tines: a manual utility, a test or leftover. Report it; do not translate it unless asked.
4. Skip components where every agent is `disabled`.
5. For "trigger → GroupAgent" components, the workflow body is `group.agents` / `group.links`; start reading at the GroupInputAgent.
6. Treat each element of `send_to_stories` as one more workflow (a callable one). Several workflows may call the same sub-story.
7. One component can have more than one entry point (two schedules feeding one chain; a page and a webhook). Keep them together.

**Shared state between workflows.** Workflows in one story (and in other stories) often communicate only through resources: one workflow writes a resource through the Tines API, another reads `RESOURCE.x`. No link shows this dependency. Find it by listing, per workflow, the resources it reads (`RESOURCE.x`) and writes (HTTP calls to `/api/v1/global_resources/...`, extras file).

**What an export does not contain:**

| Missing | Consequence |
|---|---|
| Resource **values** (lookup tables, connection settings, stored lambdas, state) | Only names are visible. Ask the user for the content of each one. |
| Credential values and types | Only names are visible. |
| Sub-stories that are called but not embedded | Ask for their exports. |
| Record type data, case data, event history | Not needed to read the logic. |

An export **does** contain, in clear text: webhook `path` and `secret`, page `url_identifier`, email addresses, internal hostnames. Treat it as sensitive.

## 9. Unverified items

Neither the docs nor the two exports settle these. Confirm with the user or the story's real behaviour before relying on them.

1. Links: `link_type` value for failure paths; how Condition **Paths** appear in `options` / `links`.
2. Rules: `field==null` (inferred); type coercion; regex anchoring and case.
3. References: result for an action not on the event's path (assumed null); written form of the `raw` tag.
4. Options: JSON values of `emit_failure_event`; `loop` on HTTPRequestAgent; meaning of status `0`; implode output order; whether an `automatic` script is exported; that throttle `capacity` equals the docs' `runs_per_interval`.
5. Groups: direct visibility of parent actions from inside; behaviour when Output is reached more than once; whether a GroupAgent itself can be scheduled (its `schedule` key exists, always `null`).
6. Pages: `visibility` values other than `world` / `tenant`; that `story_run` is the UI's "Move to next page"; output shape of field types not seen in the export.
7. Story keys: mapping of `api_entry_action_guids`, `api_exit_action_guids`, `synchronous_webhooks_enabled` to "Workflows as APIs".
8. Extras file: LLMAgent key names, RecordAgent output, Case and MCP server export shapes.

## Copied actions (clipboard JSON)

Copying actions from the storyboard gives JSON that holds the same things as
an export with different spelling. `scripts/tines_outline.py` converts it when
it loads the file, so the outline looks the same and you do not handle this
yourself. Seen in one real sample:

| Export | Copied actions |
|---|---|
| `standard_lib_version`, `diagram_notes` | `standardLibVersion`, `diagramNotes` |
| `"type": "Agents::HTTPRequestAgent"` | `"type": "httpRequest"` (also `eventTransformation`, `trigger`, `group`) |
| `options` is an object | `options` is a string holding JSON |
| links: `source`, `receiver`, `"link_type": "secondary"` | links: `sourceIdentifier`, `receiverIdentifier` (index, as a number or a string), `"linkType": "NO_MATCH"` |
| a group's actions in `group.agents` | in `group.actions` |
| positions in `diagram_layout` | `position` on each action |

There is no story name, no `guid`, and no pages, integrations or
send-to-story settings. The short type names of other action kinds (email,
webhook, send to story, group input and output) are **(unverified)**.
