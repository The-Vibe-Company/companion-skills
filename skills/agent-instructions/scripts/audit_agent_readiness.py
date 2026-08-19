#!/usr/bin/env python3
"""Audit evidence for repository agent readiness without assigning a numeric score."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from snapshot_instruction_stack import EXCLUDED_DIRS, snapshot

AUTHORITY_PATTERNS = {
    "architecture": re.compile(
        r"(?:^|/)(?:architecture\.md|architecture/|adr/|adrs/)", re.I
    ),
    "design": re.compile(r"(?:^|/)design\.md$|(?:^|/)design/", re.I),
    "product": re.compile(r"(?:^|/)(?:product|prd|vision)(?:[-_/].*)?\.md$", re.I),
    "security": re.compile(r"(?:^|/)(?:security|threat-model)(?:[-_/].*)?\.md$", re.I),
    "reliability": re.compile(
        r"(?:^|/)(?:reliability|operations|runbook)(?:[-_/].*)?\.md$", re.I
    ),
    "testing": re.compile(r"(?:^|/)(?:testing|test-strategy)(?:[-_/].*)?\.md$", re.I),
    "decisions": re.compile(r"(?:^|/)(?:decisions?|adr|adrs)(?:/|[-_].*)", re.I),
}
COMMAND_GROUPS = {
    "setup": {"bootstrap", "install", "prepare", "setup"},
    "start": {"dev", "serve", "start"},
    "build": {"build", "compile"},
    "test": {"check", "ci", "test", "verify"},
    "lint": {"format", "lint", "typecheck", "type-check"},
}
REVIEW_HINT_RE = re.compile(
    r"(?:review[-_ ]?rules?|golden|instructionsloaded|doc[-_ ]?lint)", re.I
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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


def read_text(path: Path, limit: int = 512_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def package_scripts(paths: list[Path], repo: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path in paths:
        if path.name != "package.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        scripts = data.get("scripts")
        if isinstance(scripts, dict):
            rel = path.relative_to(repo).as_posix()
            result[rel] = {
                str(key): str(value) for key, value in sorted(scripts.items())
            }
    return result


def command_evidence(
    package_data: dict[str, dict[str, str]], files: list[str], repo: Path
) -> dict[str, list[str]]:
    evidence = {key: [] for key in COMMAND_GROUPS}
    for manifest, scripts in package_data.items():
        for name in scripts:
            normalized = name.lower()
            for group, hints in COMMAND_GROUPS.items():
                if normalized in hints or any(
                    normalized.startswith(f"{hint}:") for hint in hints
                ):
                    evidence[group].append(f"{manifest}#{name}")

    makefile = repo / "Makefile"
    if makefile.is_file():
        for match in re.finditer(
            r"(?m)^([A-Za-z0-9_.-]+):(?:\s|$)", read_text(makefile)
        ):
            name = match.group(1).lower()
            for group, hints in COMMAND_GROUPS.items():
                if name in hints:
                    evidence[group].append(f"Makefile#{name}")

    for group in evidence:
        evidence[group] = sorted(set(evidence[group]))
    return evidence


def classify_instruction_scope(records: list[dict[str, Any]]) -> dict[str, Any]:
    root_agents = next((item for item in records if item["path"] == "AGENTS.md"), None)
    root_claude = next((item for item in records if item["path"] == "CLAUDE.md"), None)
    nested_agents = [item for item in records if item["path"].endswith("/AGENTS.md")]
    nested_claude = [item for item in records if item["path"].endswith("/CLAUDE.md")]
    claude_scopes = {item["scope"] for item in nested_claude}
    missing_adapters = sorted(
        item["scope"] for item in nested_agents if item["scope"] not in claude_scopes
    )
    adapter = bool(root_claude and "AGENTS.md" in root_claude.get("imports", []))
    return {
        "root_agents": root_agents,
        "root_claude": root_claude,
        "root_claude_imports_agents": adapter,
        "nested_agents_scopes": sorted(item["scope"] for item in nested_agents),
        "nested_claude_scopes": sorted(item["scope"] for item in nested_claude),
        "nested_agents_without_claude_adapter": missing_adapters,
    }


def broken_markdown_links(repo: Path, docs: list[Path]) -> list[dict[str, str]]:
    broken: list[dict[str, str]] = []
    for path in docs:
        text = read_text(path)
        for target in MARKDOWN_LINK_RE.findall(text):
            clean = target.split("#", 1)[0].strip()
            if not clean or clean.startswith(
                ("http://", "https://", "mailto:", "#", "<", "/")
            ):
                continue
            candidate = path.parent / clean
            if not candidate.exists() and not candidate.is_symlink():
                broken.append(
                    {"path": path.relative_to(repo).as_posix(), "target": target}
                )
    return broken[:200]


def dimension(status: str, evidence: list[str], gaps: list[str]) -> dict[str, Any]:
    return {"status": status, "evidence": evidence, "gaps": gaps}


def audit(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    paths = list(iter_files(repo))
    relative = [path.relative_to(repo).as_posix() for path in paths]
    markdown_paths = [path for path in paths if path.suffix.lower() == ".md"]
    link_check_paths = [
        path
        for path in markdown_paths
        if path.relative_to(repo).as_posix().startswith("docs/")
        or path.name
        in {
            "AGENTS.md",
            "ARCHITECTURE.md",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "DESIGN.md",
            "README.md",
            "RELIABILITY.md",
            "SECURITY.md",
            "TESTING.md",
        }
    ]
    instructions = snapshot(repo, include_content=False)
    topology = classify_instruction_scope(instructions["files"])
    packages = package_scripts(paths, repo)
    commands = command_evidence(packages, relative, repo)
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
            part.lower() in {"test", "tests", "spec", "specs", "e2e"}
            for part in Path(path).parts
        )
        or re.search(r"(?:\.test|\.spec)\.[^.]+$|^test_", Path(path).name)
    )
    authorities: dict[str, list[str]] = {}
    for role, pattern in AUTHORITY_PATTERNS.items():
        authorities[role] = sorted(path for path in relative if pattern.search(path))
    design_named_paths = list(authorities["design"])
    docs_design = repo / "docs" / "design.md"
    architecture_label_evidence = (
        read_text(docs_design)[:8000] + "\n" + read_text(repo / "README.md")
    )
    if "docs/design.md" in authorities["design"] and re.search(
        r"(?mi)^#.*\barchitecture\b|\[architecture\]\(docs/design\.md\)",
        architecture_label_evidence,
    ):
        authorities["design"].remove("docs/design.md")
        authorities["architecture"] = sorted(
            set(authorities["architecture"] + ["docs/design.md"])
        )

    findings: list[dict[str, Any]] = []
    if (
        topology["root_agents"]
        and topology["root_claude"]
        and not topology["root_claude_imports_agents"]
    ):
        findings.append(
            {
                "severity": "warning",
                "code": "parallel-root-authorities",
                "message": "Root AGENTS.md and CLAUDE.md exist without an explicit CLAUDE.md import; verify they do not duplicate or conflict.",
            }
        )
    if topology["root_agents"] and topology["root_agents"]["is_symlink"]:
        findings.append(
            {
                "severity": "info",
                "code": "agents-symlink",
                "message": "Root AGENTS.md is a symlink; verify direction, host support, setup scripts, and physical duplicate accounting before migration.",
            }
        )
    if topology["nested_agents_without_claude_adapter"]:
        findings.append(
            {
                "severity": "warning",
                "code": "nested-claude-routing-gap",
                "message": "Nested shared AGENTS.md scopes lack sibling CLAUDE.md adapters; Claude does not read AGENTS.md directly.",
                "scopes": topology["nested_agents_without_claude_adapter"],
            }
        )

    explicit_design_index = False
    index_candidates = [
        repo / "AGENTS.md",
        repo / "README.md",
        repo / "docs" / "README.md",
    ]
    if "DESIGN.md" in design_named_paths and "docs/design.md" in design_named_paths:
        for index in index_candidates:
            text = read_text(index)
            if "DESIGN.md" in text and "docs/design.md" in text:
                explicit_design_index = True
                break
        if not explicit_design_index:
            findings.append(
                {
                    "severity": "warning",
                    "code": "ambiguous-design-authorities",
                    "message": "DESIGN.md and docs/design.md both exist without a detected index distinguishing their roles; verify UI design versus system architecture ownership.",
                    "paths": ["DESIGN.md", "docs/design.md"],
                }
            )
        else:
            findings.append(
                {
                    "severity": "info",
                    "code": "multiple-design-names-disambiguated",
                    "message": "DESIGN.md and docs/design.md have different roles and a detected entry point distinguishes them; consider clearer architecture naming during the next reversible migration.",
                    "paths": ["DESIGN.md", "docs/design.md"],
                }
            )

    broken_links = broken_markdown_links(repo, link_check_paths)
    if broken_links:
        findings.append(
            {
                "severity": "warning",
                "code": "broken-internal-doc-links",
                "message": f"Detected {len(broken_links)} unresolved relative Markdown link(s); verify generated or non-file links manually.",
            }
        )

    readme = "README.md" in relative
    command_groups = [group for group, values in commands.items() if values]
    if readme and {"start", "test"}.issubset(command_groups):
        entry_status = "strong"
        entry_gaps: list[str] = []
    elif readme and command_groups:
        entry_status = "partial"
        entry_gaps = [
            "A documented start/build/test path could not be confirmed from deterministic command sources."
        ]
    else:
        entry_status = "missing"
        entry_gaps = [
            "No complete, deterministic entry and verification path was detected."
        ]

    if (
        topology["root_agents"]
        and topology["root_claude_imports_agents"]
        and not topology["nested_agents_without_claude_adapter"]
    ):
        context_status = "strong"
        context_gaps: list[str] = []
    elif instructions["summary"]["files"]:
        context_status = "partial"
        context_gaps = [
            "Host parity or representative loaded chains still require verification."
        ]
    else:
        context_status = "missing"
        context_gaps = [
            "No repository instruction entry point was detected; confirm whether persistent context is justified."
        ]

    authority_roles = [role for role, values in authorities.items() if values]
    if len(authority_roles) >= 2 and not any(
        item["code"] == "ambiguous-design-authorities" for item in findings
    ):
        authority_status = "strong"
        authority_gaps: list[str] = []
    elif authority_roles or readme:
        authority_status = "partial"
        authority_gaps = [
            "Authority ownership, consumers, executable proof, and re-review triggers require human verification."
        ]
    else:
        authority_status = "missing"
        authority_gaps = [
            "No durable knowledge authority beyond source code was detected."
        ]

    if tests and ci:
        guardrail_status = "strong"
        guardrail_gaps: list[str] = []
    elif tests or ci or commands["lint"]:
        guardrail_status = "partial"
        guardrail_gaps = ["Local checks and CI enforcement are not both evident."]
    else:
        guardrail_status = "missing"
        guardrail_gaps = ["No executable validation guardrail was detected."]

    review_evidence = sorted(
        path
        for path in relative
        if path.endswith("evals/evals.json")
        or path.startswith(".github/instructions/")
        or (
            REVIEW_HINT_RE.search(path)
            and Path(path).suffix.lower()
            in {".md", ".json", ".yaml", ".yml", ".py", ".js", ".mjs", ".ts"}
        )
    )
    if review_evidence and tests:
        review_status = "strong"
        review_gaps: list[str] = []
    elif tests or review_evidence:
        review_status = "partial"
        review_gaps = [
            "Violation, safe, unrelated, and cross-scope review cases were not all confirmed."
        ]
    else:
        review_status = "missing"
        review_gaps = ["No behavioral review evidence was detected."]

    maintenance_evidence = sorted(
        path
        for path in relative
        if re.search(
            r"(?:^|/)(?:CHANGELOG|CONTRIBUTING|CODEOWNERS|docs/README)\.md$", path, re.I
        )
        or re.search(r"(?:doc|link)[-_]?lint", path, re.I)
        or "/adr/" in f"/{path.lower()}/"
    )
    if authorities["decisions"] and any(
        re.search(r"(?:doc|link)[-_]?lint", path, re.I) for path in relative
    ):
        maintenance_status = "strong"
        maintenance_gaps: list[str] = []
    elif maintenance_evidence:
        maintenance_status = "partial"
        maintenance_gaps = [
            "Re-review triggers and instruction garbage collection were not confirmed."
        ]
    else:
        maintenance_status = "missing"
        maintenance_gaps = [
            "No explicit decision history, freshness check, or documentation maintenance path was detected."
        ]

    dimensions = {
        "entry_and_reproducibility": dimension(
            entry_status,
            (["README.md"] if readme else [])
            + [item for values in commands.values() for item in values],
            entry_gaps,
        ),
        "context_routing": dimension(
            context_status,
            [item["path"] for item in instructions["files"]],
            context_gaps,
        ),
        "knowledge_authorities": dimension(
            authority_status,
            [path for values in authorities.values() for path in values],
            authority_gaps,
        ),
        "deterministic_guardrails": dimension(
            guardrail_status,
            ci[:50] + tests[:50] + commands["lint"] + commands["test"],
            guardrail_gaps,
        ),
        "review_quality": dimension(review_status, review_evidence[:100], review_gaps),
        "feedback_and_maintenance": dimension(
            maintenance_status, maintenance_evidence[:100], maintenance_gaps
        ),
    }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "method": "Evidence heuristics for human verification; no aggregate readiness score.",
        "dimensions": dimensions,
        "instruction_topology": topology,
        "authorities": authorities,
        "commands": commands,
        "ci": ci,
        "tests_count": len(tests),
        "broken_markdown_links": broken_links,
        "findings": findings,
    }


def markdown_report(data: dict[str, Any]) -> str:
    lines = [
        "# Agent-readiness audit",
        "",
        f"Repository: `{data['repository']}`",
        "",
        "> This is an evidence-based heuristic audit for human verification. It is not a numeric score or a file checklist.",
        "",
        "## Dimensions",
        "",
        "| Dimension | Status | Evidence | Gaps |",
        "|---|---|---|---|",
    ]
    for name, item in data["dimensions"].items():
        evidence = (
            ", ".join(f"`{value}`" for value in item["evidence"][:8]) or "None detected"
        )
        if len(item["evidence"]) > 8:
            evidence += f"; +{len(item['evidence']) - 8} more"
        gaps = " ".join(item["gaps"]) or "None detected by heuristics"
        lines.append(
            f"| {name.replace('_', ' ').title()} | **{item['status']}** | {evidence} | {gaps} |"
        )

    lines.extend(["", "## Findings", ""])
    if data["findings"]:
        for item in data["findings"]:
            lines.append(
                f"- **{item['severity']} / {item['code']}** — {item['message']}"
            )
    else:
        lines.append("- No topology or authority collision detected by heuristics.")

    lines.extend(["", "## Knowledge authorities", ""])
    for role, paths in data["authorities"].items():
        rendered = ", ".join(f"`{path}`" for path in paths) or "None detected"
        lines.append(f"- **{role}:** {rendered}")

    links = data["broken_markdown_links"]
    lines.extend(["", "## Relative documentation links", ""])
    if links:
        lines.extend(f"- `{item['path']}` → `{item['target']}`" for item in links)
    else:
        lines.append("- No unresolved relative Markdown links detected.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    if not args.repo.is_dir():
        parser.error(f"repository does not exist: {args.repo}")

    result = audit(args.repo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(result), encoding="utf-8")
    print(f"Audited agent readiness for {args.repo} without assigning a score")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
