#!/usr/bin/env python3
"""validate_flow.py - mechanical checks for a Windmill flow translated from Tines.

USAGE
  validate_flow.py <dir.flow | flow.yaml | flow.json> [--story story.json]
                   [--workflow w03] [--map tines_action_map.md] [--strict]

  Exit code: 0 = no errors, 1 = errors found (or warnings with --strict),
             2 = the flow could not be read at all.
  Every finding is one line:  ERROR|WARN [check-name] where: what is wrong. Fix: ...
  Fix all ERROR lines, re-run, repeat until the last line says RESULT: OK.

CHECKS (field names follow openflow.openapi.yaml, OpenFlow spec 1.876.1)
  - the file parses; top level has summary + value.modules; schema is sane
  - every module has an id; ids are unique across the whole flow and use only
    letters, digits, underscore (hyphen is legal but warned about)
  - value.type is a known OpenFlow type and has its required fields
  - every input transform is {type: static, value} or {type: javascript, expr}
  - results.<id> in input_transforms / iterator / branch expr / skip_if /
    stop_after_if names a module that exists AND is in scope at that point:
    an earlier step of the same sequence or of an enclosing one. A step inside a
    loop or branch is not visible from outside it (use the container's result).
  - flow_input.<x> exists in schema.properties (flow_input.iter only in loops)
  - rawscript: content present, `!inline file` resolves, there is an exported
    main, and its parameters match the input_transforms keys in both
    directions (bun/deno/nativets/bunnative and python3; a parameter with a
    default value or `?` may be left without an input transform)
  - leftover Tines syntax anywhere: <<pills>>, CREDENTIAL.x, RESOURCE.x,
    =FORMULA( values, the |> pipe
  - $var:/$res: paths look like u/<user>/<name> or f/<folder>/<name>
  Heuristic checks are WARN, not ERROR.

COVERAGE (--story): the tines_action_map.md convention
  The model keeps a file named tines_action_map.md inside the .flow folder,
  next to flow.yaml. Create its skeleton ONCE, before writing the flow:

      tines_outline.py story.json --map-template --workflow w03 \\
          > <name>.flow/tines_action_map.md

  (--workflow is the workflow this flow ports, as listed by
  `tines_outline.py story.json --index`; leave it out when the story has a
  single workflow.) The skeleton records the workflow in a `# workflow: w03`
  line and has one line per Tines action of that workflow, keyed by the
  outline's action id (names are not unique in Tines, ids are):

      a01 -> TODO   # fetch orders [http_request]

  Replace each TODO with exactly one of:
      a01 -> fetch_orders                id of the flow.yaml module doing this work
      a12 -> enrich, summarize           several module ids, comma separated
      a03 -> flow_input.shop_ids         the action became a flow input
      a34 -> DROPPED: output never used  deliberately not translated, with a reason
  Never delete a line. Disabled and unreachable actions come pre-filled as
  DROPPED and need no attention.

  With --story the validator checks every enabled and reachable action of
  that ONE workflow (group actions and the actions inside them included;
  other workflows of the story are ignored): mapped, dropped, or an ERROR
  when the line is missing, still TODO, or points at a module id / flow input
  that does not exist in the flow. It also lists flow modules that no action
  maps to. The workflow is taken from --workflow, else from the map's
  `# workflow:` line, else the whole story is checked. `wmill flow push` only
  reads flow.yaml and the files it references with !inline, so the extra file
  is not pushed. --map PATH overrides the location (default: inside the flow
  folder, then its parent folder).

YAML LOADING
  Uses PyYAML when it is importable. Otherwise a built-in loader handles the
  YAML that flows are written in (block mappings and sequences, | and > block
  scalars, quoted and plain scalars, single-line or wrapped [..] / {..}, the
  !inline tag, comments). In that fallback mode the validator CANNOT load
  files using anchors/aliases (&a, *a), merge keys (<<:), complex keys (? ),
  tags other than !inline / !inline_fileset / !!str, or several documents; it
  reports those as a parse error naming the line, it never guesses. All other
  checks are identical in both modes. A flow.json is always accepted.

NOT CHECKED (in any mode)
  JavaScript/TypeScript/Python syntax and types; what the scripts do; whether
  the flow reproduces the story's logic; whether scripts, flows, variables and
  resources referenced by path exist in the workspace; parameters of
  `script`/`flow` steps and of rawscript languages other than the ones listed
  above; results[...] with a computed key.

Python 3 standard library only (PyYAML optional). --story needs
tines_outline.py in the same directory.
"""
import argparse
import difflib
import json
import os
import re
import sys

SPEC = "OpenFlow 1.876.1"

MODULE_TYPES = ("rawscript", "script", "flow", "forloopflow", "whileloopflow",
                "branchone", "branchall", "identity", "aiagent", "aidecision")
LANGUAGES = ("deno", "bun", "bunnative", "python3", "go", "bash", "powershell", "postgresql",
             "mysql", "bigquery", "snowflake", "mssql", "oracledb", "graphql", "nativets", "php",
             "rust", "ansible", "csharp", "nu", "java", "ruby", "rlang", "duckdb")
TS_LANGS = ("deno", "bun", "bunnative", "nativets")
HASH_COMMENT_LANGS = ("python3", "bash", "powershell", "ruby", "rlang", "nu", "ansible")
SHELL_LANGS = ("bash", "powershell", "nu")

TOP_KEYS = ("summary", "description", "value", "schema", "on_behalf_of_email", "on_behalf_of")
FLOW_VALUE_KEYS = (
    "modules", "failure_module", "preprocessor_module", "same_worker", "preserve_step_tags",
    "concurrent_limit", "concurrency_key", "concurrency_time_window_s", "on_concurrency_limit",
    "debounce_delay_s", "debounce_key", "debounce_args_to_accumulate", "max_total_debouncing_time",
    "max_total_debounces_amount", "skip_expr", "cache_ttl", "cache_ignore_s3_path",
    "delete_after_secs", "timeout", "flow_env", "priority", "early_return", "chat_input_enabled",
    "notes", "groups")
MODULE_KEYS = (
    "id", "value", "stop_after_if", "stop_after_all_iters_if", "skip_if", "sleep", "cache_ttl",
    "cache_ignore_s3_path", "timeout", "delete_after_secs", "summary", "mock", "suspend",
    "priority", "continue_on_error", "job_token_scopes", "retry", "debouncing")
VALUE_KEYS = {
    "rawscript": ("input_transforms", "content", "language", "path", "lock", "type", "tag",
                  "concurrent_limit", "concurrency_time_window_s", "on_concurrency_limit",
                  "custom_concurrency_key", "is_trigger", "assets"),
    "script": ("input_transforms", "path", "hash", "type", "tag_override", "is_trigger"),
    "flow": ("input_transforms", "path", "type"),
    "forloopflow": ("modules", "iterator", "skip_failures", "type", "parallel", "parallelism",
                    "squash", "iteration_label"),
    "whileloopflow": ("modules", "skip_failures", "type", "parallel", "parallelism", "squash",
                      "max_iterations", "max_duration_secs"),
    "branchone": ("branches", "default", "type"),
    "branchall": ("branches", "type", "parallel", "parallelism"),
    "identity": ("type", "flow"),
    "aiagent": ("input_transforms", "tools", "type", "tag", "omit_output_from_conversation",
                "agent", "tool_inputs", "parallel"),
    "aidecision": ("input_transforms", "type", "tag"),
}
REQUIRED_VALUE_KEYS = {
    "rawscript": ("content", "language", "input_transforms"),
    "script": ("path", "input_transforms"),
    "flow": ("path", "input_transforms"),
    "forloopflow": ("modules", "iterator", "skip_failures"),
    "whileloopflow": ("modules", "skip_failures"),
    "branchone": ("branches", "default"),
    "branchall": ("branches",),
    "identity": (),
    "aiagent": ("input_transforms",),
    "aidecision": ("input_transforms",),
}
REQUIRED_HINT = {
    "input_transforms": "add `input_transforms: {}` (or one entry per script parameter)",
    "skip_failures": "add `skip_failures: false`",
    "default": "add `default: []` (steps to run when no branch matches)",
    "language": "add `language: bun`",
    "iterator": "add `iterator: {type: javascript, expr: <array expression>}`",
    "modules": "add `modules:` with the list of steps",
    "branches": "add `branches:` with a list of {expr, modules}",
}
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
WM_PATH_RE = re.compile(r"^(u|f|g)/[A-Za-z0-9_-]+(/[A-Za-z0-9_.-]+)+$")


# ==========================================================================
# YAML loading
# ==========================================================================

class YamlError(Exception):
    def __init__(self, msg, line=None):
        Exception.__init__(self, msg)
        self.line = line


_NULLS = ("", "~", "null", "Null", "NULL")
_TRUE = ("true", "True", "TRUE")
_FALSE = ("false", "False", "FALSE")
_INT_RE = re.compile(r"^[-+]?(?:[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$")
_FLOAT_RE = re.compile(r"^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?$")
_INF_RE = re.compile(r"^[-+]?\.(?:inf|Inf|INF)$")
_NAN_RE = re.compile(r"^\.(?:nan|NaN|NAN)$")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "a": "\a", "b": "\b", "e": "\x1b",
            "f": "\f", "v": "\v", '"': '"', "\\": "\\", "/": "/", " ": " ", "N": "\x85",
            "_": "\xa0", "L": " ", "P": " ", "\t": "\t"}


def resolve_scalar(text):
    """YAML 1.2 core schema resolution of a plain scalar."""
    if text in _NULLS:
        return None
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    if _INT_RE.match(text):
        t = text.replace("0o", "0o")
        try:
            return int(t, 0) if ("x" in t or "o" in t) else int(t)
        except ValueError:
            return text
    if _FLOAT_RE.match(text):
        return float(text)
    if _INF_RE.match(text):
        return float("-inf") if text.startswith("-") else float("inf")
    if _NAN_RE.match(text):
        return float("nan")
    return text


