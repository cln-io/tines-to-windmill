# Tines story export format: extras

Rarely needed parts. Read [tines-story-format.md](tines-story-format.md) first; the same markers apply: *(observed)* = shape seen in a real export, shown with **invented names and values**; **(unverified)** = settled by neither docs nor exports.

## Contents

- [E1. IMAPAgent (Receive Email)](#e1-imapagent-receive-email)
- [E2. LLMAgent (AI Agent)](#e2-llmagent-ai-agent)
- [E3. RunScriptAgent](#e3-runscriptagent)
- [E4. RecordAgent](#e4-recordagent)
- [E5. Case tool, MCP server](#e5-case-tool-mcp-server)
- [E6. Page elements in detail](#e6-page-elements-in-detail)
- [E7. Tines API calls that read and write resources](#e7-tines-api-calls-that-read-and-write-resources)
- [E8. Templated action: resolving `INPUT`](#e8-templated-action-resolving-input)

## E1. IMAPAgent (Receive Email)

Entry point; cannot receive events. `mode`: `email` (default; a generated inbox address, no other option needed) or `imap` (polls a server on its `schedule`).

| Option (`imap` mode) | Meaning |
|---|---|
| `host`, `port`, `ssl` | Server. |
| `username`, `password` | Login; `password` is normally `<<CREDENTIAL.x>>`. `authentication_type`: `LOGIN` (default) or `XOAUTH2`. |
| `folders` | List of folder names to watch. |
| `mark_as_read` | Default `false`. |
| `mime_types`, `include_rfc822`, `disable_ssl_verification`, `use_tunnel` | Details. |

Output, one event per new email (duplicates by Message-Id are skipped; the first visit to a folder emits nothing):

```json
{ "message_id": "...", "folder": "INBOX", "subject": "...", "from": "bob@example.com", "to": ["..."], "cc": ["..."],
  "date": "2018-01-01T10:10:00+00:00", "mime_type": "text/plain", "body": "...", "has_attachment": true,
  "attachments": [ { "filename": "hello.txt", "guid": "...", "md5": "...", "sha256": "...", "sizeinbytes": 1578, "base64encodedcontents": "..." } ] }
```
`email` mode adds `headers` (object of raw mail headers) and has no `folder`. Neither export contains an IMAPAgent; this section is from the docs.

## E2. LLMAgent (AI Agent)

Docs give UI labels and two JSON examples; other key names are **(unverified)**. Neither export contains one.

| Option (JSON key seen in docs) | Meaning |
|---|---|
| `mode` | `task` (default: one-shot or autonomous tool loop) or `chat` (interactive chat page; ends when the goal in the instructions is reached). |
| `prompt` | Task-mode user prompt; usually contains pills. |
| `instructions` | System instructions. |
| `image` | Base64 image or list of images. |
| Model, fallback models, temperature (default 0.2), timeout (default 30 s), retries (default 25), output schema (JSON schema), tools | Key names unverified. Tools = templates, Send to Story stories, custom tools (actions in this story), MCP servers, built-ins (think, code analysis, web search). |
| `initial_message`, `url_identifier`, `visibility`, `idle_timeout_minutes`, `pages_*`, `page_logo`, `page_mode` | Chat mode page settings (same family of keys as FormAgent). |

Output:

- `{ "output": "Estimated severity: high" }`. `output` is parsed into an object when the model returns valid JSON or an output schema is set.
- With tools or chat: also `steps` (list of `{role, text}` / `{role: "tool", tool_name, inputs, output}`).
- Usage data (`input_tokens`, `output_tokens`, `model`, `duration`, credits): docs name the field `metadata` in one place and `meta` in another.
- Chat idle timeout: `meta.outcome` = `idle_timeout`.

## E3. RunScriptAgent

```json
{ "type": "Agents::RunScriptAgent", "name": "Count rows", "schedule": null,
  "options": { "language": "python", "script": "def main(input):\n    return {\"count\": len(input[\"rows\"])}",
               "input": { "rows": "=get_rows.body.rows" }, "timeout": "30", "requirements": "requests==2.32" } }
```
*(observed shape; content invented)*

| Option | Meaning |
|---|---|
| `language` | `python` *(observed)*. Docs also describe an AWS CLI runtime; its value is **(unverified)**. |
| `script` | Source code as one string. Must define `def main(input):`. |
| `input` | Object; values use section 5 syntax and are evaluated before the script runs. Read in the script as `input["key"]`. |
| `requirements` | requirements.txt content (one package per line). |
| `timeout` | Seconds (string or number), default 10, max 110. |
| Networking mode (standard / dedicated / none) | UI setting; key name **(unverified)**. |

Output: the value returned by `main` (docs). Read as `<slug>.<returned key>`; here `count_rows.count`. Not confirmed by a downstream reference in the exports.

## E4. RecordAgent

Writes to or reads from a Tines Records table (structured storage inside Tines). Besides `options`, the agent has two extra top-level keys.

```json
{ "type": "Agents::RecordAgent", "name": "Capture run", "schedule": null,
  "options": { "mode": "create", "parent": "", "case_ids": "" },
  "record_type": { "id": 12, "name": "Run log", "editable": true,
    "record_fields": [ { "id": 301, "name": "Item title", "description": null, "result_type": "TEXT", "fixed_values": [] } ] },
  "record_writers": [
    { "formula": "<<get_item.body.title>>", "include_in_update": false,
      "record_field": { "id": 301, "name": "Item title", "description": null, "result_type": "TEXT", "fixed_values": [] } },
    { "formula": "=get_item.body.shipped_at", "include_in_update": false,
      "record_field": { "id": 302, "name": "Shipped at", "description": null, "result_type": "TIMESTAMP", "fixed_values": [] } } ] }
```
*(observed shape, trimmed; names and values invented)*

| Part | Meaning |
|---|---|
| `options.mode` | `create` *(observed)* = insert one row. Docs also mention get and list modes (with `resolve_artifacts`); update / delete likely exist **(unverified)**. |
| `options.parent`, `options.case_ids` | Optional link to a parent record / to cases. Empty string = none. |
| `record_type` | The table: `name` and its columns `record_fields[]`. The schema **is** in the export; the stored rows are not. |
| `record_writers[]` | **One entry per column written**: `formula` (section 5 syntax) gives the value for `record_field.name`. Columns of `record_type` without a writer are left empty. |
| `result_type` | `TEXT`, `TIMESTAMP`, `ARTIFACT` (large text / JSON) *(observed)*; docs also list number, true/false and fixed-value text (`fixed_values`). |

- Type handling (docs): a timestamp is stored as `%Y-%m-%d %H:%M:%S`; a value of the wrong type is stored as empty and logs an error.
- Timestamp and story name are always captured automatically.
- Output shape is **(unverified)**. The action passes the event on, so it can sit in the middle of a chain. Other actions reach record ids through `INFO.record.<type slug>.id` and `INFO.record.<type slug>.fields.<field slug>.id`.

## E5. Case tool, MCP server

| Item | What is known (docs only; not in either export) |
|---|---|
| Case tool ("Create case") | Creates or updates a Tines Case from a template or blank, with formulas for the content. Export `type` and options **(unverified)**. |
| MCP server | A storyboard template that exposes tools (templates, Send to Story, custom tools) at `/mcp/<path>`, with webhook-style access control. Cannot be placed in a group. Export `type` **(unverified)**. |

If one appears, report its `type` and `options` to the user instead of guessing.

## E6. Page elements in detail

Each element of top-level `pages` *(observed keys)*:

| Key | Meaning |
|---|---|
| `agent_guid` | `guid` of the FormAgent this page belongs to. |
| `fields` | Input and display elements (table below). |
| `containers` | Layout boxes: `{guid, name, layout: "vertical", ranking, category, alignment, spacing, loop, user_driven_loop}`. `loop` (a list reference, empty string = none) repeats the container once per element (docs: "looping page elements"). |
| `conditions` | Show/hide rules: `{ "condition_type": "show", "match_rule": "any_rule", "container_guids": ["c2"], "rules": [ { "rule": "is_empty", "page_element_guid": "<field guid>", "value": "", "match_case": true } ] }`. Display logic only. Other `rule` names **(unverified)**. |
| `visibility`, `success_message`, `loading_message` | Copies of the FormAgent settings. |
| `logo_contents`, `logo_filename`, `display_logo`, `icon`, `display_mode`, `sso_groups`, `app` | Appearance and access; ignore (`logo_contents` is a long base64 string). |

Keys shared by every element of `fields`: `guid`, `name`, `description`, `type`, `ranking` (order inside its container), `container_guid`, `width`, `width_type`, `width_fixed_px`.

| `type` | Extra keys | In `body`? |
|---|---|---|
| `SHORT_TEXT`, `LONG_TEXT` | `required`, `default_value`, `max_characters`, `validation_pattern`, `validation_error_message` | yes, text |
| `OPTION` | `options` (list of strings, or one `=formula` string), `multi_select`, `style`, `is_searchable`, `required`, `default_value` | yes; a list per the docs sample |
| `BOOLEAN` | `required`, `default_value`, `boolean_label_true`, `boolean_label_false` | yes, true/false |
| `BUTTON` | `content` (label), `default_value`, `style` (`primary` / `secondary`) | as `body.button` |
| `TITLE`, `PARAGRAPH` | `content` (text or Markdown; may hold pills and control tags) | no |
| `TABLE` | `content` (an `=formula` giving a list of rows), `allow_table_row_selection`, `is_searchable` | no (row selection output **(unverified)**) |
| `DIVIDER` | none | no |

- The `body` key of an input element is the slug of its `name` (main file, slug rule).
- Docs list more input types (email, web URL, date or time, number, slider, file upload, password) and display types (image, map); their `type` strings are **(unverified)**.
- URL query parameters named after field slugs pre-fill a page (`...?product_name=abc`); a formula `default_value` overrides them.

## E7. Tines API calls that read and write resources

Stories change resources by calling the Tines REST API with an ordinary HTTPRequestAgent. Recognise these calls by `/api/v1/global_resources` in `url`. They are **state updates**, not calls to an external system.

```json
{ "url": "<<RESOURCE.platform_api.url>>/api/v1/global_resources/<<INFO.resource.poll_cursor.id>>/replace", "method": "post",
  "content_type": "json", "payload": { "key": "=explode_teams.team.id", "value": "<<compute_latest.ts>>" },
  "headers": { "Authorization": "Bearer <<CREDENTIAL.platform_api_key>>" } }
```
*(observed; names invented. Also observed: a literal URL with a numeric resource id, `https://tenant.example.com/api/v1/global_resources/4410/replace`, and an `x-user-token` header instead of `Authorization`.)*

| Method and path | Payload | Effect |
|---|---|---|
| `PUT /api/v1/global_resources/<id>` | `{ "value": ... }`, optionally `"name"` | Replace the whole value. |
| `POST /api/v1/global_resources/<id>/replace` | `{ "key": k, "value": v }` (object) or `{ "index": i, "value": v }` (list); optional `if_value` (compare-and-swap, 422 on mismatch) | Replace one key or one element. |
| `POST /api/v1/global_resources/<id>/append` | `{ "value": v }` | Append a string or list. |
| `POST /api/v1/global_resources/<id>/remove` | `{ "key": k }` or `{ "index": i }`; optional `if_value` | Remove one key or element. |
| `GET /api/v1/global_resources/<id>` or without id | none | Read one resource / list resources (same data as `RESOURCE.x`, but fresh). |

- `<id>` is a literal number or `<<INFO.resource.<slug>.id>>`. In the second form the slug tells you which `RESOURCE.<slug>` is being written.
- The tenant host is a literal, `META.tenant.domain`, or a value kept in a resource.
- Writes are not queued: two runs that read-modify-write the same resource can overwrite each other (docs). Per-key `replace` / `append` avoid most of this.
- Reading: `RESOURCE.x` anywhere, `GET(RESOURCE.x, key)` for a dynamic key.

## E8. Templated action: resolving `INPUT`

*(observed)* The action:

```json
{ "type": "Agents::HTTPRequestAgent", "name": "Retrieve chart image", "guid": "e96c4682...",
  "options": { "url": "https://charts.example.com/images/<<INPUT.job_id>>.png", "method": "get" } }
```

The matching element of top-level `integrations`:

```json
{ "action_guid": "e96c4682...", "product": "Chart service",
  "action_inputs": [ { "name": "Job ID", "type": "TEXT", "required": true, "value": "\"<<find_or_render_chart.body.job.id>>\"" } ] }
```

Steps: (1) find the `integrations` element with `action_guid` = the agent's `guid`; (2) slug each input `name` (`Job ID` → `job_id`); (3) JSON-decode `value`; (4) substitute it for `INPUT.<slug>`. Result: `INPUT.job_id` = `find_or_render_chart.body.job.id`. For a templated GroupAgent do the same with `GROUP_INPUT.<slug>` inside the group. Input `type` values seen: `TEXT`, `OPTION`, `CREDENTIAL`.
