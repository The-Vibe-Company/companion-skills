#!/usr/bin/env python3
"""Snapshot repository instruction-file metadata without requiring file contents in output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".turbo",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "plans",
    "target",
    "vendor",
}

ROOT_NAMES = {
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "GEMINI.md",
}

IMPORT_RE = re.compile(r"(?m)^\s*@([^\s]+)\s*$")


def is_instruction_path(path: Path, repo: Path) -> bool:
    rel = path.relative_to(repo)
    if path.name in ROOT_NAMES:
        return True
    posix = rel.as_posix()
    if posix == ".github/copilot-instructions.md":
        return True
    if posix.startswith(".claude/rules/") and path.suffix.lower() == ".md":
        return True
    if posix.startswith(".github/instructions/") and path.name.endswith(
        ".instructions.md"
    ):
        return True
    return False


def iter_instruction_paths(repo: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(repo, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        root_path = Path(root)
        for name in sorted(files):
            path = root_path / name
            if is_instruction_path(path, repo):
                yield path
        for name in sorted(dirs):
            path = root_path / name
            if path.is_symlink() and is_instruction_path(path, repo):
                yield path


def file_record(
    path: Path, repo: Path, include_content: bool = False
) -> dict[str, Any]:
    rel = path.relative_to(repo).as_posix()
    is_symlink = path.is_symlink()
    target = os.readlink(path) if is_symlink else None
    resolved = path.resolve(strict=False)
    resolved_exists = resolved.exists()
    inside_repo = False
    try:
        resolved.relative_to(repo)
        inside_repo = True
    except ValueError:
        pass

    data = b""
    text = ""
    read_error = None
    if resolved_exists and resolved.is_file():
        try:
            data = resolved.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            read_error = str(exc)

    record: dict[str, Any] = {
        "path": rel,
        "scope": path.parent.relative_to(repo).as_posix() or ".",
        "is_symlink": is_symlink,
        "symlink_target": target,
        "resolved_path": (
            resolved.relative_to(repo).as_posix() if inside_repo else str(resolved)
        ),
        "resolved_inside_repo": inside_repo,
        "exists": resolved_exists,
        "bytes": len(data),
        "lines": len(text.splitlines()) if text else 0,
        "sha256": hashlib.sha256(data).hexdigest() if data else None,
        "imports": sorted(set(IMPORT_RE.findall(text))) if text else [],
        "read_error": read_error,
    }
    if include_content and text:
        record["content"] = text
    return record


def snapshot(repo: Path, include_content: bool = False) -> dict[str, Any]:
    repo = repo.resolve()
    files = [
        file_record(path, repo, include_content)
        for path in iter_instruction_paths(repo)
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "include_content": include_content,
        "files": files,
        "summary": {
            "files": len(files),
            "symlinks": sum(1 for item in files if item["is_symlink"]),
            "broken": sum(
                1 for item in files if not item["exists"] or item["read_error"]
            ),
            "aggregate_bytes": sum(item["bytes"] for item in files),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="Repository root")
    parser.add_argument(
        "--out", type=Path, help="Write JSON to this path; stdout when omitted"
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include instruction bodies. Omit this during the cold pass.",
    )
    args = parser.parse_args()

    if not args.repo.is_dir():
        parser.error(f"repository does not exist: {args.repo}")
    result = snapshot(args.repo, args.include_content)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
