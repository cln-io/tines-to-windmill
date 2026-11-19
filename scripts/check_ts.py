#!/usr/bin/env python3
"""check_ts.py - syntax-check the TypeScript step files of a flow.

USAGE
  check_ts.py <name>.flow            every .ts file in the flow folder
  check_ts.py a.ts b.ts              the given files
  check_ts.py <name>.flow --tool node|bun|tsc|none   force one checker

  Exit code: 0 = no errors, 1 = errors found, 2 = nothing to check.
  Findings are one line each:  ERROR [syntax] file.ts:LINE: what. Fix: ...
  The last line starts with RESULT:

WHAT IT RUNS
  The first tool that is installed, in this order:
    1. bun   `bun build --no-bundle` per file (parses TypeScript, resolves nothing)
    2. node  when it can strip types (Node 22.13+/23.2+): types are removed with
             line numbers kept, then the result is parsed with `node --check`
    3. tsc   `tsc --noEmit`, keeping only syntax errors (TS1xxx); type errors and
             missing modules are ignored because the step's packages are not
             installed here
  On top of that, always: cheap text checks (brackets and quotes balance, an
  exported `main` or `preprocessor` function).

  With none of the tools installed only the text checks run. The RESULT line
  then says NOT VERIFIED: the syntax was NOT checked, and you must say so
  under "Not verified" in the notes file. This is never reported as a pass.

NOT CHECKED
  Types, imports, and whether the code does the right thing. With node, syntax
  that needs code generation (enum, namespace, parameter properties) cannot be
  stripped and is reported as a warning, not as an error.

Python 3 standard library only.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

NODE_PROBE = "process.exit(typeof require('node:module').stripTypeScriptTypes === 'function' ? 0 : 1)"
NODE_STRIP = (
    "const m=require('node:module'),fs=require('fs');"
    "try{fs.writeFileSync(process.argv[2],m.stripTypeScriptTypes(fs.readFileSync(process.argv[1],'utf8'),"
    "{mode:'strip'}))}"
    "catch(e){const l=/^[^\\n]*:(\\d+)\\n/.exec(String(e&&e.stack||''));"
    "console.error('STRIP '+(e&&e.code||'')+' @'+(l?l[1]:'')+' '+String(e&&e.message||e));process.exit(3)}"
)


def run(cmd, cwd=None, timeout=120):
    try:
        p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, "", str(exc)


def pick_tool(forced):
    """Return (name, executable) for the first usable checker, or ('none', None)."""
    order = [forced] if forced else ["bun", "node", "tsc"]
    for name in order:
        if name == "none":
            break
        exe = shutil.which(name)
        if not exe:
            continue
        if name == "node" and run([exe, "-e", NODE_PROBE])[0] != 0:
            continue
        return name, exe
    return "none", None


def first_line(text, skip=()):
    for line in text.splitlines():
        line = line.strip()
        if line and not any(s in line for s in skip):
            return line
    return ""


def check_node(exe, path, tmp):
    """[(level, line or None, message)] using type stripping + node --check."""
    out = os.path.join(tmp, re.sub(r"\W", "_", os.path.basename(path)) + ".mjs")
    rc, _, err = run([exe, "--no-warnings", "-e", NODE_STRIP, path, out])
    if rc != 0:
        msg = first_line(err.replace("STRIP ", ""), skip=("ExperimentalWarning", "--trace-warnings")) or "cannot parse the file"
        if "UNSUPPORTED_TYPESCRIPT_SYNTAX" in err:
            return [("WARN", None, "uses TypeScript syntax that node cannot strip (enum, namespace or parameter "
                     "property), so this file was not syntax-checked: %s" % re.sub(r"^(ERR_\w+)?\s*@\d*\s*", "", msg))]
        m = re.search(r"STRIP \S* @(\d+) ", err)
        return [("ERROR", int(m.group(1)) if m else None, re.sub(r"^(ERR_\w+)?\s*@\d*\s*", "", msg))]
    rc, _, err = run([exe, "--no-warnings", "--check", out])
    if rc == 0:
        return []
    line = None
    m = re.search(re.escape(out) + r":(\d+)", err) or re.search(r"\.mjs:(\d+)", err)
    if m:
        line = int(m.group(1))
    msg = next((l.strip() for l in err.splitlines() if re.match(r"\s*\w*Error:", l)), first_line(err))
    return [("ERROR", line, msg)]


def check_bun(exe, path, tmp):
    rc, out, err = run([exe, "build", "--no-bundle", path, "--outfile", os.path.join(tmp, "out.js")])
    if rc == 0:
        return []
    text = err + "\n" + out
    found = []
    lines = text.splitlines()
    for n, l in enumerate(lines):
        m = re.search(r"error:\s*(.+)", l)
        if not m:
            continue
        where = re.search(r":(\d+):(\d+)", "\n".join(lines[n:n + 6]))
        found.append(("ERROR", int(where.group(1)) if where else None, m.group(1).strip()))
    return found or [("ERROR", None, first_line(text) or "bun could not parse the file")]


def check_tsc(exe, path, tmp):
    rc, out, err = run([exe, "--noEmit", "--skipLibCheck", "--target", "esnext", "--module", "esnext",
                        "--moduleResolution", "node", path])
    found = []
    for l in (out + "\n" + err).splitlines():
        m = re.match(r".*?\((\d+),(\d+)\):\s*error\s+(TS1\d{3}):\s*(.+)", l)   # TS1xxx = syntax errors
        if m:
            found.append(("ERROR", int(m.group(1)), "%s (%s)" % (m.group(4).strip(), m.group(3))))
    return found


# --------------------------------------------------------------------------
# Text checks (no tool needed)
# --------------------------------------------------------------------------

REGEX_BEFORE = set("(,=:[!&|?{};+-*%<>~^")
REGEX_KEYWORDS = ("return", "typeof", "case", "in", "of", "void", "throw", "await", "yield", "delete", "else")


def text_checks(src):
    """[(level, line, message)] for unbalanced brackets / unterminated strings."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []          # (char, line); "`" entries mark an open template literal
    i, n, line = 0, len(src), 1
    last = ""           # last significant character, to tell a regex from a division
    word = ""

    def err(msg, at):
        return [("ERROR", at, msg)]

    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        in_template = bool(stack) and stack[-1][0] == "`"
        if in_template:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                stack.pop()
                last = "`"
            elif ch == "$" and src[i + 1:i + 2] == "{":
                stack.append(("${", line))
                i += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                return err("comment opened with /* is never closed", line)
            line += src.count("\n", i, j)
            i = j + 2
            continue
        if ch in "\"'":
            start = line
            j = i + 1
            while j < n and src[j] != ch:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    return err("string opened with %s is not closed on the same line" % ch, start)
                j += 1
            if j >= n:
                return err("string opened with %s is never closed" % ch, start)
            i, last, word = j + 1, ch, ""
            continue
        if ch == "`":
            stack.append(("`", line))
            i += 1
            continue
        if ch == "/" and (last == "" or last in REGEX_BEFORE or word in REGEX_KEYWORDS):
            j, in_class = i + 1, False
            while j < n and src[j] != "\n":
                if src[j] == "\\":
                    j += 1
                elif src[j] == "[":
                    in_class = True
                elif src[j] == "]":
                    in_class = False
                elif src[j] == "/" and not in_class:
                    break
                j += 1
            if j < n and src[j] == "/":
                i, last, word = j + 1, "/", ""
                continue
        if ch in "([{":
            stack.append((ch, line))
        elif ch in pairs:
            if ch == "}" and stack and stack[-1][0] == "${":
                stack.pop()
                i += 1
                continue
            if not stack or stack[-1][0] != pairs[ch]:
                opened = " (the `%s` opened on line %d is still open)" % stack[-1] if stack else ""
                return err("unexpected `%s`%s" % (ch, opened), line)
            stack.pop()
        if ch.isalnum() or ch in "_$":
            word = word + ch if (last.isalnum() or last in "_$") and src[i - 1:i] == last else ch
        else:
            word = ""
        last = ch
        i += 1
    if stack:
        opener, at = stack[-1]
        what = "template literal opened with `" if opener == "`" else "`%s`" % opener
        return err("%s is never closed" % what, at)
    return []


