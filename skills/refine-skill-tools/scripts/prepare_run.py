#!/usr/bin/env python3
"""Create an isolated, non-destructive Skill Refinery run workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            files[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_file():
            files[relative] = sha256(path)
    return files


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    return value or "skill"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Snapshot an Agent Skill into an isolated refinement run."
    )
    parser.add_argument("skill", type=Path, help="Directory containing SKILL.md")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".skill-refinery/runs"),
        help="Parent directory for run workspaces (default: .skill-refinery/runs)",
    )
    parser.add_argument("--run-id", help="Optional explicit run identifier")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.skill.expanduser().resolve()
    skill_file = source / "SKILL.md"
    if not source.is_dir() or not skill_file.is_file():
        print(f"error: {source} must be a directory containing SKILL.md", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    run_id = args.run_id or f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slugify(source.name)}"
    output_root = args.output_root.expanduser().resolve()
    run_dir = output_root / run_id
    if run_dir.exists():
        print(f"error: run directory already exists: {run_dir}", file=sys.stderr)
        return 2

    baseline = run_dir / "baseline" / "skill"
    candidate = run_dir / "candidate" / "skill"
    baseline.parent.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, baseline, symlinks=True)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, candidate, symlinks=True)

    for relative in (
        "best",
        "evaluations/tuning",
        "evaluations/held-out",
        "outputs/baseline",
        "outputs/candidate",
        "judgments",
    ):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "source_skill": str(source),
        "baseline_snapshot": "baseline/skill",
        "candidate_snapshot": "candidate/skill",
        "current_best": "baseline",
        "iteration": 0,
        "evaluation_mode": "static_only",
        "baseline_inventory": inventory(baseline),
    }
    (run_dir / "run.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "decisions.jsonl").touch()

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
