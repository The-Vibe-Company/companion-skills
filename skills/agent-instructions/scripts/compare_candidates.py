#!/usr/bin/env python3
"""Compare current and proposed instruction stacks using maintainability metrics and rule diffs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lint_instruction_stack import BULLET_RE, iter_instruction_files, normalized_rule


def stack_metrics(root: Path) -> dict[str, Any]:
    files = []
    rules: set[str] = set()
    total_bytes = total_lines = total_words = 0
    if root.exists() or root.is_symlink():
        for path in iter_instruction_files(root.resolve()):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = (
                path.relative_to(root.resolve()).as_posix()
                if root.resolve().is_dir()
                else path.name
            )
            raw = text.encode("utf-8")
            lines = text.splitlines()
            words = re.findall(r"\b\w+\b", text, re.UNICODE)
            for line in lines:
                match = BULLET_RE.match(line)
                if match:
                    value = normalized_rule(match.group(1))
                    if len(value) >= 24:
                        rules.add(value)
            files.append(
                {
                    "path": rel,
                    "bytes": len(raw),
                    "lines": len(lines),
                    "words": len(words),
                }
            )
            total_bytes += len(raw)
            total_lines += len(lines)
            total_words += len(words)
    return {
        "files": files,
        "summary": {
            "files": len(files),
            "bytes": total_bytes,
            "lines": total_lines,
            "words": total_words,
            "normalized_rules": len(rules),
        },
        "rules": sorted(rules),
    }


def percent_change(before: int, after: int) -> float | None:
    if before == 0:
        return None
    return round((after - before) / before * 100, 2)


def compare(current: Path, proposed: Path) -> dict[str, Any]:
    before = stack_metrics(current)
    after = stack_metrics(proposed)
    old_rules = set(before["rules"])
    new_rules = set(after["rules"])
    deltas = {
        key: {
            "absolute": after["summary"][key] - before["summary"][key],
            "percent": percent_change(before["summary"][key], after["summary"][key]),
        }
        for key in ("files", "bytes", "lines", "words", "normalized_rules")
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current": before,
        "proposed": after,
        "deltas": deltas,
        "rule_diff": {
            "retained": sorted(old_rules & new_rules),
            "removed": sorted(old_rules - new_rules),
            "added": sorted(new_rules - old_rules),
        },
        "caveat": "Static reduction does not prove behavioral improvement.",
    }


def markdown(data: dict[str, Any]) -> str:
    before = data["current"]["summary"]
    after = data["proposed"]["summary"]
    lines = [
        "# Instruction candidate comparison",
        "",
        "| Metric | Current | Proposed | Change |",
        "|---|---:|---:|---:|",
    ]
    for key in ("files", "bytes", "lines", "words", "normalized_rules"):
        delta = data["deltas"][key]
        percent = "n/a" if delta["percent"] is None else f"{delta['percent']:+.2f}%"
        lines.append(
            f"| {key} | {before[key]} | {after[key]} | {delta['absolute']:+d} ({percent}) |"
        )
    lines.extend(
        [
            "",
            "## Rule-set summary",
            "",
            f"- Retained: {len(data['rule_diff']['retained'])}",
            f"- Removed: {len(data['rule_diff']['removed'])}",
            f"- Added: {len(data['rule_diff']['added'])}",
            "",
            "> Static reduction does not prove behavioral improvement.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--proposed", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="JSON output")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown output")
    args = parser.parse_args()

    data = compare(args.current, args.proposed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(data) + "\n", encoding="utf-8")
    print(f"Compared {args.current} with {args.proposed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
