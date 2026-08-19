#!/usr/bin/env python3
"""Lint proposed or existing repository instruction files."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from snapshot_instruction_stack import IMPORT_RE, ROOT_NAMES

MAX_FILE_LINES = 200
DEFAULT_AGGREGATE_BYTES = 32 * 1024
PRIVATE_PATTERNS = {
    "absolute user path": re.compile(r"(?:/Users/|/home/)[^\s`]+"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "Notion URL": re.compile(r"https?://(?:www\.)?notion\.(?:so|site)/", re.I),
    "secret-like token": re.compile(r"\b(?:sk|ghp|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b"),
    "UUID": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.I,
    ),
}
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PACKAGE_COMMAND_RE = re.compile(
    r"^(pnpm|npm|yarn|bun)\s+(?:run\s+)?([A-Za-z0-9:_-]+)(?:\s|$)"
)
BULLET_RE = re.compile(r"^\s*(?:[-*+] |\d+[.)] )(.*\S)\s*$")


def is_instruction_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    return (
        path.name in ROOT_NAMES
        or rel == ".github/copilot-instructions.md"
        or (rel.startswith(".claude/rules/") and path.suffix.lower() == ".md")
        or (
            rel.startswith(".github/instructions/")
            and path.name.endswith(".instructions.md")
        )
    )


def iter_instruction_files(root: Path) -> Iterable[Path]:
    if root.is_file() or root.is_symlink():
        yield root
        return
    for path in sorted(root.rglob("*.md")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        if is_instruction_file(path, root):
            yield path


def issue(
    level: str, code: str, path: str, message: str, line: int | None = None
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "level": level,
        "code": code,
        "path": path,
        "message": message,
    }
    if line is not None:
        item["line"] = line
    return item


def package_scripts(repo: Path) -> set[str]:
    path = repo / "package.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return set()
    scripts = data.get("scripts")
    return set(scripts) if isinstance(scripts, dict) else set()


def normalized_rule(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", text)).strip().lower()


def plausible_path(token: str) -> bool:
    if not token or token.startswith(("http://", "https://", "@", "$", "<")):
        return False
    if " " in token or token.startswith(
        ("pnpm", "npm", "yarn", "bun", "python", "git", "./")
    ):
        return token.startswith("./") and len(token.split()) == 1
    return "/" in token or token.endswith((".md", ".json", ".toml", ".yaml", ".yml"))


def resolve_candidate_reference(
    token: str, source: Path, instruction_root: Path, repo: Path
) -> bool:
    clean = token.strip().rstrip(".,:;)")
    if any(char in clean for char in "*{}[]"):
        return True
    candidates = [source.parent / clean, instruction_root / clean, repo / clean]
    return any(candidate.exists() or candidate.is_symlink() for candidate in candidates)


def lint(repo: Path, instruction_root: Path, aggregate_budget: int) -> dict[str, Any]:
    repo = repo.resolve()
    instruction_root = instruction_root.resolve()
    issues: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    rule_locations: dict[str, list[tuple[str, int]]] = defaultdict(list)
    scripts = package_scripts(repo)
    aggregate_bytes = 0

    found = list(iter_instruction_files(instruction_root))
    if not found:
        issues.append(
            issue(
                "info",
                "empty-stack",
                ".",
                "No instruction files were found; this can be a valid result.",
            )
        )

    for path in found:
        rel = (
            path.relative_to(instruction_root).as_posix()
            if instruction_root.is_dir()
            else path.name
        )
        if path.is_symlink():
            target = path.resolve(strict=False)
            if not target.exists():
                issues.append(
                    issue(
                        "error",
                        "broken-symlink",
                        rel,
                        f"Symlink target does not exist: {os.readlink(path)}",
                    )
                )
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(issue("error", "unreadable", rel, str(exc)))
            continue

        raw = text.encode("utf-8")
        line_count = len(text.splitlines())
        aggregate_bytes += len(raw)
        files.append({"path": rel, "bytes": len(raw), "lines": line_count})
        if line_count > MAX_FILE_LINES:
            issues.append(
                issue(
                    "warning",
                    "long-file",
                    rel,
                    f"{line_count} lines exceeds the {MAX_FILE_LINES}-line maintenance warning.",
                )
            )

        for imported in sorted(set(IMPORT_RE.findall(text))):
            target = path.parent / imported
            candidate_target = instruction_root / imported
            repo_target = repo / imported
            if not any(
                item.exists() or item.is_symlink()
                for item in (target, candidate_target, repo_target)
            ):
                issues.append(
                    issue(
                        "error",
                        "broken-import",
                        rel,
                        f"Import target not found: {imported}",
                    )
                )

        for label, pattern in PRIVATE_PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                issues.append(
                    issue(
                        "warning",
                        "private-data",
                        rel,
                        f"Possible {label}: {match.group(0)}",
                        line_no,
                    )
                )

        for line_no, line in enumerate(text.splitlines(), 1):
            negative_path_example = bool(
                re.search(
                    r"\b(?:do not|don't|never|must not|avoid)\s+(?:create|add|write|edit)\b",
                    line,
                    re.I,
                )
            )
            bullet = BULLET_RE.match(line)
            if bullet:
                value = normalized_rule(bullet.group(1))
                if len(value) >= 24:
                    rule_locations[value].append((rel, line_no))
            for token in BACKTICK_RE.findall(line):
                command = PACKAGE_COMMAND_RE.match(token.strip())
                if command and scripts:
                    script = command.group(2)
                    if script not in scripts and script not in {
                        "install",
                        "exec",
                        "dlx",
                    }:
                        issues.append(
                            issue(
                                "warning",
                                "unknown-package-script",
                                rel,
                                f"Root package.json does not define script '{script}' used in `{token}`.",
                                line_no,
                            )
                        )
                elif (
                    not negative_path_example
                    and plausible_path(token)
                    and not resolve_candidate_reference(
                        token, path, instruction_root, repo
                    )
                ):
                    issues.append(
                        issue(
                            "warning",
                            "missing-path",
                            rel,
                            f"Referenced path was not found: `{token}`",
                            line_no,
                        )
                    )

    for value, locations in sorted(rule_locations.items()):
        if len(locations) > 1:
            rendered = ", ".join(f"{path}:{line}" for path, line in locations)
            issues.append(
                issue(
                    "warning",
                    "duplicate-rule",
                    locations[0][0],
                    f"Repeated rule at {rendered}: {value}",
                )
            )

    if aggregate_bytes > aggregate_budget:
        issues.append(
            issue(
                "warning",
                "aggregate-budget",
                ".",
                f"Aggregate instruction size is {aggregate_bytes} bytes; configured warning budget is {aggregate_budget}.",
            )
        )

    errors = sum(1 for item in issues if item["level"] == "error")
    warnings = sum(1 for item in issues if item["level"] == "warning")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "instruction_root": str(instruction_root),
        "files": files,
        "summary": {
            "files": len(files),
            "aggregate_bytes": aggregate_bytes,
            "errors": errors,
            "warnings": warnings,
            "valid": errors == 0,
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--instructions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--aggregate-budget", type=int, default=DEFAULT_AGGREGATE_BYTES)
    args = parser.parse_args()
    if not args.repo.is_dir():
        parser.error(f"repository does not exist: {args.repo}")
    if not args.instructions.exists() and not args.instructions.is_symlink():
        parser.error(f"instruction path does not exist: {args.instructions}")

    result = lint(args.repo, args.instructions, args.aggregate_budget)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = result["summary"]
    print(
        f"Instruction lint: {summary['errors']} error(s), {summary['warnings']} warning(s), "
        f"{summary['aggregate_bytes']} bytes"
    )
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
