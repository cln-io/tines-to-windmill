#!/usr/bin/env python3
"""Look up Tines formula functions in the offline catalogue.

Usage:
  tines_fn.py NAME [NAME ...]     print the full entry for each function
  tines_fn.py --list [CATEGORY]   list functions (optionally one docs category or file)
  tines_fn.py --search WORD       find functions whose name or entry mentions WORD
  tines_fn.py --categories        list the categories and how many functions each has

Names are case-insensitive; "index-of", "index_of" and "=INDEX_OF(" all resolve
to INDEX_OF, and several names may be given in one quoted, space- or
comma-separated argument. On a miss the closest names are suggested and the
exit status is 1.

The catalogue lives in ../references/tines-functions/ relative to this script
(override with the TINES_FN_DIR environment variable). It is a local,
non-distributed copy of vendor documentation: if it is missing, fetch the
source pages with scripts/fetch_tines_function_docs.py and build it.

Standard library only.
"""
import difflib
import os
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^## ([A-Z][A-Z0-9_]*)\s*$")
FENCE = re.compile(r"^(`{3,}|~{3,})")


def catalogue_dir():
    env = os.environ.get("TINES_FN_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "references" / "tines-functions"


def die_missing(directory):
    sys.stderr.write(
        "tines_fn.py: no function catalogue found (looked in %s).\n"
        "The catalogue (references/tines-functions/) is a local copy of the Tines\n"
        "functions documentation and is not distributed with this skill.\n"
        "Download the source pages with:\n"
        "    python3 scripts/fetch_tines_function_docs.py <output-dir>\n"
        "then build references/tines-functions/ from them (one '## NAME' entry per\n"
        "function), or set TINES_FN_DIR to an existing catalogue directory.\n"
        "Until then, treat every Tines function's behaviour as unknown: do not guess.\n"
        % directory
    )
    sys.exit(2)


def load(directory):
    """Return {NAME: entry dict} parsed from every category file."""
    if not directory.is_dir():
        die_missing(directory)
    entries = {}
    for path in sorted(directory.glob("*.md")):
        if path.name.upper() == "INDEX.MD":
            continue
        name, buf, fence = None, [], None

        def flush():
            if name is not None:
                text = "\n".join(buf).rstrip() + "\n"
                entries[name] = {"name": name, "file": path.name, "text": text, **meta(text)}

        for line in path.read_text(encoding="utf-8").split("\n"):
            m = FENCE.match(line)
            if m:
                marker = m.group(1)
                if fence is None:
                    fence = marker
                elif marker[0] == fence[0] and len(marker) >= len(fence) and line.strip() == marker:
                    fence = None
            h = HEADING.match(line) if fence is None else None
            if h:
                flush()
                name, buf = h.group(1), [line]
            elif name is not None:
                buf.append(line)
        flush()
    if not entries:
        die_missing(directory)
    return entries


def meta(text):
    out = {"summary": "", "signature": "", "categories": []}
    for line in text.split("\n")[:12]:
        m = re.match(r"^- \*\*(Summary|Signature|Categories):\*\* (.*)$", line)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key == "categories":
            out[key] = [c.strip() for c in val.split(",")]
        elif key == "signature":
            out[key] = val.strip("`")
        else:
            out[key] = val
    return out


def normalise(raw):
    s = raw.strip().lstrip("=").strip()
    s = s.split("(")[0]
    return re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")


def index_line(e):
    return "%s — `%s` — %s — %s — %s" % (
        e["name"], e["signature"], ", ".join(e["categories"]), e["summary"], e["file"])


def undocumented_notes(directory):
    """Names listed under 'Names that are not documented functions' in INDEX.md."""
    notes, on = {}, False
    index = directory / "INDEX.md"
    if not index.is_file():
        return notes
    for line in index.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            on = line.strip() == "## Names that are not documented functions"
            continue
        if on and line.startswith("- "):
            head, _, rest = line[2:].partition(" — ")
            for nm in head.split(","):
                notes[nm.strip().upper()] = rest.strip()
    return notes


def suggest(name, entries):
    names = sorted(entries)
    close = difflib.get_close_matches(name, names, n=6, cutoff=0.6)
    parts = [p for p in name.split("_") if len(p) >= 3]
    contains = [n for n in names if name and (name in n or any(p in n.split("_") for p in parts))]
    out = []
    for n in close + contains:
        if n not in out:
            out.append(n)
    return out[:8]


def cmd_show(names, entries, directory):
    missing = 0
    notes = None
    for i, raw in enumerate(names):
        name = normalise(raw)
        if i:
            print()
        e = entries.get(name)
        if e:
            print(e["text"].rstrip())
            print("\n(file: %s; conventions: INDEX.md - only FALSE/NULL are falsy, missing key = NULL, 0-based indexes, never mutate inputs)" % e["file"])
            continue
        missing += 1
        if notes is None:
            notes = undocumented_notes(directory)
        print("## %s\n" % (name or raw))
        if name in notes:
            print("Not a documented Tines function: %s" % notes[name])
        else:
            print("No entry for %r in the catalogue (%d functions)." % (raw, len(entries)))
            near = suggest(name, entries)
            if near:
                print("Did you mean:")
                for n in near:
                    print("  " + index_line(entries[n]))
            else:
                print("No similar names. Try: tines_fn.py --search WORD")
            print("If the name really appears in a story, its behaviour is not in the docs: do not guess, flag it.")
    return 1 if missing else 0


def cat_key(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cmd_list(category, entries):
    items = sorted(entries.values(), key=lambda e: e["name"])
    if category:
        want = cat_key(category)
        want_file = want[:-3] if want.endswith("-md") else want
        sel = [e for e in items
               if any(cat_key(c) == want or cat_key(c).startswith(want) for c in e["categories"])
               or cat_key(e["file"][:-3]) == want_file]
        if not sel:
            cats = sorted({c for e in items for c in e["categories"]})
            print("No category matching %r. Categories: %s" % (category, ", ".join(cats)))
            return 1
        items = sel
    for e in items:
        print(index_line(e))
    print("\n%d function(s)%s" % (len(items), " in %r" % category if category else ""))
    return 0


def cmd_categories(entries):
    counts = {}
    for e in entries.values():
        for c in e["categories"]:
            counts[c] = counts.get(c, 0) + 1
    for c in sorted(counts):
        print("%-26s %d" % (c, counts[c]))
    return 0


def cmd_search(word, entries):
    w = word.lower()
    wn = normalise(word)
    by_name, by_summary, by_body = [], [], []
    for e in sorted(entries.values(), key=lambda e: e["name"]):
        if wn and wn in e["name"]:
            by_name.append(e)
        elif w in e["summary"].lower() or w in e["signature"].lower():
            by_summary.append(e)
        elif w in e["text"].lower():
            by_body.append(e)
    if not (by_name or by_summary or by_body):
        print("No function mentions %r." % word)
        return 1
    for title, group in (("name matches", by_name), ("summary/signature matches", by_summary), ("mentioned in entry", by_body)):
        if group:
            print("# %s" % title)
            for e in group:
                print(index_line(e))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 1
    directory = catalogue_dir()
    entries = load(directory)
    if argv[0] == "--list":
        return cmd_list(" ".join(argv[1:]) if len(argv) > 1 else None, entries)
    if argv[0] == "--categories":
        return cmd_categories(entries)
    if argv[0] == "--search":
        if len(argv) < 2:
            sys.stderr.write("usage: tines_fn.py --search WORD\n")
            return 1
        return cmd_search(" ".join(argv[1:]), entries)
    if argv[0].startswith("--"):
        sys.stderr.write("unknown option %s\n\n%s\n" % (argv[0], __doc__.strip()))
        return 1
    names = [n for arg in argv for n in re.split(r"[\s,]+", arg) if n.strip("=() ")]
    return cmd_show(names, entries, directory)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
