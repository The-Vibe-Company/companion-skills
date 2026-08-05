#!/usr/bin/env python3
"""Registre local atomique pour le cron de veille des pull requests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_STATE = Path(os.environ.get("HERMES_HOME", "/Users/fred/.hermes")) / "state/veille-pr.json"
CLAIM_TTL = dt.timedelta(hours=2)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def pr_key(repo: str, number: int) -> str:
    return f"{repo.lower()}#{number}"


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "initialized_at": None,
        "baseline": {},
        "in_progress": {},
        "reviewed": {},
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Version de registre non prise en charge")
    for field in ("baseline", "in_progress", "reviewed"):
        data.setdefault(field, {})
    return data


def save_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def read_candidates(source: str) -> list[dict[str, Any]]:
    if source == "-":
        raw = json.load(sys.stdin)
    else:
        raw = json.loads(Path(source).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("pull_requests", raw.get("items", []))
    if not isinstance(raw, list):
        raise ValueError("La liste de PR doit être un tableau JSON")
    candidates = []
    for item in raw:
        repo = item.get("repo") or item.get("repository")
        number = item.get("number")
        url = item.get("url")
        if not repo or not isinstance(number, int) or not url:
            raise ValueError("Chaque PR doit contenir repo, number et url")
        candidates.append(
            {
                "repo": repo,
                "number": number,
                "url": url,
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "created_at": item.get("created_at") or item.get("createdAt"),
            }
        )
    return candidates


def claim_is_active(claim: dict[str, Any]) -> bool:
    claimed_at = claim.get("claimed_at")
    if not claimed_at:
        return False
    try:
        parsed = dt.datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return now_utc() - parsed < CLAIM_TTL


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    if state.get("initialized_at") and not args.replace:
        print(json.dumps({"initialized": False, "reason": "already_initialized"}))
        return
    candidates = read_candidates(args.input)
    state["initialized_at"] = iso_now()
    state["baseline"] = {
        pr_key(item["repo"], item["number"]): item for item in candidates
    }
    save_state(path, state)
    print(json.dumps({"initialized": True, "baseline_count": len(candidates)}))


def cmd_pending(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    if not state.get("initialized_at"):
        raise RuntimeError("Registre non initialisé")
    pending = []
    for item in read_candidates(args.input):
        key = pr_key(item["repo"], item["number"])
        if key in state["baseline"] or key in state["reviewed"]:
            continue
        claim = state["in_progress"].get(key)
        if claim and claim_is_active(claim):
            continue
        pending.append(item)
    print(json.dumps({"pull_requests": pending}, ensure_ascii=False))


def cmd_claim(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    key = pr_key(args.repo, args.number)
    if key in state["baseline"] or key in state["reviewed"]:
        print(json.dumps({"claimed": False, "reason": "already_handled"}))
        return
    existing = state["in_progress"].get(key)
    if existing and claim_is_active(existing):
        print(json.dumps({"claimed": False, "reason": "already_in_progress"}))
        return
    state["in_progress"][key] = {
        "repo": args.repo,
        "number": args.number,
        "url": args.url,
        "claimed_at": iso_now(),
        "run_id": args.run_id,
    }
    save_state(path, state)
    print(json.dumps({"claimed": True, "key": key}))


def cmd_mark_reviewed(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    key = pr_key(args.repo, args.number)
    claim = state["in_progress"].pop(key, {})
    state["reviewed"][key] = {
        "repo": args.repo,
        "number": args.number,
        "url": args.url or claim.get("url"),
        "reviewed_at": iso_now(),
        "review_session": args.review_session,
        "slack_message_id": args.slack_message_id,
    }
    save_state(path, state)
    print(json.dumps({"reviewed": True, "key": key}))


def cmd_release(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    key = pr_key(args.repo, args.number)
    released = state["in_progress"].pop(key, None) is not None
    save_state(path, state)
    print(json.dumps({"released": released, "key": key}))


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    print(
        json.dumps(
            {
                "initialized_at": state.get("initialized_at"),
                "baseline_count": len(state["baseline"]),
                "in_progress_count": len(state["in_progress"]),
                "reviewed_count": len(state["reviewed"]),
            },
            ensure_ascii=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--input", default="-")
    init.add_argument("--replace", action="store_true")
    init.set_defaults(func=cmd_init)

    pending = sub.add_parser("pending")
    pending.add_argument("--input", default="-")
    pending.set_defaults(func=cmd_pending)

    claim = sub.add_parser("claim")
    claim.add_argument("--repo", required=True)
    claim.add_argument("--number", required=True, type=int)
    claim.add_argument("--url", required=True)
    claim.add_argument("--run-id", default="")
    claim.set_defaults(func=cmd_claim)

    reviewed = sub.add_parser("mark-reviewed")
    reviewed.add_argument("--repo", required=True)
    reviewed.add_argument("--number", required=True, type=int)
    reviewed.add_argument("--url")
    reviewed.add_argument("--review-session", default="")
    reviewed.add_argument("--slack-message-id", default="")
    reviewed.set_defaults(func=cmd_mark_reviewed)

    release = sub.add_parser("release")
    release.add_argument("--repo", required=True)
    release.add_argument("--number", required=True, type=int)
    release.set_defaults(func=cmd_release)

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
