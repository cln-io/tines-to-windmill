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
5. **Never guess what the export does not contain.** There are two kinds of
   missing thing, handled differently:
   - *Missing data*: the value of a credential or of a resource that is only
     read (settings, a lookup table, state). The flow reads it at run time
     from a Windmill variable or resource. List it under Setup in the notes.
     Do not write a stub for it.
   - *Missing logic*: a lambda stored in a resource, a called story that is
     not in the export, a call to the Tines API that has no Windmill
     equivalent. Ask the user. If there is no answer, write a stub that throws
     an error naming what is missing.
6. **Never write a secret value into any file.** Refer to it by variable or
   resource path. The export can contain webhook secrets and internal
   hostnames: do not copy them into the flow.
7. **Never deploy.** Do not run `wmill sync push` or `wmill flow push` unless
   the user asks.
8. **Code goes in separate files.** In `flow.yaml` write
   `content: "!inline <step_id>.ts"`, with the quotes. Do not embed code in YAML.
9. **You are done with a workflow only when** `scripts/validate_flow.py` ends
   with `RESULT: OK` and you have written the notes file from step 8.

## How to read the references

The references are long. Do not open a whole reference file. Read one section
at a time with `scripts/ref.py`:

```
python3 scripts/ref.py --toc                    every file with its sections and sizes
python3 scripts/ref.py openflow --toc           the sections of one file
python3 scripts/ref.py openflow 5.4             one section
python3 scripts/ref.py --search suspend resume  find the sections that mention words
```

| You need to | Read |
|---|---|
| Understand an action type, its options, or how events flow | `ref.py story-format --toc`, then the section for that action type (section 7 has one part per type) |
| A rare action type: IMAP, AI, run script, record, case | `ref.py story-format-extras --toc` |
| Read formula syntax: `<<pills>>`, `=FORMULA()`, operators, `<%if%>` / `<%for%>` tags | `ref.py formula-language --toc` |
| Translate one formula function to TypeScript | `python3 scripts/tines_fn.py NAME` for the full entry, or `ref.py formulas-to-ts --search NAME` for the short table row |
| See a full formula translated | `ref.py formulas-examples --toc` |
| Write `flow.yaml`: step types, expressions, loops, branches, triggers | `ref.py openflow --toc`, then the section you need |
| Copy a working pattern for one Tines shape | `ref.py patterns 0` for the list, then `ref.py patterns <number>` |
| See the whole method applied once | `ref.py worked-example --toc` |
| See a complete story export and its finished flow | `examples/cold-chain/` |

## Process

### Step 1. Get the index and make a plan

```
python3 scripts/tines_outline.py S --index
```

The index lists every workflow (`w01`, `w02`, ...), its entry point (schedule,
webhook or page), its size, the credentials and resources it uses, embedded
sub-stories (`s1`, ...), stories that are called but not in the export, and
resources that are called as functions.

Write `OUT/PLAN.md` (start from `templates/PLAN.md`) with one line per workflow:

```
w04 | sync_open_tickets | schedule 15 6 * * * Europe/Oslo | 7 actions | TODO
```

- Give each workflow a short snake_case flow name.
- Mark `DISABLED` workflows and pieces with no entry point as `SKIP`, unless
  the user asked for them.
- A sub-story that workflows call becomes one shared flow. Give it a line in
  the plan with its planned path, for example `s1 | send_chat_message |
  f/<folder>/send_chat_message | called by 14 workflows | TODO`.
- You do not have to port a sub-story before its callers. A caller refers to
  the planned path (see "Send to story" in step 5). Port the sub-story when
  the user asks for it or when it is next in the plan.
- A workflow with several cron lines gets one plan line. List all the cron
  lines in it, separated by `;`.
- A workflow marked `NO-EFFECT` in the index has no outside effect: nothing
  that runs in it sends, writes or calls anything. Mark it `SKIP: no effect`
  and tell the user.
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

While reading, write what you learn into a worksheet file,
`OUT/<flow_name>.WORK.md`. Your memory of the outline will not last through
the whole port, and the worksheet will. Read the worksheet again before step
5, before step 6 and before step 8. Write down:

