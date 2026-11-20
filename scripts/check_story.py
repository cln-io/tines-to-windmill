#!/usr/bin/env python3
"""check_story.py - check a story file that was written from pasted text.

USAGE
  check_story.py S

Prints `STORY: OK` with counts and names to compare against the pasted text,
or `STORY: FAIL` with the place where the JSON breaks (exit 1). It proves that
the file is complete, well-formed JSON in a shape the other scripts can read.
It cannot prove that every value was copied exactly.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tines_outline  # noqa: E402


def walk(agents, depth=0):
    for a in agents:
        yield depth, a
        group = a.get("group")
        if isinstance(group, dict):
            for item in walk(group.get("agents") or [], depth + 1):
                yield item


def count_links(story):
    n = len(story.get("links") or [])
    for a in story.get("agents") or []:
        if isinstance(a.get("group"), dict):
            n += count_links(a["group"])
    return n


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    path = argv[1]
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError as exc:
        print("STORY: FAIL - cannot read %s: %s" % (path, exc))
        return 1
    try:
        json.loads(text)
    except ValueError as exc:
        pos = getattr(exc, "pos", 0)
        print("STORY: FAIL - not valid JSON: %s" % exc)
        print("  around the break: ...%s<<HERE>>%s..." % (text[max(0, pos - 80):pos], text[pos:pos + 40]))
        print("  file is %d characters; it ends with: %r" % (len(text), text[-60:]))
        print("  Usual causes: the text was cut off, or a character was changed while copying.")
        return 1
    try:
        tines_outline.load_export(path)
    except ValueError as exc:
        print("STORY: FAIL - valid JSON, but not a Tines story or copied actions: %s" % exc)
        return 1
    raw = json.loads(text)
    if isinstance(raw.get("story"), dict) and "agents" not in raw:
        raw = raw["story"]
    if tines_outline.is_copied_actions(raw):
        raw = tines_outline.normalize_copied(raw)
    actions = list(walk(raw.get("agents") or []))
    top = [a for d, a in actions if d == 0]
    names = [str(a.get("name")) for _, a in actions]
    print("STORY: OK - %d characters, %d top-level action(s), %d action(s) in all, %d link(s)"
          % (len(text), len(top), len(actions), count_links(raw)))
    print("  first actions: %s" % "; ".join(names[:5]))
    print("  last actions:  %s" % "; ".join(names[-5:]))
    print("  file ends with: %r" % text[-60:])
    print("Compare the counts, the first and last action names and the ending with the pasted text.")
    print("If they differ, the copy is wrong: do not continue with this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
