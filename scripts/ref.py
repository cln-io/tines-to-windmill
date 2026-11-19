#!/usr/bin/env python3
"""ref.py - read one section of a reference file instead of the whole file.

USAGE
  ref.py --toc                    every reference file with its sections and sizes
  ref.py openflow --toc           the sections of one file
  ref.py openflow 5.4             print section 5.4 (a section prints with its sub-sections)
  ref.py openflow 7               print section 7 and everything under it
  ref.py story-format "event rules"   a section by a fragment of its title (any case)
  ref.py --search suspend resume  sections that contain ALL the words, one line each
  ref.py openflow --search retry  the same, in one file

  SEARCH RULE: words are matched as plain text, any case, anywhere in a section
  (its own text, not its sub-sections). A section is listed only if it contains
  EVERY word, so use one or two distinctive words. When no section contains
  all of them, the search is repeated for ANY of the words, sections matching
  the most words first, and the first output line says so.

  A file is named by its file name or any unambiguous part of it
  (windmill-openflow.md, openflow, formulas-to-ts, worked).
  Every output starts with a `# ... N chars (~T tokens)` line.
  Exit code 1 when the file or section is not found (the candidates are listed).

HOW SECTIONS ARE FOUND
  Markdown headings (`##`, `###`, ...) outside fenced code blocks. A heading may
  carry a number (`## 5. Module types`, `### 5.1 rawscript`, `## E2. ...`); one
  heading can carry two (`### 5.2 x and 5.3 y`), either number finds it.
  Headings without a number are found by title. A file with no `##` headings
  but numbered bold paragraphs (`**3. Title** ...`) is split at those. Text
  before the first section is section 0, "(introduction)".

The reference folder is ../references next to this script (override with
--dir). Python 3 standard library only.
"""
import argparse
import os
import re
import sys

NUM_RE = re.compile(r"^([A-Z]{0,2}\d+(?:\.\d+)*)[.):]?\s+(.*)$")
ALIAS_RE = re.compile(r"\band\s+([A-Z]{0,2}\d+(?:\.\d+)+)\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BOLD_RE = re.compile(r"^\*\*([A-Z]{0,2}\d+(?:\.\d+)*)\.\s+(.+?)\*\*")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")


