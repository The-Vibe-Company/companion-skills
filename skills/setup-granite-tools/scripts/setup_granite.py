#!/usr/bin/env python3
"""Plan or apply a safe, idempotent Granite setup.

The script is dependency-free and defaults to dry-run mode. It installs the
Granite CLI when needed, initializes a new default vault, starts the persistent
web UI daemon, connects selected agent hosts, and maintains marked guidance.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


START_MARKER = "<!-- granite-setup:start -->"
END_MARKER = "<!-- granite-setup:end -->"
GRANITE_RULE = """<!-- granite-setup:start -->
## Granite

Use Granite when a task may benefit from prior knowledge, decisions, relationships, meetings, sources, or durable memory.

Granite is an LLM-operated knowledge compiler, not a file dump. The agent harness must use the Granite MCP for every knowledge operation because its intention-first tools enforce the vault's business logic, type contracts, validation, provenance, and editorial lifecycle.

Before Granite-backed work, call the MCP tool `granite_wakeup` once per conversation. Use MCP tools such as `granite_research_topic`, `granite_query`, `granite_compile_context`, and `granite_understand_note` for retrieval; use `granite_capture_knowledge`, `granite_import_document`, and `granite_revise_note` for writes. Read `granite://vault/types` before writing when the type contract is unfamiliar.

Do not declare the Granite knowledge runtime verified until the configured host has successfully called both `granite_wakeup` and at least one real MCP retrieval tool against the intended vault.

Do not use Granite CLI knowledge commands such as `granite search`, `new`, `add`, `edit`, `extract`, or `import`, and do not edit vault Markdown files directly. The CLI is reserved for installation, initialization, daemon lifecycle, and diagnostics when repairing the MCP connection.

