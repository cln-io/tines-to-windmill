#!/usr/bin/env python3
"""bundle_flow.py - one JSON file of a flow folder, and a check of what Windmill gives back.

USAGE
  bundle_flow.py FLOW_DIR                 write FLOW_DIR/../<name>.bundle.json and print a fingerprint
  bundle_flow.py FLOW_DIR --check FILE    compare a flow read back from Windmill (JSON) with the folder

The bundle is the flow with every `!inline file` replaced by the file's text:
{"path", "summary", "description", "schema", "value"}. That is the shape Windmill
takes when a flow is created through its API or pasted into the editor as JSON.

--check prints `WINDMILL: MATCH`, `WINDMILL: DIFFERENT` with what differs (exit 1), or
`WINDMILL: NOT CHECKED` when the file is not an answer from Windmill (exit 1).
It compares module ids, their order, kinds, languages, code (ignoring trailing
spaces) and input_transforms. It does not prove that the flow runs.
"""
import hashlib
import json
import re
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_flow  # noqa: E402

CHILD_KEYS = ("modules", "default")


def inline(node, flow_dir):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and v.startswith("!inline "):
                rel = v.split(" ", 1)[1].strip()
                with open(os.path.join(flow_dir, rel), encoding="utf-8") as fh:
                    out[k] = fh.read()
            else:
                out[k] = inline(v, flow_dir)
        return out
    if isinstance(node, list):
        return [inline(x, flow_dir) for x in node]
    return node


