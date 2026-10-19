#!/usr/bin/env python3
"""Analyze Codex and Claude conversation history for skill improvement signals.

The script is intentionally local-only: it reads conversation metadata/logs from
the user's machine and writes bounded evidence artifacts to an output directory.
It never edits a skill directly.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


SYSTEM_BLOCK_RE = re.compile(
    r"<(?:system_instruction|permissions instructions|app-context|skills_instructions|plugins_instructions|collaboration_mode)[^>]*>.*?</(?:system_instruction|permissions instructions|app-context|skills_instructions|plugins_instructions|collaboration_mode)>",
    re.DOTALL | re.IGNORECASE,
)
TAG_RE = re.compile(r"</?[\w:-]+[^>]*>")
SPACE_RE = re.compile(r"\s+")
NOISE_PATTERNS = [
    re.compile(r"^# AGENTS\.md instructions\b", re.I),
    re.compile(r"--- project-doc ---", re.I),
    re.compile(r"^Automation:\s", re.I),
    re.compile(r"^You are installing the Companion skill\b", re.I),
    re.compile(r"Authorization header:\s*Bearer\b", re.I),
    re.compile(r"^Base directory for this skill\b", re.I),
    re.compile(r"^Respond directly to the user's prompt\. Do not run shell commands\b", re.I),
    re.compile(r"^You are generating a short conversation title\b", re.I),
    re.compile(r"^You are working inside Conductor\b", re.I),
    re.compile(r"^# Codex desktop context\b", re.I),
]

SIGNAL_PATTERNS = {
    "trigger_or_routing": [
        r"undertrigger",
        r"overtrigger",
        r"trigger(?:ed|ing)?",
        r"d(?:id|oes)n['’]?t trigger",
        r"wrong skill",
        r"mauvais skill",
        r"pas d[eé]clench",
        r"d[eé]clench(?:e|er)? pas",
        r"should have used",
        r"aurait d[uû] utiliser",
    ],
    "failure_or_blocker": [
        r"\berror\b",
        r"\bfailed\b",
        r"\bfail(?:ed|ing|ure)?\b",
        r"traceback",
        r"exception",
        r"\bblocked\b",
        r"cannot",
        r"can't",
        r"could not",
        r"impossible",
        r"bloqu",
        r"[eé]chec",
        r"erreur",
    ],
    "user_correction": [
        r"\bnon\b",
        r"attention",
        r"corrige",
        r"plut[oô]t",
        r"pas [cç]a",
        r"oublie",
        r"j['’]?aimerais",
        r"ajoute",
        r"supprime",
        r"retire",
        r"instead",
    ],
    "packaging_or_setup": [
        r"companion",
        r"publish",
        r"publie",
        r"upload",
        r"setup\.sh",
        r"dependency",
        r"d[eé]pendance",
        r"validate",
        r"validation",
        r"manifest",
    ],
}


@dataclass
class Message:
    role: str
    text: str


@dataclass
class SessionHit:
    source: str
    session_id: str
    date: str
    title: str = ""
    cwd: str = ""
    path: str = ""
    skill_hits: Counter = field(default_factory=Counter)
    signal_hits: Counter = field(default_factory=Counter)
    snippets: list[dict] = field(default_factory=list)


def clean_text(value: str, limit: int | None = None) -> str:
    value = SYSTEM_BLOCK_RE.sub(" ", value or "")
    value = TAG_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value).strip()
    if limit and len(value) > limit:
        return value[: limit - 1].rstrip() + "..."
    return value


def is_context_noise(value: str) -> bool:
    text = clean_text(value)
    if not text:
        return True
    if any(pattern.search(text) for pattern in NOISE_PATTERNS):
        return True
    if len(text) > 2500 and ("SKILL.md" in text and "allowed-tools" in text):
        return True
    return False


def parse_ts_date(value: str | None) -> str:
    if not value:
        return ""
    return value[:10]


def ms_days_ago(days: int) -> int:
    return int((time.time() - days * 86400) * 1000)


def skill_aliases(skills: Iterable[str]) -> set[str]:
    aliases: set[str] = set()
    for skill in skills:
        raw = skill.strip()
        if not raw:
            continue
        forms = {raw, raw.lower(), raw.replace("_", "-"), raw.replace("-", "_")}
        for form in list(forms):
            if ":" in form:
                forms.add(form.split(":")[-1])
            if form.startswith("vibe_"):
                forms.add(form[5:])
            if form.startswith("vibe-"):
                forms.add(form[5:])
        aliases.update(f.lower() for f in forms if f)
    return aliases


def dedupe_messages(messages: list[Message]) -> list[Message]:
    seen: set[tuple[str, str]] = set()
    out: list[Message] = []
    for message in messages:
        key = (message.role, clean_text(message.text).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(message)
    return out


def alias_regexes(aliases: set[str]) -> list[re.Pattern]:
    out = []
    for alias in sorted(aliases, key=len, reverse=True):
        escaped = re.escape(alias)
        out.append(re.compile(rf"(?<![a-z0-9_-])/?{escaped}(?![a-z0-9_-])", re.I))
    return out


def signal_regexes() -> dict[str, list[re.Pattern]]:
    return {
        name: [re.compile(pattern, re.I) for pattern in patterns]
        for name, patterns in SIGNAL_PATTERNS.items()
    }


def extract_content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"text", "input_text", "output_text"}:
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return ""


def read_jsonl(path: Path):
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def codex_messages_from_rollout(path: Path) -> tuple[list[Message], str, str]:
    messages: list[Message] = []
    title = ""
    cwd = ""
    for row in read_jsonl(path):
        typ = row.get("type")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if typ == "session_meta":
            meta = payload
            cwd = str(meta.get("cwd") or cwd)
            continue
        if typ == "response_item":
            role = payload.get("role")
            item_type = payload.get("type")
            if item_type == "message" and role in {"user", "assistant"}:
                text = clean_text(extract_content_text(payload.get("content")))
                if text and not is_context_noise(text):
                    messages.append(Message(role=role, text=text))
                    if role == "user" and not title:
                        title = clean_text(text, 120)
        elif typ == "event_msg":
            if payload.get("type") == "agent_message":
                text = clean_text(str(payload.get("message") or ""))
                if text and not is_context_noise(text):
                    messages.append(Message(role="assistant", text=text))
    return messages, title, cwd


def load_codex_threads(codex_home: Path, days: int, max_sessions: int) -> list[dict]:
    db_candidates = [codex_home / "state_5.sqlite", codex_home / "sqlite" / "state_5.sqlite"]
    db_path = next((path for path in db_candidates if path.exists()), None)
    if not db_path:
        return []
    cutoff = ms_days_ago(days)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            select id, rollout_path, title, first_user_message, preview, cwd, updated_at_ms
            from threads
            where coalesce(updated_at_ms, updated_at, created_at_ms, created_at) >= ?
            order by coalesce(updated_at_ms, updated_at, created_at_ms, created_at) desc
            limit ?
            """,
            (cutoff, max_sessions),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def claude_messages_from_jsonl(path: Path) -> tuple[list[Message], str, str, str]:
    messages: list[Message] = []
    title = ""
    cwd = ""
    date = ""
    for row in read_jsonl(path):
        if not date:
            date = parse_ts_date(row.get("timestamp"))
        if not cwd and row.get("cwd"):
            cwd = str(row.get("cwd"))
        typ = row.get("type")
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        if typ == "user" and message.get("role") == "user":
            text = clean_text(extract_content_text(message.get("content")))
            if text and not is_context_noise(text):
                messages.append(Message(role="user", text=text))
                if not title:
                    title = clean_text(text, 120)
        elif typ == "assistant" and message.get("role") == "assistant":
            text = clean_text(extract_content_text(message.get("content")))
            if text and not is_context_noise(text):
                messages.append(Message(role="assistant", text=text))
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        name = item.get("name")
                        inp = item.get("input")
                        if name == "Skill":
                            skill = inp.get("skill") if isinstance(inp, dict) else ""
                            messages.append(Message(role="tool", text=f"Skill {skill}"))
    return messages, title, cwd, date


