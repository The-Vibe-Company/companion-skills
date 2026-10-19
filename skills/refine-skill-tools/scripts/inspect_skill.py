#!/usr/bin/env python3
"""Portable static checks for an Agent Skill package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?<![\w.])/(?:Users|home)/[^\s)`]+"),
    re.compile(r"(?<![\w.])[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\s)`]+"),
    re.compile(r"(?<![\w.])~/[^\s)`]+"),
)
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"
)
DANGEROUS_PATTERNS = {
    "recursive deletion": re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r"),
    "destructive git reset": re.compile(r"\bgit\s+reset\s+--hard\b"),
    "remote script execution": re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b"),
}


def finding(severity: str, code: str, message: str, path: str, line: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"severity": severity, "code": code, "message": message, "path": path}
    if line is not None:
        item["line"] = line
    return item


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not text.startswith("---\n"):
        return {}, [finding("error", "frontmatter.missing", "SKILL.md must start with YAML frontmatter", "SKILL.md", 1)]
    end = text.find("\n---", 4)
    if end == -1:
        return {}, [finding("error", "frontmatter.unclosed", "YAML frontmatter is not closed", "SKILL.md", 1)]
    block = text[4:end]
    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in block.splitlines():
        if raw.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {raw.strip()}".strip()
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if match:
            current_key = match.group(1)
            data[current_key] = match.group(2).strip().strip("'\"")
    return data, issues


def inspect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    skill_file = root / "SKILL.md"
    findings: list[dict[str, Any]] = []
    if not skill_file.is_file():
        findings.append(finding("error", "skill.missing", "No SKILL.md found", "SKILL.md"))
        return {"skill": str(root), "findings": findings, "counts": {"error": 1, "warning": 0, "info": 0}}

    text = skill_file.read_text(encoding="utf-8", errors="replace")
    metadata, metadata_findings = parse_frontmatter(text)
    findings.extend(metadata_findings)
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not name:
        findings.append(finding("error", "frontmatter.name", "Required name is missing", "SKILL.md", 2))
    elif not NAME_RE.fullmatch(name):
        findings.append(finding("error", "frontmatter.name-format", "name must use lowercase kebab-case", "SKILL.md", 2))
    elif name != root.name and root.name not in {"skill", "baseline", "candidate", "best"}:
        findings.append(finding("warning", "package.name-mismatch", f"name '{name}' differs from folder '{root.name}'", "SKILL.md", 2))
    if not description:
        findings.append(finding("error", "frontmatter.description", "Required description is missing", "SKILL.md", 3))
    else:
        if len(description) > 1024:
            findings.append(finding("warning", "frontmatter.description-length", "description exceeds 1024 characters", "SKILL.md", 3))
        if not re.search(r"(?i)\b(use|when|whenever|trigger|ask|want|need)\b", description):
            findings.append(finding("warning", "routing.when-to-use", "description does not clearly state when to use the skill", "SKILL.md", 3))

    line_count = len(text.splitlines())
    if line_count > 500:
        findings.append(finding("warning", "context.large-entrypoint", f"SKILL.md has {line_count} lines; consider progressive disclosure", "SKILL.md"))

    text_files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            resolved = path.resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                findings.append(finding("error", "package.external-symlink", "Symlink points outside the skill package", path.relative_to(root).as_posix()))
            continue
        if path.is_file() and path.stat().st_size <= 2_000_000:
            try:
                path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            text_files.append(path)

    for path in text_files:
        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if SECRET_RE.search(line):
                findings.append(finding("error", "security.possible-secret", "Possible embedded secret; never reproduce the value in reports", relative, line_no))
            for label, pattern in DANGEROUS_PATTERNS.items():
                if pattern.search(line):
                    findings.append(finding("warning", "safety.dangerous-command", f"Review {label} and require explicit scope and approval", relative, line_no))
            for pattern in ABSOLUTE_PATH_PATTERNS:
                is_scanner_pattern = path.name == "inspect_skill.py" and line.lstrip().startswith("re.compile(")
                if pattern.search(line) and not is_scanner_pattern:
                    findings.append(finding("warning", "portability.absolute-path", "Possible machine-specific absolute path", relative, line_no))

        if path.suffix.lower() in {".md", ".markdown"}:
            for match in LINK_RE.finditer(content):
                raw_target = match.group(1).strip().split()[0].strip("<>")
                if not raw_target or raw_target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                    continue
                target = raw_target.split("#", 1)[0]
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    findings.append(finding("warning", "links.escape-root", f"Local link escapes the skill package: {raw_target}", relative))
                    continue
                if not resolved.exists():
                    findings.append(finding("error", "links.broken", f"Broken local link: {raw_target}", relative))

    evals_file = root / "evals" / "evals.json"
    if not evals_file.exists():
        findings.append(finding("info", "evals.missing", "No evals/evals.json found; behavioral optimization will need a benchmark", "evals/evals.json"))
    else:
        try:
            evals = json.loads(evals_file.read_text(encoding="utf-8"))
            if name and evals.get("skill_name") != name:
                findings.append(finding("error", "evals.skill-name", "evals skill_name does not match frontmatter name", "evals/evals.json"))
            if not isinstance(evals.get("evals"), list) or not evals.get("evals"):
                findings.append(finding("warning", "evals.empty", "evals/evals.json has no eval cases", "evals/evals.json"))
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(finding("error", "evals.invalid-json", f"Invalid evals/evals.json: {exc}", "evals/evals.json"))

    counts = {level: sum(1 for item in findings if item["severity"] == level) for level in ("error", "warning", "info")}
    digest = hashlib.sha256(skill_file.read_bytes()).hexdigest()
    return {
        "skill": str(root),
        "name": name or None,
        "skill_md_sha256": digest,
        "skill_md_lines": line_count,
        "findings": findings,
        "counts": counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect an Agent Skill package without modifying it.")
    parser.add_argument("skill", type=Path)
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = inspect(args.skill)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 1 if report["counts"]["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
