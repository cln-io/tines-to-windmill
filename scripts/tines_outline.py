#!/usr/bin/env python3
"""tines_outline.py - compact digest of an exported Tines story, readable in pieces.

Work from this digest instead of the raw story JSON (which is mostly layout
and metadata noise). Every text output starts with a `# ... N chars (~T tokens)`
line so you know what you just spent, and nothing bigger than --budget is
printed unless you ask for it with --full.

USAGE (S = the exported story JSON)
  tines_outline.py S                     small story: the full digest.
                                         large story: the INDEX (same as --index).
  tines_outline.py S --index             one line per workflow + what is not triggered,
                                         sub-stories, called stories, callable resources.
  tines_outline.py S --workflow w03      one workflow in full detail, groups expanded.
                                         Too big for the budget -> an overview that
                                         lists the exact commands for each piece.
                                         Accepts w03, s1.w02, or any action id in it.
  tines_outline.py S --workflow w03 --graph    graph only (groups expanded)
  tines_outline.py S --workflow w03 --brief    graph + one line per action
  tines_outline.py S --group a012        the inside of one group action (paged the
                                         same way when it is too big)
  tines_outline.py S --actions a012.001-a012.040   digest of an id range or list
                                         (a007,a009). Same content as in a workflow.
  tines_outline.py S --page a030         digest of one page (form) action
  tines_outline.py S --action a007       one action, raw options JSON, nothing
                                         elided; id or reference name; repeatable
  tines_outline.py S --story s1          an embedded sub-story (index or full digest)
  tines_outline.py S --map-template --workflow w03   skeleton tines_action_map.md
                                         for validate_flow.py --story (omit --workflow
                                         for a single-workflow story)
  tines_outline.py S --json [--workflow w03]         machine-readable
  Modifiers: --full (ignore the budget, elide nothing), --budget N (chars,
  default 32000).

WORDS
  workflow  a set of top-level actions connected by links, with at least one
            entry point (schedule, webhook, page, send-to-story entry). Big
            stories are often many unrelated workflows on one canvas; each one
            becomes its own Windmill flow. Ids: w01, w02, ... (s1.w01 inside
            embedded sub-story s1), numbered by position in the export.
  aNN       an action, numbered by position in the export (a01 = first).
            aNN.MM = action MM inside group action aNN. s1.aNN = action of
            embedded sub-story s1. Ids are stable for a given export file.
  ref name  the snake_cased action name used by formulas (<<fetch_orders.body>>).
            Names are NOT unique in Tines: a formula sees the nearest upstream
            action with that name. Each reference is resolved to an id, and
            marked when it is ambiguous or not upstream.

GRAPH MARKERS
  FAN-OUT xN   emits to N receivers (parallel branches)
  NO-MATCH FAN-OUT xN   a trigger with N no-match links: when its rules do not
               match, ALL N of them fire, in parallel, like a fan-out
  recipe N,M   sections of references/patterns.md that cover this action's
               shape (`ref.py patterns N`). The header of a workflow lists the
               distinct numbers to read. No number: nothing special to port.
  JOIN xN      N inbound links
  CYCLE        part of a loop of links (retry / poll loop)
  ^ aNN ...    link to an action already printed (join, or loop back)
  (no-match)   link taken when a trigger's rules do NOT match (one match link +
               one no-match link is an if / else, not a fan-out)
  END          no outgoing links
  DEAD-END     no outgoing links and no side effect (unused trigger/transform)
  NO-EFFECT    (index, workflow header) no action that runs in the workflow has
               an outside effect: no HTTP request other than GET, email, story
               call, record, or page shown to a person. Plan: SKIP: no effect
  DISABLED     disabled; it and everything only reachable through it never runs
  UNREACHABLE  enabled, but no enabled path from any entry point

WHAT IS SHOWN FOR AN ACTION
  id, ref name, type/mode, links, the actions and globals it references
  (parsed from <<pills>>, =formulas and <%if%>/<%for%> text tags), action inputs,
  and its options. Formulas are never shortened. Layout, monitoring, reporting,
  template, logo and colour settings are dropped. Multi-line text is shown as a
  block whose marker says exactly how the text ends: `|-` no trailing newline,
  `|` exactly one, `|+` every blank line shown is part of the text. A name
  listed as unresolved is one no action on the path provides: it is NULL in
  Tines, port it as null. A run of static text longer
  than 400 characters (embedded HTML/CSV/base64) is shortened to its head and
  tail with a marker `[... N chars of static text elided; full: --action ID]`.
  Pages show mode, visibility, input fields and buttons, display conditions and
  where they submit. Record actions show the record type and each field
  formula. Send-to-story actions show which story they call and whether its
  body is embedded in this export; for an embedded one, also the payload keys
  the called story reads, those sent but never read, and those read but not
  sent. The index entry of a callable sub-story lists the keys it reads. Webhook secrets are redacted.

GLOBALS
  CREDENTIAL.x / RESOURCE.x / other namespaces, with the actions using them
  (an id tagged (unreachable) or (disabled) never runs). The index counts
  only actions that run.
  `CALLED AS FUNCTION` marks a resource that holds lambdas invoked from
  formulas (<<RESOURCE.text_helpers.shorten(x, 30)>>): the lambda bodies are
  NOT in the export, ask the user for them.

Python 3 standard library only.
"""
import argparse
import json
import os
import re
import sys
from collections import deque

DEFAULT_BUDGET = 32000
STATIC_RUN_LIMIT = 400
STATIC_HEAD, STATIC_TAIL = 160, 80
INDEX_MEMBER_CAP = 8      # plain top-level actions named per workflow line in the index

TYPE_NAMES = {
    "HTTPRequestAgent": "http_request",
    "EventTransformationAgent": "event_transform",
    "TriggerAgent": "trigger",
    "EmailAgent": "send_email",
    "WebhookAgent": "webhook",
    "IMAPAgent": "receive_email",
    "SendToStoryAgent": "send_to_story",
    "GroupAgent": "group",
    "GroupInputAgent": "group_input",
    "GroupOutputAgent": "group_output",
    "FormAgent": "page",
    "RecordAgent": "record",
    "RunScriptAgent": "run_script",
    "LLMAgent": "ai",
}
# Action types that start a run by themselves when they have no inbound link.
SELF_TRIGGERING = {"webhook": "webhook", "receive_email": "incoming email", "page": "page"}
NO_SIDE_EFFECT = {"trigger", "event_transform"}
PLUMBING = ("group_input", "group_output")
# Namespaces scoped to one action / loop rather than global.
ACTION_SCOPED_NS = {"LOCAL", "INPUT", "GROUP_INPUT", "LOOP", "FORLOOP"}
LITERALS = {"TRUE", "FALSE", "NULL", "NIL"}
PAGE_NOISE = {"fields", "page_logo", "page_width", "pages_action_color", "pages_appearance_mode",
              "pages_background_color", "mode"}
PAGE_TEXT_TYPES = {"TITLE", "PARAGRAPH", "DIVIDER", "IMAGE"}


# --------------------------------------------------------------------------
# Recipes: which section of references/patterns.md covers the shape of an action.
# One row per recipe: (number, what the outline shows, test). The test gets the
# action and a small context and returns True when the recipe applies. To change
# the mapping, edit this table only. Rows whose number has no section in
# patterns.md are reported on stderr and not printed.
# --------------------------------------------------------------------------

def _opt_on(a, key):
    return a["options"].get(key) not in (None, False, "", "false", "False", 0)


def _status_rules(a):
    """Values a trigger compares an HTTP status with."""
    if a["type"] != "trigger":
        return []
    rules = a["options"].get("rules")
    return [str(r.get("value")) for r in rules if isinstance(r, dict) and ".status" in str(r.get("path"))] \
        if isinstance(rules, list) else []


def _tines_api(a):
    if a["type"] != "http_request":
        return False
    headers = a["options"].get("headers") if isinstance(a["options"].get("headers"), dict) else {}
    return "global_resources" in str(a["options"].get("url")) or any(str(k).lower() == "x-user-token" for k in headers)


def _resource_write(a):
    method = str(a["options"].get("method") or "").lower()
    return _tines_api(a) and method not in ("", "get") and (
        "global_resources" in str(a["options"].get("url")) or
        (isinstance(a["options"].get("payload"), dict) and "value" in a["options"]["payload"]))


RECIPES = [
    (1, "schedule on an action", lambda a, c: bool(a["schedule"])),
    (2, "webhook entry, body fields only", lambda a, c: a["type"] == "webhook" and not c["webhook_extra"]),
    (3, "webhook entry that needs headers, query or accepts GET", lambda a, c: a["type"] == "webhook" and c["webhook_extra"]),
    (4, "page that starts a workflow", lambda a, c: a["type"] == "page" and not a["in"]),
    (5, "page in the middle of a workflow", lambda a, c: a["type"] == "page" and bool(a["in"])),
    (6, "HTTP request / 2xx status trigger", lambda a, c: (a["type"] == "http_request" and not _tines_api(a))
        or any(v.startswith("2") for v in _status_rules(a))),
    (7, "non-2xx status treated as data", lambda a, c: any(not v.startswith("2") for v in _status_rules(a))
        or (bool(_status_rules(a)) and any(k == "no-match" for _, k in a["out"]))),
    (8, "retry settings on an HTTP request", lambda a, c: a["type"] == "http_request"
        and (_opt_on(a, "retry_on_status") or _opt_on(a, "retries"))),
    (9, "poll / retry loop of links", lambda a, c: a["in_cycle"]),
    (10, "TLS verification disabled", lambda a, c: _opt_on(a, "disable_ssl_verification")),
    (11, "message-only transform", lambda a, c: a["type"] == "event_transform" and a["mode"] == "message_only"),
    (12, "<%for%> / <%if%> tags in text", lambda a, c: c["has_tags"]),
    (13, "explode / implode", lambda a, c: a["mode"] in ("explode", "implode")),
    (14, "trigger with a no-match link", lambda a, c: any(k == "no-match" for _, k in a["out"] + a["in"])),
    (15, "fan-out", lambda a, c: bool(a["fan_out"] or a["nomatch_fan_out"])),
    (16, "join of several links", lambda a, c: bool(a["join"]) and a["mode"] != "implode" and not a["in_cycle"]),
    (17, "group action", lambda a, c: a["type"] == "group"),
    (18, "send to story, callee in the export", lambda a, c: bool(a["calls"] and a["calls"]["embedded"])),
    (19, "delay", lambda a, c: a["mode"] == "delay" and not a["in_cycle"]),
    (20, "throttle", lambda a, c: a["mode"] == "throttle"),
    (21, "deduplicate", lambda a, c: a["mode"] == "deduplicate"),
    (22, "send email", lambda a, c: a["type"] == "send_email"),
    (23, "resource that is only read", lambda a, c: bool(c["resources"] - c["written"]
        - {k.split(".", 1)[1] for k in a["called"]}) and not _tines_api(a)),   # a resource called as a function is recipe 27
    (24, "resource written through the Tines API (state)", lambda a, c: _resource_write(a) or bool(c["resources"] & c["written"])),
    (25, "credential", lambda a, c: any(g.startswith("CREDENTIAL") for g in a["globals"])),
    (26, "META / story run id", lambda a, c: any(g.split(".")[0] == "META" for g in a["globals"]) or c["run_guid"]),
    (27, "missing logic: lambda, story not in export, other Tines API call",
        lambda a, c: bool(a["called"]) or bool(a["calls"] and not a["calls"]["embedded"])
        or (_tines_api(a) and not _resource_write(a))),
    (29, "disabled, unreachable or dead end", lambda a, c: a["status"] != "active" or a["dead_end"]),
    (30, "early exit, then a shared final step that reads the skipped action", lambda a, c: bool(a["join"])
        and not a["in_cycle"] and any(set(r["actions"]) & c["skippable_sources"] for r in a["refs"])),
    (31, "link to a page of another workflow (PAGE.x)", lambda a, c: a["type"] != "page"
        and any(g.split(".")[0] == "PAGE" for g in a["globals"])),
]