def has_entry(src):
    return re.search(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*(main|preprocessor)\b", src) is not None


# --------------------------------------------------------------------------

def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                files.extend(os.path.join(root, f) for f in sorted(names) if f.endswith(".ts") and not f.endswith(".d.ts"))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print("ERROR [file] %s: does not exist. Fix: pass the flow folder (<name>.flow) or .ts files." % p)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Syntax-check the TypeScript step files of a flow.")
    ap.add_argument("paths", nargs="+", help="a flow folder or .ts files")
    ap.add_argument("--tool", choices=["bun", "node", "tsc", "none"], help="force one checker (default: first installed)")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        print("RESULT: FAIL - no .ts files found in %s" % ", ".join(args.paths))
        return 2
    tool, exe = pick_tool(args.tool)
    if args.tool and args.tool != "none" and tool == "none":
        print("WARN  [tool] %s is not installed or cannot check TypeScript; falling back to text checks." % args.tool)
    version = first_line(run([exe, "--version"])[1]) if exe else ""
    print("check_ts: %d file(s), checker: %s" % (len(files), "%s %s" % (tool, version) if exe else
                                                  "NONE (bun, node >= 22.13 and tsc are all missing)"))
    checker = {"node": check_node, "bun": check_bun, "tsc": check_tsc}.get(tool)
    errors = warnings = 0
    with tempfile.TemporaryDirectory(prefix="check_ts_") as tmp:
        for path in files:
            try:
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
            except (OSError, UnicodeDecodeError) as exc:
                print("ERROR [file] %s: cannot be read: %s." % (path, exc))
                errors += 1
                continue
            findings = checker(exe, path, tmp) if checker else []
            real_errors = [f for f in findings if f[0] == "ERROR"]
            if not real_errors:
                # the tool found nothing (or there is no tool): the text checks still apply
                findings += [(lvl, ln, msg + " (text check)") for lvl, ln, msg in text_checks(src)] if not checker else []
            if not has_entry(src) and src.strip():
                findings.append(("WARN", None, "no exported `main` function (a step file needs "
                                 "`export async function main(...)`)"))
            if not src.strip():
                findings.append(("ERROR", None, "file is empty"))
            for level, line, msg in findings:
                where = "%s:%d" % (path, line) if line else path
                context = ""
                if line and 0 < line <= len(src.splitlines()):
                    context = " | %s" % src.splitlines()[line - 1].strip()[:80]
                tag = "syntax" if level == "ERROR" else "check"
                fix = (" Fix: correct the syntax at that line (often a missing bracket, quote or comma just above it)."
                       if level == "ERROR" else "")
                print("%-5s [%s] %s: %s.%s%s" % (level, tag, where, msg.rstrip("."), context, fix))
                if level == "ERROR":
                    errors += 1
                else:
                    warnings += 1
    print("")
    if errors:
        print("RESULT: FAIL - %d error(s), %d warning(s) in %d file(s)" % (errors, warnings, len(files)))
        return 1
    if tool == "none":
        print("RESULT: NOT VERIFIED - no TypeScript checker is installed (bun, node >= 22.13 or tsc), so the syntax "
              "was NOT checked. Only bracket/quote/main text checks ran: 0 error(s), %d warning(s) in %d file(s). "
              "Say so under \"Not verified\" in the notes file." % (warnings, len(files)))
        return 0
    print("RESULT: OK - 0 error(s), %d warning(s), %d file(s) parsed with %s (syntax only: types and imports "
          "are not checked)" % (warnings, len(files), tool))
    return 0


if __name__ == "__main__":
    sys.exit(main())