def flow_path(flow_dir):
    parts = os.path.abspath(flow_dir).replace("\\", "/").split("/")
    name = parts[-1]
    for suffix in (".flow", "__flow"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    for i in range(len(parts) - 2, -1, -1):
        if parts[i] in ("f", "u"):
            return "/".join(parts[i:-1] + [name])
    return name


def bundle(flow_dir):
    with open(os.path.join(flow_dir, "flow.yaml"), encoding="utf-8") as fh:
        data, _ = validate_flow.load_yaml(fh.read())
    data = inline(data, flow_dir)
    return {"path": flow_path(flow_dir), "summary": data.get("summary", ""),
            "description": data.get("description", ""), "schema": data.get("schema", {}),
            "value": data.get("value", {})}


def norm_code(code):
    return "\n".join(line.rstrip() for line in str(code).replace("\r\n", "\n").strip().split("\n"))


def walk(value, trail=""):
    """Yield (id, record) for every module, in order, through loops and branches."""
    def modules(mods, where):
        for n, m in enumerate(mods or []):
            if not isinstance(m, dict) or not isinstance(m.get("id"), str) or not isinstance(m.get("value"), dict):
                yield "(not a module: entry %d of %s)" % (n + 1, where or "the top level"), {
                    "where": where, "type": "BROKEN", "language": None, "code": None, "inputs": "{}"}
                continue
            v = m.get("value") or {}
            yield m.get("id"), {
                "where": where, "type": v.get("type"), "language": v.get("language"),
                "code": hashlib.sha256(norm_code(v["content"]).encode()).hexdigest()[:12]
                if isinstance(v.get("content"), str) else None,
                "inputs": json.dumps(v.get("input_transforms") or {}, sort_keys=True),
            }
            inner = where + "/" + str(m.get("id"))
            for item in modules(v.get("modules"), inner):
                yield item
            for item in modules(v.get("default"), inner + "/default"):
                yield item
            for n, br in enumerate(v.get("branches") or []):
                for item in modules((br or {}).get("modules"), "%s/branch%d" % (inner, n)):
                    yield item
    for key in ("preprocessor_module", "failure_module"):
        if isinstance(value.get(key), dict):
            for item in modules([value[key]], key):
                yield item
    for item in modules(value.get("modules"), trail):
        yield item


def fingerprint(flow):
    return list(walk(flow.get("value") or {}))


def unwrap(obj):
    """Accept the flow itself, or the usual wrappers around it."""
    for _ in range(4):
        if isinstance(obj, dict) and isinstance(obj.get("value"), dict) and "modules" in obj["value"]:
            return obj
        if isinstance(obj, dict):
            for key in ("flow", "draft", "item", "result", "data", "value"):
                if isinstance(obj.get(key), (dict, str)):
                    obj = obj[key]
                    break
            else:
                break
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except ValueError:
                break
    if isinstance(obj, dict) and "modules" in obj:
        return {"value": obj}
    return obj if isinstance(obj, dict) else {}


CHAT_LIMIT = 16000   # bytes of bundle; above this a tool answer with the flow in it is cut off in a chat


SERVER_KEYS = {"created_at", "edited_at", "edited_by", "workspace_id", "extra_perms", "versions", "archived", "draft_only"}


def server_marks(obj, depth=0):
    """True when the answer holds a field only Windmill adds (not in our own bundle)."""
    if depth > 5 or not isinstance(obj, dict):
        return False
    if SERVER_KEYS & set(obj):
        return True
    for key in ("flow", "draft", "deployed", "item", "result", "data", "value"):
        v = obj.get(key)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                continue
        if server_marks(v, depth + 1):
            return True
    return False


def main(argv):
    if len(argv) not in (2, 4) or (len(argv) == 4 and argv[2] != "--check"):
        print(__doc__.strip())
        return 2
    flow_dir = argv[1].rstrip("/")
    try:
        local = bundle(flow_dir)
    except (OSError, validate_flow.YamlError) as exc:
        print("BUNDLE: FAIL - %s" % exc)
        return 1
    if len(local["path"].split("/")) < 3:
        print("BUNDLE: FAIL - workspace path `%s` has no folder: Windmill paths are f/<folder>/<name>. "
              "Move the flow folder to OUT/f/<folder>/." % local["path"])
        return 1
    mine = fingerprint(local)
    if len(argv) == 2:
        out = os.path.join(os.path.dirname(os.path.abspath(flow_dir)), flow_path(flow_dir).split("/")[-1] + ".bundle.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(local, fh, indent=1, ensure_ascii=False)
        print("BUNDLE: OK - %s (%d bytes, %d module(s), path %s)" % (out, os.path.getsize(out), len(mine), local["path"]))
        for mid, rec in mine:
            print("  %-28s %-12s %-8s code %s  in %s" % (mid, rec["type"], rec["language"] or "-", rec["code"] or "-",
                                                         rec["where"] or "top level"))
        size = os.path.getsize(out)
        if size > CHAT_LIMIT:
            print("DRAFT: TOO LARGE FOR A CHAT TOOL - %d bytes, limit %d. Do NOT save this flow through a Windmill "
                  "tool: retyping a flow of this size goes wrong (branches end up in the wrong place, steps get "
                  "lost) and the read-back is cut off, so it cannot be checked. Tell the user: \"This flow is too "
                  "large to save and verify from the chat. Push the folder with `wmill sync push`, or import %s "
                  "in Windmill.\" Then go on with the next workflow." % (size, CHAT_LIMIT, os.path.basename(out)))
        else:
            print("DRAFT: OK TO SAVE - %d bytes. Do these in order, all of them:" % size)
            print("  1. read what is at `%s` in Windmill now; if a flow or draft is there, ask the user first" % local["path"])
            print("  2. save the draft: pass summary, description, schema and value of the bundle file, unchanged, "
                  "as a JSON object (not as one long string)")
            print("  3. read the flow back, and write the tool's answer, unchanged, to a file readback.json")
            print("  4. bundle_flow.py %s --check readback.json" % flow_dir)
            print("  5. for every item under Setup in the notes: does it exist in the workspace (by name only)")
            print("  Say MATCH or \"identical\" to the user only when step 4 printed `WINDMILL: MATCH`.")
        return 0
    try:
        with open(argv[3], encoding="utf-8-sig") as fh:
            raw = json.load(fh)
        theirs = fingerprint(unwrap(raw))
    except (OSError, ValueError) as exc:
        print("WINDMILL: DIFFERENT - cannot read %s as JSON: %s" % (argv[3], exc))
        return 1
    if not server_marks(raw):
        print("WINDMILL: NOT CHECKED - %s has none of the fields Windmill adds to an answer (%s), so it "
              "looks built from your own files, which compares the folder with itself. Save the Windmill "
              "tool's answer exactly as it came back. If the answer was cut off because it is too long, "
              "do not rebuild it: tell the user the draft could not be compared and that they should open "
              "it in Windmill." % (argv[3], ", ".join(sorted(SERVER_KEYS))))
        return 1
    problems = []
    if re.search(r'"content"\s*:\s*"!inline ', json.dumps(raw)):
        problems.append("the flow in Windmill holds `!inline <file>` where the code should be: it has no code. "
                        "It was not saved from the bundle file. Save again with the `value` of the bundle "
                        "file (`bundle_flow.py %s` writes it)" % flow_dir)
    a, b = [m for m, _ in mine], [m for m, _ in theirs]
    there = dict(theirs)
    for mid in a:
        if mid not in there:
            problems.append("module `%s` is missing in Windmill" % mid)
    for mid, rec in theirs:
        if rec["type"] == "BROKEN":
            problems.append("Windmill holds something that is not a module: %s" % mid)
        elif mid not in dict(mine):
            problems.append("module `%s` is in Windmill but not in the folder" % mid)
    if not problems and a != b:
        problems.append("module order differs: folder %s, Windmill %s" % (a, b))
    for mid, rec in mine:
        other = there.get(mid)
        if not other:
            continue
        if rec["where"] != other["where"]:
            problems.append("module `%s` sits in a different place: folder `%s`, Windmill `%s`"
                            % (mid, rec["where"] or "top level", other["where"] or "top level"))
        for key, label in (("type", "kind"), ("language", "language"), ("code", "code"), ("inputs", "input_transforms")):
            if rec[key] != other[key]:
                problems.append("module `%s`: %s differs" % (mid, label))
    if problems:
        print("WINDMILL: DIFFERENT - %d difference(s)" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("WINDMILL: MATCH - %d module(s): ids, order, kinds, languages, code and input_transforms are the same" % len(mine))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)
    sys.exit(main(sys.argv))
