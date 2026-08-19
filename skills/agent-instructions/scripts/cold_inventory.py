#!/usr/bin/env python3
"""Inventory repository evidence without emitting instruction-file bodies."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from snapshot_instruction_stack import EXCLUDED_DIRS, snapshot

MANIFEST_NAMES = {
    "Cargo.toml",
    "Gemfile",
    "Makefile",
    "Taskfile.yml",
    "bun.lock",
    "composer.json",
    "deno.json",
    "docker-compose.yml",
    "go.mod",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "turbo.json",
    "uv.lock",
    "yarn.lock",
}

DOC_NAMES = {
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "DESIGN.md",
    "PRODUCT.md",
    "README.md",
    "RELIABILITY.md",
    "SECURITY.md",
    "TESTING.md",
}


def iter_files(repo: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(repo, followlinks=False):
        root_path = Path(root)
        tool_skill_parents = {
            ".agent",
            ".agents",
            ".claude",
            ".cline",
            ".codex",
            ".cursor",
            ".gemini",
            ".github",
        }
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in EXCLUDED_DIRS
            and not (root_path.name in tool_skill_parents and d == "skills")
        )
        for name in sorted(files):
            path = root_path / name
            if not path.is_symlink():
                yield path


def git_value(repo: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()


def package_scripts(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in sorted(scripts.items())}


def build_inventory(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    files = list(iter_files(repo))
    relative = [path.relative_to(repo).as_posix() for path in files]
    manifests = sorted(path for path in relative if Path(path).name in MANIFEST_NAMES)
    docs = sorted(
        path
        for path in relative
        if Path(path).name in DOC_NAMES
        or (path.startswith("docs/") and path.endswith(".md"))
    )
    ci = sorted(
        path
        for path in relative
        if path.startswith(".github/workflows/")
        or path in {".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"}
    )
    tests = sorted(
        path
        for path in relative
        if any(
            part in {"test", "tests", "spec", "specs", "e2e"}
            for part in Path(path).parts
        )
        or Path(path).name.startswith("test_")
        or any(
            Path(path).name.endswith(suffix)
            for suffix in (".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")
        )
    )
    scripts = sorted(
        path
        for path in relative
        if "scripts" in Path(path).parts
        or Path(path).name in {"Makefile", "Taskfile.yml"}
    )
    packages: dict[str, dict[str, str]] = {}
    for manifest in manifests:
        if Path(manifest).name == "package.json":
            found = package_scripts(repo / manifest)
            if found:
                packages[manifest] = found

    extensions = Counter()
    for path in relative:
        suffix = Path(path).suffix.lower() or "[none]"
        extensions[suffix] += 1

    top_level = sorted(entry.name for entry in repo.iterdir() if entry.name != ".git")
    instruction_snapshot = snapshot(repo, include_content=False)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "git": {
            "branch": git_value(repo, ["branch", "--show-current"]),
            "commit": git_value(repo, ["rev-parse", "HEAD"]),
            "status": (git_value(repo, ["status", "--short"]) or "").splitlines(),
        },
        "top_level": top_level,
        "manifests": manifests,
        "package_scripts": packages,
        "ci": ci,
        "documentation": docs,
        "scripts": scripts,
        "tests": tests,
        "file_counts_by_extension": dict(sorted(extensions.items())),
        "instruction_metadata": instruction_snapshot,
        "cold_pass_note": "Instruction bodies were not included in this inventory.",
    }


def markdown_report(data: dict[str, Any]) -> str:
    git = data["git"]
    instruction_summary = data["instruction_metadata"]["summary"]
    lines = [
        "# Cold repository inventory",
        "",
        f"Repository: `{data['repository']}`",
        f"Branch: `{git['branch'] or 'unknown'}`",
        f"Commit: `{git['commit'] or 'unknown'}`",
        f"Dirty paths: {len(git['status'])}",
        "",
        "> Instruction bodies were intentionally excluded from this pass.",
        "",
        "## Instruction metadata",
        "",
        f"- Files: {instruction_summary['files']}",
        f"- Symlinks: {instruction_summary['symlinks']}",
        f"- Broken or unreadable: {instruction_summary['broken']}",
        f"- Aggregate bytes: {instruction_summary['aggregate_bytes']}",
        "",
    ]
    for heading, key in (
        ("Manifests", "manifests"),
        ("CI", "ci"),
        ("Documentation", "documentation"),
        ("Repository scripts", "scripts"),
        ("Tests", "tests"),
    ):
        values = data[key]
        lines.extend([f"## {heading}", ""])
        if values:
            lines.extend(f"- `{value}`" for value in values[:200])
            if len(values) > 200:
                lines.append(f"- … {len(values) - 200} more")
        else:
            lines.append("- None detected")
        lines.append("")
    lines.extend(["## Package scripts", ""])
    if data["package_scripts"]:
        for manifest, scripts in data["package_scripts"].items():
            lines.append(f"### `{manifest}`")
            lines.append("")
            lines.extend(
                f"- `{name}` — `{command}`" for name, command in scripts.items()
            )
            lines.append("")
    else:
        lines.extend(["- None detected", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="JSON output path")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown output path")
    args = parser.parse_args()
    if not args.repo.is_dir():
        parser.error(f"repository does not exist: {args.repo}")

    data = build_inventory(args.repo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(data) + "\n", encoding="utf-8")
    print(f"Wrote cold inventory for {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
