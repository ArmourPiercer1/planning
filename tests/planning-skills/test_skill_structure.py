"""Structure tests for the planning skills under .agents/skills/.

Host convention (verified live): each skill is a directory with a SKILL.md
whose YAML frontmatter must parse cleanly — in particular, an unquoted
`description` value must NOT contain a colon+space (": "), or the host
silently drops the skill from its catalog. These tests encode that rule and
the required section skeleton so the convention cannot silently regress.
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"

EXPECTED_SKILLS = {
    "long-task-planning",
    "stage-contract",
    "context-decomposer",
    "dependency-dag",
    "integration-planner",
    "task-packager",
    "plan-risk-estimator",
    "plan-auditor",
    "checkpoint-handoff",
    "replan-controller",
}

# Keywords that must each appear in some H2 header (e.g. "## Failure & Escalation")
REQUIRED_SECTION_KEYWORDS = [
    "Trigger",
    "Inputs",
    "Procedure",
    "Heuristics",
    "Output",
    "Failure",
    "Examples",
]

MIN_DESCRIPTION_LEN = 80
MAX_DESCRIPTION_LEN = 1000  # catalog truncation guard


def parse_frontmatter(text):
    """Parse the flat key: value YAML frontmatter block. Raises ValueError on
    malformed input. Deliberately minimal: the host loader accepts the same
    flat subset, so a stricter parser would only create false positives."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md does not start with '---' frontmatter")
    fm = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        if not line.strip():
            continue
        if line.startswith((" ", "\t")):
            raise ValueError(f"nested/indented frontmatter line not allowed: {line!r}")
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise ValueError(f"unparseable frontmatter line: {line!r}")
        fm[key.strip()] = value.strip()
    if not closed:
        raise ValueError("frontmatter block is never closed")
    return fm


def check_skill(skill_dir, problems):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        problems.append(f"{skill_dir.name}: missing SKILL.md")
        return
    text = skill_md.read_text(encoding="utf-8")
    name = skill_dir.name

    # 1. frontmatter parses
    try:
        fm = parse_frontmatter(text)
    except ValueError as e:
        problems.append(f"{name}: frontmatter unparseable — {e}")
        return

    # 2. name == directory name (host identity)
    if fm.get("name") != name:
        problems.append(f"{name}: frontmatter name {fm.get('name')!r} != directory name")

    # 3. description: present, bounded, trigger-oriented, and — the hard-won
    #    rule — no unquoted ": " which silently drops the skill from the host
    desc = fm.get("description", "")
    if not desc:
        problems.append(f"{name}: missing description")
    else:
        if ": " in desc or desc.endswith(":"):
            problems.append(f"{name}: description contains ': ' — the host drops "
                            f"skills whose frontmatter value has a bare colon+space")
        if not (MIN_DESCRIPTION_LEN <= len(desc) <= MAX_DESCRIPTION_LEN):
            problems.append(f"{name}: description length {len(desc)} outside "
                            f"[{MIN_DESCRIPTION_LEN}, {MAX_DESCRIPTION_LEN}]")
        if not re.search(r"\b(use|must run|interface reserved)\b", desc, re.IGNORECASE):
            problems.append(f"{name}: description has no trigger phrasing "
                            f"(expected 'Use when/as', 'Must run', or 'INTERFACE RESERVED')")

    # 4. required H2 sections
    h2s = re.findall(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)
    for kw in REQUIRED_SECTION_KEYWORDS:
        if not any(kw.lower() in h.lower() for h in h2s):
            problems.append(f"{name}: missing required H2 section matching {kw!r} "
                            f"(have: {h2s})")

    # 5. body sanity: a skill with no procedure body is useless
    body = text.split("---", 2)[-1]
    if len(body) < 800:
        problems.append(f"{name}: body suspiciously short ({len(body)} chars)")


def run():
    problems = []
    if not SKILLS_DIR.is_dir():
        print(f"FAIL: {SKILLS_DIR} does not exist")
        return 1
    skill_dirs = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}
    missing = EXPECTED_SKILLS - skill_dirs
    if missing:
        problems.append(f"expected skills missing: {sorted(missing)}")
    extra = skill_dirs - EXPECTED_SKILLS
    if extra:
        # not an error: new skills are allowed, but report for awareness
        print(f"note: extra skill dirs beyond the V1 set: {sorted(extra)}")
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / "SKILL.md").is_file():
            check_skill(d, problems)
    for p in problems:
        print(f"FAIL: {p}")
    if not problems:
        print(f"PASS: {len(skill_dirs)} skills, all conform to host frontmatter + section convention")
    return len(problems)


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