def tokens(n):
    t = max(1, n // 4)
    return "~%.1fk tok" % (t / 1000.0) if t >= 1000 else "~%d tok" % t


def size_line(what, text):
    return "# ref %s: %s chars (~%s tokens)\n" % (what, "{:,}".format(len(text)), "{:,}".format(max(1, len(text) // 4)))


class Doc:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            self.lines = fh.read().split("\n")
        self.title = ""
        self.sections = self._parse()

    def _headings(self):
        found, fence = [], None
        for n, line in enumerate(self.lines):
            f = FENCE_RE.match(line)
            if f:
                mark = f.group(1)[0]
                if fence is None:
                    fence = mark
                elif fence == mark:
                    fence = None
                continue
            if fence:
                continue
            m = HEADING_RE.match(line)
            if m:
                found.append((n, len(m.group(1)), m.group(2), "h"))
            else:
                b = BOLD_RE.match(line)
                if b:
                    found.append((n, 0, "%s. %s" % (b.group(1), b.group(2).rstrip(". ")), "b"))
        real = [h for h in found if h[3] == "h"]
        if any(level >= 2 for _, level, _, _ in real):
            return real
        # no ## headings: numbered bold paragraphs act as the sections
        return [h if h[3] == "h" else (h[0], 2, h[2], "b") for h in found]

    def _parse(self):
        heads = self._headings()
        sections = []
        first = len(self.lines)
        for n, level, text, _ in heads:
            if level == 1 and not self.title:
                self.title = text
                continue
            first = min(first, n)
            m = NUM_RE.match(text)
            nums = [m.group(1)] if m else []
            title = m.group(2) if m else text
            nums += ALIAS_RE.findall(title) if nums else []
            sections.append({"nums": nums, "title": title, "raw": text, "level": level, "start": n})
        for k, s in enumerate(sections):
            nxt = [t["start"] for t in sections[k + 1:] if t["level"] <= s["level"]]
            s["end"] = nxt[0] if nxt else len(self.lines)
            s["own_end"] = sections[k + 1]["start"] if k + 1 < len(sections) else len(self.lines)
        intro_start = next((n + 1 for n, level, _, _ in heads if level == 1), 0)
        intro = "\n".join(self.lines[intro_start:first]).strip()
        if intro:
            sections.insert(0, {"nums": ["0"], "title": "(introduction)", "raw": "(introduction)", "level": 2,
                                "start": intro_start, "end": first, "own_end": first})
        return sections

    def text(self, s, own=False):
        return "\n".join(self.lines[s["start"]:s["own_end"] if own else s["end"]]).strip("\n") + "\n"

    def label(self, s):
        return "/".join(s["nums"]) if s["nums"] else "-"

    def toc(self):
        out = ["%s  %s  (%s)" % (self.name, self.title, tokens(sum(len(l) + 1 for l in self.lines)))]
        base = min([s["level"] for s in self.sections] or [2])
        for s in self.sections:
            out.append("  %s%-7s %s  (%s)" % ("  " * (s["level"] - base), self.label(s), s["title"],
                                             tokens(len(self.text(s)))))
        return out

    def find(self, query):
        """Sections matching a number or a title fragment: (matches, how)."""
        q = query.strip().rstrip(".")
        by_num = [s for s in self.sections if q.upper() in [n.upper() for n in s["nums"]]]
        if by_num:
            return by_num[:1], "number"
        low = q.lower()
        exact = [s for s in self.sections if s["title"].lower() == low or s["raw"].lower() == low]
        if exact:
            return exact[:1], "title"
        words = low.split()
        hits = [s for s in self.sections if all(w in s["raw"].lower() for w in words)]
        return hits, "title"


def load(ref_dir):
    try:
        names = sorted(f for f in os.listdir(ref_dir) if f.endswith(".md"))
    except OSError as exc:
        sys.stderr.write("ref: cannot list %s: %s\n" % (ref_dir, exc))
        return []
    return [Doc(os.path.join(ref_dir, f)) for f in names]


def pick(docs, key):
    k = key.lower()
    if k.endswith(".md"):
        k = k[:-3]
    stems = {d: d.name[:-3].lower() for d in docs}
    for test in (lambda s: s == k, lambda s: s.endswith(k) or s.startswith(k), lambda s: k in s):
        hits = [d for d in docs if test(stems[d])]
        if len(hits) == 1:
            return hits[0], []
        if hits:
            return None, hits
    return None, []


def search(docs, words, any_word=False):
    words = [w.lower() for w in words]
    rows = []
    for d in docs:
        for s in d.sections:
            body = d.text(s, own=True)
            low = body.lower()
            present = [w for w in words if w in low]
            if not present or (not any_word and len(present) < len(words)):
                continue
            count = sum(low.count(w) for w in words) + 100000 * len(present)
            first = present[0]
            line = next((l.strip() for l in body.split("\n")[1:] if first in l.lower()), "") or \
                next((l.strip() for l in body.split("\n") if first in l.lower()), "")
            pos = line.lower().find(first)
            if len(line) > 110:
                start = max(0, pos - 40)
                line = ("..." if start else "") + line[start:start + 110] + "..."
            hit = " [has: %s]" % " ".join(present) if any_word and len(words) > 1 else ""
            rows.append((-count, "%s %s  %s  (%s)%s | %s" % (d.name[:-3], d.label(s), s["title"],
                                                           tokens(len(d.text(s))), hit, line)))
    rows.sort(key=lambda r: r[0])
    return [r[1] for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print one section of a reference file (see the header of this file).")
    ap.add_argument("file", nargs="?", help="reference file name or an unambiguous part of it")
    ap.add_argument("section", nargs="*", help="section number (5.3) or words of its title")
    ap.add_argument("--toc", action="store_true", help="list sections (of one file, or of every file)")
    ap.add_argument("--search", nargs="+", metavar="WORD",
                    help="list sections containing ALL the words (plain text, any case); if none does, "
                         "sections containing ANY of them, most words first")
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references"),
                    help="reference folder (default: ../references)")
    args = ap.parse_args(argv)
    docs = load(args.dir)
    if not docs:
        sys.stderr.write("ref: no .md files in %s\n" % args.dir)
        return 1
    me = "ref.py"

    doc = None
    if args.file:
        doc, several = pick(docs, args.file)
        if doc is None:
            sys.stderr.write("ref: %s reference file %r. Files: %s\n" % (
                "several files match" if several else "no", args.file,
                ", ".join(d.name for d in (several or docs))))
            return 1

    if args.search:
        rows = search([doc] if doc else docs, args.search)
        note = ""
        if not rows and len(args.search) > 1:
            rows = search([doc] if doc else docs, args.search, any_word=True)
            if rows:
                note = ("no section contains ALL of: %s. Showing sections that contain ANY of the words, "
                        "most words first:\n" % " ".join(args.search))
        shown = rows[:40 if not note else 15]
        body = note + "\n".join(shown) + ("\n" if shown else "")
        if len(rows) > len(shown):
            body += "... %d more section(s): add a word to narrow the search\n" % (len(rows) - len(shown))
        if not rows:
            body = "no section contains any of: %s (words are matched as plain text; try a shorter or different word)\n" % " ".join(args.search)
        else:
            body += "print one with: %s <file> <section number or title words>\n" % me
        sys.stdout.write(size_line("search %s" % " ".join(args.search), body) + body)
        return 0 if rows else 1

    if doc is None or (args.toc and not args.section) or not args.section:
        lines = []
        for d in ([doc] if doc else docs):
            lines.extend(d.toc())
        lines.append("print one section with: %s <file> <section number or title words>" % me)
        body = "\n".join(lines) + "\n"
        sys.stdout.write(size_line("toc" + (" " + doc.name if doc else ""), body) + body)
        return 0

    query = " ".join(args.section)
    hits, _ = doc.find(query)
    if len(hits) == 1:
        s = hits[0]
        body = doc.text(s)
        sys.stdout.write(size_line("%s %s" % (doc.name, doc.label(s) if s["nums"] else s["title"]), body) + body)
        return 0
    if hits:
        sys.stderr.write("ref: %d sections of %s match %r. Name one by number or with more words:\n" % (
            len(hits), doc.name, query))
        for s in hits:
            sys.stderr.write("  %-7s %s\n" % (doc.label(s), s["title"]))
        return 1
    rows = search([doc], query.split())
    sys.stderr.write("ref: no section of %s is numbered or titled %r.\n" % (doc.name, query))
    if rows:
        sys.stderr.write("Sections whose text contains it:\n" + "".join("  %s\n" % r for r in rows[:8]))
    else:
        sys.stderr.write("List the sections with: %s %s --toc\n" % (me, doc.name[:-3]))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
