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
| `references/worked-example.md` | Walkthrough of porting one example story |
| `examples/cold-chain/` | An invented story export and its finished Windmill flow |
| `scripts/tines_outline.py` | Compact digest of a story export |
| `scripts/validate_flow.py` | Checks a written flow, with optional coverage against the story |
| `scripts/tines_fn.py` | Looks up one function in the optional local function catalogue |
| `scripts/fetch_tines_function_docs.py` | Downloads the Tines function reference pages |

The scripts need Python 3 and no extra packages.

## The function catalogue is not included

`scripts/tines_fn.py` reads a per-function catalogue under
`references/tines-functions/`. That catalogue reproduces Tines' documentation,
so it is not part of this repository. `fetch_tines_function_docs.py` downloads
the source pages so you can build your own copy. The lookup table in
`references/tines-formulas-to-ts.md` works without it.

## Not affiliated

This project is not affiliated with or endorsed by Tines or Windmill.
