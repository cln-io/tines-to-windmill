---
name: tines-to-windmill
description: Translate an exported Tines story (JSON) into one or more Windmill flows (flow.yaml plus TypeScript step files). Use when the user gives a Tines story export and wants it ported, migrated or rewritten for Windmill.
allowed-tools: ["execute_code"]
compatibility: Needs a way to run Python 3 and to write files (a code sandbox or a shell).
---

# Translate a Tines story into Windmill flows

You are porting automation from Tines to Windmill. A Tines story export is a
JSON file of actions and links. A Windmill flow is a folder holding `flow.yaml`
and one TypeScript file per step.

## Where things are

- `SKILL_DIR` is this skill's folder. In a chat sandbox it is usually
  `/mnt/data/skills/tines-to-windmill`. In a coding agent it is the folder
  this file is in. Paths such as `scripts/...` and `references/...` below are
  inside `SKILL_DIR`.
- `S` is the path of the story export the user gave you. In a chat sandbox,
  uploaded files are usually under `/mnt/data`. If you cannot find it, list
  that folder. If there is no export, ask the user to attach one.
- `OUT` is where you write results. In a coding agent, use the project folder.
  In a chat sandbox, use `/mnt/data/out`, and when a workflow is finished zip
  that folder and give the user the zip.
- You need to run Python 3 scripts. If you have no tool that runs code, stop
  and tell the user that this skill needs code execution turned on.

## Rules that always apply

1. **Never read the story JSON directly.** It is mostly noise and can be
   megabytes. Read it only through `scripts/tines_outline.py`.
2. **One workflow at a time.** One story often holds many independent
   workflows. Each becomes its own flow folder. Finish and validate one before
   starting the next.
3. **Port the behaviour, not the actions.** Several Tines actions usually
   become one script step. Do not create one Windmill step per Tines action.
4. **Account for every action.** Each action of the workflow is either mapped
   to a step or marked `DROPPED` with a reason in `tines_action_map.md`.
5. **Never guess what the export does not contain.** Resource values, lambdas
   stored in resources, credential values and sub-stories that are not embedded
   are missing. Ask the user, or write a stub that throws an error naming what
   is missing.
6. **Never write a secret value into any file.** Refer to it by variable or
   resource path. The export can contain webhook secrets and internal
   hostnames: do not copy them into the flow.
7. **Never deploy.** Do not run `wmill sync push` or `wmill flow push` unless
   the user asks.
8. **Code goes in separate files.** In `flow.yaml` write
   `content: "!inline <step_id>.ts"`, with the quotes. Do not embed code in YAML.
9. **You are done with a workflow only when** `scripts/validate_flow.py` ends
   with `RESULT: OK` and you have written the notes file from step 8.

## Which file to open when

Open a reference only when you need it. Do not load them all.

| You need to | Open |
|---|---|
| Understand an action type, its options, or how events flow | `references/tines-story-format.md` (section 7 has one part per action type) |
| A rare action type: IMAP, AI, run script, record, case | `references/tines-story-format-extras.md` |
| Read formula syntax: `<<pills>>`, `=FORMULA()`, operators, `<%if%>` / `<%for%>` tags | `references/tines-formula-language.md` |
| Translate one formula function to TypeScript | `references/tines-formulas-to-ts.md`, or run `scripts/tines_fn.py NAME` |
| See a full formula translated | `references/tines-formulas-examples.md` |
| Write `flow.yaml`: step types, expressions, loops, branches, triggers | `references/windmill-openflow.md` |
| See the whole method applied once | `references/worked-example.md` |
| See a complete story export and its finished flow | `examples/cold-chain/` |

`scripts/tines_fn.py NAME` prints full documentation for one formula function
from a local catalogue. If it says the catalogue is absent, use the lookup
table in `references/tines-formulas-to-ts.md` instead.

## Process

### Step 1. Get the index and make a plan

```
python3 scripts/tines_outline.py S --index
```

The index lists every workflow (`w01`, `w02`, ...), its entry point (schedule,
webhook or page), its size, the credentials and resources it uses, embedded
sub-stories (`s1`, ...), stories that are called but not in the export, and
resources that are called as functions.

Write `OUT/PLAN.md` with one line per workflow:

```
w04 | sync_open_tickets | schedule 15 6 * * * Europe/Oslo | 7 actions | TODO
```

- Give each workflow a short snake_case flow name.
- Mark `DISABLED` workflows and pieces with no entry point as `SKIP`, unless
  the user asked for them.