- the entry point and its trigger details (every cron line with its timezone,
  or the webhook path and verbs, or the page fields);
- where the workflow branches, loops, fans out and joins;
- which actions are dead ends: nothing reads their output and they have no
  outside effect;
- every `CREDENTIAL.x`, `RESOURCE.x` and `STORY.x` it uses.

Also write down, as a numbered list, every outside effect of the workflow:
each request that changes something, each email, each story call, each state
write. This list is your checklist in step 7.

The outline marks some names as unresolved: a reference to something that no
action on the path provides. In Tines such a reference gives `NULL`. Port it
as `null`, do not match it to a similarly named action somewhere else, and
list it in the notes.

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

- the definition of each lambda stored in a resource (the index lists
  resources that are called as functions);
- the export of each called story that the index marks as not in the export;
- which Windmill folder, and which existing variables or resources, to use.

You do not need the values of ordinary resources and credentials to write the
flow. They are read at run time and go under Setup in the notes (rule 5).

If the user cannot answer now, continue. For each piece of missing logic
write a stub that throws, for example
`throw new Error("MISSING: Tines resource text_helpers.shorten - definition not in export")`,
and list it in the notes file.

### Step 5. Design the steps

Group the actions into steps using this table. The last column is the recipe
number in `references/patterns.md`. A recipe shows the shape as the outline
prints it, a complete `flow.yaml` fragment, the step files and the map lines.
For every shape in your workflow, read its recipe and copy from it:

```
python3 scripts/ref.py patterns 0      which outline shape is which recipe
python3 scripts/ref.py patterns 13     one recipe
```

If you are unsure how to group actions into steps, read
`python3 scripts/ref.py worked-example 2`.

| Tines shape | Windmill | Recipe |
|---|---|---|
| Schedule on an action | Separate `<flow_path>.schedule.yaml`. Windmill cron has 6 fields with seconds first: Tines `*/5 * * * *` becomes `0 */5 * * * *`. Keep the timezone. One file per cron line. | 1 |
| Webhook action | Flow inputs for the body fields. Windmill webhooks take POST: if the Tines webhook also accepted GET, say so in the notes. The flow's built-in webhook, or an `http_trigger.yaml` for a custom path. Add a preprocessor if headers or query are needed. | 2, 3 |
| Page (form) that starts a workflow | Flow input `schema` with one property per page field. Tell the user that a styled public page needs a Windmill app. | 4 |
| Page in the middle of a workflow | A step with `suspend` (approval or resume form). | 5 |
| HTTP request | `rawscript` in `bun` using `fetch`. | 6 |
| HTTP request followed by status triggers (`200`, `404`) | The same script: check `res.status` and throw or return. | 6, 7 |
| Retry settings, or a trigger -> delay -> back-link loop | Step-level `retry`, or a bounded loop inside the script. Always set a maximum. | 8, 9 |
| Event transform, message-only | Fold into the script of the next step that uses it. Keep a separate step only when several later steps read it. | 11, 12 |
| Explode -> per-item work -> implode | `forloopflow`. The loop result is the array. Drop the prep and implode plumbing. | 13 |
| Trigger with a no-match link (if / else) | `branchone`. | 14 |
| One action linking to several actions | `branchall` if a later step needs all the results. Otherwise put them in sequence. | 15 |
| Group action | Inline its steps. Make it a separate flow, called with `type: flow`, only if several workflows use it. | 17 |
| Send to story | `type: flow` with the path of the ported story. If it is not ported yet, use its planned path from `PLAN.md`, pass the Tines payload keys unchanged as its inputs, and list it under Setup in the notes as a dependency. This is not a `MISSING` stub. If the called story is not in the export at all, it is missing logic (rule 5). | 18, 27 |
| Several links leading into the same action | Write that work once. Put the parts that differ in a `branchone` or in one script that decides, and put the shared step after it. Never copy a step once per incoming link. | 16 |
| A payload field set to `=META` or built from `META.x` | Build a small object in the script from the values that are really used later. Say so in the notes. | 26 |
| Deduplicate | A script that keeps seen keys in `wmill.getState()` / `setState()`. | 21 |
| Throttle | First check which branch it is on: it limits only the actions after it. On the main work: flow `concurrent_limit` or step `sleep`. On a side branch (for example state writes only): often nothing is needed. Say what you did in the notes. | 20 |
| Delay | Step `sleep`. | 19 |
| Email action | A script with `nodemailer` and an `smtp` resource. | 22 |
| Resource read (`RESOURCE.x`) | Settings or lookup table: a Windmill resource or a non-secret variable. | 23 |
| Resource written through the Tines API | State: `setState` if one step both reads and writes it. Otherwise a non-secret variable holding JSON. | 24 |
| `CREDENTIAL.x` | A secret variable `f/<folder>/<x>`, or a typed resource. Keep the Tines name. If a credential and a resource have the same name, add `_secret` to the credential's path. | 25 |
| A credential that is only used to call the Tines API | Dropped together with those calls. Say so in the notes. | 25 |
| `disable_ssl_verification` on an HTTP request | `fetch(url, { tls: { rejectUnauthorized: false } })` in Bun. Keep it only for that host and say so in the notes. | 10 |
| `STORY_RUN_GUID()`, `META.story_run.id` | `process.env.WM_ROOT_FLOW_JOB_ID ?? process.env.WM_FLOW_JOB_ID ?? process.env.WM_JOB_ID`. `WM_JOB_ID` alone changes at every step. Say so in the notes. | 26 |
| Calls to the Tines API for anything else | No equivalent. Stub it and report it. | 27 |
| Disabled or unreachable action | Not ported. Inside the workflow it is already `DROPPED` in the map. Disabled chains outside the workflow have no map line. | 29 |

