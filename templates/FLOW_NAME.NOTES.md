# my_flow (Tines workflow wNN, "ENTRY ACTION NAME")

One or two sentences: what the flow does and what starts it.

## 1. Setup

Create these before the first run. Never write a secret value in this file.

| Path | Kind | Secret | Holds |
|---|---|---|---|
| `f/my_folder/api_key` | variable | yes | API key of the item service: was `CREDENTIAL.api_key` |
| `f/my_folder/item_api` | resource (custom type `c_item_api`) | no | keys `url`, `timeout`: was `RESOURCE.item_api` |
| `f/my_folder/item_api_base_url` | variable | no | base URL of the item server (describe the system; do not write an internal host name here) |
| `f/my_folder/request_form_url` | variable | no | URL of the form or app that replaces the Tines page `Request form`: was `PAGE.request_form` |
| `f/my_folder/my_flow_state` | variable | no | JSON state, create it with the value `{}`: was `RESOURCE.my_flow_state` |

Trigger: schedule file `f/my_folder/my_flow.schedule.yaml` (`0 */20 * * * *`, Europe/Dublin; Tines: `*/20 * * * *`).
Or: the webhook URL and the JSON body the sender must post. Or: the users run the flow from its form.

Depends on: `f/my_folder/other_flow` (Tines sub-story `other_story`, not ported yet; inputs `item_id`).

### Webhook entry (delete this block when the flow is not started by a webhook)

- Who calls the Tines webhook today, and that this sender must be pointed at the Windmill URL of the flow.
- The Tines webhook secret is not used any more: the sender needs a Windmill token (never write either value here).
- What the sender gets back: Tines answered with (say what); Windmill answers with a job id, unless the flow is called on its "run and wait for result" URL.

## 2. Mapping

| Step | Tines actions |
|---|---|
| flow inputs | a01 entry action |
| `http_get` | a02 Get item, a03 200 |
| `loop_rows` / `http_post` | a04 explode rows, a05 Post label |

## 3. Behaviour differences

One entry per difference: the Tines action and its id, what the story did, what the flow does, what the user will notice.

- **`slow down` (a06)** limited the state writes to 4 per minute. The flow writes the state once per run, so no limit is needed. The main work was never throttled.
- **Deliberate change:** ...

## 4. Not ported

- Dropped actions with the reason: `debug copy` (a07): dead end, nothing reads its output.
- Every stub, with its message: `short_title` throws `MISSING: Tines resource text_tools.shorten`. Needed: the lambda's definition.
- Credentials used only to call the Tines API: `CREDENTIAL.tines_api_key`.

## 5. Not verified

- The flow has not been run. (After a test run in step 10: replace this line with what was run,
  when, and the TEST result. Do not leave both.)
- The TypeScript files were checked for syntax only (say with which tool, or say that they were not checked).
- Each formula or action whose Tines behaviour you were not sure of, and how you read it.
- Each pill that puts an array or an object into a request body or a message: Tines does not specify the rendering; the flow sends JSON.
- Each Windmill behaviour you rely on that is marked "not verified" in the references.