def iter_claude_paths(projects_dir: Path, days: int, max_sessions: int) -> list[Path]:
    if not projects_dir.exists():
        return []
    cutoff = time.time() - days * 86400
    paths = []
    for path in projects_dir.glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime >= cutoff:
                paths.append(path)
        except OSError:
            continue
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[:max_sessions]


def classify_session(
    source: str,
    session_id: str,
    date: str,
    title: str,
    cwd: str,
    path: str,
    messages: list[Message],
    alias_patterns: list[re.Pattern],
    sig_patterns: dict[str, list[re.Pattern]],
    max_snippets: int,
) -> SessionHit | None:
    messages = dedupe_messages([message for message in messages if not is_context_noise(message.text)])
    report_title = "" if is_context_noise(title) else title
    joined = "\n".join([report_title, *(m.text for m in messages)])
    skill_counts = Counter()
    for pattern in alias_patterns:
        matches = pattern.findall(joined)
        if matches:
            skill_counts[pattern.pattern] += len(matches)
    if not skill_counts:
        return None

    hit = SessionHit(source=source, session_id=session_id, date=date, title=report_title, cwd=cwd, path=path)
    hit.skill_hits = skill_counts

    skill_message_indexes = [
        idx for idx, message in enumerate(messages) if any(pattern.search(message.text) for pattern in alias_patterns)
    ]
    relevant_indexes: set[int] = set()
    for idx in skill_message_indexes:
        relevant_indexes.update(range(max(0, idx - 2), min(len(messages), idx + 7)))
    if not relevant_indexes and any(pattern.search(report_title) for pattern in alias_patterns):
        relevant_indexes.update(range(min(len(messages), 6)))

    snippet_keys: set[str] = set()
    for idx, message in enumerate(messages):
        if idx not in relevant_indexes:
            continue
        text = message.text
        if not text:
            continue
        msg_signals = []
        for signal, patterns in sig_patterns.items():
            if any(pattern.search(text) for pattern in patterns):
                hit.signal_hits[signal] += 1
                msg_signals.append(signal)
        skill_mentioned = any(pattern.search(text) for pattern in alias_patterns)
        if (skill_mentioned or msg_signals) and len(hit.snippets) < max_snippets:
            snippet_key = clean_text(text, 180).lower()
            if snippet_key in snippet_keys:
                continue
            snippet_keys.add(snippet_key)
            hit.snippets.append(
                {
                    "role": message.role,
                    "signals": msg_signals,
                    "skill_mentioned": bool(skill_mentioned),
                    "text": clean_text(text, 700),
                }
            )
    return hit


