# tines-to-windmill

A skill (instructions, references and helper scripts) for translating exported
[Tines](https://www.tines.com) stories into [Windmill](https://www.windmill.dev)
flows. It is written for a smaller on-prem model such as Qwen: the references
are explicit and example-heavy, and the scripts take over the mechanical work
(digesting a large export, checking the flow that was written).

## Status

Work in progress.

- Nothing here has been validated against a live Windmill instance, and the
  skill has not yet been tried with the model it is written for.
- The references were checked against the Tines docs, the OpenFlow spec and
  real story exports. Each file marks what could not be verified.
- The example flow passes `scripts/validate_flow.py`, which checks structure
  and references only. It has not been run.

## Use

Load the folder as a skill in an agent that can run Python 3 and write files.
`SKILL.md` is the entry point. Try the scripts on the bundled example:

```
python3 scripts/tines_outline.py examples/cold-chain/story.json --index
python3 scripts/validate_flow.py examples/cold-chain/f/cold_chain/review_excursions.flow --story examples/cold-chain/story.json
```

## Download

A workflow builds `tines-to-windmill-skill.zip` on every push and pull
request. It holds one folder, `tines-to-windmill/`, with `SKILL.md` inside,
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