class MiniYaml:
    """Loader for the YAML subset flows are written in. See module docstring."""

    def __init__(self, text):
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.n = len(self.lines)
        self.i = 0

    def err(self, msg, line=None):
        raise YamlError(msg, (self.i if line is None else line) + 1)

    def _skip(self):
        """Move to the next significant line; return (indent, content) or None."""
        while self.i < self.n:
            raw = self.lines[self.i]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if raw[indent] == "\t":
                self.err("tab character used for indentation; YAML needs spaces")
            return indent, raw[indent:].rstrip()
        return None

    def load(self):
        nxt = self._skip()
        if nxt and nxt[1].startswith("%"):
            self.err("YAML directives (%...) are not supported by the built-in loader")
        if nxt and nxt[1] == "---":
            self.i += 1
        nxt = self._skip()
        value = self.block(nxt[0]) if nxt else None
        nxt = self._skip()
        if nxt:
            if nxt[1] in ("---", "...") or nxt[1].startswith("--- "):
                self.err("multiple YAML documents are not supported; keep one document per file")
            self.err("unexpected content: this line is indented less than the block above it "
                     "but matches no enclosing block. Check the indentation")
        return value

    def block(self, min_indent):
        nxt = self._skip()
        if not nxt or nxt[0] < min_indent:
            return None
        indent, content = nxt
        if content == "-" or content.startswith("- "):
            return self.seq(indent)
        if content.startswith("? "):
            self.err("complex mapping keys ('? ') are not supported by the built-in loader")
        if self.split_key(content) is not None:
            return self.map(indent)
        line = self.i
        self.i += 1
        return self.inline_value(content, indent - 1, line)

    def split_key(self, content):
        """Return (key, rest) if the line is `key: rest`, else None."""
        if content[0] in "\"'":
            q = content[0]
            j = 1
            while j < len(content):
                if content[j] == "\\" and q == '"':
                    j += 2
                    continue
                if content[j] == q:
                    if q == "'" and content[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            else:
                return None
            tail = content[j + 1:].lstrip(" ")
            if tail.startswith(":") and (len(tail) == 1 or tail[1] == " "):
                key = content[1:j].replace("''", "'") if q == "'" else self._unescape(content[1:j])
                return key, tail[1:].strip()
            return None
        if content[0] in "[{!&*|>@`%":
            return None
        for j, ch in enumerate(content):
            if ch == "#" and j > 0 and content[j - 1] == " ":
                return None
            if ch == ":" and (j + 1 == len(content) or content[j + 1] == " "):
                key = content[:j].rstrip()
                return (key, content[j + 1:].strip()) if key else None
        return None

    def map(self, indent):
        result = {}
        while True:
            nxt = self._skip()
            if not nxt or nxt[0] < indent:
                break
            ind, content = nxt
            if ind > indent:
                self.err("unexpected indentation (%d spaces; the keys of this mapping are at %d)"
                         % (ind, indent))
            if content == "-" or content.startswith("- "):
                self.err("list item ('- ') found where a `key: value` line was expected; "
                         "the list is probably missing its parent key or is mis-indented")
            kv = self.split_key(content)
            if kv is None:
                self.err("expected `key: value`, found %r" % content[:60])
            key, rest = kv
            if key == "<<":
                self.err("merge keys (<<:) are not supported by the built-in loader")
            if key in result:
                self.err("duplicate key %r in the same mapping; merge the two blocks into one" % key)
            line = self.i
            self.i += 1
            result[key] = self.value_after(rest, indent, line)
        return result

    def value_after(self, rest, parent_indent, line):
        if rest == "" or rest.startswith("#"):
            nxt = self._skip()
            if nxt is None:
                return None
            ind, content = nxt
            if ind > parent_indent:
                return self.block(ind)
            if ind == parent_indent and (content == "-" or content.startswith("- ")):
                return self.seq(ind)
            return None
        return self.inline_value(rest, parent_indent, line)

    def seq(self, indent):
        result = []
        while True:
            nxt = self._skip()
            if not nxt or nxt[0] < indent:
                break
            ind, content = nxt
            if ind > indent:
                self.err("unexpected indentation (%d spaces; the items of this list are at %d)"
                         % (ind, indent))
            if not (content == "-" or content.startswith("- ")):
                break
            line = self.i
            rest = content[1:]
            stripped = rest.lstrip(" ")
            if stripped == "" or stripped.startswith("#"):
                self.i += 1
                nxt2 = self._skip()
                result.append(self.block(nxt2[0]) if nxt2 and nxt2[0] > indent else None)
                continue
            item_indent = indent + 1 + (len(rest) - len(stripped))
            if stripped == "-" or stripped.startswith("- ") or self.split_key(stripped) is not None:
                # `- key: value` / `- - x`: re-read the rest of the line as a nested block
                self.lines[self.i] = " " * item_indent + stripped
                result.append(self.block(item_indent))
            else:
                self.i += 1
                result.append(self.inline_value(stripped, indent, line))
        return result

    def inline_value(self, rest, parent_indent, line):
        c = rest[0]
        if c == "!":
            m = re.match(r"!(\S*)\s*(.*)$", rest)
            tag, remainder = m.group(1), m.group(2)
            if tag in ("inline", "inline_fileset", "!str"):
                if not remainder or remainder.startswith("#"):
                    self.err("tag !%s needs a value on the same line" % tag, line)
                if remainder[0] in "\"'":
                    text = self.quoted(remainder, parent_indent, line)
                else:
                    text = self.strip_comment(remainder)
                # same representation the wmill CLI uses after parsing
                return text if tag == "!str" else "!%s %s" % (tag, text)
            self.err("YAML tag !%s is not supported by the built-in loader "
                     "(only !inline, !inline_fileset, !!str)" % tag, line)
        if c in "&*":
            self.err("YAML anchors/aliases (&name, *name) are not supported by the built-in "
                     "loader; write the value out in full (or quote it if it is plain text)", line)
        if c in "|>":
            return self.block_scalar(rest, parent_indent, line)
        if c in "[{":
            return self.flow(rest, line)
        if c in "\"'":
            return self.quoted(rest, parent_indent, line)
        return self.plain(rest, parent_indent, line)

    @staticmethod
    def strip_comment(text):
        if text.startswith("#"):
            return ""
        j = text.find(" #")
        return (text[:j] if j >= 0 else text).rstrip()

    def plain(self, rest, parent_indent, line):
        text = self.strip_comment(rest)
        if text[:1] in ("@", "`", "%", ","):
            self.err("an unquoted value cannot start with %r; put the value in quotes or use a "
                     "block scalar (key: |)" % text[0], line)
        if re.search(r":(\s|$)", text):
            self.err("unquoted value contains ': ' (YAML reads that as a nested mapping): %r. "
                     "Put the value in quotes or use a block scalar (key: |)" % text[:60], line)
        parts, blank = [text], 0
        while self.i < self.n:
            raw = self.lines[self.i]
            content = raw.strip()
            if not content:
                blank += 1
                self.i += 1
                continue
            ind = len(raw) - len(raw.lstrip(" "))
            if ind <= parent_indent or content.startswith("#"):
                break
            if self.split_key(content) is not None:
                self.err("this line is indented under a value that is already complete "
                         "(line %d). Either the indentation is wrong or the previous value "
                         "needs quotes / a block scalar" % (line + 1))
            parts.append("\n" * blank if blank else " ")
            parts.append(self.strip_comment(content))
            blank = 0
            self.i += 1
        if len(parts) == 1:
            return resolve_scalar(text)
        return "".join(parts)

    def _unescape(self, body):
        out, j = [], 0
        while j < len(body):
            ch = body[j]
            if ch != "\\":
                out.append(ch)
                j += 1
                continue
            nxt = body[j + 1:j + 2]
            if nxt in ("x", "u", "U"):
                size = {"x": 2, "u": 4, "U": 8}[nxt]
                hexs = body[j + 2:j + 2 + size]
                try:
                    out.append(chr(int(hexs, 16)))
                except ValueError:
                    self.err("bad \\%s escape in double-quoted string" % nxt)
                j += 2 + size
            elif nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                j += 2
            else:
                self.err("unknown escape \\%s in double-quoted string (use single quotes or a "
                         "block scalar to avoid escaping)" % nxt)
        return "".join(out)

    def quoted(self, rest, parent_indent, line):
        q = rest[0]
        s, pos = rest, 1
        buf = []       # pieces of raw (still escaped) text for the current logical string
        while True:
            escaped_break = False
            closed = None
            while pos < len(s):
                ch = s[pos]
                if q == '"' and ch == "\\":
                    if pos + 1 >= len(s):
                        escaped_break = True
                        pos += 1
                        break
                    buf.append(s[pos:pos + 2])
                    pos += 2
                    continue
                if ch == q:
                    if q == "'" and s[pos + 1:pos + 2] == "'":
                        buf.append("''")
                        pos += 2
                        continue
                    closed = pos
                    break
                buf.append(ch)
                pos += 1
            if closed is not None:
                tail = s[closed + 1:].strip()
                if tail and not tail.startswith("#"):
                    self.err("unexpected text after the closing quote: %r" % tail[:40])
                body = "".join(buf)
                return body.replace("''", "'") if q == "'" else self._unescape(body)
            # continue on the following line(s): fold line breaks
            if not escaped_break:
                joined = "".join(buf).rstrip(" ")
                buf = [joined]
            blank = 0
            while self.i < self.n and not self.lines[self.i].strip():
                blank += 1
                self.i += 1
            if self.i >= self.n:
                self.err("quoted string opened here is never closed", line)
            if blank:
                buf.append("\\n" * blank if q == '"' else "\n" * blank)
            elif not escaped_break:
                buf.append(" ")
            s, pos = self.lines[self.i].strip(), 0
            self.i += 1

    def block_scalar(self, header, parent_indent, line):
        m = re.match(r"^([|>])([+-]?)([1-9]?)([+-]?)\s*(#.*)?$", header)
        if not m:
            self.err("bad block scalar header %r (expected |, |-, >, >- ...) - text must start "
                     "on the next line" % header[:30], line)
        style, chomp = m.group(1), m.group(2) or m.group(4)
        block_indent = parent_indent + int(m.group(3)) if m.group(3) else None
        lines, j = [], self.i
        while j < self.n:
            raw = self.lines[j]
            if not raw.strip():
                lines.append(raw[block_indent:] if block_indent is not None and style == "|"
                             and len(raw) > block_indent else "")
                j += 1
                continue
            ind = len(raw) - len(raw.lstrip(" "))
            if block_indent is None:
                if ind <= parent_indent:
                    break
                block_indent = ind
            if ind < block_indent:
                break
            lines.append(raw[block_indent:])
            j += 1
        self.i = j
        trailing = 0
        while lines and lines[-1].strip() == "":
            lines.pop()
            trailing += 1
        if style == "|":
            text = "\n".join(lines)
        else:
            out, prev, blank = [], None, 0
            for ln in lines:
                if ln == "":
                    blank += 1
                    continue
                kind = "m" if ln[0] in " \t" else "n"
                if prev is None:
                    out.append("\n" * blank)
                elif prev == "n" and kind == "n":
                    out.append("\n" * blank if blank else " ")
                else:
                    out.append("\n" * (blank + 1))
                out.append(ln)
                prev, blank = kind, 0
            text = "".join(out)
        if chomp == "-":
            return text
        if chomp == "+":
            return text + "\n" * (trailing + (1 if lines else 0))
        return text + "\n" if text else ""

    def flow(self, rest, line):
        text = rest
        while True:
            depth, q, j, done = 0, None, 0, None
            while j < len(text):
                ch = text[j]
                if q:
                    if ch == "\\" and q == '"':
                        j += 1
                    elif ch == q:
                        q = None
                elif ch in "\"'":
                    q = ch
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
                    if depth == 0:
                        done = j
                        break
                elif ch == "#" and j > 0 and text[j - 1] == " ":
                    text = text[:j].rstrip()
                    break
                j += 1
            if done is not None:
                tail = text[done + 1:].strip()
                if tail and not tail.startswith("#"):
                    self.err("unexpected text after closing %r: %r" % (text[done], tail[:40]), line)
                text = text[:done + 1]
                break
            if self.i >= self.n:
                self.err("flow collection opened here ([ or {) is never closed", line)
            text += " " + self.strip_comment(self.lines[self.i].strip())
            self.i += 1
        value, pos = self._flow_value(text, 0, line)
        return value

    def _flow_ws(self, s, p):
        while p < len(s) and s[p] in " \t":
            p += 1
        return p

    def _flow_scalar(self, s, p, line, stops):
        if s[p] in "\"'":
            q, j = s[p], p + 1
            while j < len(s):
                if s[j] == "\\" and q == '"':
                    j += 2
                    continue
                if s[j] == q:
                    if q == "'" and s[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            body = s[p + 1:j]
            return (body.replace("''", "'") if q == "'" else self._unescape(body)), j + 1, True
        j = p
        while j < len(s) and s[j] not in stops:
            if s[j] == ":" and (j + 1 >= len(s) or s[j + 1] in " ,]}"):
                break
            j += 1
        return s[p:j].strip(), j, False

    def _flow_value(self, s, p, line):
        p = self._flow_ws(s, p)
        if p >= len(s):
            self.err("incomplete flow collection", line)
        if s[p] == "[":
            out, p = [], self._flow_ws(s, p + 1)
            while p < len(s) and s[p] != "]":
                v, p = self._flow_value(s, p, line)
                out.append(v)
                p = self._flow_ws(s, p)
                if p < len(s) and s[p] == ",":
                    p = self._flow_ws(s, p + 1)
                elif p < len(s) and s[p] != "]":
                    self.err("expected ',' or ']' in flow sequence near %r" % s[p:p + 20], line)
            return out, p + 1
        if s[p] == "{":
            out, p = {}, self._flow_ws(s, p + 1)
            while p < len(s) and s[p] != "}":
                key, p, _ = self._flow_scalar(s, p, line, ",}")
                p = self._flow_ws(s, p)
                val = None
                if p < len(s) and s[p] == ":":
                    p = self._flow_ws(s, p + 1)
                    if p < len(s) and s[p] not in ",}":
                        val, p = self._flow_value(s, p, line)
                if key in out:
                    self.err("duplicate key %r in flow mapping" % key, line)
                out[str(key)] = val
                p = self._flow_ws(s, p)
                if p < len(s) and s[p] == ",":
                    p = self._flow_ws(s, p + 1)
                elif p < len(s) and s[p] != "}":
                    self.err("expected ',' or '}' in flow mapping near %r" % s[p:p + 20], line)
            return out, p + 1
        if s[p] in "&*!":
            self.err("anchors, aliases and tags inside [..] / {..} are not supported by the "
                     "built-in loader", line)
        text, p, was_quoted = self._flow_scalar(s, p, line, ",]}")
        return (text if was_quoted else resolve_scalar(text)), p


def _stringify_keys(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k is None:
                k = "null"
            elif isinstance(k, bool):
                k = "true" if k else "false"
            out[str(k)] = _stringify_keys(v)
        return out
    if isinstance(node, list):
        return [_stringify_keys(v) for v in node]
    return node


def _pyyaml_load(yaml, text):
    class Loader(yaml.SafeLoader):
        yaml_implicit_resolvers = {}

        def construct_mapping(self, node, deep=False):
            seen = set()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue
                key = self.construct_object(key_node, deep=True)
                try:
                    if key in seen:
                        raise yaml.constructor.ConstructorError(
                            None, None, "duplicate key %r in the same mapping; merge the two "
                            "blocks into one" % (key,), key_node.start_mark)
                    seen.add(key)
                except TypeError:
                    pass
            return yaml.SafeLoader.construct_mapping(self, node, deep)

    # YAML 1.2 core schema, as the `yaml` npm package used by the wmill CLI
    Loader.add_implicit_resolver("tag:yaml.org,2002:null",
                                 re.compile(r"^(?:~|null|Null|NULL|)$"), ["~", "n", "N", ""])
    Loader.add_implicit_resolver("tag:yaml.org,2002:bool",
                                 re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))
    Loader.add_implicit_resolver("tag:yaml.org,2002:int", _INT_RE, list("-+0123456789"))
    Loader.add_implicit_resolver(
        "tag:yaml.org,2002:float",
        re.compile("|".join(r.pattern for r in (_FLOAT_RE, _INF_RE, _NAN_RE))), list("-+0123456789."))
    Loader.add_implicit_resolver("tag:yaml.org,2002:merge", re.compile(r"^(?:<<)$"), ["<"])
    Loader.add_constructor("tag:yaml.org,2002:int",
                           lambda l, n: resolve_scalar(l.construct_scalar(n)))
    Loader.add_constructor("tag:yaml.org,2002:float",
                           lambda l, n: resolve_scalar(l.construct_scalar(n)))
    for tag in ("inline", "inline_fileset"):
        Loader.add_constructor("!" + tag, lambda l, n, t=tag: "!%s %s" % (t, l.construct_scalar(n)))
    try:
        # Loader derives from SafeLoader: no arbitrary object construction
        return yaml.load(text, Loader=Loader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        msg = " ".join(str(p) for p in (getattr(exc, "context", None), getattr(exc, "problem", None)) if p)
        raise YamlError(msg or str(exc), mark.line + 1 if mark else None)


def load_yaml(text, force_builtin=False):
    """Return (data, loader_name). Raises YamlError."""
    yaml = None
    if not force_builtin:
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None
    if yaml is not None:
        return _stringify_keys(_pyyaml_load(yaml, text)), "PyYAML"
    return MiniYaml(text).load(), "built-in"


# ==========================================================================
# Small source-code helpers
# ==========================================================================

def strip_comments(code, lang):
    """Blank out comments (string aware, heuristic). Keeps string literals."""
    if lang in TS_LANGS or lang in ("go", "php", "rust", "csharp", "java"):
        line_c, block_c, quotes = "//", ("/*", "*/"), "\"'`"
    elif lang in HASH_COMMENT_LANGS:
        line_c, block_c, quotes = "#", None, "\"'"
    elif lang in ("postgresql", "mysql", "bigquery", "snowflake", "mssql", "oracledb", "duckdb"):
        line_c, block_c, quotes = "--", ("/*", "*/"), "'"
    else:
        return code
    out, i, n, q = [], 0, len(code), None
    while i < n:
        ch = code[i]
        if q:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(code[i + 1])
                i += 2
                continue
            if ch == q or (ch == "\n" and q != "`" and lang in TS_LANGS):
                q = None
            i += 1
        elif ch in quotes:
            q = ch
            out.append(ch)
            i += 1
        elif code.startswith(line_c, i):
            j = code.find("\n", i)
            i = n if j < 0 else j
        elif block_c and code.startswith(block_c[0], i):
            j = code.find(block_c[1], i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def matching_paren(code, start):
    """Index of the ')' matching the '(' at code[start], or -1."""
    depth, q, i = 0, None, start
    while i < len(code):
        ch = code[i]
        if q:
            if ch == "\\":
                i += 1
            elif ch == q:
                q = None
        elif ch in "\"'`":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_top_level(text, sep=","):
    parts, depth, angle, q, cur = [], 0, 0, None, []
    prev = ""
    for ch in text:
        if q:
            cur.append(ch)
            if ch == q and prev != "\\":
                q = None
        elif ch in "\"'`":
            q = ch
            cur.append(ch)
        else:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "<":
                angle += 1
            elif ch == ">" and prev != "=" and angle > 0:
                angle -= 1
            if ch == sep and depth == 0 and angle == 0:
                parts.append("".join(cur))
                cur = []
                prev = ch
                continue
            cur.append(ch)
        prev = ch
    parts.append("".join(cur))
    return parts


def has_default(param):
    pieces = split_top_level(param.replace("=>", "\0\0"), "=")
    return len(pieces) > 1


def parse_main(code, lang, name="main"):
    """Return dict(found, exported, params[(name, optional)], open_ended, problem)."""
    res = {"found": False, "exported": True, "params": [], "open_ended": False, "problem": None}
    clean = strip_comments(code, lang)
    if lang in TS_LANGS:
        m = re.search(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*%s\s*(?:<[^(]*>)?\s*\(" % name, clean)
        if not m:
            m = re.search(r"(?<![\w$.])(?:async\s+)?function\s+%s\s*(?:<[^(]*>)?\s*\(" % name, clean)
            if m:
                res["exported"] = False
            elif re.search(r"\b(?:export\s+)?(?:const|let|var)\s+%s\s*=" % name, clean):
                res["problem"] = "arrow"
                return res
            else:
                return res
    elif lang == "python3":
        m = re.search(r"^(?:async\s+)?def\s+%s\s*\(" % name, clean, re.M)
        if not m:
            return res
    else:
        res["problem"] = "unsupported-language"
        return res
    res["found"] = True
    start = m.end() - 1
    end = matching_paren(clean, start)
    if end < 0:
        res["problem"] = "unbalanced"
        return res
    for raw in split_top_level(clean[start + 1:end]):
        p = " ".join(raw.split())
        if not p or p in ("*", "/"):
            continue
        if p[0] in "{[" or p.startswith("...") or p.startswith("*"):
            res["open_ended"] = True
            continue
        m2 = re.match(r"^(?:(?:public|private|protected|readonly)\s+)*([A-Za-z_$][\w$]*)\s*(\?)?", p)
        if not m2:
            res["open_ended"] = True
            continue
        res["params"].append((m2.group(1), bool(m2.group(2)) or has_default(p)))
    return res


def suggest(word, options):
    close = difflib.get_close_matches(word, list(options), n=1, cutoff=0.6)
    return " Did you mean `%s`?" % close[0] if close else ""


# ==========================================================================
# Validator
# ==========================================================================

RESULTS_DOT = re.compile(r"(?<![\w$.])results\s*(?:\?\.|\.)\s*([A-Za-z_$][\w$]*)")
RESULTS_BR = re.compile(r"(?<![\w$.])results\s*(?:\?\.)?\[\s*([\"'`])([^\"'`]+)\1\s*\]")
INPUT_DOT = re.compile(r"(?<![\w$.])flow_input\s*(?:\?\.|\.)\s*([A-Za-z_$][\w$]*)")
INPUT_BR = re.compile(r"(?<![\w$.])flow_input\s*(?:\?\.)?\[\s*([\"'`])([^\"'`]+)\1\s*\]")
INPUT_WHOLE = re.compile(r"(?<![\w$.])flow_input\b(?!\s*(?:\?\.|\.|\[))")
PILL = re.compile(r"<<\s*[A-Za-z_][\s\S]{0,400}?>>")
TINES_NS = re.compile(r"(?<![\w$.])(CREDENTIAL|RESOURCE|GROUP_INPUT)\.[A-Za-z_]\w*")
TINES_NS_SOFT = re.compile(r"(?<![\w$.])(LOCAL|INPUT|META|STORY)\.[a-z_]\w*")
TINES_FUNC = re.compile(r"(?<![\w$.])(?<!new )([A-Z][A-Z0-9_]{2,})\s*\(")
VARRES = re.compile(r"\$(var|res):([^\s\"'`,;)}\]]*)")


class Validator:
    def __init__(self, data, flow_dir, raw_text=None):
        self.data = data
        self.flow_dir = flow_dir
        self.raw_lines = raw_text.split("\n") if raw_text is not None else None
        self.errors, self.warnings, self.notes = [], [], []
        self.ids = {}            # id -> [record]
        self.seq_counter = 0
        self.schema_props = None
        self.used_inputs = set()
        self.whole_input_used = False
        self.noted = set()
        self.resolved = {}       # id(rawscript value) -> script source after !inline resolution

    # -- reporting ---------------------------------------------------------
    def line_of(self, mid):
        if not self.raw_lines or not isinstance(mid, str):
            return ""
        pat = re.compile(r"^\s*(?:-\s+)?[\"']?id[\"']?\s*:\s*[\"']?%s[\"']?\s*,?\s*(#.*)?$" % re.escape(mid))
        hits = [str(n + 1) for n, ln in enumerate(self.raw_lines) if pat.match(ln)]
        return " (line %s)" % ", ".join(hits) if hits else ""

    def where(self, mid, field=None):
        w = "module `%s`%s" % (mid, self.line_of(mid)) if mid else "flow"
        return w + (", %s" % field if field else "")

    def error(self, check, where, msg, fix=None):
        self.errors.append("ERROR [%s] %s: %s%s" % (check, where, msg, " Fix: " + fix if fix else ""))

    def warn(self, check, where, msg, fix=None):
        self.warnings.append("WARN  [%s] %s: %s%s" % (check, where, msg, " Fix: " + fix if fix else ""))

    def note(self, msg):
        if msg not in self.noted:
            self.noted.add(msg)
            self.notes.append("NOTE  " + msg)

    # -- entry -------------------------------------------------------------
    def run(self):
        d = self.data
        if not isinstance(d, dict):
            self.error("structure", "flow", "top level must be a mapping with `summary` and `value`, "
                       "found %s." % type(d).__name__)
            return
        if "value" not in d and "modules" in d:
            self.error("structure", "flow", "`modules` is at the top level.",
                       "nest it: `value:` then `modules:` indented under it")
            return
        if not isinstance(d.get("summary"), str):
            self.error("structure", "flow", "missing top-level `summary` (required string).",
                       "add `summary: <one line describing the flow>` as the first line")
        for k in d:
            if k not in TOP_KEYS:
                hint = suggest(k, TOP_KEYS)
                if hint or k in FLOW_VALUE_KEYS:
                    self.warn("unknown-key", "flow", "unknown top-level key `%s`.%s%s" % (
                        k, hint, " It belongs under `value:`." if k in FLOW_VALUE_KEYS else ""))
        value = d.get("value")
        if not isinstance(value, dict):
            self.error("structure", "flow", "missing top-level `value` mapping.",
                       "add `value:` containing `modules:`")
            return
        self.unknown_keys(value, FLOW_VALUE_KEYS, "flow", "`value`", None)
        modules = value.get("modules")
        if not isinstance(modules, list):
            self.error("structure", "flow", "`value.modules` must be a list of steps.",
                       "add `modules:` under `value:` with one `- id: ...` item per step")
            modules = []
        elif not modules:
            self.warn("structure", "flow", "`value.modules` is empty: the flow does nothing.")
        self.check_schema(d.get("schema"))

        # pass 1: register ids
        self.register_seq(modules, ())
        for slot, forced in (("preprocessor_module", "preprocessor"), ("failure_module", "failure")):
            m = value.get(slot)
            if m is None:
                continue
            if not isinstance(m, dict):
                self.error("structure", "flow", "`value.%s` must be a single module mapping." % slot)
                continue
            self.register_seq([m], (), kind=forced)
            if m.get("id") != forced:
                self.error("module-id", "value.%s" % slot, "its id must be `%s`, found `%s`."
                           % (forced, m.get("id")), "set `id: %s`" % forced)
            vt = m.get("value", {}).get("type") if isinstance(m.get("value"), dict) else None
            if vt and vt not in ("rawscript", "script"):
                self.error("module-type", "value.%s" % slot,
                           "only `rawscript` or `script` are allowed here, found `%s`." % vt)
        for mid, recs in self.ids.items():
            if len(recs) > 1:
                places = "; ".join(r["place"] for r in recs)
                self.error("duplicate-id", "module `%s`%s" % (mid, self.line_of(mid)),
                           "id is used %d times (%s). Ids must be unique in the whole flow, "
                           "including inside loops and branches." % (len(recs), places),
                           "rename all but one (and update the results.%s references that meant "
                           "the renamed step)" % mid)
            elif mid in ("failure", "preprocessor") and recs[0]["kind"] == "module":
                self.error("module-id", self.where(mid), "id `%s` is reserved for "
                           "value.%s_module." % (mid, mid), "rename the step")

        # pass 2: validate
        ctx = {"loop": False, "while": False, "mode": "normal", "tool": False}
        self.walk_seq(modules, frozenset(), ctx)
        if isinstance(value.get("preprocessor_module"), dict):
            self.check_module(value["preprocessor_module"], frozenset(), dict(ctx, mode="preprocessor"))
        if isinstance(value.get("failure_module"), dict):
            self.check_module(value["failure_module"], frozenset(), dict(ctx, mode="failure"))

        er = value.get("early_return")
        if er is not None and er not in self.ids:
            self.error("unknown-id", "flow, value.early_return", "`%s` is not a module id.%s"
                       % (er, suggest(str(er), self.ids)))
        for g in value.get("groups") or []:
            if isinstance(g, dict):
                for k in ("start_id", "end_id"):
                    if g.get(k) not in self.ids:
                        self.warn("unknown-id", "flow, value.groups", "%s `%s` is not a module id.%s"
                                  % (k, g.get(k), suggest(str(g.get(k)), self.ids)))
        if isinstance(value.get("skip_expr"), str):
            self.check_expr(value["skip_expr"], None, "value.skip_expr", frozenset(), ctx, "before")

        self.scan_strings(d, None, "static", None, "")
        if self.schema_props is not None and not self.whole_input_used and not self.errors:
            for p in self.schema_props:
                if p not in self.used_inputs:
                    self.warn("unused-input", "flow, schema.properties.%s" % p,
                              "flow input is declared but no expression reads flow_input.%s." % p,
                              "wire it into a step's input_transforms or remove it from the schema")

    # -- schema ------------------------------------------------------------
    def check_schema(self, schema):
        if schema is None:
            self.warn("schema", "flow", "no top-level `schema`: the flow has no declared inputs.",
                      "add `schema: {type: object, properties: {}}` (plus one property per flow input)")
            self.schema_props = {}
            return
        if not isinstance(schema, dict):
            self.error("schema", "flow, schema", "must be a JSON Schema mapping.")
            self.schema_props = {}
            return
        if schema.get("type") not in (None, "object"):
            self.warn("schema", "flow, schema", "`type` should be `object`, found `%s`." % schema.get("type"))
        props = schema.get("properties")
        if props is None:
            props = {}
        if not isinstance(props, dict):
            self.error("schema", "flow, schema.properties", "must be a mapping of input name -> JSON Schema.")
            props = {}
        self.schema_props = props
        for name, spec in props.items():
            if not isinstance(spec, dict):
                self.error("schema", "flow, schema.properties.%s" % name,
                           "must be a mapping such as `{type: string}`.")
        for key in ("required", "order"):
            lst = schema.get(key)
            if lst is None:
                continue
            if not isinstance(lst, list):
                self.error("schema", "flow, schema.%s" % key, "must be a list of property names.")
                continue
            for name in lst:
                if name not in props:
                    self.warn("schema", "flow, schema.%s" % key,
                              "`%s` is not in schema.properties.%s" % (name, suggest(str(name), props)))

    # -- pass 1 ------------------------------------------------------------
    def register(self, mid, chain, kind, mtype):
        self.seq_counter += 1
        if not isinstance(mid, str) or not mid:
            return
        place = " > ".join("%s%s" % (c, "[%s]" % b if b else "") for c, b, _ in chain) or "top level"
        if kind in ("failure", "preprocessor"):
            place = "value.%s_module" % kind
        self.ids.setdefault(mid, []).append(
            {"chain": chain, "seq": self.seq_counter, "kind": kind, "type": mtype, "place": place})

    def register_seq(self, modules, chain, kind="module"):
        if not isinstance(modules, list):
            return
        for m in modules:
            if not isinstance(m, dict):
                continue
            v = m.get("value") if isinstance(m.get("value"), dict) else {}
            t = v.get("type")
            mid = m.get("id")
            self.register(mid, chain, kind, t)
            if t in ("forloopflow", "whileloopflow"):
                self.register_seq(v.get("modules"), chain + ((mid, "", t),))
            elif t in ("branchone", "branchall"):
                for n, b in enumerate(v.get("branches") or []):
                    if isinstance(b, dict):
                        self.register_seq(b.get("modules"), chain + ((mid, "branch %d" % (n + 1), t),))
                if t == "branchone":
                    self.register_seq(v.get("default"), chain + ((mid, "default", t),))
            elif t == "aiagent":
                for tool in v.get("tools") or []:
                    if isinstance(tool, dict):
                        self.register(tool.get("id"), chain + ((mid, "tools", t),), "tool", None)

    # -- pass 2 ------------------------------------------------------------
    def walk_seq(self, modules, visible, ctx):
        if not isinstance(modules, list):
            return
        local = set(visible)
        for n, m in enumerate(modules):
            if not isinstance(m, dict):
                self.error("structure", "flow", "item %d of a `modules` list is not a mapping "
                           "(found %s)." % (n + 1, type(m).__name__),
                           "each step must look like `- id: my_step` followed by `value:`")
                continue
            self.check_module(m, frozenset(local), ctx)
            if isinstance(m.get("id"), str):
                local.add(m["id"])

    def unknown_keys(self, mapping, known, where_mid, label, other_level):
        for k in mapping:
            if k in known:
                continue
            hint = suggest(str(k), known)
            if not hint and other_level and k in other_level[1]:
                hint = " It belongs %s." % other_level[0]
            self.warn("unknown-key", self.where(where_mid) if where_mid != "flow" else "flow",
                      "`%s` is not a known key of %s (%s).%s" % (k, label, SPEC, hint))

    def check_module(self, m, visible, ctx):
        mid = m.get("id")
        label = mid if isinstance(mid, str) and mid else "(no id)"
        w = self.where(label)
        if not isinstance(mid, str) or not mid:
            summary = m.get("summary")
            self.error("module-id", "module %s" % ("with summary `%s`" % summary if summary else "(no id)"),
                       "missing `id`.", "add `id: <unique_snake_case_name>`")
            mid = None
        elif not ID_RE.match(mid):
            self.error("module-id", w, "id contains characters other than letters, digits, "
                       "underscore, hyphen.", "rename it to `%s`" % re.sub(r"[^A-Za-z0-9_]+", "_", mid).strip("_"))
        elif "-" in mid or mid[0].isdigit():
            self.warn("module-id", w, "id %s, so `results.%s` is not valid JavaScript (it needs "
                      "results[\"%s\"])." % ("contains a hyphen" if "-" in mid else "starts with a digit", mid, mid),
                      "rename it using letters, digits and underscores, starting with a letter")

        value = m.get("value")
        if not isinstance(value, dict):
            misplaced = [k for k in ("type", "content", "language", "input_transforms", "modules",
                                     "branches", "iterator", "path") if k in m]
            self.error("structure", w, "missing `value` mapping.%s" % (
                " Keys %s are directly on the module." % ", ".join("`%s`" % k for k in misplaced)
                if misplaced else ""),
                "put them under `value:` (indented one level deeper than `id`)" if misplaced
                else "add `value:` with `type:` and the type's fields")
            return
        vtype = value.get("type")
        self.unknown_keys(m, MODULE_KEYS, label, "a module",
                          ("inside `value:`", VALUE_KEYS.get(vtype, ())))

        # module-level expressions
        for key in ("stop_after_if", "stop_after_all_iters_if", "skip_if"):
            cond = m.get(key)
            if cond is None:
                continue
            if not isinstance(cond, dict) or not isinstance(cond.get("expr"), str):
                self.error("structure", w, "`%s` must be a mapping with a string `expr`." % key,
                           "write `%s:` then `expr: <javascript condition>` under it" % key)
                continue
            self.check_expr(cond["expr"], mid, "%s.expr" % key, visible, ctx,
                            "before" if key == "skip_if" else "after")
            if key == "stop_after_all_iters_if" and vtype not in ("forloopflow", "whileloopflow"):
                self.warn("structure", w, "`stop_after_all_iters_if` only applies to loop modules.")
        for key in ("sleep", "timeout"):
            if isinstance(m.get(key), dict):
                self.check_transform(m[key], mid, key, visible, ctx)
        retry_if = (m.get("retry") or {}).get("retry_if") if isinstance(m.get("retry"), dict) else None
        if isinstance(retry_if, dict) and isinstance(retry_if.get("expr"), str):
            self.check_expr(retry_if["expr"], mid, "retry.retry_if.expr", visible, ctx, "after")

        self.check_value(value, mid, label, visible, ctx)

    def check_value(self, value, mid, label, visible, ctx):
        w = self.where(label)
        vtype = value.get("type")
        if vtype not in MODULE_TYPES:
            if vtype is None:
                self.error("module-type", w, "`value.type` is missing.",
                           "add `type:` with one of: %s" % ", ".join(MODULE_TYPES))
            else:
                self.error("module-type", w, "`value.type: %s` is not an OpenFlow module type.%s"
                           % (vtype, suggest(str(vtype), MODULE_TYPES)),
                           "use one of: %s" % ", ".join(MODULE_TYPES))
            return
        allowed = VALUE_KEYS[vtype] + (("tool_type",) if ctx["tool"] else ())
        self.unknown_keys(value, allowed, label, "a `%s` value" % vtype, ("on the module, next to `id`", MODULE_KEYS))
        for req in REQUIRED_VALUE_KEYS[vtype]:
            if req not in value or value[req] is None:
                self.error("required-field", w, "`value.%s` is required for type `%s`." % (req, vtype),
                           REQUIRED_HINT.get(req))

        transforms = value.get("input_transforms")
        if transforms is not None:
            if not isinstance(transforms, dict):
                self.error("input-transform", w, "`input_transforms` must be a mapping of "
                           "parameter name -> transform.", "use `input_transforms: {}` when there are no inputs")
                transforms = None
            else:
                for name, t in transforms.items():
                    self.check_transform(t, mid, "input_transforms.%s" % name, visible, ctx)

        if vtype == "rawscript":
            self.check_rawscript(value, mid, label, transforms,
                                 "preprocessor" if ctx["mode"] == "preprocessor" else "main")
        elif vtype in ("script", "flow"):
            path = value.get("path")
            if isinstance(path, str) and not re.match(r"^(u|f|g|hub)/", path):
                self.error("path", w, "`value.path: %s` is not a workspace path." % path,
                           "use u/<user>/<name>, f/<folder>/<name> or hub/<id>/... (wmill flow push rejects other paths)")
            self.note("input_transforms of `script`/`flow` steps are not compared with the target's "
                      "parameters (the target lives in the workspace).")
        elif vtype in ("forloopflow", "whileloopflow"):
            if vtype == "forloopflow" and value.get("iterator") is not None:
                self.check_transform(value["iterator"], mid, "iterator", visible, ctx)
            for key in ("parallelism", "iteration_label"):
                if isinstance(value.get(key), dict):
                    self.check_transform(value[key], mid, key, visible, dict(ctx, loop=True))
            inner = value.get("modules")
            if inner is not None and not isinstance(inner, list):
                self.error("structure", w, "`value.modules` must be a list of steps.")
            elif isinstance(inner, list):
                if not inner:
                    self.warn("structure", w, "loop body `value.modules` is empty.")
                self.walk_seq(inner, visible, dict(ctx, loop=True, **{"while": vtype == "whileloopflow"}))
            if vtype == "whileloopflow" and "max_iterations" not in value and not self.has_stop(value, mid):
                self.warn("while-loop", w, "no stop_after_if on the loop or its steps and no "
                          "max_iterations: the loop never ends.",
                          "add `stop_after_if: {expr: ...}` to the loop module and/or `max_iterations`")
        elif vtype in ("branchone", "branchall"):
            branches = value.get("branches")
            if branches is not None and not isinstance(branches, list):
                self.error("structure", w, "`value.branches` must be a list.")
                branches = []
            for n, b in enumerate(branches or []):
                bl = "branches[%d]" % (n + 1)
                if not isinstance(b, dict):
                    self.error("structure", w, "%s must be a mapping with `modules`." % bl)
                    continue
                if not isinstance(b.get("modules"), list):
                    self.error("required-field", w, "%s.modules is required (a list of steps)." % bl,
                               "add `modules: []` or the steps of this branch")
                if vtype == "branchone":
                    if not isinstance(b.get("expr"), str):
                        self.error("required-field", w, "%s.expr is required (JavaScript condition)." % bl,
                                   "add `expr: <condition>`; put the fallback steps in `default:`")
                    else:
                        self.check_expr(b["expr"], mid, bl + ".expr", visible, ctx, "before")
                elif "expr" in b:
                    self.warn("structure", w, "%s.expr is ignored: `branchall` runs every branch." % bl,
                              "use `branchone` for conditions, or `skip_if` on the steps")
                self.walk_seq(b.get("modules"), visible, ctx)
            if vtype == "branchone" and value.get("default") is not None:
                if not isinstance(value["default"], list):
                    self.error("structure", w, "`value.default` must be a list of steps (use `[]` for none).")
                else:
                    self.walk_seq(value["default"], visible, ctx)
            if isinstance(value.get("parallelism"), dict):
                self.check_transform(value["parallelism"], mid, "parallelism", visible, ctx)
        elif vtype == "aiagent":
            tools = value.get("tools")
            if tools is not None and not isinstance(tools, list):
                self.error("structure", w, "`value.tools` must be a list.")
                tools = []
            for tool in tools or []:
                if not isinstance(tool, dict):
                    continue
                tid = tool.get("id")
                tw = self.where(tid if isinstance(tid, str) else "(tool without id)")
                if not isinstance(tid, str) or not re.match(r"^[A-Za-z0-9_-]+$", tid):
                    self.error("module-id", tw, "AI agent tool needs an `id` without spaces.")
                tv = tool.get("value")
                if not isinstance(tv, dict):
                    self.error("required-field", tw, "tool `value` is required.")
                    continue
                tt = tv.get("tool_type")
                if tt not in ("flowmodule", "mcp", "websearch", "question"):
                    self.error("module-type", tw, "tool `value.tool_type` must be one of flowmodule, "
                               "mcp, websearch, question; found `%s`." % tt)
                elif tt == "flowmodule":
                    self.check_value(tv, tid, tid if isinstance(tid, str) else "(tool)", visible,
                                     dict(ctx, tool=True))
                elif tt == "mcp" and not isinstance(tv.get("resource_path"), str):
                    self.error("required-field", tw, "mcp tool needs `value.resource_path`.")
            for tool_id, mapping in (value.get("tool_inputs") or {}).items() if isinstance(value.get("tool_inputs"), dict) else ():
                if isinstance(mapping, dict):
                    for name, t in mapping.items():
                        self.check_transform(t, mid, "tool_inputs.%s.%s" % (tool_id, name), visible, ctx)
        elif vtype == "aidecision" and isinstance(transforms, dict):
            for req in ("provider", "state", "questions"):
                if req not in transforms:
                    self.error("required-field", w, "`input_transforms.%s` is required for `aidecision`." % req)

    def has_stop(self, value, mid):
        def any_stop(mods):
            for m in mods or []:
                if isinstance(m, dict):
                    if "stop_after_if" in m:
                        return True
                    v = m.get("value") if isinstance(m.get("value"), dict) else {}
                    if any_stop(v.get("modules")) or any_stop(v.get("default")):
                        return True
                    for b in v.get("branches") or []:
                        if isinstance(b, dict) and any_stop(b.get("modules")):
                            return True
            return False
        if any_stop(value.get("modules")):
            return True
        # stop_after_if on the loop module itself: find the module by id in the raw data
        return self._module_has_key(self.data.get("value", {}).get("modules"), mid, "stop_after_if")

    def _module_has_key(self, mods, mid, key):
        for m in mods or []:
            if not isinstance(m, dict):
                continue
            if m.get("id") == mid:
                return key in m
            v = m.get("value") if isinstance(m.get("value"), dict) else {}
            subs = [v.get("modules"), v.get("default")] + [b.get("modules") for b in v.get("branches") or [] if isinstance(b, dict)]
            if any(self._module_has_key(s, mid, key) for s in subs if isinstance(s, list)):
                return True
        return False

    # -- transforms and expressions ---------------------------------------
    def check_transform(self, t, mid, field, visible, ctx):
        w = self.where(mid, field)
        if not isinstance(t, dict):
            looks_expr = isinstance(t, str) and re.match(r"^\s*(results|flow_input)\b", t)
            example = ("{type: javascript, expr: %s}" % json.dumps(t) if looks_expr
                       else "{type: static, value: %s}" % json.dumps(t))
            self.error("input-transform", w, "must be a mapping with `type`, found a bare %s."
                       % type(t).__name__, "write it as %s" % example)
            return
        ttype = t.get("type")
        if ttype == "javascript":
            expr = t.get("expr")
            if not isinstance(expr, str) or not expr.strip():
                self.error("input-transform", w, "`type: javascript` needs a non-empty string `expr`%s."
                           % (" (found `value`: a javascript transform ignores `value`)" if "value" in t else ""),
                           "add `expr: <javascript expression>`, or use `type: static` with `value:`")
                return
            self.check_expr(expr, mid, field + ".expr", visible, ctx, "before")
        elif ttype == "static":
            if "expr" in t:
                self.error("input-transform", w, "`type: static` ignores `expr`; the step would receive "
                           "%s instead." % ("the `value`" if "value" in t else "null"),
                           "change to `type: javascript` (keep `expr`), or replace `expr` with `value`")
            elif isinstance(t.get("value"), str) and re.match(r"^\s*(results|flow_input)\s*[.\[?]", t["value"]):
                self.warn("input-transform", w, "static value `%s` looks like an expression; a static "
                          "value is passed as literal text." % t["value"][:60],
                          "use `type: javascript` with `expr:` if it should be evaluated")
        elif ttype == "ai":
            if not ctx["tool"]:
                self.warn("input-transform", w, "`type: ai` is only meaningful for AI agent tool inputs.")
        elif ttype is None:
            guess = "javascript" if "expr" in t else "static"
            self.error("input-transform", w, "missing `type`.", "add `type: %s`" % guess)
        else:
            self.error("input-transform", w, "`type: %s` is not valid.%s" % (ttype, suggest(str(ttype), ("static", "javascript"))),
                       "use `type: static` (with `value`) or `type: javascript` (with `expr`)")

    def diagnose_scope(self, ref, mid):
        """Explain why existing module `ref` is not visible from module `mid`."""
        target = self.ids[ref][0]
        here = self.ids.get(mid, [{}])[0] if mid else {}
        my_chain = here.get("chain", ())
        t_chain = target["chain"]
        if any(c == ref for c, _, _ in my_chain):
            return ("`%s` is the %s that contains this step; its result does not exist until it "
                    "has finished." % (ref, target["type"]),
                    "inside a loop use flow_input.iter.value / an earlier step of the loop body")
        common = 0
        while common < len(my_chain) and common < len(t_chain) and my_chain[common] == t_chain[common]:
            common += 1
        if common < len(t_chain):
            cid, branch, ctype = t_chain[common]
            if common < len(my_chain) and my_chain[common][0] == cid:
                return ("`%s` is in a different branch (%s) of %s `%s`; branches cannot see each "
                        "other's steps." % (ref, branch, ctype, cid),
                        "move the shared step before `%s`, or read results.%s after the branches finish" % (cid, cid))
            kind = "loop" if "loop" in (ctype or "") else "branch module"
            return ("`%s` is inside %s `%s` (%s) and is not visible outside it."
                    % (ref, kind, cid, ctype),
                    "reference the container instead: results.%s (%s), or move this step inside `%s`"
                    % (cid, "an array with one entry per iteration" if kind == "loop"
                       else "the result of the branch that ran / an array for branchall", cid))
        if target["seq"] > here.get("seq", 0):
            return ("`%s` is defined AFTER this step; a step can only read results of earlier steps." % ref,
                    "move `%s` before this step, or reference an earlier step" % ref)
        return ("`%s` is not in scope here." % ref, None)

    def check_expr(self, expr, mid, field, visible, ctx, when):
        w = self.where(mid, field)
        text = expr.strip()
        if not text:
            self.error("expression", w, "expression is empty.")
            return
        if re.match(r"^\$\{[\s\S]*\}$", text) or text.startswith("{{"):
            self.error("expression", w, "expression is wrapped in template markers (`%s...`); `expr` is "
                       "plain JavaScript." % text[:2], "remove the wrapper, e.g. `results.step.field`")
        self.check_balance(text, w)

        for regex, grp in ((RESULTS_DOT, 1), (RESULTS_BR, 2)):
            for m in regex.finditer(expr):
                ref = m.group(grp)
                if regex is RESULTS_DOT:
                    tail = re.match(r"((?:-[A-Za-z0-9_]+)+)", expr[m.end():])
                    if tail and ref not in self.ids and ref + tail.group(1) in self.ids:
                        full = ref + tail.group(1)
                        self.error("unknown-result", w, "`results.%s` is parsed as `results.%s` minus "
                                   "something because the id has a hyphen." % (full, ref),
                                   "write results[\"%s\"], or better rename the step with underscores" % full)
                        continue
                self.check_result_ref(ref, mid, w, visible, ctx, when)

        for regex, grp in ((INPUT_DOT, 1), (INPUT_BR, 2)):
            for m in regex.finditer(expr):
                name = m.group(grp)
                props = self.schema_props or {}
                if name in props:
                    self.used_inputs.add(name)
                elif name == "iter":
                    if not ctx["loop"]:
                        self.error("flow-input", w, "`flow_input.iter` only exists inside a "
                                   "forloopflow/whileloopflow body; this step is not in a loop.",
                                   "move the step into the loop's `modules`, or reference a step result instead")
                elif ctx["mode"] != "preprocessor":
                    self.error("flow-input", w, "`flow_input.%s` is not declared in schema.properties.%s"
                               % (name, suggest(name, props)),
                               "add `%s` to schema.properties, or use an existing input (%s)"
                               % (name, ", ".join(sorted(props)) or "none declared"))
        if INPUT_WHOLE.search(expr):
            self.whole_input_used = True
        if when != "after" and re.search(r"(?<![\w$.])result\s*(?:\?\.|\.|\[)", expr):
            self.warn("expression", w, "`result` (singular) is only defined in stop_after_if / retry_if.",
                      "use `results.<step_id>`")
        if re.search(r"(?<![\w$.])iter\s*\.\s*(value|index)\b", expr):
            self.warn("expression", w, "bare `iter.value` / `iter.index`.", "write `flow_input.iter.value`")

    def check_result_ref(self, ref, mid, w, visible, ctx, when):
        if ctx["mode"] == "preprocessor":
            self.error("unknown-result", w, "the preprocessor runs before every step and cannot read "
                       "`results.%s`." % ref, "use only its own arguments")
            return
        if ref not in self.ids:
            self.error("unknown-result", w, "`results.%s`: no module has id `%s`.%s"
                       % (ref, ref, suggest(ref, self.ids)),
                       "use the id of an earlier step (in scope here: %s)"
                       % (", ".join(sorted(visible)) or "none"))
            return
        if ref in visible or ctx["mode"] == "failure":
            return
        if ref == mid:
            if when == "after" or ctx["while"]:
                return
            self.error("result-scope", w, "`results.%s` is this step's own result, which does not "
                       "exist while its inputs are evaluated." % ref,
                       "reference an earlier step (in scope here: %s)" % (", ".join(sorted(visible)) or "none"))
            return
        why, fix = self.diagnose_scope(ref, mid)
        self.error("result-scope", w, "`results.%s` is out of scope: %s" % (ref, why), fix)

    def check_balance(self, text, w):
        stack, q, i = [], None, 0
        pairs = {")": "(", "]": "[", "}": "{"}
        while i < len(text):
            ch = text[i]
            if q:
                if ch == "\\":
                    i += 1
                elif ch == q:
                    q = None
            elif ch in "\"'`":
                q = ch
            elif ch in "([{":
                stack.append(ch)
            elif ch in pairs:
                if not stack or stack.pop() != pairs[ch]:
                    self.warn("expression", w, "unbalanced `%s` in expression." % ch)
                    return
            i += 1
        if stack or (q and q != "`"):
            self.warn("expression", w, "unclosed %s in expression." % ("`%s`" % stack[-1] if stack else "quote"))

    # -- rawscript ---------------------------------------------------------
    def resolve_inline(self, text, w, what):
        """Return file content for `!inline path`, or None (error reported)."""
        parts = text.split(" ")
        rel = parts[1].strip() if len(parts) > 1 else ""
        if not rel:
            self.error("inline", w, "`!inline` has no file name.", "write `%s: !inline <file in the .flow folder>`" % what)
            return None
        if self.flow_dir is None:
            self.error("inline", w, "cannot resolve `!inline %s`: flow folder unknown." % rel)
            return None
        full = os.path.normpath(os.path.join(self.flow_dir, rel))
        base = os.path.normpath(self.flow_dir)
        if os.path.isabs(rel) or not (full == base or full.startswith(base + os.sep)):
            self.error("inline", w, "`!inline %s` must be a relative path inside the .flow folder." % rel)
            return None
        if not os.path.isfile(full):
            present = sorted(f for f in os.listdir(base) if os.path.isfile(os.path.join(base, f))) if os.path.isdir(base) else []
            self.error("inline", w, "`!inline %s`: file not found in %s.%s" % (rel, base, suggest(rel, present)),
                       "create the file, fix the name, or put the code directly in `%s: |`" % what)
            return None
        try:
            with open(full, encoding="utf-8") as fh:
                return fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            self.error("inline", w, "`!inline %s` cannot be read: %s" % (rel, exc))
            return None

    def script_content(self, value, w):
        content = value.get("content")
        if not isinstance(content, str):
            if content is not None:
                self.error("rawscript", w, "`value.content` must be a string (the script source).",
                           "use a block scalar: `content: |` and indent the code under it")
            return None
        if content.startswith("!inline"):
            return self.resolve_inline(content, w, "content")
        return content

    def check_rawscript(self, value, mid, label, transforms, entry="main"):
        w = self.where(label)
        lang = value.get("language")
        if lang is not None and lang not in LANGUAGES:
            self.error("rawscript", w, "`language: %s` is not a rawscript language.%s" % (lang, suggest(str(lang), LANGUAGES)),
                       "use one of: %s (TypeScript = bun, Python = python3)" % ", ".join(LANGUAGES))
            lang = None
        lock = value.get("lock")
        if isinstance(lock, str) and lock.lstrip().startswith("!inline "):
            rel = lock.split(" ")[1]
            if self.flow_dir and not os.path.isfile(os.path.join(self.flow_dir, rel)):
                self.warn("inline", w, "lock file `%s` not found (wmill treats it as empty)." % rel,
                          "remove the `lock:` line unless you have a lock file")
        code = self.script_content(value, w)
        if code is None:
            return
        self.resolved[id(value)] = code
        if not code.strip():
            self.error("rawscript", w, "script content is empty.", "write the script with an exported `main` function")
            return
        if lang is None:
            return
        info = parse_main(code, lang, entry)
        if not info["found"] and entry != "main" and not info["problem"]:
            entry = "main"
            info = parse_main(code, lang, entry)
        if info["problem"] == "unsupported-language":
            self.note("main()/parameter check is not implemented for language `%s` (module `%s`)." % (lang, label))
            return
        if info["problem"] == "arrow":
            self.warn("rawscript", w, "`%s` is declared as a variable/arrow function; Windmill expects a "
                      "function declaration." % entry, "write `export async function %s(...) { ... }`" % entry)
            return
        if not info["found"]:
            example = "def main(arg1: str):" if lang == "python3" else "export async function main(arg1: string) { ... }"
            self.error("rawscript", w, "no `main` function found in the script.", "add `%s`" % example)
            return
        if not info["exported"]:
            self.error("rawscript", w, "`%s` is not exported." % entry, "write `export async function %s(...)`" % entry)
        if info["problem"] == "unbalanced":
            self.warn("rawscript", w, "could not find the end of main's parameter list (unbalanced brackets?).")
            return
        if transforms is None or entry == "preprocessor":
            return  # a preprocessor's arguments come from the trigger, not from input_transforms
        params = [p for p, _ in info["params"]]
        if info["open_ended"]:
            self.note("module `%s`: main() uses destructured/rest parameters; input_transforms keys "
                      "are not compared with it." % label)
        else:
            for key in transforms:
                if key not in params:
                    self.error("param-mismatch", w, "`input_transforms.%s` has no matching parameter; "
                               "main takes (%s).%s" % (key, ", ".join(params) or "no parameters", suggest(key, params)),
                               "rename the input transform to the parameter name, or add the parameter to main")
        for name, optional in info["params"]:
            if name not in transforms and not optional:
                self.error("param-mismatch", w, "main parameter `%s` has no entry in input_transforms; "
                           "the script would receive undefined/None.%s" % (name, suggest(name, list(transforms))),
                           "add `input_transforms.%s` ({type: javascript, expr: ...} or {type: static, value: ...}), "
                           "or give the parameter a default value" % name)
        clean = strip_comments(code, lang)
        declared = set(params) | set(re.findall(r"\b(?:const|let|var|function|import)\s+\{?\s*(results|flow_input)\b", clean))
        for name, regex in (("flow_input", r"(?<![\w$.])flow_input\s*(?:\?\.|\.)\s*[A-Za-z_]"),
                            ("results", r"(?<![\w$.])results\s*(?:\?\.|\.)\s*(%s)\b" % "|".join(map(re.escape, self.ids)) if self.ids else None)):
            if regex and name not in declared and re.search(regex, clean):
                self.warn("rawscript", w, "script code uses `%s.`, which exists only in flow expressions, "
                          "not inside scripts." % name,
                          "pass the value in through input_transforms and read it as a main parameter")

    # -- leftover Tines syntax, $var/$res ----------------------------------
    def scan_strings(self, node, mid, kind, lang, path):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and isinstance(node.get("value"), dict):
                mid, path = node["id"], ""
            is_script = node.get("type") == "rawscript" and "content" in node
            for k, v in node.items():
                if is_script and k == "content" and id(node) in self.resolved:
                    self.scan_text(self.resolved[id(node)], mid, "code", node.get("language"), path)
                    continue
                if k in ("summary", "description", "title", "note", "text"):
                    continue
                child = "expr" if k in ("expr", "skip_expr") and isinstance(v, str) else kind
                if is_script and k == "content":
                    child = "code"
                if is_script and k == "lock":
                    continue
                sub = k if not path or (path == "value" and mid) else "%s.%s" % (path, k)
                self.scan_strings(v, mid, child, node.get("language") if is_script else lang, sub)
        elif isinstance(node, list):
            for n, v in enumerate(node):
                self.scan_strings(v, mid, kind, lang, "%s[%d]" % (path, n + 1))
        elif isinstance(node, str):
            self.scan_text(node, mid, kind, lang, path)

    def scan_text(self, text, mid, kind, lang, path):
        w = self.where(mid, "script content" if kind == "code" else path)
        body = strip_comments(text, lang) if kind == "code" else text
        if kind == "code" and lang in SHELL_LANGS:
            body = re.sub(r"<<[-~]?\s*[\"']?\w+[\"']?(?=\s|$)", " ", body)  # heredoc openers
        m = PILL.search(body)
        if m:
            snippet = " ".join(m.group(0).split())[:70]
            self.error(
                "tines-syntax", w, "leftover Tines pill `%s`." % snippet,
                "replace it with the Windmill equivalent: a script parameter fed by input_transforms, "
                "`results.<id>...` / `flow_input.<name>` in an expr, or ${...} inside script code")
        m = TINES_NS.search(body)
        if m:
            self.error("tines-syntax", w, "leftover Tines reference `%s`." % m.group(0),
                       "CREDENTIAL -> Windmill variable/resource ($var:/$res: static input or "
                       "wmill.getVariable); RESOURCE -> variable, resource or flow input")
        elif kind != "code":
            m = TINES_NS_SOFT.search(body)
            if m:
                self.warn("tines-syntax", w, "`%s` looks like a Tines namespace reference." % m.group(0))
        if kind == "expr":
            if body.lstrip().startswith("="):
                self.error("tines-syntax", w, "expression starts with `=` (Tines formula prefix).",
                           "write plain JavaScript without the leading `=`")
            if "|>" in body:
                self.error("tines-syntax", w, "Tines pipe operator `|>` is not JavaScript.",
                           "rewrite as nested calls / method chains, e.g. `xs.map(...).join(\",\")`")
            m = TINES_FUNC.search(body)
            if m:
                self.warn("tines-syntax", w, "`%s(` looks like a Tines formula function." % m.group(1),
                          "use JavaScript (e.g. SIZE(x) -> x.length, IS_BLANK(x) -> !x)")
        elif kind == "static":
            if re.match(r"^=\s*[A-Z][A-Z0-9_]*\s*\(", body):
                self.error("tines-syntax", w, "static value is a Tines formula `%s`." % body[:50],
                           "translate it: `type: javascript` with a JavaScript `expr`")
            elif re.match(r"^=\s*[A-Za-z_]\w*(\.\w+)*\s*$", body):
                self.warn("tines-syntax", w, "static value `%s` looks like a Tines `=reference`." % body[:50],
                          "use `type: javascript` with `expr: results.<id>...` or `flow_input.<name>`")
        elif kind == "code":
            if re.search(r"[\"'`]=\s*[A-Z][A-Z0-9_]{2,}\s*\(", body):
                self.warn("tines-syntax", w, "a string in the script looks like a Tines `=FORMULA(`.",
                          "compute the value in code instead")

        # $var: / $res:
        if kind == "static" and re.match(r"^\$(var|res):", text):
            path = text.split(":", 1)[1]
            if not WM_PATH_RE.match(path):
                self.error("var-res-path", w, "`%s`: path is not well-formed." % text[:80],
                           "use $%s:u/<user>/<name> or $%s:f/<folder>/<name> (no spaces, at least two `/`)"
                           % (text[1:4], text[1:4]))
        else:
            for m in VARRES.finditer(body):
                if not WM_PATH_RE.match(m.group(2)):
                    self.warn("var-res-path", w, "`%s`: path is not well-formed (expected "
                              "u/<user>/<name> or f/<folder>/<name>)." % m.group(0))
                if kind == "code":
                    self.warn("var-res-path", w, "`%s` inside script code is plain text; it is only "
                              "resolved in a static input value." % m.group(0),
                              "pass it as `{type: static, value: \"%s\"}` in input_transforms, or call "
                              "wmill.getVariable / wmill.getResource" % m.group(0))
                    break
        if kind == "static" and re.match(r"^\$(variable|variables|resource|resources|secret|vars):", text):
            self.warn("var-res-path", w, "`%s` is not a Windmill reference prefix." % text.split(":")[0],
                      "use `$var:<path>` for variables/secrets and `$res:<path>` for resources")


# ==========================================================================
# Coverage (--story)
# ==========================================================================

MAP_LINE = re.compile(r"^\s*(?:[-*]\s+)?((?:s\d+\.)?a\d+(?:\.\d+)?)\s*(?:->|=>|→|:)\s*(.*)$", re.I)
MAP_WORKFLOW = re.compile(r"^#\s*workflow\s*:\s*(\S+)", re.I)


def find_map(flow_dir, explicit):
    if explicit:
        return explicit
    for d in (flow_dir, os.path.dirname(os.path.abspath(flow_dir))):
        p = os.path.join(d, "tines_action_map.md")
        if os.path.isfile(p):
            return p
    return os.path.join(flow_dir, "tines_action_map.md")


def coverage(v, story_path, flow_dir, map_arg, out, workflow=None):
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        sys.dont_write_bytecode = True
        import tines_outline
    except ImportError:
        v.error("coverage", "story", "tines_outline.py must be in the same directory as validate_flow.py.")
        return
    try:
        export = tines_outline.load_export(story_path)
    except (OSError, ValueError) as exc:
        v.error("coverage", "story", "cannot read %s: %s" % (story_path, exc))
        return
    map_path = find_map(flow_dir, map_arg)
    entries, declared = {}, None
    if os.path.isfile(map_path):
        with open(map_path, encoding="utf-8") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.replace("`", "").strip()
                wf = MAP_WORKFLOW.match(line)
                if wf and declared is None:
                    declared = wf.group(1)
                if not line or line.startswith("#"):
                    continue
                m = MAP_LINE.match(line)
                if not m:
                    continue
                aid = m.group(1).lower()
                target = re.split(r"\s+#", m.group(2), maxsplit=1)[0].strip()
                if aid in entries:
                    v.warn("coverage", "action map line %d" % n, "action %s is listed twice; the later line wins." % aid)
                entries[aid] = (target, n)
    if workflow and declared and workflow.lower() != declared.lower():
        v.warn("coverage", "action map", "--workflow %s differs from the map's `# workflow: %s` line; "
               "using --workflow." % (workflow, declared))
    selector = workflow or declared
    if not selector and len(export.main.workflows) > 1:
        # no workflow named: accept the map only if all its lines point into one workflow
        seen = sorted({export.actions[a].get("workflow") or "none" for a in entries if a in export.actions})
        if len(seen) == 1 and seen[0] != "none":
            selector = seen[0]
            v.note("coverage: workflow %s inferred from the action ids in the map (add a `# workflow: %s` "
                   "line or pass --workflow to make it explicit)." % (selector, selector))
        else:
            v.error("coverage", "action map", "the story has %d workflows and nothing says which one this flow "
                    "ports%s." % (len(export.main.workflows),
                                  " (the map mixes ids of %s)" % ", ".join(seen) if len(seen) > 1 else ""),
                    "pass --workflow <id> (ids: `tines_outline.py %s --index`) and create the map with "
                    "`tines_outline.py %s --map-template --workflow <id>`" % (story_path, story_path))
            return
    try:
        label, story, _, ids = export.select(selector)
    except ValueError as exc:
        v.error("coverage", "story", "%s." % exc, "list the workflow ids with `tines_outline.py %s --index`" % story_path)
        return
    if label.startswith("story"):
        label = "the whole story" if story is export.main else "sub-story %s" % story.sid
    required = story.required(ids)
    template_cmd = "tines_outline.py %s --map-template%s > %s" % (
        story_path, " --workflow %s" % selector if selector else "", os.path.join(flow_dir, "tines_action_map.md"))
    out.append("")
    out.append("COVERAGE of %s, story \"%s\" (%d enabled, reachable actions) - map: %s"
               % (label, export.main.name, len(required), map_path))
    if not os.path.isfile(map_path):
        v.error("coverage", "action map", "%s does not exist, so no Tines action is accounted for." % map_path,
                "create it with `%s`, then replace every TODO" % template_cmd)
        return
    in_scope = set(ids)
    foreign = [aid for aid in entries if aid in export.actions and aid not in in_scope]
    for aid in entries:
        if aid not in export.actions:
            v.warn("coverage", "action map line %d" % entries[aid][1],
                   "`%s` is not an action id of this story (ids come from tines_outline.py)." % aid)
    if foreign:
        v.warn("coverage", "action map", "%d line(s) are for actions outside %s and are ignored: %s."
               % (len(foreign), label, ", ".join(foreign[:12]) + (" ..." if len(foreign) > 12 else "")))
    props = v.schema_props or {}
    by_target, dropped, todo, missing, noreason, bad_count = {}, [], [], [], [], 0
    for aid in required:
        a = story.actions[aid]
        desc = "%s \"%s\" [%s]" % (aid, a["name"], a["type"] + ("/" + a["mode"] if a["mode"] else ""))
        if aid not in entries:
            missing.append(aid)
            out.append("  MISSING  %s" % desc)
            continue
        target, n = entries[aid]
        if not target or target.upper().startswith("TODO") or target in ("?", "-"):
            todo.append(aid)
            out.append("  TODO     %s" % desc)
            continue
        if re.match(r"^DROPPED\b", target, re.I):
            reason = target[7:].lstrip(" :-")
            if reason:
                dropped.append("  dropped  %s - %s" % (desc, reason))
            else:
                noreason.append(aid)
                out.append("  NOREASON %s" % desc)
            continue
        bad = []
        targets = [x.strip() for x in re.split(r"[,\s]+", target) if x.strip()]
        for t in targets:
            if t.startswith("flow_input."):
                if t.split(".", 1)[1].split(".")[0] not in props:
                    bad.append((t, "is not in schema.properties." + suggest(t.split(".", 1)[1], props)))
            elif t not in v.ids:
                bad.append((t, "is not a module id in the flow." + suggest(t, v.ids)))
        if bad:
            bad_count += 1
            out.append("  BADREF   %s -> %s" % (desc, target))
            for t, why in bad:
                v.error("coverage", "Tines action %s" % desc, "maps to `%s`, which %s (map line %d)" % (t, why, n),
                        "use an existing module id, `flow_input.<name>`, or `DROPPED: <reason>`")
        else:
            for t in targets:
                by_target.setdefault(t, []).append(aid)
    if missing:
        v.error("coverage", "action map", "%d action(s) have no line: %s." % (len(missing), ", ".join(missing)),
                "add `<id> -> <module id>` (or `flow_input.<name>` / `DROPPED: <reason>`) for each")
    if todo:
        v.error("coverage", "action map", "%d action(s) are still TODO: %s." % (len(todo), ", ".join(todo)),
                "for each, read `tines_outline.py %s --action <id>`, make sure a module does its work, "
                "then replace TODO with that module id (or `DROPPED: <reason>`)" % story_path)
    if noreason:
        v.error("coverage", "action map", "%d action(s) are DROPPED without a reason: %s." % (len(noreason), ", ".join(noreason)),
                "write `<id> -> DROPPED: <why it is not needed in Windmill>`")
    for t in sorted(by_target):
        out.append("  ok       %s <- %s" % (t, ", ".join(by_target[t])))
    out.extend(dropped)
    n_bad = len(missing) + len(todo) + len(noreason) + bad_count
    out.append("  summary: %d mapped, %d dropped, %d not accounted for (of %d)"
               % (len(required) - n_bad - len(dropped), len(dropped), n_bad, len(required)))
    mapped_modules = set(by_target)
    containers = ("forloopflow", "whileloopflow", "branchone", "branchall")
    extra = sorted(i for i, recs in v.ids.items() if i not in mapped_modules and recs[0]["kind"] == "module")
    if extra:
        out.append("  flow modules no Tines action maps to (fine for glue/containers, check the rest): "
                   + ", ".join("%s%s" % (i, " (container)" if v.ids[i][0]["type"] in containers else "") for i in extra))


# ==========================================================================
# CLI
# ==========================================================================

def locate(path):
    """Return (flow_file, flow_dir) or raise ValueError."""
    if os.path.isdir(path):
        for name in ("flow.yaml", "flow.yml", "flow.json"):
            p = os.path.join(path, name)
            if os.path.isfile(p):
                return p, os.path.abspath(path)
        raise ValueError("%s contains no flow.yaml (or flow.yml / flow.json)" % path)
    if os.path.isfile(path):
        return path, os.path.dirname(os.path.abspath(path))
    raise ValueError("%s does not exist" % path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Validate a Windmill flow (see the header of this file for checks and conventions).")
    ap.add_argument("flow", help="<name>.flow directory, flow.yaml or flow.json")
    ap.add_argument("--story", help="Tines story export: also report action coverage via tines_action_map.md")
    ap.add_argument("--workflow", help="workflow of the story this flow ports (w03, s1.w01); default: the "
                    "`# workflow:` line of the action map")
    ap.add_argument("--map", help="path of the action map (default: tines_action_map.md in the flow folder)")
    ap.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")
    ap.add_argument("--builtin-yaml", action="store_true", help="use the built-in YAML loader even if PyYAML is installed")
    args = ap.parse_args(argv)

    try:
        flow_file, flow_dir = locate(args.flow)
        with open(flow_file, encoding="utf-8") as fh:
            text = fh.read()
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        print("ERROR [file] %s" % exc)
        print("RESULT: FAIL - flow could not be read")
        return 2

    if flow_file.endswith(".json"):
        loader = "JSON"
        try:
            data = json.loads(text)
        except ValueError as exc:
            print("validate_flow: %s" % flow_file)
            print("ERROR [json] %s. Fix: correct the JSON syntax at that position." % exc)
            print("RESULT: FAIL - flow could not be parsed")
            return 2
    else:
        try:
            data, loader = load_yaml(text, args.builtin_yaml)
        except YamlError as exc:
            lines = text.split("\n")
            print("validate_flow: %s" % flow_file)
            at = " line %d" % exc.line if exc.line else ""
            print("ERROR [yaml]%s: %s" % (at, exc))
            if exc.line and 0 < exc.line <= len(lines):
                print("      %d | %s" % (exc.line, lines[exc.line - 1]))
            print("      Fix: check indentation (spaces only, children indented consistently) and put "
                  "values containing `: `, ` #`, or starting with one of `*&!|>@%{[ in quotes or a "
                  "block scalar (`key: |`).")
            print("RESULT: FAIL - YAML does not parse; nothing else was checked")
            return 2

    print("validate_flow: %s (loader: %s)" % (flow_file, loader))
    if loader == "built-in":
        print("NOTE  PyYAML is not installed: using the built-in YAML subset loader. Anchors/aliases, "
              "merge keys, complex keys, multi-document files and tags other than !inline are "
              "reported as parse errors; all checks otherwise run as usual.")
    v = Validator(data, flow_dir, None if loader == "JSON" else text)
    v.run()
    extra = []
    if args.story:
        coverage(v, args.story, flow_dir, args.map, extra, args.workflow)
    for line in v.errors + v.warnings + v.notes + extra:
        print(line)
    n_mod = sum(1 for recs in v.ids.values() for r in recs if r["kind"] != "tool")
    failed = bool(v.errors) or (args.strict and bool(v.warnings))
    print("")
    print("RESULT: %s - %d error(s), %d warning(s), %d module(s) checked%s" % (
        "FAIL" if failed else "OK", len(v.errors), len(v.warnings), n_mod,
        "" if failed else " (structure and references only: this does not prove the flow runs "
        "or reproduces the story's logic)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
