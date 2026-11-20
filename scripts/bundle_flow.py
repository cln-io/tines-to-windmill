#!/usr/bin/env python3
"""bundle_flow.py - one JSON file of a flow folder, and a check of what Windmill gives back.

USAGE
  bundle_flow.py FLOW_DIR                 write FLOW_DIR/../<name>.bundle.json and print a fingerprint
  bundle_flow.py FLOW_DIR --check FILE    compare a flow read back from Windmill (JSON) with the folder

The bundle is the flow with every `!inline file` replaced by the file's text:
{"path", "summary", "description", "schema", "value"}. That is the shape Windmill
takes when a flow is created through its API or pasted into the editor as JSON.

--check prints `WINDMILL: MATCH` or `WINDMILL: DIFFERENT` with what differs (exit 1).
It compares module ids, their order, kinds, languages, code (ignoring trailing
spaces) and input_transforms. It does not prove that the flow runs.
"""
import hashlib
import json
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
        for m in mods or []:
            if not isinstance(m, dict):
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
    mine = fingerprint(local)
    if len(argv) == 2:
        out = os.path.join(os.path.dirname(os.path.abspath(flow_dir)), flow_path(flow_dir).split("/")[-1] + ".bundle.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(local, fh, indent=1, ensure_ascii=False)
        print("BUNDLE: OK - %s (%d bytes, %d module(s), path %s)" % (out, os.path.getsize(out), len(mine), local["path"]))
        for mid, rec in mine:
            print("  %-28s %-12s %-8s code %s" % (mid, rec["type"], rec["language"] or "-", rec["code"] or "-"))
        return 0
    try:
        with open(argv[3], encoding="utf-8-sig") as fh:
            theirs = fingerprint(unwrap(json.load(fh)))
    except (OSError, ValueError) as exc:
        print("WINDMILL: DIFFERENT - cannot read %s as JSON: %s" % (argv[3], exc))
        return 1
    problems = []
    a, b = [m for m, _ in mine], [m for m, _ in theirs]
    if a != b:
        problems.append("module ids or order differ: folder %s, Windmill %s" % (a, b))
    there = dict(theirs)
    for mid, rec in mine:
        other = there.get(mid)
        if not other:
            continue
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
    sys.exit(main(sys.argv))