Do not tell users to upload, copy, or drag files directly into the vault as if that completed ingestion. For a document, use `granite_extract_document` through MCP, analyze its meaning, research existing knowledge through MCP, and write the useful information through MCP as structured Granite sources and notes. Attach the original with `granite_import_document` only when it is useful evidence or an artifact worth preserving. Do not load Granite for unrelated tasks.
<!-- granite-setup:end -->"""

SUPPORTED_HOSTS = ("claude", "codex", "cursor")
LOCAL_WEB_HOST = "127.0.0.1"
WEB_SECURITY_WARNING = (
    "Granite's web UI has no authentication, and current releases may listen on more than loopback "
    "even when the daemon reports 127.0.0.1. Use it only on a trusted machine/network and firewall the selected web port."
)
USAGE_MODEL = {
    "principle": "Granite is an LLM-operated knowledge compiler, not a file dump.",
    "harness_required": True,
    "knowledge_interface": "mcp",
    "mcp_required_for_knowledge_operations": True,
    "cli_knowledge_operations_allowed": False,
    "cli_allowed_for": [
        "installation",
        "vault_initialization",
        "daemon_lifecycle",
        "diagnostics_and_mcp_repair",
    ],
    "mcp_business_logic": [
        "intention_first_workflow",
        "type_contracts",
        "validation",
        "provenance",
        "editorial_lifecycle",
    ],
    "mcp_runtime_verification_requires": [
        "granite_wakeup",
        "real_mcp_retrieval_against_intended_vault",
    ],
    "direct_file_upload_recommended": False,
    "file_ingestion_flow": [
        "read_or_extract",
        "analyze_with_llm",
        "search_and_deduplicate",
        "write_structured_knowledge_with_provenance",
        "attach_original_only_if_useful",
    ],
    "mcp_file_ingestion_flow": [
        "granite_extract_document",
        "analyze_with_llm",
        "granite_research_topic_or_query",
        "granite_capture_knowledge_or_import_document",
        "mcp_validation_and_recommendations",
    ],
}


@dataclass
class Action:
    area: str
    target: str
    status: str
    detail: str
    command: list[str] | None = None
    environment: dict[str, str] | None = None


class SetupError(RuntimeError):
    pass


@dataclass
class FileSnapshot:
    existed: bool
    content: bytes | None
    mode: int | None


def resolve_user_path(value: str, home: Path) -> Path:
    if value == "~":
        return home.resolve()
    if value.startswith("~/") or value.startswith("~\\"):
        return (home / value[2:]).resolve()
    return Path(value).expanduser().resolve()


def run(
    command: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    check: bool = False,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SetupError(f"Command timed out after {timeout}s: {' '.join(command)}") from exc
    except OSError as exc:
        raise SetupError(f"Could not run command: {' '.join(command)} ({exc})") from exc
    if check and result.returncode != 0:
        raise SetupError(f"Command failed ({result.returncode}): {' '.join(command)}\n{result.stdout.strip()}")
    return result


def command_exists(name: str, env: dict[str, str]) -> str | None:
    return shutil.which(name, path=env.get("PATH"))


def parse_hosts(value: str, home: Path, env: dict[str, str]) -> list[str]:
    if value != "auto":
        hosts = [item.strip().lower() for item in value.split(",") if item.strip()]
        unknown = sorted(set(hosts) - set(SUPPORTED_HOSTS))
        if unknown:
            raise SetupError(f"Unsupported host(s): {', '.join(unknown)}")
        return list(dict.fromkeys(hosts))

    detected: list[str] = []
    if command_exists("claude", env):
        detected.append("claude")
    if command_exists("codex", env):
        detected.append("codex")
    if (home / ".cursor").exists():
        detected.append("cursor")
    return detected


def resolve_granite_binary(explicit: str | None, env: dict[str, str]) -> Path | None:
    if explicit:
        candidate = resolve_user_path(explicit, Path(env["HOME"]))
        if not candidate.is_file():
            return None
        if os.name != "nt" and not os.access(candidate, os.X_OK):
            return None
        return candidate
    found = command_exists("granite", env)
    return Path(found).absolute() if found else None


def find_npm_global_granite(env: dict[str, str]) -> Path | None:
    candidate = npm_global_granite_path(env)
    return candidate if candidate and candidate.exists() else None


def npm_global_granite_path(env: dict[str, str]) -> Path | None:
    npm = command_exists("npm", env)
    if not npm:
        return None
    prefix = run([npm, "prefix", "-g"], env=env)
    if prefix.returncode != 0:
        return None
    executable = "granite.cmd" if os.name == "nt" else "granite"
    base = Path(prefix.stdout.strip())
    candidate = base / executable if os.name == "nt" else base / "bin" / executable
    return candidate.absolute()


def install_granite(
    *,
    apply: bool,
    skip_install: bool,
    explicit_binary: str | None,
    env: dict[str, str],
    actions: list[Action],
) -> Path | None:
    binary = resolve_granite_binary(explicit_binary, env)
    if binary:
        version = run([str(binary), "--version"], env=env)
        if version.returncode != 0:
            actions.append(
                Action(
                    "install",
                    str(binary),
                    "blocked",
                    "A Granite executable was found, but `granite --version` failed. Repair or replace the binary before configuring vaults or MCP hosts.",
                )
            )
            return None
        detail = version.stdout.strip() or "version reported without text"
        actions.append(Action("install", str(binary), "ok", f"Granite already installed ({detail})."))
        return binary

    if explicit_binary:
        actions.append(
            Action(
                "install",
                explicit_binary,
                "blocked",
                "The requested Granite binary does not exist, is not a regular file, or is not executable.",
            )
        )
        return None
    if skip_install:
        actions.append(Action("install", "granite", "blocked", "Granite is absent and --skip-install was set."))
        return None

    npm = command_exists("npm", env)
    if not npm:
        actions.append(Action("install", "granite-mem", "blocked", "npm is required to install Granite."))
        return None

    command = [npm, "install", "-g", "granite-mem@latest"]
    if not apply:
        predicted = npm_global_granite_path(env)
        detail = "Install Granite globally with npm."
        if predicted:
            detail += f" Expected executable: {predicted}."
        actions.append(Action("install", "granite-mem", "planned", detail, command))
        return predicted

    run(command, env=env, check=True)
    binary = resolve_granite_binary(None, env) or find_npm_global_granite(env)
    if not binary:
        actions.append(
            Action(
                "install",
                "granite-mem",
                "blocked",
                "npm completed but the Granite executable could not be located. Restart the shell or pass --granite-bin.",
            )
        )
        return None
    actions.append(Action("install", str(binary), "changed", "Installed Granite globally with npm.", command))
    return binary


def parse_version(output: str) -> str | None:
    match = re.search(r"(?<![0-9A-Za-z])v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)", output)
    return match.group(1) if match else None


def version_key(version: str) -> tuple[int, int, int, int, str]:
    without_build = version.split("+", 1)[0]
    core, separator, prerelease = without_build.partition("-")
    major, minor, patch = (int(part) for part in core.split("."))
    return major, minor, patch, 0 if separator else 1, prerelease


def update_granite(
    *,
    binary: Path | None,
    requested: bool,
    apply: bool,
    explicit_binary: str | None,
    env: dict[str, str],
    actions: list[Action],
) -> tuple[Path | None, dict[str, Any], bool]:
    result: dict[str, Any] = {
        "requested": requested,
        "installed_version": None,
        "latest_version": None,
        "update_available": False,
        "updated": False,
    }
    if not requested:
        return binary, result, False
    if not binary:
        actions.append(Action("update", "granite-mem", "blocked", "Granite must be installed before it can be updated."))
        return binary, result, False
    if not binary.exists() and not apply:
        actions.append(
            Action(
                "update",
                "granite-mem",
                "ok",
                "A fresh granite-mem@latest installation is already planned; no separate update is needed.",
            )
        )
        return binary, result, False

    current = run([str(binary), "--version"], env=env)
    installed_version = parse_version(current.stdout) if current.returncode == 0 else None
    if not installed_version:
        actions.append(Action("update", str(binary), "blocked", "Could not determine the installed Granite version safely."))
        return binary, result, False
    result["installed_version"] = installed_version

    npm = command_exists("npm", env)
    if not npm:
        actions.append(Action("update", "granite-mem", "blocked", "npm is required to check for and install Granite updates."))
        return binary, result, False
    latest = run([npm, "view", "granite-mem@latest", "version", "--json"], env=env)
    latest_version = parse_version(latest.stdout) if latest.returncode == 0 else None
    if not latest_version:
        actions.append(
            Action(
                "update",
                "granite-mem",
                "blocked",
                "Could not read the latest granite-mem version from the npm registry. No update was attempted.",
            )
        )
        return binary, result, False
    result["latest_version"] = latest_version
    installed_key = version_key(installed_version)
    latest_key = version_key(latest_version)
    result["update_available"] = installed_key < latest_key

    if installed_key == latest_key:
        actions.append(Action("update", "granite-mem", "ok", f"Granite is current ({installed_version})."))
        return binary, result, False
    if installed_key > latest_key:
        actions.append(
            Action(
                "update",
                "granite-mem",
                "ok",
                f"Installed Granite {installed_version} is newer than npm latest {latest_version}; no downgrade was attempted.",
            )
        )
        return binary, result, False
    if explicit_binary:
        actions.append(
            Action(
                "update",
                str(binary),
                "blocked",
                f"Granite {installed_version} is behind {latest_version}, but --granite-bin points to an explicit executable. Update that installation with its owning package manager, then rerun without --update-granite.",
            )
        )
        return binary, result, False

    command = [npm, "install", "-g", "granite-mem@latest"]
    if not apply:
        actions.append(
            Action(
                "update",
                "granite-mem",
                "planned",
                f"Update Granite from {installed_version} to {latest_version}, then restart and verify the persistent daemon.",
                command,
            )
        )
        return binary, result, False

    run(command, env=env, check=True)
    updated_binary = resolve_granite_binary(None, env) or find_npm_global_granite(env)
    if not updated_binary:
        raise SetupError("npm updated granite-mem, but the Granite executable could not be located afterward.")
    confirmed = run([str(updated_binary), "--version"], env=env)
    confirmed_version = parse_version(confirmed.stdout) if confirmed.returncode == 0 else None
    if confirmed_version != latest_version:
        raise SetupError(
            f"Granite update verification failed: expected {latest_version}, got {confirmed_version or 'an unreadable version'}."
        )
    result["installed_version"] = confirmed_version
    result["updated"] = True
    actions.append(
        Action(
            "update",
            "granite-mem",
            "changed",
            f"Updated Granite from {installed_version} to {confirmed_version}.",
            command,
        )
    )
    return updated_binary, result, True


def initialize_vault(
    *,
    binary: Path | None,
    vault: Path,
    template: str,
    apply: bool,
    skip_init: bool,
    env: dict[str, str],
    actions: list[Action],
) -> bool:
    config = vault / "granite.yml"
    if config.exists():
        if binary:
            preflight = run([str(binary), "status", "--json"], env=env, cwd=vault)
            if preflight.returncode != 0:
                actions.append(
                    Action(
                        "vault",
                        str(vault),
                        "blocked",
                        "The existing vault failed `granite status`. Repair the vault before changing MCP host configuration.",
                    )
                )
                return False
        actions.append(Action("vault", str(vault), "ok", "Existing vault preserved."))
        return True
    if vault.exists() and any(vault.iterdir()):
        actions.append(
            Action(
                "vault",
                str(vault),
                "blocked",
                "The vault path is non-empty but has no granite.yml. Inspect or migrate it before initialization.",
            )
        )
        return False
    if skip_init:
        actions.append(Action("vault", str(vault), "blocked", "No vault exists and --skip-init was set."))
        return False
    if vault.name != ".granite":
        actions.append(
            Action(
                "vault",
                str(vault),
                "blocked",
                "Granite currently initializes the default ~/.granite path. Use an existing custom vault or choose a path ending in .granite.",
            )
        )
        return False

    minimal = template.lower() in {"minimal", "default", "none"}
    command = [str(binary) if binary else "granite", "init"]
    if not minimal:
        command.extend(["--template", template])
    if not apply:
        detail = "Initialize a new vault with the minimal core types." if minimal else f"Initialize a new vault with template {template}."
        actions.append(Action("vault", str(vault), "planned", detail, command))
        return True
    if not binary:
        actions.append(Action("vault", str(vault), "blocked", "Granite must be installed before vault initialization."))
        return False

    init_env = dict(env)
    init_env["HOME"] = str(vault.parent)
    if os.name == "nt":
        init_env["USERPROFILE"] = str(vault.parent)
    run(command, env=init_env, check=True)
    if not config.exists():
        raise SetupError(f"Granite init completed without creating {config}")
    detail = "Initialized vault with the minimal core types." if minimal else f"Initialized vault with template {template}."
    actions.append(Action("vault", str(vault), "changed", detail, command))
    return True


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value}") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 1 and 65535: {value}")
    return port


def parse_daemon_status(output: str) -> dict[str, Any] | None:
    if "Granite daemon running" not in output:
        return None
    fields: dict[str, str] = {}
    for key in ("Vault", "MCP", "Web"):
        match = re.search(rf"^\s*{key}:\s+(.+?)\s*$", output, flags=re.MULTILINE)
        if match:
            fields[key.lower()] = match.group(1)
    if not all(name in fields for name in ("vault", "mcp", "web")):
        return None
    mcp_url = urllib.parse.urlparse(fields["mcp"])
    web_url = urllib.parse.urlparse(fields["web"])
    if not mcp_url.hostname or not mcp_url.port or not web_url.hostname or not web_url.port:
        return None
    return {
        "vault": str(Path(fields["vault"]).expanduser().resolve()),
        "host": web_url.hostname,
        "mcp_port": mcp_url.port,
        "web_port": web_url.port,
        "mcp_url": fields["mcp"],
        "web_url": fields["web"],
    }


def read_daemon_status(binary: Path, vault: Path, env: dict[str, str]) -> dict[str, Any] | None:
    daemon_env = dict(env)
    daemon_env["GRANITE_VAULT"] = str(vault)
    result = run([str(binary), "daemon", "status"], env=daemon_env)
    if result.returncode != 0:
        if "not running" in result.stdout.lower():
            return None
        raise SetupError(f"Could not inspect the Granite daemon: {result.stdout.strip()}")
    status = parse_daemon_status(result.stdout)
    if not status:
        raise SetupError("Granite reported a running daemon, but its status output could not be parsed safely.")
    return status


def port_available(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as handle:
        handle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            handle.bind((host, port))
        except OSError:
            return False
    return True


def http_responding(url: str, timeout: float = 2.0) -> bool:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_http(url: str, attempts: int = 30, delay: float = 0.2) -> bool:
    for _ in range(attempts):
        if http_responding(url):
            return True
        time.sleep(delay)
    return False


def wait_for_ports_available(host: str, ports: tuple[int, ...], attempts: int = 30, delay: float = 0.1) -> bool:
    for _ in range(attempts):
        if all(port_available(host, port) for port in ports):
            return True
        time.sleep(delay)
    return False


def wait_for_daemon_status(
    binary: Path,
    vault: Path,
    env: dict[str, str],
    attempts: int = 30,
    delay: float = 0.2,
) -> dict[str, Any] | None:
    for _ in range(attempts):
        status = read_daemon_status(binary, vault, env)
        if status:
            return status
        time.sleep(delay)
    return None


def daemon_start_command(
    binary: Path,
    *,
    host: str,
    mcp_port: int,
    web_port: int,
) -> list[str]:
    return [
        str(binary),
        "daemon",
        "start",
        "--host",
        host,
        "--mcp-port",
        str(mcp_port),
        "--web-port",
        str(web_port),
    ]


def configure_web_daemon(
    *,
    binary: Path,
    vault: Path,
    apply: bool,
    replace: bool,
    force_restart: bool = False,
    web_port: int,
    mcp_port: int,
    env: dict[str, str],
    actions: list[Action],
) -> dict[str, Any]:
    host = LOCAL_WEB_HOST
    desired = {
        "vault": str(vault.resolve()),
        "host": host,
        "mcp_port": mcp_port,
        "web_port": web_port,
        "mcp_url": f"http://{host}:{mcp_port}/mcp",
        "web_url": f"http://{host}:{web_port}",
        "security_warning": WEB_SECURITY_WARNING,
    }
    current = read_daemon_status(binary, vault, env)
    matches = bool(
        current
        and current["vault"] == desired["vault"]
        and current["host"] in {host, "localhost"}
        and current["mcp_port"] == mcp_port
        and current["web_port"] == web_port
    )
    web_responding = matches and http_responding(desired["web_url"])
    if web_responding and not force_restart:
        actions.append(
            Action(
                "web",
                desired["web_url"],
                "ok",
                f"Persistent Granite web UI is already running. {WEB_SECURITY_WARNING}",
            )
        )
        return {"ok": True, "persistent": True, **desired}

    conflict = current is not None
    if conflict and not matches and not replace:
        actions.append(
            Action(
                "web",
                desired["web_url"],
                "blocked",
                f"A Granite daemon already uses {current['web_url']} and {current['mcp_url']}. Review it, then rerun with --replace-daemon to move the persistent UI to port {web_port}.",
            )
        )
        return {"ok": False, "persistent": True, **desired}

    command = daemon_start_command(binary, host=host, mcp_port=mcp_port, web_port=web_port)
    daemon_env = dict(env)
    daemon_env["GRANITE_VAULT"] = str(vault)
    if not apply:
        unavailable = []
        if not conflict or web_port != current["web_port"]:
            if not port_available(host, web_port):
                unavailable.append(str(web_port))
        if not conflict or mcp_port != current["mcp_port"]:
            if not port_available(host, mcp_port):
                unavailable.append(str(mcp_port))
        if unavailable:
            actions.append(
                Action(
                    "web",
                    desired["web_url"],
                    "blocked",
                    f"Required local port(s) are already in use: {', '.join(unavailable)}. Granite will not replace an unrelated service.",
                    command,
                    {"GRANITE_VAULT": str(vault)},
                )
            )
            return {"ok": False, "persistent": True, **desired}
        if matches:
            status = "planned-restart"
            reason = "Restart the matching Granite daemon after the update." if force_restart else "Restart the matching Granite daemon because its web UI is not responding."
        elif conflict:
            status = "planned-replacement"
            reason = f"Replace the approved conflicting Granite daemon and start the web UI on port {web_port}."
        else:
            status = "planned"
            reason = f"Start Granite as a persistent daemon with the web UI on port {web_port}."
        actions.append(
            Action(
                "web",
                desired["web_url"],
                status,
                f"{reason} Verify daemon status and an HTTP response before reporting success. {WEB_SECURITY_WARNING}",
                command,
                {"GRANITE_VAULT": str(vault)},
            )
        )
        return {"ok": True, "persistent": True, **desired}

    old_status = current
    try:
        if old_status:
            stop = run([str(binary), "daemon", "stop"], env=daemon_env)
            if stop.returncode != 0:
                raise SetupError(f"Could not stop the existing Granite daemon: {stop.stdout.strip()}")
        if not wait_for_ports_available(host, (web_port, mcp_port)):
            unavailable = [str(port) for port in (web_port, mcp_port) if not port_available(host, port)]
            raise SetupError(
                f"Required local port(s) are already in use after daemon stop: {', '.join(unavailable)}. "
                "Granite will not replace an unrelated service."
            )
        run(command, env=daemon_env, check=True)
        confirmed = wait_for_daemon_status(binary, vault, env)
        if not confirmed or any(
            (
                confirmed["vault"] != desired["vault"],
                confirmed["host"] not in {host, "localhost"},
                confirmed["mcp_port"] != mcp_port,
                confirmed["web_port"] != web_port,
            )
        ):
            raise SetupError("Granite daemon did not retain the requested vault and ports.")
        if not wait_for_http(desired["web_url"]):
            raise SetupError(f"Granite daemon started, but the web UI did not respond at {desired['web_url']}.")
    except Exception as exc:
        try:
            running = read_daemon_status(binary, vault, env)
        except SetupError:
            running = None
        if running:
            run([str(binary), "daemon", "stop"], env=daemon_env)
            wait_for_ports_available(host, (running["web_port"], running["mcp_port"]))
        if old_status:
            restore = daemon_start_command(
                binary,
                host=old_status["host"],
                mcp_port=old_status["mcp_port"],
                web_port=old_status["web_port"],
            )
            restored = run(restore, env=daemon_env)
            if restored.returncode != 0:
                raise SetupError(
                    f"{exc} The previous Granite daemon configuration could not be restored: {restored.stdout.strip()}"
                ) from exc
        raise

    detail = "Restarted" if old_status else "Started"
    actions.append(
        Action(
            "web",
            desired["web_url"],
            "changed",
            f"{detail} the persistent Granite daemon; web UI is available at {desired['web_url']}. {WEB_SECURITY_WARNING}",
            command,
            {"GRANITE_VAULT": str(vault)},
        )
    )
    return {"ok": True, "persistent": True, **desired}


def expected_mcp(binary: Path, vault: Path) -> tuple[str, list[str]]:
    return str(binary), ["mcp", "--vault", str(vault)]


def output_matches_mcp(output: str, binary: Path, vault: Path) -> bool:
    normalized = output.replace("\\", "/")
    if str(vault).replace("\\", "/") not in normalized:
        return False
    for line in output.splitlines():
        if not re.match(r"^\s*command\s*:", line, flags=re.IGNORECASE):
            continue
        raw = line.split(":", 1)[1].strip().strip("\"'")
        candidate = Path(raw.rstrip(",;)"))
        try:
            if candidate.exists() and binary.exists() and os.path.samefile(candidate, binary):
                return True
        except OSError:
            continue
    return False


def snapshot_files(paths: list[Path]) -> dict[Path, FileSnapshot]:
    snapshots: dict[Path, FileSnapshot] = {}
    for path in paths:
        if path.exists():
            snapshots[path] = FileSnapshot(True, path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        else:
            snapshots[path] = FileSnapshot(False, None, None)
    return snapshots


def atomic_write_bytes(path: Path, content: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_write_text(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    atomic_write_bytes(path, text.encode("utf-8"), mode)


def restore_files(snapshots: dict[Path, FileSnapshot]) -> None:
    for path, snapshot in snapshots.items():
        if snapshot.existed:
            atomic_write_bytes(path, snapshot.content or b"", snapshot.mode)
        elif path.exists():
            path.unlink()


def remove_mcp(command: list[str], *, env: dict[str, str], cwd: Path | None = None) -> None:
    result = run(command, env=env, cwd=cwd)
    if result.returncode == 0:
        return
    lower = result.stdout.lower()
    if "not found" in lower or "no mcp server" in lower or "no server" in lower or "does not exist" in lower:
        return
    raise SetupError(f"MCP removal failed ({result.returncode}): {' '.join(command)}")


def configure_claude(
    *,
    binary: Path,
    vault: Path,
    apply: bool,
    replace: bool,
    project_root: Path,
    env: dict[str, str],
    actions: list[Action],
) -> None:
    claude = command_exists("claude", env)
    if not claude:
        actions.append(Action("mcp", "claude", "blocked", "Claude Code CLI is not installed."))
        return

    current = run([claude, "mcp", "get", "granite"], env=env, cwd=project_root)
    listing = run([claude, "mcp", "list"], env=env, cwd=project_root)
    exists = current.returncode == 0
    conflict_scopes = "Conflicting scopes" in listing.stdout and "granite" in listing.stdout.lower()
    matching = exists and output_matches_mcp(current.stdout, binary, vault) and not conflict_scopes

    if matching:
        actions.append(Action("mcp", "claude", "ok", "Claude Code already uses the canonical Granite MCP."))
        return
    if exists or conflict_scopes:
        if not replace:
            actions.append(
                Action(
                    "mcp",
                    "claude",
                    "blocked",
                    "A different or scope-conflicting Granite MCP exists. Review it, then rerun with --replace-mcp if replacement is intended.",
                )
            )
            return
    command = [claude, "mcp", "add", "--scope", "user", "granite", "--", str(binary), "mcp", "--vault", str(vault)]
    if not apply:
        status = "planned" if not (exists or conflict_scopes) else "planned-replacement"
        actions.append(Action("mcp", "claude", status, "Register one canonical user-scope Granite MCP.", command))
        return
    home = Path(env["HOME"])
    claude_user = home / ".claude.json"
    claude_project = project_root / ".mcp.json"
    snapshots = snapshot_files(
        [
            claude_user.resolve() if claude_user.is_symlink() else claude_user,
            claude_project.resolve() if claude_project.is_symlink() else claude_project,
        ]
    )
    try:
        if exists or conflict_scopes:
            for scope in ("local", "project", "user"):
                remove_mcp([claude, "mcp", "remove", "granite", "--scope", scope], env=env, cwd=project_root)
        run(command, env=env, cwd=project_root, check=True)
        confirmed = run([claude, "mcp", "get", "granite"], env=env, cwd=project_root)
        confirmed_listing = run([claude, "mcp", "list"], env=env, cwd=project_root)
        if (
            confirmed.returncode != 0
            or not output_matches_mcp(confirmed.stdout, binary, vault)
            or ("Conflicting scopes" in confirmed_listing.stdout and "granite" in confirmed_listing.stdout.lower())
        ):
            raise SetupError("Claude Code did not report the canonical Granite MCP after configuration.")
    except Exception:
        restore_files(snapshots)
        raise
    actions.append(Action("mcp", "claude", "changed", "Registered canonical user-scope Granite MCP.", command))


def configure_codex(
    *,
    binary: Path,
    vault: Path,
    apply: bool,
    replace: bool,
    env: dict[str, str],
    actions: list[Action],
) -> None:
    codex = command_exists("codex", env)
    if not codex:
        actions.append(Action("mcp", "codex", "blocked", "Codex CLI is not installed."))
        return

    current = run([codex, "mcp", "get", "granite"], env=env)
    exists = current.returncode == 0
    if exists and output_matches_mcp(current.stdout, binary, vault):
        actions.append(Action("mcp", "codex", "ok", "Codex already uses the canonical Granite MCP."))
        return
    if exists and not replace:
        actions.append(
            Action(
                "mcp",
                "codex",
                "blocked",
                "A different Granite MCP exists. Review it, then rerun with --replace-mcp if replacement is intended.",
            )
        )
        return
    command = [codex, "mcp", "add", "granite", "--", str(binary), "mcp", "--vault", str(vault)]
    if not apply:
        status = "planned" if not exists else "planned-replacement"
        actions.append(Action("mcp", "codex", status, "Register the canonical Granite MCP.", command))
        return
    home = Path(env["HOME"])
    codex_home = Path(env.get("CODEX_HOME", home / ".codex"))
    codex_config = codex_home / "config.toml"
    snapshots = snapshot_files([codex_config.resolve() if codex_config.is_symlink() else codex_config])
    try:
        if exists:
            remove_mcp([codex, "mcp", "remove", "granite"], env=env)
        run(command, env=env, check=True)
        confirmed = run([codex, "mcp", "get", "granite"], env=env)
        if confirmed.returncode != 0 or not output_matches_mcp(confirmed.stdout, binary, vault):
            raise SetupError("Codex did not report the canonical Granite MCP after configuration.")
    except Exception:
        restore_files(snapshots)
        raise
    actions.append(Action("mcp", "codex", "changed", "Registered the canonical Granite MCP.", command))


def configure_cursor(
    *,
    binary: Path,
    vault: Path,
    apply: bool,
    replace: bool,
    home: Path,
    actions: list[Action],
) -> None:
    path = home / ".cursor" / "mcp.json"
    if path.is_symlink():
        if not path.exists():
            actions.append(Action("mcp", "cursor", "blocked", f"Refusing to edit broken symlink: {path}"))
            return
        path = path.resolve()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            actions.append(Action("mcp", "cursor", "blocked", f"{path} contains invalid JSON: {exc}"))
            return
        if not isinstance(loaded, dict):
            actions.append(Action("mcp", "cursor", "blocked", f"{path} must contain a JSON object."))
            return
        data = loaded

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        actions.append(Action("mcp", "cursor", "blocked", f"{path}: mcpServers must be an object."))
        return

    command, args = expected_mcp(binary, vault)
    expected = {"command": command, "args": args}
    current = servers.get("granite")
    if current == expected:
        actions.append(Action("mcp", "cursor", "ok", "Cursor already uses the canonical Granite MCP."))
        return
    if current is not None and not replace:
        actions.append(
            Action(
                "mcp",
                "cursor",
                "blocked",
                "A different Cursor Granite MCP exists. Review it, then rerun with --replace-mcp if replacement is intended.",
            )
        )
        return

    if not apply:
        status = "planned" if current is None else "planned-replacement"
        actions.append(Action("mcp", "cursor", status, f"Write the canonical Granite entry to {path}."))
        return

    servers["granite"] = expected
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    try:
        written = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"Could not verify the Cursor MCP configuration at {path}: {exc}") from exc
    if written.get("mcpServers", {}).get("granite") != expected:
        raise SetupError(f"Cursor did not retain the canonical Granite MCP at {path}.")
    actions.append(Action("mcp", "cursor", "changed", f"Wrote the canonical Granite entry to {path}."))


def replace_managed_block(text: str, block: str) -> tuple[str, str]:
    start_count = text.count(START_MARKER)
    end_count = text.count(END_MARKER)
    if start_count > 1 or end_count > 1:
        raise SetupError("Found duplicate granite-setup managed blocks; review them before replacement.")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 and end == -1:
        prefix = text.rstrip()
        updated = f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"
        return updated, "added"
    if start == -1 or end == -1 or end < start:
        raise SetupError("Found an incomplete granite-setup managed block.")
    end += len(END_MARKER)
    updated = text[:start] + block + text[end:]
    if not updated.endswith("\n"):
        updated += "\n"
    return updated, "unchanged" if updated == text else "updated"


def guidance_targets(project_root: Path) -> list[tuple[Path, list[str]]]:
    paths = [project_root / "AGENTS.md", project_root / "CLAUDE.md"]
    grouped: dict[str, tuple[Path, list[str]]] = {}
    for path in paths:
        if path.is_symlink() and not path.exists():
            raise SetupError(f"Refusing to edit broken symlink: {path}")
        target = path.resolve() if path.exists() or path.is_symlink() else path
        key = str(target)
        if key not in grouped:
            grouped[key] = (target, [])
        grouped[key][1].append(path.name)
    return list(grouped.values())


def configure_guidance(project_root: Path, apply: bool, actions: list[Action]) -> None:
    for target, aliases in guidance_targets(project_root):
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        try:
            updated, change = replace_managed_block(current, GRANITE_RULE)
        except SetupError as exc:
            actions.append(Action("guidance", ", ".join(aliases), "blocked", str(exc)))
            continue

        label = ", ".join(aliases)
        if change == "unchanged":
            actions.append(Action("guidance", label, "ok", f"Managed Granite rule is current in {target}."))
        elif not apply:
            actions.append(Action("guidance", label, "planned", f"{change.capitalize()} managed Granite rule in {target}."))
        else:
            atomic_write_text(target, updated)
            actions.append(Action("guidance", label, "changed", f"{change.capitalize()} managed Granite rule in {target}."))


def verify(binary: Path | None, vault: Path, env: dict[str, str], actions: list[Action]) -> dict[str, Any]:
    verification: dict[str, Any] = {}
    if not binary or not (vault / "granite.yml").exists():
        return verification
    for name, command in (
        ("status", [str(binary), "status", "--json"]),
        ("doctor", [str(binary), "doctor", "--json"]),
    ):
        result = run(command, env=env, cwd=vault)
        verification[name] = {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
        }
        actions.append(
            Action(
                "verify",
                name,
                "ok" if result.returncode == 0 else "blocked",
                f"Granite {name} {'succeeded' if result.returncode == 0 else 'failed'}.",
                command,
            )
        )
    verification["mcp_knowledge_runtime"] = {
        "ok": False,
        "pending": True,
        "required": True,
        "detail": "Reload the configured host, then call granite_wakeup and a real Granite MCP retrieval tool. CLI wakeup is intentionally not used as a substitute.",
    }
    return verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project whose AGENTS.md and CLAUDE.md should receive Granite rules.")
    parser.add_argument("--home", help="Home directory override, useful for isolated tests.")
    parser.add_argument("--vault", help="Vault path. Defaults to <home>/.granite.")
    parser.add_argument("--template", default="founder-os", help="Template for a new vault.")
    parser.add_argument("--hosts", default="auto", help="auto or comma-separated: claude,codex,cursor")
    parser.add_argument("--granite-bin", help="Explicit Granite executable path.")
    parser.add_argument("--apply", action="store_true", help="Apply the plan. Without this flag the script is read-only.")
    parser.add_argument("--replace-mcp", action="store_true", help="Replace conflicting Granite MCP entries.")
    parser.add_argument("--replace-daemon", action="store_true", help="Replace a conflicting Granite daemon after review.")
    parser.add_argument("--update-granite", action="store_true", help="Compare against granite-mem@latest and update only when a newer version exists.")
    parser.add_argument("--web-port", type=parse_port, default=4321, help="Persistent local Granite web UI port (default: 4321).")
    parser.add_argument("--mcp-http-port", type=parse_port, default=3321, help="Granite daemon HTTP MCP port (default: 3321).")
    parser.add_argument("--skip-install", action="store_true", help="Do not install Granite when absent.")
    parser.add_argument("--skip-init", action="store_true", help="Do not initialize a vault when absent.")
    parser.add_argument("--skip-web", action="store_true", help="Do not start the persistent Granite web UI daemon.")
    parser.add_argument("--skip-mcp", action="store_true", help="Do not inspect or change agent MCP registrations during package or dashboard maintenance.")
    parser.add_argument("--skip-guidance", action="store_true", help="Do not manage AGENTS.md or CLAUDE.md.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    home = Path(args.home).expanduser().resolve() if args.home else Path.home().resolve()
    project_root = Path(args.project_root).expanduser().resolve()
    vault = resolve_user_path(args.vault, home) if args.vault else home / ".granite"
    env = dict(os.environ)
    env["HOME"] = str(home)
    if os.name == "nt":
        env["USERPROFILE"] = str(home)
    actions: list[Action] = []

    try:
        if not project_root.exists() or not project_root.is_dir():
            raise SetupError(f"Project root does not exist or is not a directory: {project_root}")
        if args.web_port == args.mcp_http_port:
            raise SetupError("The Granite web UI and HTTP MCP ports must be different.")
        hosts = [] if args.skip_mcp else parse_hosts(args.hosts, home, env)
        if not hosts and not args.skip_mcp:
            actions.append(Action("hosts", "auto", "blocked", "No supported agent host was detected. Pass --hosts explicitly."))

        binary = install_granite(
            apply=args.apply,
            skip_install=args.skip_install,
            explicit_binary=args.granite_bin,
            env=env,
            actions=actions,
        )
        binary, granite_update, granite_updated = update_granite(
            binary=binary,
            requested=args.update_granite,
            apply=args.apply,
            explicit_binary=args.granite_bin,
            env=env,
            actions=actions,
        )
        vault_ready = initialize_vault(
            binary=binary,
            vault=vault,
            template=args.template,
            apply=args.apply,
            skip_init=args.skip_init,
            env=env,
            actions=actions,
        )
        web = {}
        if args.skip_web:
            actions.append(Action("web", f"http://{LOCAL_WEB_HOST}:{args.web_port}", "skipped", "Persistent Granite web UI was skipped."))
        elif binary and vault_ready:
            web = configure_web_daemon(
                binary=binary,
                vault=vault,
                apply=args.apply,
                replace=args.replace_daemon,
                force_restart=granite_updated or (not args.apply and granite_update["update_available"]),
                web_port=args.web_port,
                mcp_port=args.mcp_http_port,
                env=env,
                actions=actions,
            )
        else:
            actions.append(
                Action(
                    "web",
                    f"http://{LOCAL_WEB_HOST}:{args.web_port}",
                    "blocked",
                    "Granite and a healthy vault are required before starting the persistent web UI.",
                )
            )

        if args.skip_mcp:
            actions.append(Action("mcp", "all", "skipped", "Agent MCP registrations were left unchanged for this maintenance run."))
        elif binary and vault_ready:
            for host in hosts:
                if host == "claude":
                    configure_claude(
                        binary=binary,
                        vault=vault,
                        apply=args.apply,
                        replace=args.replace_mcp,
                        project_root=project_root,
                        env=env,
                        actions=actions,
                    )
                elif host == "codex":
                    configure_codex(
                        binary=binary,
                        vault=vault,
                        apply=args.apply,
                        replace=args.replace_mcp,
                        env=env,
                        actions=actions,
                    )
                elif host == "cursor":
                    configure_cursor(
                        binary=binary,
                        vault=vault,
                        apply=args.apply,
                        replace=args.replace_mcp,
                        home=home,
                        actions=actions,
                    )
        elif hosts:
            detail = (
                "The Granite vault must pass preflight before MCP configuration."
                if binary
                else "Granite must be installed before MCP configuration."
            )
            actions.append(Action("mcp", ",".join(hosts), "blocked", detail))

        if not args.skip_guidance:
            configure_guidance(project_root, args.apply, actions)

        verification = verify(binary, vault, env, actions) if args.apply else {}
        blocked = [action for action in actions if action.status == "blocked"]
        report = {
            "mode": "apply" if args.apply else "dry-run",
            "project_root": str(project_root),
            "home": str(home),
            "vault": str(vault),
            "hosts": hosts,
            "granite_binary": str(binary) if binary else None,
            "granite_update": granite_update,
            "usage_model": USAGE_MODEL,
            "web_ui": web,
            "actions": [asdict(action) for action in actions],
            "verification": verification,
            "restart_required": any(action.area == "mcp" and action.status == "changed" for action in actions),
            "blocked": len(blocked),
        }
    except SetupError as exc:
        report = {
            "mode": "apply" if args.apply else "dry-run",
            "project_root": str(project_root),
            "vault": str(vault),
            "usage_model": USAGE_MODEL,
            "error": str(exc),
            "actions": [asdict(action) for action in actions],
            "blocked": 1,
        }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Granite setup ({report['mode']})")
        print(f"- Usage model: {USAGE_MODEL['principle']} The configured agent harness should perform ingestion and retrieval.")
        print("- Knowledge interface: Granite MCP is mandatory; CLI knowledge commands and direct vault-file edits are forbidden.")
        print("- Files: let the harness read, analyze, deduplicate, and structure them; do not use direct vault uploads as a knowledge dump.")
        for action in report.get("actions", []):
            print(f"- [{action['status']}] {action['area']} {action['target']}: {action['detail']}")
        if report.get("error"):
            print(f"ERROR: {report['error']}", file=sys.stderr)

    return 2 if report.get("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
