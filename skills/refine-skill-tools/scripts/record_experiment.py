#!/usr/bin/env python3
"""Append one refinement experiment to JSONL and TSV ledgers."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUSES = {"keep", "discard", "crash", "inconclusive"}
TSV_FIELDS = [
    "timestamp",
    "iteration",
    "status",
    "target_file",
    "baseline_result",
    "candidate_result",
    "evaluation_mode",
    "hypothesis",
    "reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record one Skill Refinery experiment.")
    parser.add_argument("run", type=Path, help="Run directory containing run.json")
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--status", choices=sorted(STATUSES), required=True)
    parser.add_argument("--target-file", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--baseline-result", required=True)
    parser.add_argument("--candidate-result", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--evaluation-mode",
        choices=("benchmark", "sanity_check", "static_only"),
        default="benchmark",
    )
    parser.add_argument("--patch-summary", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run.expanduser().resolve()
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        print(f"error: missing run manifest: {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    decisions_path = run_dir / "decisions.jsonl"
    existing_iterations: set[int] = set()
    if decisions_path.exists():
        for line in decisions_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing_iterations.add(int(json.loads(line)["iteration"]))
            except (ValueError, KeyError, json.JSONDecodeError):
                print("error: decisions.jsonl contains an invalid record", file=sys.stderr)
                return 2
    if args.iteration in existing_iterations:
        print(f"error: iteration {args.iteration} is already recorded", file=sys.stderr)
        return 2

    promoted_path: str | None = None
    if args.status == "keep":
        candidate = run_dir / str(manifest.get("candidate_snapshot", "candidate/skill"))
        if not (candidate / "SKILL.md").is_file():
            print(f"error: candidate snapshot is missing: {candidate}", file=sys.stderr)
            return 2
        destination = run_dir / "best" / f"candidate-{args.iteration}"
        if destination.exists():
            print(f"error: promotion destination already exists: {destination}", file=sys.stderr)
            return 2
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate, destination, symlinks=True)
        promoted_path = destination.relative_to(run_dir).as_posix()

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "timestamp": timestamp,
        "iteration": args.iteration,
        "status": args.status,
        "target_file": args.target_file,
        "hypothesis": args.hypothesis,
        "patch_summary": args.patch_summary,
        "baseline_result": args.baseline_result,
        "candidate_result": args.candidate_result,
        "evaluation_mode": args.evaluation_mode,
        "decision": "accepted" if args.status == "keep" else "rejected" if args.status in {"discard", "crash"} else "inconclusive",
        "reason": args.reason,
    }
    if promoted_path:
        record["promoted_snapshot"] = promoted_path
    with decisions_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    tsv_path = run_dir / "results.tsv"
    write_header = not tsv_path.exists() or tsv_path.stat().st_size == 0
    with tsv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_FIELDS, delimiter="\t", extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(record)

    manifest["iteration"] = max(int(manifest.get("iteration", 0)), args.iteration)
    manifest["evaluation_mode"] = args.evaluation_mode
    if promoted_path:
        manifest["current_best"] = promoted_path
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