- An embedded sub-story that several workflows call becomes one shared flow.
  Port it first, because the callers depend on it.
- If there are more than three workflows, show the user the plan and ask which
  ones to port. Then work through them in order, updating `PLAN.md` as you go.

### Step 2. Read one workflow

```
python3 scripts/tines_outline.py S --workflow w04
```

Every output starts with a line giving its size. If the workflow is too big to
print at once, you get an overview that lists the exact next commands
(`--graph`, `--group a016`, `--actions a016.001-a016.066`, `--page a031`).
Run `--graph` first to see the shape, then read the details part by part. Use
`--action a07` to see one action in full.

While reading, write down:

- the entry point and its trigger details (every cron line with its timezone,
  or the webhook path and verbs, or the page fields);
- where the workflow branches, loops, fans out and joins;
- which actions are dead ends: nothing reads their output and they have no
  outside effect;
- every `CREDENTIAL.x`, `RESOURCE.x` and `STORY.x` it uses.

### Step 3. Create the folder and the action map

```
mkdir -p OUT/f/<folder>/<flow_name>.flow
python3 scripts/tines_outline.py S --map-template --workflow w04 > OUT/f/<folder>/<flow_name>.flow/tines_action_map.md
```

Ask the user for `<folder>` if they did not give one. If the project has a
`wmill.yaml` with `nonDottedPaths: true`, the folder suffix is `__flow`, not
`.flow`.

The map has one line per action, such as `a01 -> TODO   # fetch orders [http_request]`.
You fill it in at step 6. Never delete a line.

### Step 4. Collect what the export does not contain

Before writing code, list what is missing for this workflow and ask the user
once, in one message:

- the value of each `RESOURCE.x` that holds a lookup table, settings or a lambda;
- the export of each called story that the index marks as not in the export;
- which Windmill folder, and which existing variables or resources, to use.

If the user cannot answer now, continue. For each missing piece write a stub
that throws, for example
`throw new Error("MISSING: Tines resource text_helpers.shorten - definition not in export")`,
and list it in the notes file.

### Step 5. Design the steps

Group the actions into steps using this table. Read
`references/worked-example.md` section 2 if you are unsure how to group.

| Tines shape | Windmill |
|---|---|
| Schedule on an action | Separate `<flow_path>.schedule.yaml`. Windmill cron has 6 fields with seconds first: Tines `*/5 * * * *` becomes `0 */5 * * * *`. Keep the timezone. One file per cron line. |
| Webhook action | Flow inputs for the body fields. The flow's built-in webhook, or an `http_trigger.yaml` for a custom path. Add a preprocessor if headers or query are needed. |
| Page (form) that starts a workflow | Flow input `schema` with one property per page field. Tell the user that a styled public page needs a Windmill app. |
| Page in the middle of a workflow | A step with `suspend` (approval or resume form). |
| HTTP request | `rawscript` in `bun` using `fetch`. |
| HTTP request followed by status triggers (`200`, `404`) | The same script: check `res.status` and throw or return. |
| Retry settings, or a trigger -> delay -> back-link loop | Step-level `retry`, or a bounded loop inside the script. Always set a maximum. |
| Event transform, message-only | Fold into the script of the next step that uses it. Keep a separate step only when several later steps read it. |
| Explode -> per-item work -> implode | `forloopflow`. The loop result is the array. Drop the prep and implode plumbing. |
| Trigger with a no-match link (if / else) | `branchone`. |
| One action linking to several actions | `branchall` if a later step needs all the results. Otherwise put them in sequence. |
| Group action | Inline its steps. Make it a separate flow, called with `type: flow`, only if several workflows use it. |
| Send to story | `type: flow` with the path of the ported story. |
| Deduplicate | A script that keeps seen keys in `wmill.getState()` / `setState()`. |
| Throttle | First check which branch it is on: it limits only the actions after it. On the main work: flow `concurrent_limit` or step `sleep`. On a side branch (for example state writes only): often nothing is needed. Say what you did in the notes. |
| Delay | Step `sleep`. |
| Email action | A script with `nodemailer` and an `smtp` resource. |
| Resource read (`RESOURCE.x`) | Settings or lookup table: a Windmill resource or a non-secret variable. |
| Resource written through the Tines API | State: `setState` if one step both reads and writes it. Otherwise a non-secret variable holding JSON. |
| `CREDENTIAL.x` | A secret variable `f/<folder>/<x>`, or a typed resource. |
| `STORY_RUN_GUID()`, `META.story_run.id` | The `WM_JOB_ID` environment variable. Say so in the notes. |
| Calls to the Tines API for anything else | No equivalent. Stub it and report it. |
| Disabled or unreachable action | Not ported. Inside the workflow it is already `DROPPED` in the map. Disabled chains outside the workflow have no map line. |