def collect_hits(args) -> list[SessionHit]:
    aliases = skill_aliases(args.skill)
    alias_patterns = alias_regexes(aliases)
    sig_patterns = signal_regexes()
    hits: list[SessionHit] = []

    if "codex" in args.source:
        for row in load_codex_threads(args.codex_home, args.days, args.max_sessions):
            rollout = Path(row.get("rollout_path") or "")
            messages, rollout_title, rollout_cwd = codex_messages_from_rollout(rollout) if rollout.exists() else ([], "", "")
            title = clean_text(row.get("title") or row.get("first_user_message") or row.get("preview") or rollout_title, 140)
            cwd = str(row.get("cwd") or rollout_cwd or "")
            date = ""
            if row.get("updated_at_ms"):
                date = time.strftime("%Y-%m-%d", time.localtime(int(row["updated_at_ms"]) / 1000))
            seed_text = clean_text("\n".join([str(row.get("first_user_message") or ""), str(row.get("preview") or "")]))
            if seed_text and not is_context_noise(seed_text):
                messages.insert(0, Message(role="user", text=seed_text))
            hit = classify_session(
                "codex",
                str(row.get("id") or rollout.stem),
                date,
                title,
                cwd,
                str(rollout),
                messages,
                alias_patterns,
                sig_patterns,
                args.max_snippets,
            )
            if hit:
                hits.append(hit)

    if "claude" in args.source:
        for path in iter_claude_paths(args.claude_projects, args.days, args.max_sessions):
            messages, title, cwd, date = claude_messages_from_jsonl(path)
            hit = classify_session(
                "claude",
                path.stem,
                date,
                title,
                cwd,
                str(path),
                messages,
                alias_patterns,
                sig_patterns,
                args.max_snippets,
            )
            if hit:
                hits.append(hit)

    hits.sort(key=lambda h: (h.date, h.source, h.session_id), reverse=True)
    return hits


