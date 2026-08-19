#!/usr/bin/env python3
"""Trace repository instruction discovery candidates for a representative path."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def directories(repo: Path, target: Path) -> list[Path]:
    resolved = target.resolve()
    if resolved.is_file():
        resolved = resolved.parent
    try:
        rel = resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"target is outside repository: {target}") from exc
    chain = [repo]
    current = repo
    for part in rel.parts:
        current = current / part
        chain.append(current)
    return chain


def record(path: Path, repo: Path, reason: str) -> dict[str, str]:
    return {"path": path.relative_to(repo).as_posix(), "reason": reason}


def trace_codex(
    repo: Path, chain: list[Path], fallbacks: list[str]
) -> tuple[list[dict[str, str]], list[str]]:
    loaded: list[dict[str, str]] = []
    for directory in chain:
        names = ["AGENTS.override.md", "AGENTS.md", *fallbacks]
        for name in names:
            candidate = directory / name
            if candidate.is_file() or candidate.is_symlink():
                loaded.append(
                    record(
                        candidate,
                        repo,
                        f"first supported file in {directory.relative_to(repo).as_posix() or '.'}",
                    )
                )
                break
    notes = [
        "Models the project chain at run start from repository root to startup working directory.",
        "Editing a deeper path later does not by itself add that directory to this regular chain.",
    ]
    return loaded, notes


def trace_claude(
    repo: Path, chain: list[Path]
) -> tuple[list[dict[str, str]], list[str]]:
    loaded: list[dict[str, str]] = []
    for directory in chain:
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            candidate = directory / name
            if candidate.is_file() or candidate.is_symlink():
                loaded.append(
                    record(
                        candidate,
                        repo,
                        "project memory candidate on ancestor/startup chain",
                    )
                )
    notes = [
        "Models project-level ancestor/startup candidates only; managed and user memory are outside repository scope.",
        "Child CLAUDE.md files are discovered on demand when Claude reads that subtree and may need rediscovery after compaction.",
        "Use InstructionsLoaded or /context when exact runtime loading is consequential.",
    ]
    return loaded, notes


def trace_copilot(
    repo: Path, chain: list[Path]
) -> tuple[list[dict[str, str]], list[str]]:
    loaded: list[dict[str, str]] = []
    seen: set[Path] = set()
    for directory in chain:
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            candidate = directory / name
            if (
                candidate.is_file() or candidate.is_symlink()
            ) and candidate not in seen:
                seen.add(candidate)
                loaded.append(
                    record(candidate, repo, "Copilot CLI discovery candidate")
                )
    repository_wide = repo / ".github" / "copilot-instructions.md"
    if repository_wide.is_file():
        loaded.append(
            record(repository_wide, repo, "repository-wide Copilot instruction")
        )
    path_rules = repo / ".github" / "instructions"
    if path_rules.is_dir():
        for candidate in sorted(path_rules.glob("*.instructions.md")):
            loaded.append(
                record(
                    candidate,
                    repo,
                    "path-specific candidate; applyTo matching not evaluated",
                )
            )
    notes = [
        "GitHub support varies by Copilot surface.",
        "No general precedence across all instruction families is modeled; remove conflicts instead of relying on a winner.",
        "Inspect applyTo frontmatter before treating a path-specific candidate as loaded.",
    ]
    return loaded, notes


def trace(
    repo: Path, target: Path, host: str, fallbacks: list[str] | None = None
) -> dict[str, Any]:
    repo = repo.resolve()
    chain = directories(repo, target)
    if host == "codex":
        loaded, notes = trace_codex(repo, chain, fallbacks or [])
    elif host == "claude":
        loaded, notes = trace_claude(repo, chain)
    else:
        loaded, notes = trace_copilot(repo, chain)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "target": str(target.resolve()),
        "host": host,
        "directories": [
            directory.relative_to(repo).as_posix() or "." for directory in chain
        ],
        "instruction_candidates": loaded,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Representative startup directory or worked file",
    )
    parser.add_argument("--host", choices=("codex", "claude", "copilot"), required=True)
    parser.add_argument(
        "--fallback",
        action="append",
        default=[],
        help="Additional Codex fallback filename",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not args.repo.is_dir():
        parser.error(f"repository does not exist: {args.repo}")
    target = args.path if args.path.is_absolute() else args.repo / args.path
    if not target.exists():
        parser.error(f"representative path does not exist: {target}")
    try:
        result = trace(args.repo, target, args.host, args.fallback)
    except ValueError as exc:
        parser.error(str(exc))
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
