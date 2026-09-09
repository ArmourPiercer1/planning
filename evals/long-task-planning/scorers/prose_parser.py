"""Prose parser for baseline (free-form / checklist) plans.

Deliberately lightweight: it extracts what a human-readable markdown plan
actually lets us measure — sections, task lines, file mentions, explicit
ordering phrases, parallel markers, out-of-scope and acceptance text — and
leaves the rest as 'not measurable' instead of guessing. No LLM judge here.
"""

import re

# explicit ordering phrases — two narrow, high-precision patterns
AFTER_DONE = re.compile(
    r"\bafter\s+(?:the\s+)?([A-Za-z0-9_ ./-]{3,40}?)(?:\s+is\s+| gets | is)?\s*(?:done|complete|finished|landed)\b",
    re.IGNORECASE,
)
DEPENDS_ON = re.compile(
    r"([A-Za-z0-9_ ./-]{3,40}?)\s+depends\s+on\s+([A-Za-z0-9_ ./-]{3,40})\b",
    re.IGNORECASE,
)
PARALLEL_RE = re.compile(
    r"\b(in parallel|concurrently|simultaneously|at the same time|can be done together)\b", re.IGNORECASE
)
BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d{1,2}[.)]\s+)(.{8,400})$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STEP_NUM_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def parse_plan_md(text: str, repo_files: list[str]) -> dict:
    """repo_files: repo-relative paths of the fixture (for mention matching)."""
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    sections: list[dict] = []          # {level, title, content_lines}
    current: dict | None = None
    tasks: list[dict] = []             # {text, line_no, step_no|None}
    in_code = False
    for i, raw in enumerate(lines):
        if raw.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        h = HEADING_RE.match(raw)
        if h:
            current = {"level": len(h.group(1)), "title": h.group(2).strip(), "content_lines": []}
            sections.append(current)
            headings.append((len(h.group(1)), current["title"]))
            continue
        if current is not None:
            current["content_lines"].append(raw)
        m = BULLET_RE.match(raw)
        if m:
            step = STEP_NUM_RE.match(raw)
            tasks.append({
                "text": m.group(1).strip(),
                "line_no": i,
                "step_no": int(step.group(1)) if step else None,
                "is_numbered": bool(step),
            })

    def mention_files(needle_text: str) -> list[str]:
        """repo files whose basename or path appears in the text."""
        found = []
        low = needle_text.lower()
        for f in repo_files:
            base = f.split("/")[-1]
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(base.lower()) + r"(?![A-Za-z0-9])", low) or f.lower() in low:
                found.append(f)
        return found

    for t in tasks:
        t["files"] = mention_files(t["text"])
        t["parallel_marker"] = bool(PARALLEL_RE.search(t["text"]))

    out_of_scope = ""
    acceptance = ""
    integration = ""
    for s in sections:
        title = _norm(s["title"])
        body = "\n".join(s["content_lines"])
        if re.search(r"out.of.scope|non.?goal|not doing|exclud|beyond scope|won'?t|will not", title):
            out_of_scope += body + "\n"
        if re.search(r"accept|definition of done|verif|success criteri|test", title):
            acceptance += body + "\n"
        if re.search(r"integrat|e2e|end.to.end|wiring|seam", title):
            integration += body + "\n"
    # fallback: keyword paragraphs anywhere
    if not out_of_scope:
        for m in re.finditer(r"(?im)^(.*out.of.scope.*|.*non.?goals?.*)$", text):
            out_of_scope += m.group(1) + "\n"
    if not acceptance:
        for m in re.finditer(r"(?im)^(.*definition of done.*|.*acceptance.*|.*verification?.*)$", text):
            acceptance += m.group(1) + "\n"

    # explicit ordering pairs: (later fragment, earlier fragment)
    ordering: list[dict] = []
    for m in AFTER_DONE.finditer(text):
        ordering.append({"later": m.group(0).strip(), "earlier": m.group(1).strip(), "form": "after-...-done"})
    for m in DEPENDS_ON.finditer(text):
        ordering.append({"later": m.group(1).strip(), "earlier": m.group(2).strip(), "form": "depends-on"})

    # numbered sequential tasks within one list imply order
    numbered = [t for t in tasks if t["is_numbered"]]
    implied_order_pairs = []
    for a, b in zip(numbered, numbered[1:]):
        if b.get("step_no") == (a.get("step_no") or 0) + 1:
            implied_order_pairs.append({"later": a["text"][:60], "earlier": b["text"][:60]})

    return {
        "headings": [(lvl, t) for lvl, t in headings],
        "sections": sections,
        "tasks": tasks,
        "file_mentions": {f: sum(1 for t in tasks if f in t["files"]) for f in repo_files},
        "out_of_scope_text": out_of_scope.strip(),
        "acceptance_text": acceptance.strip(),
        "integration_text": integration.strip(),
        "explicit_ordering": ordering,
        "implied_order_pairs": implied_order_pairs,
        "parallel_marker_any": bool(PARALLEL_RE.search(text)),
        "word_count": len(re.findall(r"\b\w+\b", text)),
    }
