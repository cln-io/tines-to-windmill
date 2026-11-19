# Tines formula functions: Story Metadata

Independent, unofficial porting notes for the functions Tines files under "Story Metadata": what each one does, edge cases that matter in a port, and a TypeScript (Bun) equivalent.
The Tines documentation is the authority; every entry links to its page. Examples are illustrative and were written for this catalogue.
Look up one function with `python3 scripts/tines_fn.py NAME`. Conventions and the full list are in `INDEX.md`. "Not specified in docs" means the Tines page is silent, so do not assume.

Functions in this file: PROMPT, STORY_RUN_GUID, STORY_RUN_LINK, WORKBENCH_LINK

## PROMPT

- **Summary:** URL that resumes the current action with a new event when opened
- **Signature:** `PROMPT("text")`
- **Categories:** Story Metadata
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/prompt/

**Arguments**

- `text` (optional): A status word, readable afterwards as `status` on the resulting event. It must be URL-encoded already, since it travels in the query string.

**Returns:** A URL on the Tines tenant with query parameters identifying the action and event, plus the status text.

**Porting semantics**

- Opening the URL makes the action that produced it emit a fresh event; this is the building block for "wait for a person to click".
- Tines-platform feature: the URL only works against a Tines tenant.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: PROMPT("approve")
output:  a tenant URL ending in the status text; in the port, a Windmill resume link
(not executed: depends on a running Windmill flow (wmill.getResumeUrls) or a Tines tenant)
```

**TypeScript equivalent** (APPROXIMATE: no formula-level equivalent; replace the pattern with a Windmill approval/suspend step)

```ts
import * as wmill from "windmill-client";
// In a flow step configured to suspend: send these links instead of the PROMPT() URL.
const { approvalPage, resume, cancel } = await wmill.getResumeUrls();
// e.g. one link per choice: `${resume}?status=approve`
```

- Restructure rather than translate: the action containing PROMPT() becomes a step that sends the resume link and suspends; the actions downstream of the prompt event become the steps after the suspend. The clicked choice arrives as the resume payload.

## STORY_RUN_GUID

- **Summary:** identifier of the story run in progress
- **Signature:** `STORY_RUN_GUID()`
- **Categories:** Story Metadata
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/story-run-guid/

**Arguments**

- None.

**Returns:** Text: the GUID of the current story run.

**Porting semantics**

- The identifier is the same for every event of one run; splitting an event into many with an explode does not change it.
- That makes it usable as the grouping key of an implode that should gather a whole run. Downstream of an explode it is too coarse: events belonging to different exploded items share it and would be merged silently.
- Downstream of an explode, group by the explode's own guid (with its size as the expected count) to rebuild the list, or by guid plus item index to rejoin the branches of one item.
- A group shares the run of the story that calls it, whereas sending to another story starts a separate run with a different identifier.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STORY_RUN_GUID()
output:  the run's identifier; in the port, the root flow job id (here the test set WM_ROOT_FLOW_JOB_ID to "0198c2f4-root")
```

**TypeScript equivalent** (APPROXIMATE: Tines-platform value; the closest Windmill notion is the root flow job id)

```ts
process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID
```

- When the GUID is only used as an implode identifier it usually disappears in the port: a Windmill for-loop step already returns the collected results of its iterations.
- When it is used as a correlation id in logs or outbound requests, the root flow job id serves the same purpose.

## STORY_RUN_LINK

- **Summary:** URL of the story run in progress
- **Signature:** `STORY_RUN_LINK([mode: "story_runs"])`
- **Categories:** Story Metadata
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/story-run-link/

**Arguments**

- `mode` (optional): `"story_runs"` (the default) links to the run; `"action"` links to the current action with its events narrowed to this run.

**Returns:** A URL on the Tines tenant pointing at the story and the run.

**Porting semantics**

- The documented signature writes the argument by name, while a docs example passes it by position; both spellings may occur in stories.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: STORY_RUN_LINK()
output:  in the port, a link to the Windmill flow run (here "https://wm.example.org/run/0198c2f4-root?workspace=ops" from test environment variables)
```

**TypeScript equivalent** (APPROXIMATE: Tines-platform value; replaced by a link to the Windmill flow run)

```ts
`${process.env.WM_BASE_URL}/run/${process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID}?workspace=${process.env.WM_WORKSPACE}`
```

- There is no per-action equivalent of `"action"` mode; link to the flow run.

## WORKBENCH_LINK

- **Summary:** URL that loads the incoming event data in Tines Workbench
- **Signature:** `WORKBENCH_LINK()`
- **Categories:** Story Metadata
- **Source page:** https://www.tines.com/stories/docs/formulas/functions/workbench-link/

**Arguments**

- None.

**Returns:** A URL that opens Tines Workbench with the current event's data loaded, for a viewer who is allowed to see that event.

**Porting semantics**

- Tines-platform feature (Workbench is Tines' AI chat interface); the docs give no example output.

**Examples (illustrative, not from the Tines docs)**

```text
# 1
formula: WORKBENCH_LINK()
output:  a Tines Workbench URL; the port substitutes a link to the flow run
```

**TypeScript equivalent** (APPROXIMATE: no Windmill equivalent; substitute a link to the flow run or drop the link)

```ts
`${process.env.WM_BASE_URL}/run/${process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID}?workspace=${process.env.WM_WORKSPACE}`
```

- Mention the substitution in the port notes so a human can decide whether the link is still wanted.