def known_recipes():
    """Section numbers present in ../references/patterns.md, or None when the file is absent."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "patterns.md")
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except OSError:
        return None
    found, fence = set(), False
    for line in lines:
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        elif not fence:
            m = re.match(r"^#{2,3}\s+(\d+)[.):]?\s", line)
            if m:
                found.add(int(m.group(1)))
    return found


def outside_effect(a):
    """Short description of what an action changes outside the story run, or None.

    HTTP GET, triggers, transforms, groups and entry points only read or route.
    Types this script does not know are assumed to have an effect.
    """
    typ = a["type"]
    if a.get("exit"):
        return "returns data to the calling story"
    if typ == "http_request":
        method = a["options"].get("method")
        method = method.strip().lower() if isinstance(method, str) else ""
        return None if method == "get" else "HTTP %s" % (method.upper() or "request with a computed method")
    if typ == "page":
        return "page shown to a person" if a["in"] else None
    if typ in ("send_email", "send_to_story", "record"):
        return {"send_email": "sends email", "send_to_story": "calls a story", "record": "writes a record"}[typ]
    if typ in NO_SIDE_EFFECT or typ in PLUMBING or typ in ("group", "webhook", "receive_email"):
        return None
    return "%s action" % typ


def snake(name):
    """Tines reference name for an action / input / field name."""
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    if not s:
        return "_"
    return "_" + s if s[0].isdigit() else s


def short_type(raw):
    t = (raw or "").split("::")[-1]
    if t in TYPE_NAMES:
        return TYPE_NAMES[t]
    t = re.sub(r"Agent$", "", t)
    t = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", t)
    return t.lower() or "unknown"


def short_size(n):
    tokens = max(1, n // 4)
    return "~%.1fk tok" % (tokens / 1000.0) if tokens >= 1000 else "~%d tok" % tokens


def size_text(n):
    return "%s chars (~%s tokens)" % ("{:,}".format(n), "{:,}".format(max(1, n // 4)))


# --------------------------------------------------------------------------
# Formula source inside option strings: <<pills>>, =formulas, <%tags%>
# --------------------------------------------------------------------------

DYNAMIC_RE = re.compile(r"<<.*?>>|<%.*?%>", re.S)
STRING_LIT_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
IDENT_RE = re.compile(r"(?<![\w.])([A-Za-z_]\w*)((?:\s*\.\s*\w+)*)")
LAMBDA_RE = re.compile(r"\bLAMBDA\s*\(\s*((?:[A-Za-z_]\w*\s*,\s*)+)")
TAG_FOR_RE = re.compile(r"^for\s+([A-Za-z_]\w*)(?:\s*,\s*([A-Za-z_]\w*))?\s+in\s+(.*)$", re.S)
TAG_IF_RE = re.compile(r"^(?:if|elseif|elsif|unless)\s+(.*)$", re.S)


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_strings(v)


def formula_parts(text):
    """Return (expressions, local names) found in one option string."""
    if text.startswith("="):
        return [text[1:]], set()
    exprs, local_names = [], set()
    for m in DYNAMIC_RE.finditer(text):
        token = m.group(0)
        body = token[2:-2].strip()
        if token.startswith("<<"):
            exprs.append(body)
            continue
        loop = TAG_FOR_RE.match(body)
        if loop:
            local_names.update(n for n in loop.group(1, 2) if n)
            exprs.append(loop.group(3))
            continue
        cond = TAG_IF_RE.match(body)
        if cond:
            exprs.append(cond.group(1))
    return exprs, local_names


def identifiers_in(expr, local_names=()):
    """Yield (head, path, called) for every variable-like token in a formula."""
    expr = STRING_LIT_RE.sub('""', expr)
    skip = set(local_names)
    for m in LAMBDA_RE.finditer(expr):
        skip.update(p.strip() for p in m.group(1).split(",") if p.strip())
    for m in IDENT_RE.finditer(expr):
        head, path = m.group(1), re.sub(r"\s+", "", m.group(2))
        called = expr[m.end():].lstrip().startswith("(")
        if called and not path:
            continue  # plain function call
        if head in skip or head.upper() in LITERALS:
            continue
        yield head, path, called


def elide_static(text, hint):
    """Shorten long runs of static text; pills, tags and formulas stay intact."""
    if len(text) <= STATIC_RUN_LIMIT or text.startswith("="):
        return text
    out, pos = [], 0
    for m in list(DYNAMIC_RE.finditer(text)) + [None]:
        end = m.start() if m else len(text)
        run = text[pos:end]
        if len(run) > STATIC_RUN_LIMIT:
            cut = len(run) - STATIC_HEAD - STATIC_TAIL
            run = "%s[... %s chars of static text elided; full: %s]%s" % (
                run[:STATIC_HEAD], "{:,}".format(cut), hint, run[-STATIC_TAIL:])
        out.append(run)
        if m:
            out.append(m.group(0))
            pos = m.end()
    return "".join(out)


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

class Story:
    """One story of the export: the main one, or an embedded sub-story."""

    def __init__(self, raw, sid, prefix):
        self.raw = raw
        self.sid = sid                 # "main" or "s1"
        self.prefix = prefix           # "" or "s1."
        self.name = raw.get("name") or ""
        self.slug = raw.get("slug") or snake(self.name)
        self.actions = {}              # id -> action dict
        self.order = []                # ids, depth first (group internals after their group)
        self.scopes = {}               # None or group action id -> [ids]
        self.inputs_by_guid = {}
        self.notes = {}                # None or group action id -> (sticky notes, layout)
        self.pages_by_guid = {p.get("agent_guid"): p for p in raw.get("pages") or []
                              if isinstance(p, dict)}
        self._collect_inputs(raw)
        self._build_scope(raw, None, prefix + "a", 0)
        self._entry_points()
        self._status(None, True, None)
        self._graph_flags()
        self._workflows()
        self._references()

    # -- construction ------------------------------------------------------
    def _collect_inputs(self, container):
        for integ in container.get("integrations") or []:
            guid = integ.get("action_guid")
            inputs = {}
            for inp in integ.get("action_inputs") or []:
                value = inp.get("value")
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                entry = {"value": value}
                if inp.get("required"):
                    entry["required"] = True
                if inp.get("type") and inp["type"] != "TEXT":
                    entry["type"] = inp["type"]
                    if inp["type"] == "OPTION" and inp.get("options"):
                        entry["choices"] = inp["options"]
                inputs[snake(inp.get("name"))] = entry
            if guid and inputs:
                self.inputs_by_guid.setdefault(guid, {}).update(inputs)

    def _build_scope(self, container, parent, prefix, depth):
        agents = container.get("agents") or []
        width = max(2, len(str(len(agents))))
        ids = []
        for i, ag in enumerate(agents):
            aid = "%s%0*d" % (prefix, width, i + 1)
            typ = short_type(ag.get("type"))
            options = ag.get("options") if isinstance(ag.get("options"), dict) else {}
            act = {
                "id": aid, "index": i, "depth": depth, "story": self.sid,
                "name": ag.get("name") or "", "ref": snake(ag.get("name")),
                "type": typ, "raw_type": ag.get("type"),
                "mode": options.get("mode") if isinstance(options.get("mode"), str) else None,
                "disabled": bool(ag.get("disabled")),
                "schedule": ag.get("schedule") or [],
                "guid": ag.get("guid"), "description": ag.get("description"),
                "options": options,
                "inputs": self.inputs_by_guid.get(ag.get("guid"), {}),
                "group": parent, "children": [],
                "out": [], "in": [], "entry": [],
                "page": None, "record": None, "calls": None,
            }
            if typ == "page":
                act["page"] = self._page(ag)
            elif typ == "record":
                act["record"] = self._record(ag)
            self.actions[aid] = act
            self.order.append(aid)
            ids.append(aid)
            if isinstance(ag.get("group"), dict):
                self._collect_inputs(ag["group"])
                act["children"] = self._build_scope(ag["group"], aid, aid + ".", depth + 1)
        self.scopes[parent] = ids
        try:
            layout = json.loads(container.get("diagram_layout") or "{}")
        except (ValueError, TypeError):
            layout = {}
        self.notes[parent] = (container.get("diagram_notes") or [], layout if isinstance(layout, dict) else {})
        for link in container.get("links") or []:
            try:
                s, r = ids[link["source"]], ids[link["receiver"]]
            except (KeyError, IndexError, TypeError):
                continue
            kind = "no-match" if link.get("link_type") == "secondary" else (link.get("link_type") or "")
            self.actions[s]["out"].append((r, kind))
            self.actions[r]["in"].append((s, kind))
        return ids

    def _page(self, agent):
        page = self.pages_by_guid.get(agent.get("guid")) or {}
        elements, by_guid, by_container = [], {}, {}
        fields = [f for f in sorted(page.get("fields") or [], key=lambda f: f.get("ranking") or 0)
                  if isinstance(f, dict)]
        total, seen = {}, {}
        for f in fields:
            total[f.get("name") or ""] = total.get(f.get("name") or "", 0) + 1
        for f in fields:
            ftype = f.get("type") or "?"
            name = f.get("name") or ""
            seen[name] = seen.get(name, 0) + 1
            # label is unique on the page: a repeated name gets #1, #2 ... in page order
            el = {"name": name, "type": ftype,
                  "label": "%s#%d" % (name, seen[name]) if total[name] > 1 else name}
            if ftype not in PAGE_TEXT_TYPES and ftype != "BUTTON":
                el["ref"] = snake(f.get("name"))
            for key in ("content", "description", "options", "default_value"):
                value = f.get(key)
                if key == "default_value" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                if value not in (None, "", [], {}):
                    el[key] = value
            if f.get("required"):
                el["required"] = True
            elements.append(el)
            by_guid[f.get("guid")] = el["label"]
            by_container.setdefault(f.get("container_guid"), []).append(el["label"])
        conditions = []
        for cond in page.get("conditions") or []:
            if not isinstance(cond, dict):
                continue
            targets = [n for g in cond.get("container_guids") or [] for n in by_container.get(g, [])]
            rules = ["%s %s%s" % (by_guid.get(r.get("page_element_guid"), "?"), r.get("rule"),
                                  " %s" % json.dumps(r["value"]) if r.get("value") not in (None, "") else "")
                     for r in cond.get("rules") or [] if isinstance(r, dict)]
            conditions.append("%s [%s] when %s: %s" % (
                cond.get("condition_type"), ", ".join(targets) or "?",
                cond.get("match_rule"), "; ".join(rules)))
        return {"found": bool(page), "elements": elements, "conditions": conditions,
                "success_message": page.get("success_message") or None}

    @staticmethod
    def _record(agent):
        rtype = agent.get("record_type") if isinstance(agent.get("record_type"), dict) else {}
        writers = []
        for w in agent.get("record_writers") or []:
            if not isinstance(w, dict):
                continue
            field = w.get("record_field") if isinstance(w.get("record_field"), dict) else {}
            writers.append({"field": field.get("name"), "type": field.get("result_type"),
                            "formula": w.get("formula")})
        return {"record_type": rtype.get("name"), "writers": writers}

    def _entry_points(self):
        raw = self.raw
        entry_guid = raw.get("entry_agent_guid")
        api_entries = set(raw.get("api_entry_action_guids") or [])
        for aid in self.scopes[None]:
            a = self.actions[aid]
            for sch in a["schedule"]:
                if isinstance(sch, dict):
                    tz = " (%s)" % sch["timezone"] if sch.get("timezone") else ""
                    a["entry"].append("schedule cron %s%s" % (sch.get("cron"), tz))
                else:
                    a["entry"].append("schedule %s" % (sch,))
            if a["type"] in SELF_TRIGGERING and (a["type"] != "page" or not a["in"]):
                a["entry"].append(SELF_TRIGGERING[a["type"]])
            if entry_guid and a["guid"] == entry_guid:
                a["entry"].append("send-to-story entry")
            if a["guid"] in api_entries:
                a["entry"].append("API entry")
        for key, ids in self.scopes.items():
            if key is None:
                continue
            inputs = [i for i in ids if self.actions[i]["type"] == "group_input"]
            for i in inputs or [i for i in ids if not self.actions[i]["in"]]:
                self.actions[i]["entry"].append("group input")

    def _status(self, scope, running, why):
        """status: active | disabled | unreachable (+ status_reason)."""
        ids = self.scopes[scope]
        reached = set()
        if running:
            queue = deque(i for i in ids if self.actions[i]["entry"] and not self.actions[i]["disabled"])
            reached.update(queue)
            while queue:
                for nxt, _ in self.actions[queue.popleft()]["out"]:
                    if nxt not in reached and not self.actions[nxt]["disabled"]:
                        reached.add(nxt)
                        queue.append(nxt)
        for i in ids:
            a = self.actions[i]
            if a["disabled"]:
                a["status"], a["status_reason"] = "disabled", "disabled"
            elif not running:
                a["status"], a["status_reason"] = why
            elif i in reached:
                a["status"], a["status_reason"] = "active", ""
            else:
                a["status"] = "unreachable"
                if not a["in"]:
                    a["status_reason"] = "no inbound links and not an entry point"
                elif any(self.actions[s]["disabled"] for s, _ in a["in"]):
                    a["status_reason"] = "only reachable through disabled actions"
                else:
                    a["status_reason"] = "no enabled path from an entry point"
            if a["children"]:
                if a["status"] == "active":
                    self._status(i, True, None)
                elif a["status"] == "disabled":
                    self._status(i, False, ("disabled", "group %s is disabled" % i))
                else:
                    self._status(i, False, ("unreachable", "group %s is unreachable" % i))

    def _graph_flags(self):
        exits = set(self.raw.get("exit_agent_guids") or []) | set(self.raw.get("api_exit_action_guids") or [])
        for aid in self.order:
            a = self.actions[aid]
            a["exit"] = a["guid"] in exits
            primary = sum(1 for _, k in a["out"] if k != "no-match")
            other = len(a["out"]) - primary
            a["fan_out"] = primary if primary > 1 else 0          # several match / ordinary links
            a["nomatch_fan_out"] = other if other > 1 else 0      # several no-match links: all fire
            a["join"] = len(a["in"]) if len(a["in"]) > 1 else 0
            a["in_cycle"] = aid in self._descendants(aid)
            a["end"] = not a["out"]
            a["dead_end"] = (a["end"] and a["type"] in NO_SIDE_EFFECT and not a["exit"])
            a["effect"] = outside_effect(a)

    def _descendants(self, aid):
        seen, queue = set(), deque([aid])
        while queue:
            for nxt, _ in self.actions[queue.popleft()]["out"]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def _ancestor_distance(self, aid):
        dist, queue = {aid: 0}, deque([aid])
        while queue:
            cur = queue.popleft()
            for prev, _ in self.actions[cur]["in"]:
                if prev not in dist:
                    dist[prev] = dist[cur] + 1
                    queue.append(prev)
        return dist

    def members(self, top_ids):
        """Top-level ids plus everything nested inside their groups, in export order."""
        out = []

        def add(aid):
            out.append(aid)
            for child in self.actions[aid]["children"]:
                add(child)
        for aid in top_ids:
            add(aid)
        return out

    def _workflows(self):
        top = self.scopes[None]
        comp = {i: i for i in top}

        def find(x):
            while comp[x] != x:
                comp[x] = comp[comp[x]]
                x = comp[x]
            return x
        for i in top:
            for nxt, _ in self.actions[i]["out"]:
                comp[find(i)] = find(nxt)
        groups = {}
        for i in top:
            groups.setdefault(find(i), []).append(i)
        self.workflows, self.orphans = [], []
        for ids in groups.values():
            entries = [i for i in ids if self.actions[i]["entry"]]
            if entries:
                wid = "%sw%02d" % (self.prefix, len(self.workflows) + 1)
                wf = {"id": wid, "top": ids, "all": self.members(ids), "entries": entries,
                      "disabled": all(self.actions[i]["disabled"] for i in entries)}
                wf["no_effect"] = not wf["disabled"] and not any(
                    self.actions[i]["status"] == "active" and self.actions[i]["effect"] for i in wf["all"])
                self.workflows.append(wf)
                for i in wf["all"]:
                    self.actions[i]["workflow"] = wid
            else:
                self.orphans.append(ids)
                for i in self.members(ids):
                    self.actions[i]["workflow"] = None

    def _sources(self, a):
        """Every string of an action that may hold formulas."""
        opts = a["options"] if a["type"] != "page" else {k: v for k, v in a["options"].items() if k != "page_logo"}
        if isinstance(opts.get("rules"), list):
            # A formula rule keeps its formula in `path`; Tines ignores its `value` (often a leftover).
            opts = dict(opts, rules=[{k: v for k, v in r.items() if k != "value"}
                                     if isinstance(r, dict) and str(r.get("type", "")).strip() in ("formula", "not formula")
                                     else r for r in opts["rules"]])
        yield from iter_strings(opts)
        yield from iter_strings([v.get("value") for v in a["inputs"].values()])
        if a["page"]:
            for el in a["page"]["elements"]:
                yield from iter_strings([el.get(k) for k in ("content", "options", "default_value")])
        if a["record"]:
            yield from iter_strings([w.get("formula") for w in a["record"]["writers"]])

    def _references(self):
        self.namespaces = {}   # "CREDENTIAL.x" -> {"actions": [ids], "called": [function names]}
        self.duplicates = {}   # scope -> {ref: [ids]}
        for scope, ids in self.scopes.items():
            by_ref = {}
            for i in ids:
                by_ref.setdefault(self.actions[i]["ref"], []).append(i)
            self.duplicates[scope] = {r: v for r, v in by_ref.items() if len(v) > 1}
            for i in ids:
                a = self.actions[i]
                dist = self._ancestor_distance(i)
                found, globals_used, called, unresolved = {}, [], {}, []
                for text in self._sources(a):
                    exprs, local_names = formula_parts(text)
                    for expr in exprs:
                        for head, path, is_call in identifiers_in(expr, local_names):
                            if head.isupper():
                                parts = [p for p in path.split(".") if p]
                                fn = None
                                if is_call:
                                    fn = parts.pop() if len(parts) > 1 else "(the value itself)"
                                key = head + ("." + parts[0] if parts else "")
                                if key not in globals_used:
                                    globals_used.append(key)
                                if fn and fn not in called.setdefault(key, []):
                                    called[key].append(fn)
                                continue
                            if is_call:
                                path = path.rsplit(".", 1)[0]
                            full = head + path
                            if head in by_ref:
                                found.setdefault(head, []).append(full)
                            elif head == "input" and a["group"]:
                                if "GROUP_INPUT (input.*)" not in globals_used:
                                    globals_used.append("GROUP_INPUT (input.*)")
                            elif full not in unresolved:
                                unresolved.append(full)
                refs = []
                for ref, paths in found.items():
                    cands = by_ref[ref]
                    upstream = sorted((c for c in cands if c in dist and c != i), key=lambda c: dist[c])
                    entry = {"ref": ref, "paths": sorted(set(paths))}
                    if upstream:
                        entry["actions"] = upstream
                        entry["resolution"] = "ambiguous" if len(upstream) > 1 else "ok"
                    elif i in cands:
                        entry["actions"] = [i]
                        entry["resolution"] = "self"
                    else:
                        entry["actions"] = cands
                        entry["resolution"] = "not-upstream"
                    refs.append(entry)
                a["refs"], a["globals"], a["unresolved"], a["called"] = refs, globals_used, unresolved, called
                for g in globals_used:
                    if g.split(".")[0].split(" ")[0] in ACTION_SCOPED_NS:
                        continue
                    rec = self.namespaces.setdefault(g, {"actions": [], "called": []})
                    rec["actions"].append(i)
                    for fn in called.get(g, []):
                        if fn not in rec["called"]:
                            rec["called"].append(fn)

    def required(self, ids=None):
        """Actions a translation must account for: enabled, reachable, not group plumbing."""
        return [i for i in (self.order if ids is None else ids)
                if self.actions[i]["status"] == "active" and self.actions[i]["type"] not in PLUMBING]


class Export:
    """A story export: the main story plus any sub-stories embedded under send_to_stories."""

    def __init__(self, raw):
        self.stories = []
        self._add(raw)
        self.actions = {}
        for s in self.stories:
            self.actions.update(s.actions)
        self.main = self.stories[0]
        by_slug = {}
        for s in self.stories[1:]:
            by_slug.setdefault(s.slug, s.sid)
            by_slug.setdefault(snake(s.name), s.sid)
        self.called_stories = {}   # slug -> {"embedded": sid or None, "callers": [ids]}
        for s in self.stories:
            for aid in s.order:
                a = s.actions[aid]
                if a["type"] != "send_to_story":
                    continue
                target = a["options"].get("story")
                m = re.search(r"\bSTORY\.(\w+)", target) if isinstance(target, str) else None
                slug = m.group(1) if m else None
                a["calls"] = {"story": slug, "raw": target, "embedded": by_slug.get(slug)}
                if slug:
                    rec = self.called_stories.setdefault(slug, {"embedded": by_slug.get(slug), "callers": []})
                    rec["callers"].append(aid)
        for s in self.stories:
            s.input_keys = self._input_keys(s)
        for s in self.stories:
            for aid in s.order:
                c = s.actions[aid]["calls"]
                if c and c["embedded"]:
                    self._compare_payload(s.actions[aid], self.story(c["embedded"]))
        self._recipes()

    @staticmethod
    def _input_keys(story):
        """Dotted paths a callable story reads from the body its caller sends (entry.body.x.y)."""
        guid = story.raw.get("entry_agent_guid")
        entry = next((a for a in story.actions.values() if guid and a["guid"] == guid), None)
        if not entry:
            return None
        readers = [a for a in story.actions.values() if a["status"] == "active"] or list(story.actions.values())
        keys = set()
        for a in readers:
            for r in a["refs"]:
                if r["ref"] != entry["ref"] or entry["id"] not in r["actions"]:
                    continue
                for path in r["paths"]:
                    parts = path.split(".")[1:]
                    if parts[:1] == ["body"]:
                        keys.add(".".join(parts[1:4]) or "(the whole body)")
        return {"entry": entry["id"], "keys": sorted(keys)}

    @staticmethod
    def _compare_payload(action, callee):
        c = action["calls"]
        payload = action["options"].get("payload")
        info = callee.input_keys
        if not info or not isinstance(payload, dict):
            c["reads"] = info["keys"] if info else None
            c["sent"] = sorted(payload) if isinstance(payload, dict) else None
            return
        read_top = {k.split(".")[0] for k in info["keys"] if not k.startswith("(")}
        whole = any(k.startswith("(") for k in info["keys"])
        c["reads"], c["sent"] = info["keys"], sorted(payload)
        c["sent_not_read"] = [] if whole else sorted(set(payload) - read_top)
        c["read_not_sent"] = sorted(read_top - set(payload))

    def _recipes(self):
        known = known_recipes()
        table = RECIPES
        if known is None:
            sys.stderr.write("tines_outline: note: references/patterns.md not found next to the scripts; "
                             "recipe numbers are not printed.\n")
            table = []
        else:
            missing = [n for n, _, _ in RECIPES if n not in known]
            if missing:
                sys.stderr.write("tines_outline: warning: recipe(s) %s have no section in references/patterns.md "
                                 "and are not printed; update RECIPES in tines_outline.py.\n"
                                 % ", ".join(map(str, missing)))
            table = [r for r in RECIPES if r[0] in known]
        for s in self.stories:
            written = set()
            for a in s.actions.values():
                if _resource_write(a):
                    blob = json.dumps(a["options"], ensure_ascii=False)
                    written.update(k.split(".", 1)[1] for k in s.namespaces
                                   if k.startswith("RESOURCE.") and re.search(r"\b%s\b" % re.escape(k.split(".", 1)[1]), blob))
            header_readers = set()
            for a in s.actions.values():
                for r in a["refs"]:
                    if any(re.match(r"^\w+\.(headers|query|method)\b", pth) for pth in r["paths"]):
                        header_readers.update(r["actions"])
            for a in s.actions.values():
                texts = list(s._sources(a))
                ctx = {
                    "webhook_extra": a["id"] in header_readers,
                    "has_tags": any("<%" in t for t in texts),
                    "run_guid": any("STORY_RUN_GUID" in t for t in texts),
                    "resources": {g.split(".", 1)[1] for g in a["globals"] if g.startswith("RESOURCE.")},
                    "written": written,
                    # direct match-side sources of an action that a no-match link also reaches (recipe 30)
                    "skippable_sources": ({s.actions[k]["id"] for k, kind in a["in"] if kind != "no-match"}
                                          if any(kind == "no-match" for _, kind in a["in"]) else set()),
                }
                hits = [n for n, _, test in table if test(a, ctx)]
                if 29 in hits and a["status"] != "active":
                    hits = [29]      # an action that never runs is not ported: only that recipe matters
                a["recipes"] = hits

    def _add(self, raw):
        sid = "main" if not self.stories else "s%d" % len(self.stories)
        self.stories.append(Story(raw, sid, "" if sid == "main" else sid + "."))
        for sub in raw.get("send_to_stories") or []:
            if isinstance(sub, dict) and isinstance(sub.get("agents"), list):
                self._add(sub)

    def story(self, sid):
        for s in self.stories:
            if s.sid == sid or (sid in ("s0", "main") and s is self.main):
                return s
        return None

    def story_of(self, aid):
        return self.story(self.actions[aid]["story"])

    def workflow(self, wid):
        for s in self.stories:
            for wf in s.workflows:
                if wf["id"] == wid:
                    return s, wf
        return None, None

    def find(self, key):
        key = key.strip()
        if key.lower() in self.actions:
            return [key.lower()]
        return [i for s in self.stories for i in s.order
                if s.actions[i]["ref"] == key or s.actions[i]["name"] == key]

    def select(self, selector):
        """(label, story, top ids, all ids) for 'main', 's1', 'w03', 's1.w02' or an action id."""
        sel = (selector or "main").strip().lower()
        s = self.story(sel)
        if s:
            return "story %s" % s.sid, s, list(s.scopes[None]), list(s.order)
        s, wf = self.workflow(sel)
        if wf:
            return "workflow %s" % wf["id"], s, wf["top"], wf["all"]
        if sel in self.actions:
            a = self.actions[sel]
            if a.get("workflow"):
                s, wf = self.workflow(a["workflow"])
                return "workflow %s" % wf["id"], s, wf["top"], wf["all"]
            raise ValueError("action %s is not part of any workflow (it is never triggered)" % sel)
        raise ValueError("unknown selector %r: use a workflow id (w01), a story id (main, s1) "
                         "or an action id (a07)" % selector)

    def expand_ids(self, spec):
        """'a010-a020' or 'a03,a07' -> list of action ids."""
        out = []
        for part in [p.strip().lower() for p in spec.split(",") if p.strip()]:
            if "-" in part:
                lo, hi = [x.strip() for x in part.split("-", 1)]
                if lo not in self.actions or hi not in self.actions:
                    raise ValueError("unknown action id in range %r" % part)
                order = self.story_of(lo).order
                if hi not in order or order.index(hi) < order.index(lo):
                    raise ValueError("bad range %r (ids must be in export order, same story)" % part)
                out.extend(order[order.index(lo):order.index(hi) + 1])
            elif part in self.actions:
                out.append(part)
            else:
                raise ValueError("unknown action id %r" % part)
        return out


def load_export(path):
    with open(path, encoding="utf-8-sig") as fh:   # utf-8-sig: a file saved on Windows may start with a BOM
        raw = json.load(fh)
    if isinstance(raw, dict) and "agents" not in raw and isinstance(raw.get("story"), dict):
        raw = raw["story"]
    if not isinstance(raw, dict) or not isinstance(raw.get("agents"), list):
        raise ValueError("not a Tines story export (no top-level 'agents' list)")
    if is_copied_actions(raw):
        raw = normalize_copied(raw)
    return Export(raw)


# --------------------------------------------------------------------------
# Copied actions (the JSON Tines puts on the clipboard when actions are copied
# from the storyboard). Same content as an export, different spelling:
# camelCase keys, short type names, options as a JSON string, links that use
# sourceIdentifier / receiverIdentifier, groups under group.actions.
# Seen in one real sample; type names other than eventTransformation,
# httpRequest, trigger and group are guesses.
# --------------------------------------------------------------------------

COPIED_TYPES = {
    "eventtransformation": "EventTransformation", "httprequest": "HTTPRequest",
    "trigger": "Trigger", "group": "Group", "groupinput": "GroupInput",
    "groupoutput": "GroupOutput", "email": "Email", "sendemail": "Email",
    "webhook": "Webhook", "sendtostory": "SendToStory", "imap": "IMAP",
    "form": "Form", "page": "Form", "llm": "LLM", "ai": "LLM",
}


def is_copied_actions(raw):
    if "standardLibVersion" in raw or "actionRuntimeVersion" in raw:
        return True
    if any(isinstance(l, dict) and "sourceIdentifier" in l for l in raw.get("links") or []):
        return True
    return any(isinstance(a, dict) and isinstance(a.get("type"), str)
               and not a["type"].startswith("Agents::") for a in raw["agents"])


def normalize_copied(raw, counter=None, layout=None):
    top = counter is None
    counter = counter if counter is not None else [0]
    layout = layout if layout is not None else {}
    agents = []
    for a in raw.get("agents") or raw.get("actions") or []:
        a = dict(a)
        kind = str(a.get("type") or "")
        if not kind.startswith("Agents::"):
            name = COPIED_TYPES.get(kind.lower().replace("_", ""), kind[:1].upper() + kind[1:])
            a["type"] = "Agents::%sAgent" % name
        if isinstance(a.get("options"), str):
            try:
                a["options"] = json.loads(a["options"])
            except ValueError:
                a["options"] = {"unparsed_options": a["options"]}
        if not a.get("guid"):
            counter[0] += 1
            a["guid"] = "copied%04d" % counter[0]
        pos = a.get("position")
        if isinstance(pos, dict) and "x" in pos and "y" in pos:
            layout[a["guid"]] = [pos["x"], pos["y"]]
        if isinstance(a.get("group"), dict):
            a["group"] = normalize_copied(a["group"], counter, layout)
        agents.append(a)
    links = []
    for l in raw.get("links") or []:
        try:
            s = int(l["sourceIdentifier"] if "sourceIdentifier" in l else l["source"])
            r = int(l["receiverIdentifier"] if "receiverIdentifier" in l else l["receiver"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("copied actions: cannot read link %r" % (l,))
        if not (0 <= s < len(agents) and 0 <= r < len(agents)):
            raise ValueError("copied actions: link %r points outside the %d actions" % (l, len(agents)))
        out = {"source": s, "receiver": r}
        kind = l.get("linkType") or l.get("link_type")
        if kind in ("NO_MATCH", "secondary"):
            out["link_type"] = "secondary"
        links.append(out)
    story = {k: v for k, v in raw.items() if k not in ("agents", "actions", "links")}
    story["agents"], story["links"] = agents, links
    story.setdefault("name", "copied actions" if top else "")
    story.setdefault("diagram_notes", raw.get("diagramNotes") or raw.get("annotations") or [])
    if top:
        story["diagram_layout"] = json.dumps(layout)
    return story


# --------------------------------------------------------------------------
# Text rendering
# --------------------------------------------------------------------------

def type_label(a):
    return a["type"] + ("/" + a["mode"] if a["mode"] else "")


def scalar_text(s):
    if isinstance(s, str):
        if s == "" or s != s.strip() or re.fullmatch(r"-?\d+(\.\d+)?|true|false|null", s):
            return json.dumps(s, ensure_ascii=False)
        return s
    return json.dumps(s, ensure_ascii=False)


def has_multiline(v):
    return any("\n" in s for s in iter_strings(v))


def map_strings(value, fn):
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, dict):
        return {k: map_strings(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [map_strings(v, fn) for v in value]
    return value


def emit(key, value, indent, out):
    """Append a compact YAML-like rendering of key: value."""
    pad = " " * indent
    head = pad + (key + ":" if key is not None else "-")
    if isinstance(value, str) and "\n" in value:
        # YAML chomping says exactly how the text ends: |- none, | one, |+ all the newlines shown
        body = value.rstrip("\n")
        trailing = len(value) - len(body)
        out.append(head + (" |-" if trailing == 0 else " |" if trailing == 1 else " |+"))
        out.extend((pad + "  " + line).rstrip() for line in body.split("\n"))
        out.extend([""] * (trailing - 1))
    elif isinstance(value, (dict, list)) and value:
        flat = json.dumps(value, ensure_ascii=False)
        if len(flat) <= 160 and not has_multiline(value):
            out.append(head + " " + flat)
        elif isinstance(value, dict):
            out.append(head)
            for k, v in value.items():
                emit(str(k), v, indent + 2, out)
        else:
            out.append(head)
            for v in value:
                emit(None, v, indent + 2, out)
    else:
        out.append(head + " " + scalar_text(value))


def flags(a, in_tree=False):
    f = []
    if a["status"] == "disabled":
        f.append("DISABLED")
    elif a["status"] == "unreachable":
        f.append("UNREACHABLE")
    if a["fan_out"]:
        f.append("FAN-OUT x%d" % a["fan_out"])
    if a["nomatch_fan_out"]:
        f.append("NO-MATCH FAN-OUT x%d" % a["nomatch_fan_out"])
    if a["join"]:
        f.append("JOIN x%d" % a["join"])
    if a["in_cycle"]:
        f.append("CYCLE")
    if a["exit"]:
        f.append("STORY-EXIT")
    if a["dead_end"]:
        f.append("DEAD-END")
    elif a["end"] and in_tree:
        f.append("END")
    return f


def recipe_tag(a):
    return "recipe %s" % ",".join(map(str, a["recipes"])) if a.get("recipes") else ""


def recipes_line(actions):
    """'RECIPES ...' line for a set of actions: distinct numbers, those of actions that run first."""
    live = sorted({n for a in actions if a["status"] == "active" for n in a.get("recipes", [])})
    dead = any(a["status"] != "active" for a in actions)
    nums = live + ([29] if dead and 29 not in live and any(29 in a.get("recipes", []) for a in actions) else [])
    if not nums:
        return None
    return ("RECIPES for these shapes (read each with `ref.py patterns N`; the number is printed beside "
            "every action it applies to): " + " ".join(map(str, nums)))


FUNC_CALL = re.compile(r"(?<![\w$.])([A-Z][A-Z0-9_]{1,})\s*\(")
EASY_FUNCS = {"IF", "AND", "OR", "NOT", "SIZE", "DEFAULT", "TEXT", "NUMBER"}


def functions_line(story, actions):
    """'FUNCTIONS ...' line: the formula functions the running actions use."""
    names = set()
    for a in actions:
        if a["status"] != "active":
            continue
        for text in story._sources(a):
            names.update(FUNC_CALL.findall(text))
    names = sorted(n for n in names if n not in EASY_FUNCS and n not in ("CREDENTIAL", "RESOURCE", "META", "LAMBDA"))
    if not names:
        return None
    return ("FUNCTIONS used by the actions that run (look up each one you have not looked up yet, also the "
            "ones you think you know: `tines_fn.py %s`): %s" % (" ".join(names[:3]), " ".join(names)))


def mask_path(v):
    """A random webhook path works like a password: show only its start."""
    v = str(v)
    return v[:4] + "...<redacted>" if re.fullmatch(r"[A-Za-z0-9_-]{16,}", v) and re.search(r"\d", v) else v


def entry_detail(a):
    """Trigger details of an entry action, for index lines."""
    bits = list(a["entry"])
    o = a["options"]
    if a["type"] == "webhook":
        extra = ["%s=%s" % (k, mask_path(o[k]) if k == "path" else o[k]) for k in ("path", "verbs") if o.get(k)]
        bits = ["webhook" + (" " + " ".join(extra) if extra else "")] + [b for b in bits if b != "webhook"]
    elif a["type"] == "page":
        fields = [el["ref"] for el in a["page"]["elements"] if "ref" in el]
        desc = "page %s/%s" % (a["mode"] or "?", o.get("visibility") or "?")
        if fields:
            desc += " fields: " + ", ".join(fields)
        bits = [desc] + [b for b in bits if b != "page"]
    return "; ".join(bits)


class Renderer:
    def __init__(self, export, cmd="tines_outline.py story.json", full=False):
        self.x = export
        self.cmd = cmd
        self.full = full

    # -- pieces ------------------------------------------------------------
    def shorten(self, value, aid):
        if self.full:
            return value
        hint = "--action %s" % aid
        return map_strings(value, lambda s: elide_static(s, hint))

    def tree(self, story, scope, roots, indent, out, expand=True, sizes=None):
        acts = story.actions
        ids = story.scopes[scope] if roots is None else roots
        allowed = set(ids)
        shown = set()

        def visit(aid, depth, kind, stack):
            a = acts[aid]
            pad = " " * (indent + 2 * depth)
            edge = "(%s) " % kind if kind else ""
            if aid in shown:
                why = "CYCLE: loops back" if aid in stack else "JOIN: shown above"
                out.append("%s%s^ %s %s  (%s)" % (pad, edge, aid, a["ref"], why))
                return
            shown.add(aid)
            bits = ["%s%s%s %s [%s]" % (pad, edge, aid, a["ref"], type_label(a))]
            if a["entry"] and scope is None:
                bits.append("ENTRY: " + "; ".join(a["entry"]))
            if a["calls"]:
                bits.append("-> STORY.%s" % a["calls"]["story"])
            bits.extend(flags(a, in_tree=True))
            if recipe_tag(a):
                bits.append(recipe_tag(a))
            if a["children"] and not expand:
                bits.append("{%d actions inside%s}" % (
                    len(a["children"]), ", " + size_text(sizes[aid]) if sizes else ""))
            out.append("  ".join(bits))
            if a["children"] and expand:
                out.append(pad + "  { inside group %s:" % aid)
                self.tree(story, aid, None, indent + 2 * depth + 4, out)
                out.append(pad + "  }")
            for nxt, k in a["out"]:
                if nxt in allowed:
                    visit(nxt, depth + 1, k, stack | {aid})

        for i in [i for i in ids if acts[i]["entry"]]:
            visit(i, 0, "", frozenset())
        header = False
        for i in [i for i in ids if not acts[i]["in"]] + list(ids):
            if i in shown:
                continue
            if not header and scope is None:
                out.append(" " * indent + "-- not reachable from any entry point --")
                header = True
            visit(i, 0, "", frozenset())

    @staticmethod
    def ref_text(a):
        parts = []
        for r in a["refs"]:
            if r["resolution"] == "self":
                parts.append("%s (itself)" % r["ref"])
            elif r["resolution"] == "ok":
                parts.append("%s %s" % (r["actions"][0], r["ref"]))
            elif r["resolution"] == "ambiguous":
                parts.append("%s %s (AMBIGUOUS name: nearest upstream first)" % ("|".join(r["actions"]), r["ref"]))
            else:
                parts.append("%s %s (NOT UPSTREAM of this action)" % ("|".join(r["actions"]), r["ref"]))
        return parts

    def head_line(self, a, pad=""):
        name = '  "%s"' % a["name"] if a["name"] != a["ref"] else ""
        head = "%s%s %s%s  [%s]" % (pad, a["id"], a["ref"], name, type_label(a))
        extra = flags(a)
        if a["entry"] and not a["group"]:
            extra.insert(0, "ENTRY: " + "; ".join(a["entry"]))
        if recipe_tag(a):
            extra.append(recipe_tag(a))
        return head + ("  " + "  ".join(extra) if extra else "")

    def action(self, story, aid, out, brief=False, base_depth=0):
        a = story.actions[aid]
        pad = "  " * max(0, a["depth"] - base_depth)
        out.append(self.head_line(a, pad))
        if brief:
            return
        body = len(pad) + 2
        sp = " " * body
        if a["status"] != "active" and a["status_reason"] not in ("", "disabled"):
            out.append(sp + "why: " + a["status_reason"])
        ins = ",".join(("%s(%s)" % (i, k) if k else i) for i, k in a["in"]) or "-"
        outs = ",".join(("%s(%s)" % (i, k) if k else i) for i, k in a["out"]) or "-"
        out.append("%slinks: in %s | out %s" % (sp, ins, outs))
        uses = self.ref_text(a) + [g + ("()" if g in a["called"] else "") for g in a["globals"]]
        if uses:
            out.append(sp + "uses: " + ", ".join(uses))
        if a["unresolved"]:
            out.append(sp + "unresolved names (no such action on the path: NULL in Tines, port as null): "
                       + ", ".join(a["unresolved"]))
        if a["effect"] and a["type"] not in ("send_email", "send_to_story", "record"):
            out.append(sp + "outside effect: " + a["effect"])
        if a["calls"]:
            c = a["calls"]
            if not c["story"]:
                where = "target is not a STORY.x reference: %s" % json.dumps(c["raw"])
            elif c["embedded"]:
                where = "STORY.%s - body embedded in this export as %s (print it with --story %s)" % (
                    c["story"], c["embedded"], c["embedded"])
                if c.get("reads") is not None:
                    where += "\n%s  %s reads these keys of the payload: %s" % (
                        sp, c["embedded"], ", ".join(c["reads"]) or "none")
                    if c.get("sent") is None:
                        where += "\n%s  this call sends a computed payload: compare by hand" % sp
                    else:
                        where += "\n%s  sent here but never read by %s: %s" % (
                            sp, c["embedded"], ", ".join(c.get("sent_not_read") or []) or
                            ("cannot tell (it also uses the whole body)" if "(the whole body)" in c["reads"] else "none"))
                        where += "\n%s  read by %s but not sent here (NULL there): %s" % (
                            sp, c["embedded"], ", ".join(c.get("read_not_sent") or []) or "none")
            else:
                where = "STORY.%s - body NOT in this export (separate story; port or ask for it)" % c["story"]
            out.append(sp + "calls: " + where)
        if a["inputs"]:
            out.append(sp + "inputs (read as INPUT.x here, GROUP_INPUT.x inside a group):")
            for k, v in a["inputs"].items():
                value = v["value"] if set(v) <= {"value", "required"} else v
                emit(k, self.shorten(value, aid), body + 2, out)
        if a["page"]:
            self.page_body(a, body, out)
        if a["record"]:
            rec = a["record"]
            out.append("%srecord type: %s" % (sp, json.dumps(rec["record_type"], ensure_ascii=False)))
            if rec["writers"]:
                out.append(sp + "writes fields:")
                for w in rec["writers"]:
                    emit("%s (%s)" % (w["field"], w["type"]), self.shorten(w["formula"], aid), body + 2, out)
        for k, v in a["options"].items():
            if k == "mode" and a["mode"]:
                continue
            if a["type"] == "page" and (k in PAGE_NOISE or v in (None, "", False)):
                continue
            if a["type"] == "webhook" and k == "secret" and v:
                v = "<redacted>"
            if a["type"] == "webhook" and k == "path" and v:
                v = mask_path(v)
            emit(k, self.shorten(v, aid), body, out)

    def page_body(self, a, body, out):
        sp = " " * body
        page = a["page"]
        if not page["found"]:
            out.append(sp + "page definition: NOT found in the export's `pages` list")
        if page["elements"]:
            out.append(sp + "page elements (downstream formulas read an input as <<%s.body.NAME>> and the "
                       "clicked button's value as <<%s.body.button>>):" % (a["ref"], a["ref"]))
        for el in page["elements"]:
            if el["type"] in PAGE_TEXT_TYPES:
                if el.get("content"):
                    tag = " %s" % json.dumps(el["label"], ensure_ascii=False) if el["label"] != el["name"] else ""
                    emit("text %s%s" % (el["type"].lower(), tag), self.shorten(el["content"], a["id"]), body + 2, out)
                continue
            kind = "button" if el["type"] == "BUTTON" else "input"
            shown = el["label"] if kind == "button" or el["label"] != el["name"] else el.get("ref")
            label = "%s %s [%s]%s" % (kind, json.dumps(shown, ensure_ascii=False) if kind == "button" else shown,
                                      el["type"], " required" if el.get("required") else "")
            detail = {k: el[k] for k in ("content", "description", "default_value", "options") if k in el}
            if kind == "button":
                detail = {("label" if k == "content" else "value" if k == "default_value" else k): v
                          for k, v in detail.items()}
            if detail:
                emit(label, self.shorten(detail, a["id"]), body + 2, out)
            else:
                out.append("%s  %s" % (sp, label))
        for cond in page["conditions"]:
            out.append("%s  display condition (layout only, not logic): %s" % (sp, cond))
        if page["success_message"]:
            emit("success_message", page["success_message"], body, out)
        targets = ", ".join("%s %s" % (i, self.x.actions[i]["ref"]) for i, _ in a["out"])
        out.append("%ssubmits into: %s" % (sp, targets or "nothing (no outgoing link)"))

    def globals_block(self, story, ids, out):
        wanted = set(ids)
        rows = []
        for key, rec in story.namespaces.items():
            users = [i for i in rec["actions"] if i in wanted]
            if users:
                called = sorted({fn for i in users for fn in story.actions[i]["called"].get(key, [])})
                rows.append((key, users, called))
        out.append("GLOBALS")
        if not rows:
            out.append("  none referenced")
        order = lambda r: (0 if r[0].startswith("CREDENTIAL") else 1 if r[0].startswith("RESOURCE") else 2, r[0])
        for key, users, called in sorted(rows, key=order):
            note = ""
            if called:
                note = "  CALLED AS FUNCTION: %s - lambda body not in export, ask the user for it" % ", ".join(called)
            tagged = [i if story.actions[i]["status"] == "active" else "%s(%s)" % (i, story.actions[i]["status"])
                      for i in users]
            out.append("  %s: %s%s" % (key, ", ".join(tagged), note))

    def notes_block(self, story, top_ids, out, scopes=(None,)):
        """Sticky notes of the given scopes (None = top level, or group ids) near the wanted actions."""
        acts, lines = story.actions, []
        wanted = set(top_ids)
        for scope in scopes:
            notes, layout = story.notes.get(scope, ([], {}))
            placed = [i for i in story.scopes[scope] if acts[i]["guid"] in layout]
            for n in notes:
                pos, best = n.get("position"), None
                if isinstance(pos, list) and len(pos) == 2 and placed:
                    best = min(placed, key=lambda i: (layout[acts[i]["guid"]][0] - pos[0]) ** 2
                               + (layout[acts[i]["guid"]][1] - pos[1]) ** 2)
                if scope is not None or best is None or best in wanted:
                    text = " ".join(str(n.get("content", "")).split())
                    lines.append("  -%s %s" % (" (near %s)" % best if best else "",
                                               text if self.full else elide_static(text, "the raw export")))
        if lines:
            out.append("")
            out.append("AUTHOR NOTES (sticky notes on the diagram; 'near' = closest action)")
            out.extend(lines)

    def duplicates_block(self, story, ids, out):
        wanted, lines = set(ids), []
        for scope, dups in story.duplicates.items():
            for ref, dup_ids in dups.items():
                hit = [i for i in dup_ids if i in wanted]
                if len(hit) > 1:
                    where = " (inside group %s)" % scope if scope else ""
                    lines.append("  %s%s: %s" % (ref, where, ", ".join(hit)))
        if lines:
            out.append("")
            out.append("DUPLICATE REFERENCE NAMES (a formula sees the nearest upstream action with the name)")
            out.extend(lines)

    def details(self, story, ids, out, brief=False, base_depth=0):
        for aid in ids:
            self.action(story, aid, out, brief, base_depth)

    def detail_size(self, story, ids):
        out = []
        self.details(story, ids, out)
        return sum(len(line) + 1 for line in out)

    # -- story header and index -------------------------------------------
    def story_head(self, story, out, brief=False):
        raw, acts = story.raw, story.actions
        top = story.scopes[None]
        nested = [i for i in story.order if acts[i]["group"]]
        groups = [i for i in story.order if acts[i]["children"]]
        count = lambda st: sum(1 for i in story.order if acts[i]["status"] == st)
        label = "STORY" if story.sid == "main" else "SUB-STORY %s (STORY.%s)" % (story.sid, story.slug)
        out.append("%s: %s" % (label, story.name))
        desc = raw.get("description")
        if desc and brief:
            flat = " ".join(str(desc).split())
            if len(flat) > 200:
                flat = "%s [... %d more chars: --story %s --brief]" % (flat[:200], len(flat) - 200, story.sid)
            out.append("  description: " + flat)
        elif desc:
            emit("description", desc, 2, out)
        out.append("  actions: %d top-level%s | active %d, disabled %d, unreachable %d" % (
            len(top), " + %d inside %d group action(s)" % (len(nested), len(groups)) if nested else "",
            count("active"), count("disabled"), count("unreachable")))
        by_guid = {acts[i]["guid"]: i for i in top}
        if raw.get("send_to_story_enabled"):
            ex = [by_guid.get(g, g) for g in raw.get("exit_agent_guids") or []]
            out.append("  send-to-story: ENABLED (callable as a sub-story) | entry %s | exit %s" % (
                by_guid.get(raw.get("entry_agent_guid"), raw.get("entry_agent_guid") or "-"), ", ".join(ex) or "-"))
        else:
            out.append("  send-to-story: not enabled (story is not called as a sub-story)")
        keys = getattr(story, "input_keys", None)
        if keys:
            out.append("  inputs: reads these keys of the payload its caller sends (%s.body.KEY; they become the "
                       "flow inputs): %s" % (acts[keys["entry"]]["ref"], ", ".join(
                           sorted({k.split(".")[0] for k in keys["keys"]}) if brief else keys["keys"]) or "none"))
        hooks = [i for i in top if acts[i]["type"] == "webhook"]
        pages = [i for i in top if acts[i]["type"] == "page"]
        out.append("  webhooks: %s%s | pages: %s" % (
            ", ".join(hooks) or "none",
            " (synchronous responses enabled)" if raw.get("synchronous_webhooks_enabled") else "",
            ", ".join(pages) or "none"))
        if raw.get("recipients") and not brief:
            out.append("  failure-notification recipients: " + ", ".join(map(str, raw["recipients"])))
        for key in ("app_endpoints",):
            if raw.get(key):
                out.append("  NOTE: story has %d %s - not digested, read key '%s' in the raw export"
                           % (len(raw[key]), key, key))

    def workflow_line(self, story, wf, with_size=True):
        acts = story.actions
        entries = "; ".join("%s %s: %s%s" % (i, acts[i]["ref"], entry_detail(acts[i]).replace("schedule cron", "cron"),
                                              " (DISABLED)" if acts[i]["disabled"] and not wf["disabled"] else "")
                            for i in wf["entries"])
        members, plain = [], 0
        for i in wf["top"]:
            if i in wf["entries"]:
                continue
            a = acts[i]
            if a["children"]:
                members.append("%s %s{%d}" % (i, a["ref"], len(a["children"])))
            elif plain < INDEX_MEMBER_CAP:
                plain += 1
                members.append("%s %s" % (i, a["ref"]))
            else:
                plain += 1
        if plain > INDEX_MEMBER_CAP:
            members.append("+%d more top-level actions (--workflow %s --graph)" % (plain - INDEX_MEMBER_CAP, wf["id"]))
        # names are counted for actions that actually run (all of them when the whole workflow is disabled)
        live = [i for i in wf["all"] if wf["disabled"] or acts[i]["status"] == "active"]
        names = {}
        for i in live:
            for g in acts[i]["globals"]:
                ns, _, key = g.partition(".")
                if ns.split(" ")[0] in ACTION_SCOPED_NS or not key:
                    continue
                label = key + ("()" if g in acts[i]["called"] else "")
                bucket = names.setdefault(ns, [])
                if label not in bucket and key + "()" not in bucket:
                    if label.endswith("()") and key in bucket:
                        bucket.remove(key)
                    bucket.append(label)
        stories = []
        for i in live:
            c = acts[i]["calls"]
            if c and c["story"]:
                tag = c["embedded"] or "%s(not in export)" % c["story"]
                if tag not in stories:
                    stories.append(tag)
        names.pop("STORY", None)
        parts = ["%s%s%s" % (wf["id"], " DISABLED" if wf["disabled"] else "",
                             " NO-EFFECT" if wf["no_effect"] else ""), entries]
        if members:
            parts.append("then: " + ", ".join(members))
        size = ", " + short_size(self.workflow_size(story, wf)) if with_size else ""
        running = sum(1 for i in wf["all"] if acts[i]["status"] == "active")
        parts.append("%d actions (%d run)%s" % (len(wf["all"]), running, size))
        short = {"CREDENTIAL": "CRED", "RESOURCE": "RES", "PAGE": "links to page"}
        if not with_size:
            short = {"PAGE": "links to page"}
        for ns in sorted(names, key=lambda n: (0 if n == "CREDENTIAL" else 1 if n == "RESOURCE" else 2, n)):
            parts.append("%s: %s" % (short.get(ns, ns), ", ".join(sorted(names[ns]))))
        if stories:
            parts.append("calls STORY: " + ", ".join(stories))
        return " | ".join(parts)

    def workflow_size(self, story, wf):
        key = ("wf", wf["id"])
        cache = self.__dict__.setdefault("_sizes", {})
        if key not in cache:
            cache[key] = len(self.workflow_text(story, wf))
        return cache[key]

    def index(self, stories=None):
        out = []
        stories = stories or self.x.stories
        for n, story in enumerate(stories):
            if n:
                out.append("")
            self.story_head(story, out, brief=True)
            out.append("")
            out.append("WORKFLOWS of %s (linked actions with an entry point. {N} = group of N actions; "
                       "run = enabled and reachable; tok = size of --workflow output; CRED/RES/calls STORY "
                       "count only actions that run; x() = resource called as a function; NO-EFFECT = "
                       "nothing that runs writes anything outside the story: plan it as SKIP: no effect)" % story.sid)
            for wf in story.workflows:
                out.append(self.workflow_line(story, wf))
            if not story.workflows:
                out.append("  none: no schedule, webhook, page or send-to-story entry; the story only runs manually")
            if story.orphans:
                out.append("")
                out.append("NOT TRIGGERED in %s (no entry point: never runs unless started by hand; `;` separates "
                           "unconnected pieces; print with --actions ID)" % story.sid)
                acts = story.actions
                out.append("  " + "; ".join(" > ".join(
                    "%s %s%s%s" % (i, acts[i]["ref"], "{%d}" % len(acts[i]["children"]) if acts[i]["children"] else "",
                                   " DISABLED" if acts[i]["disabled"] else "") for i in ids) for ids in story.orphans))
        runs = lambda i: self.x.actions[i]["status"] == "active"
        dead_wf = {w["id"] for st in self.x.stories for w in st.workflows if w["no_effect"]}
        tag = lambda ids: ", ".join(sorted(w + ("(NO-EFFECT)" if w in dead_wf else "") for w in ids))
        called = self.x.called_stories
        if called and len(stories) == len(self.x.stories):
            out.append("")
            out.append("STORIES CALLED (send_to_story actions that run)")
            for slug in sorted(called):
                rec = called[slug]
                live = [i for i in rec["callers"] if runs(i)]
                wfs = sorted({self.x.actions[i].get("workflow") or "?" for i in live})
                where = ("embedded as %s" % rec["embedded"]) if rec["embedded"] else "NOT in this export"
                dead = len(rec["callers"]) - len(live)
                out.append("  STORY.%s: %s | %s%s" % (
                    slug, where,
                    "%d call(s) from %s" % (len(live), tag(wfs)) if live else "never called by an action that runs",
                    " (+%d in disabled/unreachable actions)" % dead if dead else ""))
        fn_rows = []
        for story in stories:
            for key, rec in sorted(story.namespaces.items()):
                if not rec["called"]:
                    continue
                users = [i for i in rec["actions"] if story.actions[i]["called"].get(key)]
                live = [i for i in users if runs(i)]
                wfs = sorted({story.actions[i].get("workflow") or "?" for i in live})
                fn_rows.append("  %s: %s | %s" % (
                    key, ", ".join(sorted(rec["called"])),
                    "called by %d action(s) that run, in %s" % (len(live), tag(wfs)) if live
                    else "ONLY called by disabled/unreachable actions (%s): not needed" % ", ".join(users)))
        if fn_rows:
            out.append("")
            out.append("RESOURCES CALLED AS FUNCTIONS (lambda bodies are not in the export: ask the user)")
            out.extend(fn_rows)
        out.append("")
        out.append("NEXT: %s --workflow <id>   (one workflow; prints an overview with paging commands "
                   "when it is over the budget)" % self.cmd)
        return out

    # -- views -------------------------------------------------------------
    def story_text(self, story):
        out = []
        self.story_head(story, out)
        entries = [i for i in story.scopes[None] if story.actions[i]["entry"]]
        for i in entries:
            a = story.actions[i]
            out.append("  entry point: %s %s - %s%s" % (i, a["ref"], entry_detail(a),
                                                        " (DISABLED)" if a["disabled"] else ""))
        if not entries:
            out.append("  entry point: NONE FOUND (story only runs manually)")
        if len(story.workflows) > 1:
            out.append("  workflows: %s (independent; see --index)" % ", ".join(w["id"] for w in story.workflows))
        line = recipes_line([story.actions[i] for i in story.order])
        if line:
            out.append("  " + line)
        out.append("")
        out.append("GRAPH (indent = link; see ACTIONS for details)")
        self.tree(story, None, None, 2, out)
        out.append("")
        out.append("ACTIONS (%d)" % len(story.order))
        self.details(story, story.order, out)
        out.append("")
        self.globals_block(story, story.order, out)
        self.duplicates_block(story, story.order, out)
        self.notes_block(story, story.scopes[None], out, [None] + [g for g in story.scopes if g])
        return "\n".join(out) + "\n"

    def workflow_text(self, story, wf, mode="full"):
        out = ["WORKFLOW " + self.workflow_line(story, wf, with_size=False)]
        line = recipes_line([story.actions[i] for i in wf["all"]])
        if line:
            out.append("  " + line)
        line = functions_line(story, [story.actions[i] for i in wf["all"]])
        if line:
            out.append("  " + line)
        if wf["no_effect"]:
            out.append("  NO-EFFECT: no action that runs here writes anything outside the story (no HTTP write, "
                       "email, story call, record or page shown). Nothing to port unless the user says otherwise.")
        out.append("")
        out.append("GRAPH (indent = link)")
        self.tree(story, None, wf["top"], 2, out)
        if mode == "graph":
            return "\n".join(out) + "\n"
        out.append("")
        out.append("ACTIONS (%d)" % len(wf["all"]))
        self.details(story, wf["all"], out, brief=(mode == "brief"))
        if mode == "brief":
            return "\n".join(out) + "\n"
        out.append("")
        self.globals_block(story, wf["all"], out)
        self.duplicates_block(story, wf["all"], out)
        self.notes_block(story, wf["top"], out, [None] + [g for g in wf["all"] if story.actions[g]["children"]])
        return "\n".join(out) + "\n"

    def chunks(self, story, ids, budget):
        """Split ids into consecutive ranges whose detail fits the budget."""
        ranges, cur, cur_size = [], [], 0
        for aid in ids:
            size = self.detail_size(story, [aid])
            if cur and cur_size + size > budget:
                ranges.append((cur, cur_size))
                cur, cur_size = [], 0
            cur.append(aid)
            cur_size += size
        if cur:
            ranges.append((cur, cur_size))
        return ranges

    def range_commands(self, story, ids, budget, out):
        for chunk, size in self.chunks(story, ids, budget):
            spec = chunk[0] if len(chunk) == 1 else "%s-%s" % (chunk[0], chunk[-1])
            out.append("  %s --actions %s   # %s" % (self.cmd, spec, size_text(size)))

    def workflow_overview(self, story, wf, budget, full_size):
        acts = story.actions
        out = ["WORKFLOW " + self.workflow_line(story, wf, with_size=False)]
        line = recipes_line([story.actions[i] for i in wf["all"]])
        if line:
            out.append("  " + line)
        line = functions_line(story, [story.actions[i] for i in wf["all"]])
        if line:
            out.append("  " + line)
        out.append("  OVERVIEW ONLY: the full detail is %s, over the budget of %s chars. "
                   "Read it in pieces with the commands under NEXT." % (size_text(full_size), "{:,}".format(budget)))
        groups = [i for i in wf["top"] if acts[i]["children"]]
        sizes = {g: self.detail_size(story, story.members([g])) for g in groups}
        out.append("")
        out.append("GRAPH (top level; groups collapsed)")
        self.tree(story, None, wf["top"], 2, out, expand=False, sizes=sizes)
        top_size = self.detail_size(story, wf["top"])
        out.append("")
        if top_size <= budget:
            out.append("TOP-LEVEL ACTIONS (%d; group internals not shown)" % len(wf["top"]))
            self.details(story, wf["top"], out)
        else:
            out.append("TOP-LEVEL ACTIONS (%d; one line each, details are %s)" % (len(wf["top"]), size_text(top_size)))
            self.details(story, wf["top"], out, brief=True)
        out.append("")
        self.globals_block(story, wf["all"], out)
        out.append("")
        out.append("NEXT (sizes are what each command prints)")
        if top_size > budget:
            self.range_commands(story, wf["top"], budget, out)
        for g in groups:
            note = "" if sizes[g] <= budget else " -> over budget, prints its own paged overview"
            out.append("  %s --group %s   # %s, %s%s" % (self.cmd, g, acts[g]["ref"], size_text(sizes[g]), note))
        out.append("  %s --workflow %s --graph   # whole graph with groups expanded, %s" % (
            self.cmd, wf["id"], size_text(len(self.workflow_text(story, wf, "graph")))))
        out.append("  %s --workflow %s --full    # everything, %s" % (self.cmd, wf["id"], size_text(full_size)))
        return "\n".join(out) + "\n"

    def group_text(self, story, gid, budget, mode="auto"):
        a = story.actions[gid]
        inner = story.members([gid])[1:]
        out = ["GROUP %s (%d actions inside; workflow %s)" % (self.head_line(a), len(inner), a.get("workflow") or "none")]
        own = []
        self.action(story, gid, own)
        out.extend(own[1:])
        out.append("")
        out.append("GRAPH (inside group %s)" % gid)
        self.tree(story, gid, None, 2, out)
        self.notes_block(story, inner, out, [gid])
        if mode == "graph":
            return "\n".join(out) + "\n"
        size = self.detail_size(story, inner)
        out.append("")
        if mode == "brief":
            out.append("ACTIONS (%d; one line each)" % len(inner))
            self.details(story, inner, out, brief=True, base_depth=a["depth"] + 1)
        elif mode == "auto" and size > budget:
            if True:
                out.append("NEXT: details are %s, over the budget of %s chars. Read them in ranges:"
                           % (size_text(size), "{:,}".format(budget)))
                self.range_commands(story, inner, budget, out)
                out.append("  %s --group %s --full   # everything, %s" % (self.cmd, gid, size_text(size)))
        else:
            out.append("ACTIONS (%d)" % len(inner))
            self.details(story, inner, out, base_depth=a["depth"] + 1)
            out.append("")
            self.globals_block(story, [gid] + inner, out)
            self.duplicates_block(story, inner, out)
        return "\n".join(out) + "\n"

    def actions_text(self, ids):
        out = []
        for aid in ids:
            story = self.x.story_of(aid)
            self.action(story, aid, out, base_depth=story.actions[aid]["depth"])
        return "\n".join(out) + "\n"

    def raw_action(self, aid):
        story = self.x.story_of(aid)
        a = story.actions[aid]
        out = [self.head_line(a)]
        out.append("  name: %s" % json.dumps(a["name"], ensure_ascii=False))
        out.append("  tines type: %s | guid: %s | export index: %d | story: %s%s | workflow: %s" % (
            a["raw_type"], a["guid"], a["index"], a["story"],
            " | inside group %s" % a["group"] if a["group"] else "", a.get("workflow") or "none"))
        out.append("  status: %s%s" % (a["status"], " (%s)" % a["status_reason"] if a["status_reason"] else ""))
        if a["description"]:
            emit("description", a["description"], 2, out)
        for label, links in (("inbound", a["in"]), ("outbound", a["out"])):
            txt = ", ".join("%s %s%s" % (i, story.actions[i]["ref"], " (%s)" % k if k else "") for i, k in links)
            out.append("  %s links: %s" % (label, txt or "none"))
        if a["refs"]:
            out.append("  references to other actions:")
            for r, text in zip(a["refs"], self.ref_text(a)):
                out.append("    %s: %s" % (text, ", ".join(r["paths"])))
        if a["globals"]:
            out.append("  globals: " + ", ".join(g + ("()" if g in a["called"] else "") for g in a["globals"]))
        if a["unresolved"]:
            out.append("  unresolved names (NULL in Tines, port as null): " + ", ".join(a["unresolved"]))
        if a["calls"]:
            out.append("  calls: " + json.dumps(a["calls"], ensure_ascii=False))
        dump = lambda v: json.dumps(v, indent=2, ensure_ascii=False).replace("\n", "\n  ")
        if a["inputs"]:
            out.append("  inputs: " + dump(a["inputs"]))
        if a["page"]:
            out.append("  page: " + dump(a["page"]))
        if a["record"]:
            out.append("  record: " + dump(a["record"]))
        options = dict(a["options"])
        if a["type"] == "page" and "page_logo" in options:
            options["page_logo"] = "<logo image omitted>"
        if a["type"] == "webhook" and options.get("secret"):
            options["secret"] = "<redacted>"
        if a["type"] == "webhook" and options.get("path"):
            options["path"] = mask_path(options["path"])
        out.append("  options (raw JSON): " + dump(options))
        if a["children"]:
            out.append("  group internals:")
            self.tree(story, aid, None, 4, out)
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# JSON and map template
# --------------------------------------------------------------------------

def render_json(export, story, ids):
    keep = ("id", "name", "ref", "type", "mode", "status", "status_reason", "disabled", "schedule",
            "entry", "story", "workflow", "group", "children", "guid", "options", "inputs", "page",
            "record", "calls", "refs", "globals", "called", "unresolved", "fan_out", "nomatch_fan_out", "recipes", "join",
            "in_cycle", "end", "dead_end", "exit", "effect")
    actions = []
    for aid in ids:
        a = story.actions[aid]
        d = {k: a.get(k) for k in keep}
        if a["type"] == "page":
            d["options"] = {k: v for k, v in a["options"].items() if k != "page_logo"}
        if a["type"] == "webhook" and a["options"].get("secret"):
            d["options"] = dict(a["options"], secret="<redacted>", path=mask_path(a["options"].get("path", "")))
        d["in"] = [{"id": i, "type": k or "primary"} for i, k in a["in"]]
        d["out"] = [{"id": i, "type": k or "primary"} for i, k in a["out"]]
        actions.append(d)
    wanted = set(ids)
    raw = story.raw
    return json.dumps({
        "story": {
            "id": story.sid, "name": story.name, "slug": story.slug,
            "description": raw.get("description"),
            "send_to_story_enabled": bool(raw.get("send_to_story_enabled")),
            "synchronous_webhooks_enabled": bool(raw.get("synchronous_webhooks_enabled")),
            "entry_points": [{"id": i, "why": story.actions[i]["entry"]}
                             for i in story.scopes[None] if story.actions[i]["entry"] and i in wanted],
            "exit_actions": [i for i in ids if story.actions[i]["exit"]],
            "recipients": raw.get("recipients") or [],
        },
        "stories": [{"id": s.sid, "name": s.name, "slug": s.slug, "actions": len(s.order)} for s in export.stories],
        "workflows": [{"id": w["id"], "entries": w["entries"], "top": w["top"], "actions": len(w["all"]),
                       "disabled": w["disabled"], "no_effect": w["no_effect"]} for w in story.workflows if set(w["top"]) & wanted],
        "not_triggered": [o for o in story.orphans if set(o) & wanted],
        "called_stories": export.called_stories,
        "actions": actions,
        "globals": {k: {"actions": [i for i in v["actions"] if i in wanted], "called_as_function": v["called"]}
                    for k, v in story.namespaces.items() if set(v["actions"]) & wanted},
        "coverage_required": story.required(ids),
    }, indent=1, ensure_ascii=False) + "\n"


def render_map_template(export, selector, story, ids):
    out = [
        "# Tines action map for story: %s" % export.main.name,
        "# workflow: %s" % selector,
        "# One line per Tines action:  <action id> -> <target>   # name",
        "# Replace the placeholder after each arrow with ONE of:",
        "#   module_id                the id of the flow.yaml module that does this action's work",
        "#   module_a, module_b       several module ids, comma separated",
        "#   flow_input.name          the action became a flow input",
        "#   flow_input.a, flow_input.b, module_id   several inputs and/or modules (a page with many fields)",
        "#   SCHEDULE                 the action only starts the workflow on a schedule; the schedule file does that",
        "#   DROPPED: reason          deliberately not translated (say why; if the action wrote something",
        "#                            outside the story, say why that is no longer needed)",
        "# Do not delete lines. Check with: validate_flow.py <dir.flow> --story <story.json>",
        "",
    ]
    required = set(story.required(ids))
    for aid in ids:
        a = story.actions[aid]
        if aid in required:
            target = "TODO"
        elif a["type"] in PLUMBING:
            target = "DROPPED: group plumbing"
        else:
            target = "DROPPED: %s in Tines" % a["status"]
        out.append("%s -> %s   # %s [%s]" % (aid, target, a["name"], type_label(a)))
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Compact digest of an exported Tines story.",
                                 epilog="See the header of this file for the modes and the legend.")
    ap.add_argument("story_file", help="exported Tines story JSON")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--index", action="store_true", help="one line per workflow")
    mode.add_argument("--group", metavar="ID", help="the inside of one group action")
    mode.add_argument("--actions", metavar="IDS", help="digest of an id range (a010-a020) or list (a03,a07)")
    mode.add_argument("--page", metavar="ID", help="digest of one page (form) action")
    mode.add_argument("--action", action="append", metavar="ID",
                      help="one action, raw and unshortened (id or reference name); repeatable")
    mode.add_argument("--map-template", action="store_true",
                      help="skeleton tines_action_map.md (use with --workflow on multi-workflow stories)")
    mode.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--workflow", metavar="ID", help="one workflow: w03, s1.w02, or any action id inside it")
    ap.add_argument("--story", metavar="ID", help="one story of the export: main, or s1.. for an embedded sub-story")
    detail = ap.add_mutually_exclusive_group()
    detail.add_argument("--graph", action="store_true", help="graph only")
    detail.add_argument("--brief", action="store_true", help="graph and one line per action")
    detail.add_argument("--full", action="store_true", help="ignore the budget and elide nothing")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET, metavar="CHARS",
                    help="largest detail output printed without --full (default %d)" % DEFAULT_BUDGET)
    args = ap.parse_args(argv)

    def fail(msg, code=1):
        sys.stderr.write("tines_outline: %s\n" % msg)
        return code

    try:
        export = load_export(args.story_file)
    except (OSError, ValueError) as exc:
        return fail("cannot read %s: %s" % (args.story_file, exc), 2)
    cmd = "%s %s" % (os.path.basename(sys.argv[0]) or "tines_outline.py", args.story_file)
    r = Renderer(export, cmd, full=args.full)
    sub_mode = "graph" if args.graph else "brief" if args.brief else "full"

    try:
        selector = args.workflow or args.story
        label, story, top_ids, ids = export.select(selector)
        if args.json:
            sys.stdout.write(render_json(export, story, ids))
            return 0
        if args.map_template:
            if not selector and len(export.main.workflows) > 1:
                sys.stderr.write("tines_outline: note: this story has %d workflows; the template covers all of "
                                 "them. Use --workflow <id> for one flow.\n" % len(export.main.workflows))
            sys.stdout.write(render_map_template(export, selector or "main", story, ids))
            return 0
        if args.action:
            rc, text = 0, []
            for key in args.action:
                found = export.find(key)
                if not found:
                    rc = fail("no action with id or reference name %r" % key)
                text.extend(r.raw_action(aid) for aid in found)
            what, body = "action (raw)", "\n".join(text)
            if not body:
                return rc
        elif args.actions or args.page:
            chosen = export.expand_ids(args.actions or args.page)
            if args.page and export.actions[chosen[0]]["type"] != "page":
                pages = [i for s in export.stories for i in s.order if s.actions[i]["type"] == "page"]
                raise ValueError("%s is not a page action. Pages: %s" % (chosen[0], ", ".join(pages) or "none"))
            what, body = "actions", r.actions_text(chosen)
        elif args.group:
            gid = args.group.strip().lower()
            if gid not in export.actions or not export.actions[gid]["children"]:
                groups = [i for s in export.stories for i in s.order if s.actions[i]["children"]]
                raise ValueError("%r is not a group action. Groups: %s" % (args.group, ", ".join(groups) or "none"))
            gmode = "full" if args.full else sub_mode if (args.graph or args.brief) else "auto"
            what, body = "group %s" % gid, r.group_text(export.story_of(gid), gid, args.budget, gmode)
        elif args.workflow and label.startswith("workflow"):
            _, wf = export.workflow(label.split()[1])
            if args.graph or args.brief or args.full:
                what, body = "%s (%s)" % (label, sub_mode), r.workflow_text(story, wf, sub_mode)
            else:
                body = r.workflow_text(story, wf)
                what = label
                if len(body) > args.budget:
                    what, body = label + " (overview)", r.workflow_overview(story, wf, args.budget, len(body))
        elif args.index:
            what, body = "index", "\n".join(r.index([story] if selector else None)) + "\n"
        else:
            # default: the whole story if it fits, else the index
            if args.graph or args.brief:
                out = []
                r.story_head(story, out)
                out.append("")
                out.append("GRAPH (indent = link)")
                r.tree(story, None, None, 2, out)
                if args.brief:
                    out.append("")
                    out.append("ACTIONS (%d)" % len(ids))
                    r.details(story, ids, out, brief=True)
                what, body = "%s (%s)" % (label, sub_mode), "\n".join(out) + "\n"
            else:
                body = r.story_text(story)
                what = label + " (full digest)"
                multi = len(export.stories) > 1 and not selector
                if (len(body) > args.budget or multi) and not args.full:
                    note = ("the full digest of %s is %s, over the budget of %s chars" % (
                        label, size_text(len(body)), "{:,}".format(args.budget))
                        if len(body) > args.budget else "the export contains embedded sub-stories")
                    what = "index (%s)" % note
                    body = "\n".join(r.index([story] if selector else None)) + "\n"
    except ValueError as exc:
        return fail(str(exc))
    header = "# tines_outline %s: %s\n" % (what, size_text(len(body)))
    sys.stdout.write(header + body)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # output piped into `head` and the like
        try:
            sys.stdout.close()
        except OSError:
            pass
        sys.exit(0)
