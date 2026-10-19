#!/usr/bin/env python3
"""Audit a portable skill collection.

The script inventories SKILL.md packages, flags common portability and
ownership issues, and writes the standard skill-creator run artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "if",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "use", "user", "users", "when", "with", "you", "your",
    "skill", "skills", "agent", "agents",
}

ABSOLUTE_PATH_RE = re.compile(r"(/Users/[\w.-]+|/home/[\w.-]+|C:\\Users\\[\w.-]+)")
SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(api[_-]?key|secret|token|password|passwd|private[_-]?key)\b\s*[:=]\s*['\"]?[^\s'\"<>]+",
    re.I,
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


@dataclass
class Skill:
    folder: str
    path: Path
    name: str
    description: str
    line_count: int
    has_companion: bool
    has_evals: bool
    has_references: bool
    has_scripts: bool
    portability_flags: list[str]


def default_roots() -> list[Path]:
    roots = []
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.exists():
        roots.append(cwd_skills)
    for env_name in ("CODEX_HOME", "CLAUDE_HOME"):
        base = os.environ.get(env_name)
        if base and (Path(base) / "skills").exists():
            roots.append(Path(base) / "skills")
    home = Path.home()
    for root in (home / ".codex" / "skills", home / ".agents" / "skills"):
        if root.exists():
            roots.append(root)
    deduped = []
    seen = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            deduped.append(root)
            seen.add(resolved)
    return deduped


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    frontmatter = {}
    current_key = None
    current_value: list[str] = []
    for raw in parts[1].splitlines():
        if not raw.strip():
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if match and not raw.startswith((" ", "\t")):
            if current_key:
                frontmatter[current_key] = "\n".join(current_value).strip().strip('"').strip("'")
            current_key = match.group(1)
            current_value = [match.group(2)]
        elif current_key:
            current_value.append(raw.strip())
    if current_key:
        frontmatter[current_key] = "\n".join(current_value).strip().strip('"').strip("'")
    return frontmatter


def portability_flags(text: str, private_terms: list[str]) -> list[str]:
    flags = []
    if ABSOLUTE_PATH_RE.search(text):
        flags.append("contains a personal absolute path")
    if SECRET_ASSIGNMENT_RE.search(text) or PRIVATE_KEY_RE.search(text):
        flags.append("contains secret-like configuration; verify no real values are embedded")
    for term in private_terms:
        if term and term in text:
            flags.append(f"contains private workspace term `{term}`")
    if "mcp_notion_" in text:
        flags.append("contains host-specific tool names; confirm they are optional or documented")
    return flags


def load_skills(roots: list[Path], private_terms: list[str]) -> list[Skill]:
    skills = []
    for root in roots:
        if not root.exists():
            continue
        for md in sorted(root.glob("*/SKILL.md")):
            try:
                text = md.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            folder = md.parent.name
            skills.append(
                Skill(
                    folder=folder,
                    path=md,
                    name=fm.get("name", ""),
                    description=re.sub(r"\s+", " ", fm.get("description", "")).strip(),
                    line_count=len(text.splitlines()),
                    has_companion=(md.parent / "companion.json").exists(),
                    has_evals=(md.parent / "evals" / "evals.json").exists(),
                    has_references=(md.parent / "references").exists(),
                    has_scripts=(md.parent / "scripts").exists(),
                    portability_flags=portability_flags(text, private_terms),
                )
            )
    return skills


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def overlap_pairs(skills: list[Skill], threshold: float) -> list[tuple[float, Skill, Skill]]:
    pairs = []
    skill_tokens = {skill.path: tokens(f"{skill.name} {skill.description}") for skill in skills}
    for idx, left in enumerate(skills):
        for right in skills[idx + 1 :]:
            lt = skill_tokens[left.path]
            rt = skill_tokens[right.path]
            if not lt or not rt:
                continue
            score = len(lt & rt) / len(lt | rt)
            if score >= threshold:
                pairs.append((score, left, right))
    pairs.sort(key=lambda item: item[0], reverse=True)
    return pairs


def render_inventory(skills: list[Skill], roots: list[Path]) -> str:
    lines = ["# Skill Inventory", ""]
    lines.append("## Roots")
    for root in roots:
        lines.append(f"- `{root}`")
    lines.append("")
    lines.append("## Skills")
    for skill in sorted(skills, key=lambda s: (s.name or s.folder).lower()):
        title = skill.name or "(missing name)"
        lines.append(f"### {title}")
        lines.append(f"- Folder: `{skill.folder}`")
        lines.append(f"- Path: `{skill.path}`")
        lines.append(f"- Lines: {skill.line_count}")
        lines.append(f"- Companion manifest: {'yes' if skill.has_companion else 'no'}")
        lines.append(f"- Evals: {'yes' if skill.has_evals else 'no'}")
        lines.append(f"- Scripts: {'yes' if skill.has_scripts else 'no'}")
        lines.append(f"- References: {'yes' if skill.has_references else 'no'}")
        lines.append(f"- Description: {skill.description or '(missing)'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_frictions(skills: list[Skill], overlaps: list[tuple[float, Skill, Skill]]) -> str:
    issues = []
    names = defaultdict(list)
    for skill in skills:
        if skill.name:
            names[skill.name].append(skill)
        if not skill.name:
            issues.append(("missing-name", skill, "Frontmatter is missing `name`."))
        if not skill.description:
            issues.append(("missing-description", skill, "Frontmatter is missing `description`."))
        if skill.name and skill.name != skill.folder:
            issues.append(("name-folder-mismatch", skill, f"`name` is `{skill.name}` but folder is `{skill.folder}`."))
        if skill.line_count > 500:
            issues.append(("large-entrypoint", skill, f"`SKILL.md` is {skill.line_count} lines; consider references."))
        for flag in skill.portability_flags:
            issues.append(("portability", skill, flag))

    lines = ["# Skill Frictions", ""]
    if not issues and not overlaps:
        lines.append("No obvious structural frictions found.")
        return "\n".join(lines) + "\n"

    lines.append("## Structural Issues")
    for kind, skill, detail in issues:
        lines.append(f"- `{kind}` in `{skill.folder}`: {detail}")
    for name, matches in sorted(names.items()):
        if len(matches) > 1:
            paths = ", ".join(f"`{s.path}`" for s in matches)
            lines.append(f"- `duplicate-name` for `{name}`: {paths}")

    lines.append("")
    lines.append("## Possible Description Overlaps")
    if overlaps:
        for score, left, right in overlaps[:20]:
            lines.append(
                f"- {score:.2f}: `{left.name or left.folder}` and `{right.name or right.folder}`"
            )
    else:
        lines.append("- No high-overlap descriptions found.")
    return "\n".join(lines).rstrip() + "\n"


def render_proposal(skills: list[Skill], overlaps: list[tuple[float, Skill, Skill]]) -> str:
    missing = [s for s in skills if not s.name or not s.description]
    nonportable = [s for s in skills if s.portability_flags]
    large = [s for s in skills if s.line_count > 500]
    lines = [
        "# Skill System Proposal",
        "",
        "## Recommendation",
    ]
    if not skills:
        lines.append("No skills were found in the selected roots.")
    else:
        lines.append("Keep the public surface small, fix missing router metadata first, then handle overlaps with evidence from real prompts.")
    lines.extend(["", "## What To Simplify Now"])
    if missing:
        for skill in missing:
            lines.append(f"- Add missing frontmatter to `{skill.folder}`.")
    if nonportable:
        for skill in nonportable:
            lines.append(f"- Make `{skill.folder}` portable: {', '.join(skill.portability_flags)}.")
    if large:
        for skill in large:
            lines.append(f"- Split long entrypoint `{skill.folder}` into `references/`.")
    if overlaps:
        lines.append("- Review high-overlap descriptions before merging; confirm with real prompts.")
    if not (missing or nonportable or large or overlaps):
        lines.append("- No urgent structural simplification found.")
    lines.extend(
        [
            "",
            "## What Not To Merge Now",
            "- Do not merge skills based only on similar names. Require repeated prompt overlap or duplicated workflow responsibilities.",
            "",
            "## Suggested Patch Order",
            "1. Fix missing `name` and `description` fields.",
            "2. Remove non-portable paths or private context from shareable packages.",
            "3. Move long examples and volatile policy details into references.",
            "4. Add or update eval prompts for the highest-risk owners.",
            "5. Only then consider merges, splits, or retirements.",
            "",
            "## Bottom Line",
            "Treat metadata as routing, `SKILL.md` as the stable contract, and references/scripts as implementation support.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a portable skill system.")
    parser.add_argument("--skill-root", action="append", type=Path, help="Skill root containing */SKILL.md. Can be repeated.")
    parser.add_argument("--out", type=Path, help="Run output directory. Defaults to plans/skill-creator/runs/<timestamp>-audit.")
    parser.add_argument("--overlap-threshold", type=float, default=0.34)
    parser.add_argument("--private-term", action="append", default=[], help="Workspace-specific term to flag as non-portable. Can be repeated.")
    args = parser.parse_args()

    roots = args.skill_root or default_roots()
    if args.out:
        out = args.out
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = Path("plans") / "skill-creator" / "runs" / f"{stamp}-audit"
    out.mkdir(parents=True, exist_ok=True)

    skills = load_skills(roots, args.private_term)
    overlaps = overlap_pairs(skills, args.overlap_threshold)

    (out / "inventory.md").write_text(render_inventory(skills, roots), encoding="utf-8")
    (out / "frictions.md").write_text(render_frictions(skills, overlaps), encoding="utf-8")
    (out / "proposal.md").write_text(render_proposal(skills, overlaps), encoding="utf-8")
    (out / "audit-summary.json").write_text(
        json.dumps(
            {
                "skill_count": len(skills),
                "roots": [str(root) for root in roots],
                "overlap_count": len(overlaps),
                "output_dir": str(out),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
