#!/usr/bin/env python3
"""Compare baseline and candidate packages and enforce bounded static gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from inspect_skill import inspect


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def package_inventory(root: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            result[path.relative_to(root).as_posix()] = {"sha256": f"symlink:{os.readlink(path)}", "bytes": 0}
        elif path.is_file():
            result[path.relative_to(root).as_posix()] = {"sha256": digest(path), "bytes": path.stat().st_size}
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate a bounded Agent Skill candidate against a baseline.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, help="Write JSON report to this path")
    parser.add_argument("--max-changed-files", type=int, default=1)
    parser.add_argument("--max-size-ratio", type=float, default=1.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    if not (baseline / "SKILL.md").is_file() or not (candidate / "SKILL.md").is_file():
        print("error: baseline and candidate must both contain SKILL.md", file=sys.stderr)
        return 2

    before = package_inventory(baseline)
    after = package_inventory(candidate)
    before_paths = set(before)
    after_paths = set(after)
    added = sorted(after_paths - before_paths)
    removed = sorted(before_paths - after_paths)
    modified = sorted(path for path in before_paths & after_paths if before[path]["sha256"] != after[path]["sha256"])
    changed = added + removed + modified
    before_bytes = sum(int(item["bytes"]) for item in before.values())
    after_bytes = sum(int(item["bytes"]) for item in after.values())
    size_ratio = after_bytes / before_bytes if before_bytes else None
    candidate_report = inspect(candidate)

    gates = [
        {
            "id": "candidate-static-errors",
            "passed": candidate_report["counts"]["error"] == 0,
            "evidence": f"{candidate_report['counts']['error']} static error(s)",
        },
        {
            "id": "bounded-files",
            "passed": len(changed) <= args.max_changed_files,
            "evidence": f"{len(changed)} changed file(s), limit {args.max_changed_files}",
        },
        {
            "id": "bounded-size",
            "passed": size_ratio is not None and size_ratio <= args.max_size_ratio,
            "evidence": f"size ratio {size_ratio:.3f}, limit {args.max_size_ratio:.3f}" if size_ratio is not None else "baseline is empty",
        },
    ]
    report = {
        "baseline": str(baseline),
        "candidate": str(candidate),
        "changes": {"added": added, "removed": removed, "modified": modified},
        "size": {"baseline_bytes": before_bytes, "candidate_bytes": after_bytes, "ratio": size_ratio},
        "candidate_inspection": candidate_report,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates),
        "note": "Passing static gates does not prove behavioral improvement.",
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
