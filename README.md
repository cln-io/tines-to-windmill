# tines-to-windmill

A skill (instructions, references and helper scripts) for translating exported
[Tines](https://www.tines.com) stories into [Windmill](https://www.windmill.dev)
flows, with an AI model doing the work: an on-prem model such as Qwen in
LibreChat, or a commercial one. The references are explicit and
example-heavy, and the scripts take over the mechanical work (digesting a
large export, checking the flow that was written, comparing the draft in
Windmill with the files).

How it works, with a worked example and the setup for LibreChat and for
hosted models: [Moving Tines stories to Windmill with AI](https://cln.io/blog/tines-to-windmill/).

## Tested

With Qwen3.8 27B in an agent loop that imitates LibreChat's code sandbox,
against Windmill CE v1.882.0:

- An invented 15-action story went from export to a running flow: validator
  `RESULT: OK`, draft in Windmill `WINDMILL: MATCH`, test run `TEST: OK`, with
  every outside effect checked against a mock API's request log.
- Real stories of 63 and 143 actions were planned, mapped and written with
  the same process; the first workflow of the larger one validates with 86
  actions in 17 steps and none unaccounted for.

The references were checked against the Tines docs, the OpenFlow spec and
real story exports. Each file marks what could not be verified.

## Use

Load the folder as a skill in an agent that can run Python 3 and write files.
`SKILL.md` is the entry point. Try the scripts on the bundled example:

```
python3 scripts/tines_outline.py examples/cold-chain/story.json --index
python3 scripts/validate_flow.py examples/cold-chain/f/cold_chain/review_excursions.flow --story examples/cold-chain/story.json
```

## In LibreChat

Checked on one self-hosted instance, so treat it as a starting point:

- Turn on Run Code and the skill, and name it in your first message ("use
  the tines-to-windmill skill"). With a Windmill connection in the same chat
  a model may otherwise go straight to the Windmill tools and port by hand,
  with none of the checks.
- The model runs the scripts with the code tool; there is no separate shell
  tool.
- A big port needs more tool calls than one message allows. When the model
  stops at the limit, say "continue".
- Test runs of TypeScript steps need a worker that can install packages
  (reach the npm registry, directly or through your proxy). A job that hangs
  at `bun install` is that.
- Give the story as a `.json` file in the code environment when you can.
  A story pasted into the message also works for small stories: the model
  writes it to a file and `scripts/check_story.py` checks that it is complete
  JSON. That check cannot prove every value was copied exactly, so the notes
  file says when a story came from a paste.
- The skill's scripts have to be in the sandbox. LibreChat documents
  `/mnt/data/skills/tines-to-windmill/`. If your sandbox does not get that
  folder, attach `tines-to-windmill-skill.zip` to the chat as well; the first
  step in `SKILL.md` unpacks it.

The scripts accept a story export and also the JSON that Tines copies when
actions are copied from the storyboard.

## Download

A workflow builds `tines-to-windmill-skill.zip` on every push to `main`. It holds one folder, `tines-to-windmill/`, with `SKILL.md` inside,
which is the layout skill uploads such as LibreChat's expect. Get it from the
run's artifacts on the Actions tab, or from Releases once a `v*` tag exists.

To build the same zip locally from the committed files:

```
git archive --format=zip --prefix=tines-to-windmill/ -o tines-to-windmill-skill.zip HEAD
```

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | Entry point: the step-by-step process and which reference to open when |
| `references/tines-story-format.md` | How to read a story export: actions, links, events, groups, pages, splitting one export into workflows |
| `references/tines-story-format-extras.md` | Rarer action types |
| `references/tines-formula-language.md` | Formula syntax, operators, references, lambdas, control tags |
| `references/tines-formulas-to-ts.md` | Every Tines formula function with a TypeScript equivalent |
| `references/tines-formulas-examples.md` | Worked formula translations |
| `references/windmill-openflow.md` | How to write a valid Windmill flow by hand |
| `references/patterns.md` | One copyable recipe per recurring Tines shape |
| `templates/` | Flow skeleton, step scripts, schedule, notes and plan templates |
| `references/worked-example.md` | Walkthrough of porting one example story |
| `examples/cold-chain/` | An invented story export and its finished Windmill flow |
| `scripts/tines_outline.py` | Compact digest of a story export |
| `scripts/validate_flow.py` | Checks a written flow, with optional coverage against the story |
| `references/tines-functions/` | Per-function catalogue: 227 formula functions |
| `scripts/tines_fn.py` | Prints one function's catalogue entry |
| `scripts/ref.py` | Prints one section of a reference |
| `scripts/check_ts.py` | Syntax-checks the step scripts of a flow |
| `scripts/bundle_flow.py` | One JSON file of a flow folder, and a check of what Windmill gives back |
| `scripts/check_story.py` | Checks a story file that was written from pasted text |
| `scripts/fetch_tines_function_docs.py` | Downloads the Tines function reference pages, for checking the catalogue against the source |

The scripts need Python 3 and no extra packages.

## The function catalogue

`references/tines-functions/` has one entry per Tines formula function:
arguments, porting notes, a TypeScript equivalent and examples. It is an
independent, unofficial description written for porting. The Tines
documentation is the authority, and each entry links to its page. The examples
are illustrative and were run against the TypeScript equivalents, not against
Tines. `scripts/tines_fn.py NAME` prints one entry.

## Not affiliated

This project is not affiliated with or endorsed by Tines or Windmill.