Design rules:

- Aim for fewer steps than actions. A simple chain of HTTP calls and transforms
  for one purpose is one script.
- Step ids are snake_case, unique in the whole flow, and say what the step does
  (`fetch_alerts`, not `http_request_3`).
- When behaviour must change because Windmill has no exact equivalent, pick the
  safer behaviour and write it down for the notes file.
- Do not copy dead ends. Do not add features the story does not have.
- If the story has a bug that destroys or sends something by accident (for
  example a fallback that deletes everything when a filter matches nothing),
  do not port the bug. Keep the safe behaviour, list it under behaviour
  differences as deliberate, and tell the user.

### Step 6. Write the flow

Write `flow.yaml` and one `<step_id>.ts` per step. Start from the files in
`templates/`: copy `templates/flow.yaml` and the step template nearest to each
step (`http_get.ts`, `http_post.ts`, `transform.ts`, `state_read.ts`,
`state_write.ts`, `send_email.ts`, `ask_approval.ts`, `preprocessor.ts`,
`failure.ts`), then edit them using the recipes. For format questions read
`ref.py openflow` sections 2 to 6.

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
a05 -> flow_input.name, flow_input.email   a page with several fields
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

After the structural findings there is a `BEHAVIOUR` block. Each line there
says that the flow probably does not do something the story does: a request
that no step makes, a branch or loop that is missing, a step that was copied.
Treat each one as an error unless you can say in one sentence why it is
correct. Put that sentence in the notes file under "Not verified".

A `WARN` about a `DROPPED` action with an outside effect stays even when the
drop is right. Make sure the reason in the map says why the effect is not
needed, and repeat it in the notes under "Not ported".

The validator cannot check whether the logic is right: `RESULT: OK` means the
structure is valid, not that the flow behaves like the story. Before you call
a workflow finished, go through its graph once more and check that every
branch, loop and outside effect of the story has a place in the flow.

Check the TypeScript syntax of every step:

```
python3 scripts/check_ts.py OUT/f/<folder>/<flow_name>.flow
```

If it ends with `RESULT: NOT VERIFIED`, no syntax checker is installed. Say so
in the notes under "Not verified".

Last, take the list of outside effects from your worksheet. For each one,
name the step and the line of code that performs it. If you cannot, the flow
is not finished.

### Step 8. Write the notes file

Write `<flow_name>.NOTES.md` next to the flow folder (start from
`templates/FLOW_NAME.NOTES.md`), then mark the workflow
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