Design rules:

- Aim for fewer steps than actions. A simple chain of HTTP calls and transforms
  for one purpose is one script.
- Step ids are snake_case, unique in the whole flow, and say what the step does
  (`fetch_alerts`, not `http_request_3`).
- When behaviour must change because Windmill has no exact equivalent, pick the
  safer behaviour and write it down for the notes file.
- Do not copy dead ends. Do not add features the story does not have.

### Step 6. Write the flow

Write `flow.yaml` and one `<step_id>.ts` per step. Follow
`references/windmill-openflow.md` sections 2 to 6.

- Every parameter of `main` needs an entry in that step's `input_transforms`,
  and every entry needs a parameter.
- A step sees `flow_input.<name>` and `results.<step_id>` of earlier steps in
  the same sequence or an enclosing one. A step inside a loop or branch is not
  visible from outside: use the result of the loop or branch itself.
- Inside a loop the current item is `flow_input.iter.value`.
- Translate each formula with the references. Watch the traps in
  `references/tines-formulas-to-ts.md` section 3. In Tines only `FALSE` and
  `NULL` are falsy, a missing path gives `NULL` and does not throw, and
  `DATE` formats are strftime.
- Text with `<%for%>` or `<%if%>` tags becomes a function that builds the
  string with ordinary loops. See `references/tines-formula-language.md` section 8.
- Scripts throw on failure. Do not catch an error only to hide it.
- If the story uses credentials or settings that differ per environment, make
  the variable path a flow input with a default.

Then fill in `tines_action_map.md`. Replace every `TODO` with one of:

```
a01 -> fetch_orders                 step id that does this work
a12 -> enrich, summarize            several step ids
a03 -> flow_input.shop_ids          the action became a flow input
a34 -> DROPPED: output never used   not ported, with the reason
```

Write the trigger file next to the flow folder if the workflow has a schedule.

### Step 7. Validate and fix

```
python3 scripts/validate_flow.py OUT/f/<folder>/<flow_name>.flow --story S --workflow w04
```

Each finding is one line: `ERROR|WARN [check] where: what is wrong. Fix: ...`.
Fix every `ERROR`, read every `WARN`, and run it again. Repeat until the last
line is `RESULT: OK`. Fix the flow, not the map: do not mark an action
`DROPPED` only to make the report pass.

The validator cannot check TypeScript syntax or whether the logic is right. If
`bun` or `wmill` is installed, also run `bun build <step>.ts --outdir /tmp/x`
on each step or `wmill lint <flow folder>`.

### Step 8. Write the notes file

Write `<flow_name>.NOTES.md` next to the flow folder, then mark the workflow
`DONE` in `PLAN.md`. The notes file has these parts:

1. **Setup.** Every variable and resource to create, with its path, whether it
   is secret, and what it holds. The schedule or webhook to enable.
2. **Mapping.** A table of Tines actions to Windmill steps, grouped by step.
3. **Behaviour differences.** Each place where the flow does not behave exactly
   like the story, and why.
4. **Not ported.** Dropped actions with reasons, and every stub that throws
   `MISSING`.
5. **Not verified.** State plainly that the flow has not been run, plus any
   formula or action whose Tines behaviour you were not sure of.

Then tell the user which workflow is finished, list the open questions, and
continue with the next workflow in `PLAN.md`.

## Common mistakes

- Reading the raw export, or printing a whole large workflow with `--full`.
- One step per Tines action, including prep, implode and trigger plumbing.
- Referencing `results.<id>` of a step that is inside a loop or branch.
- Leaving Tines syntax in the flow: `<<...>>`, `CREDENTIAL.`, `RESOURCE.`, `=FUNC(`.
- Using JavaScript truthiness where the formula used Tines truthiness: `0`
  and `""` are truthy in Tines.
- Copying a Tines 5-field cron into a Windmill schedule without adding the
  seconds field.
- Inventing the body of a lambda or the content of a resource.
- An unbounded retry or polling loop.
- Catching every error around a state read, so that a permission error looks
  like a first run.
- Capping or stopping the work early while still advancing the polling cursor, so the skipped items are never processed.
- Reporting a workflow as finished without `RESULT: OK` or without the notes file.