def render_usage_evidence(hits: list[SessionHit], args) -> str:
    signal_totals = Counter()
    source_totals = Counter()
    for hit in hits:
        signal_totals.update(hit.signal_hits)
        source_totals[hit.source] += 1

    lines = [
        "# Skill Usage Evidence",
        "",
        f"- Target skills: {', '.join(args.skill)}",
        f"- Sources: {', '.join(args.source)}",
        f"- Window: last {args.days} days",
        f"- Matched sessions: {len(hits)}",
        "",
        "## Source Counts",
    ]
    if source_totals:
        for source, count in source_totals.most_common():
            lines.append(f"- `{source}`: {count}")
    else:
        lines.append("- No matching sessions found.")

    lines.extend(["", "## Signal Counts"])
    if signal_totals:
        for signal, count in signal_totals.most_common():
            lines.append(f"- `{signal}`: {count}")
    else:
        lines.append("- No problem signals found in matched sessions.")

    lines.extend(["", "## Matched Sessions"])
    for hit in hits[: args.max_report_sessions]:
        lines.append(f"### {hit.date or 'unknown-date'} | {hit.source} | {hit.title or hit.session_id}")
        if hit.cwd:
            lines.append(f"- cwd: `{hit.cwd}`")
        if hit.path:
            lines.append(f"- path: `{hit.path}`")
        if hit.signal_hits:
            lines.append("- signals: " + ", ".join(f"`{k}` x{v}" for k, v in hit.signal_hits.items()))
        for snippet in hit.snippets[: args.max_snippets]:
            signal_label = ", ".join(snippet["signals"]) if snippet["signals"] else "skill mention"
            lines.append(f"- {snippet['role']} ({signal_label}): {snippet['text']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_frictions(hits: list[SessionHit]) -> str:
    signal_totals = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for hit in hits:
        signal_totals.update(hit.signal_hits)
        for snippet in hit.snippets:
            for signal in snippet["signals"]:
                if len(examples[signal]) < 5:
                    examples[signal].append(snippet["text"])

    lines = ["# Usage-Derived Frictions", ""]
    if not hits:
        lines.append("No matching usage history was found for the selected skill.")
        return "\n".join(lines) + "\n"
    if not signal_totals:
        lines.append("Matched sessions mention the skill, but no configured problem signals were detected.")
        return "\n".join(lines) + "\n"

    recommendations = {
        "trigger_or_routing": "Review the frontmatter description and add near-miss trigger evals.",
        "failure_or_blocker": "Add troubleshooting, dependency checks, or clearer fallback behavior.",
        "user_correction": "Extract the correction as an invariant, artifact contract, or eval case.",
        "packaging_or_setup": "Clarify Companion, setup, dependency, or publishing workflow docs.",
    }
    for signal, count in signal_totals.most_common():
        lines.append(f"## {signal}")
        lines.append(f"- Occurrences: {count}")
        lines.append(f"- Suggested response: {recommendations.get(signal, 'Review the matching snippets before editing.')}")
        for idx, example in enumerate(examples.get(signal, [])[:3], start=1):
            lines.append(f"- Example {idx}: {example}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_proposal(hits: list[SessionHit], args) -> str:
    signal_totals = Counter()
    for hit in hits:
        signal_totals.update(hit.signal_hits)
    lines = [
        "# Skill Update Proposal From Usage History",
        "",
        "## Recommendation",
    ]
    if not hits:
        lines.append("Do not patch the skill yet. No matching sessions were found for the selected skill and time window.")
    elif not signal_totals:
        lines.append("No urgent patch is supported by the detected evidence. Consider adding positive examples to evals instead of changing behavior.")
    else:
        lines.append("Use a bounded SkillOpt-light pass: pick one target file, state one hypothesis from the evidence, patch narrowly, then validate with held-out prompts.")

    lines.extend(["", "## Evidence-Backed Patch Ideas"])
    if signal_totals.get("trigger_or_routing"):
        lines.append("- Add or tune trigger evals and frontmatter wording for the observed routing misses.")
    if signal_totals.get("failure_or_blocker"):
        lines.append("- Add a troubleshooting or preflight section for the most common blocker.")
    if signal_totals.get("user_correction"):
        lines.append("- Convert repeated user corrections into protected invariants or output contract language.")
    if signal_totals.get("packaging_or_setup"):
        lines.append("- Tighten Companion/setup/dependency instructions and add a package-readiness check.")
    if not signal_totals:
        lines.append("- No patch idea met the evidence threshold.")

    lines.extend(
        [
            "",
            "## Suggested Validation",
            "1. Turn 2-3 representative snippets into sanitized eval prompts.",
            "2. Keep 1-2 matched snippets held out for acceptance.",
            "3. Compare the patched skill against the current baseline.",
            "4. Accept only if the held-out prompts improve or a concrete correctness bug is fixed.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Codex and Claude conversation history for skill usage evidence.")
    parser.add_argument("--skill", action="append", required=True, help="Skill slug/name to analyze. Can be repeated.")
    parser.add_argument("--source", action="append", choices=["codex", "claude"], default=None, help="History source. Defaults to both.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-sessions", type=int, default=300)
    parser.add_argument("--max-report-sessions", type=int, default=30)
    parser.add_argument("--max-snippets", type=int, default=4)
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--claude-projects", type=Path, default=Path(os.environ.get("CLAUDE_PROJECTS_DIR", Path.home() / ".claude" / "projects")))
    parser.add_argument("--out", type=Path, help="Output run directory. Defaults to plans/skill-creator/runs/<timestamp>-usage-history.")
    args = parser.parse_args()
    if args.source is None:
        args.source = ["codex", "claude"]
    if args.out is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        args.out = Path("plans") / "skill-creator" / "runs" / f"{stamp}-usage-history"
    args.out.mkdir(parents=True, exist_ok=True)

    hits = collect_hits(args)
    (args.out / "usage-evidence.md").write_text(render_usage_evidence(hits, args), encoding="utf-8")
    (args.out / "frictions.md").write_text(render_frictions(hits), encoding="utf-8")
    (args.out / "proposal.md").write_text(render_proposal(hits, args), encoding="utf-8")
    (args.out / "usage-summary.json").write_text(
        json.dumps(
            {
                "skills": args.skill,
                "sources": args.source,
                "days": args.days,
                "matched_sessions": len(hits),
                "signal_counts": dict(sum((Counter(h.signal_hits) for h in hits), Counter())),
                "output_dir": str(args.out),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(args.out)


if __name__ == "__main__":
    main()
