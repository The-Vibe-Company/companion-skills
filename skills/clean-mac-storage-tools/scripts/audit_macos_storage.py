#!/usr/bin/env python3
"""Read-only macOS storage audit for the clean-mac-storage-tools skill."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DECIMAL_GB = 1_000_000_000
BINARY_GIB = 1_073_741_824


def human_decimal(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value / DECIMAL_GB:.1f} GB"


def human_binary(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value / BINARY_GIB:.1f} GiB"


def run_command(argv: list[str], timeout: int = 20) -> dict[str, Any]:
    executable = shutil.which(argv[0])
    if executable is None:
        return {"status": "unavailable", "command": argv}

    resolved = [executable, *argv[1:]]
    try:
        result = subprocess.run(
            resolved,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "command": argv,
            "timeout_seconds": timeout,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except OSError as exc:
        return {"status": "error", "command": argv, "error": str(exc)}

    return {
        "status": "ok" if result.returncode == 0 else "error",
        "command": argv,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def directory_size(path: Path, timeout: int) -> dict[str, Any]:
    entry: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return entry
    if path.is_symlink():
        entry.update({"skipped": True, "reason": "symlink_not_followed"})
        return entry

    result = run_command(["du", "-sk", str(path)], timeout=timeout)
    entry["measurement"] = result["status"]
    if result.get("status") == "ok":
        first_field = result.get("stdout", "").split(maxsplit=1)[0]
        try:
            entry["bytes"] = int(first_field) * 1024
        except ValueError:
            entry["error"] = "unexpected_du_output"
    else:
        entry["error"] = result.get("stderr") or result.get("error") or result["status"]
    return entry


def candidate_specs(home: Path, include_personal: bool) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "label": "User caches",
            "path": home / "Library" / "Caches",
            "tier": "A",
            "policy": "Review per application; quit and reopen affected apps.",
        },
        {
            "label": "User logs",
            "path": home / "Library" / "Logs",
            "tier": "A",
            "policy": "Review exact log directories; preserve active diagnostics when needed.",
        },
        {
            "label": "Xcode DerivedData",
            "path": home / "Library" / "Developer" / "Xcode" / "DerivedData",
            "tier": "A",
            "policy": "Rebuildable; Xcode will compile again.",
        },
        {
            "label": "Xcode archives",
            "path": home / "Library" / "Developer" / "Xcode" / "Archives",
            "tier": "C",
            "policy": "Review archive by archive; some are needed for distribution or symbolication.",
        },
        {
            "label": "Simulator devices",
            "path": home / "Library" / "Developer" / "CoreSimulator" / "Devices",
            "tier": "B",
            "policy": "Use simctl identifiers; preserve booted and user-designated devices.",
        },
        {
            "label": "npm download cache",
            "path": home / ".npm" / "_cacache",
            "tier": "A",
            "policy": "Rebuildable; future installs download packages again.",
        },
        {
            "label": "pnpm store",
            "path": home / "Library" / "pnpm" / "store",
            "tier": "A",
            "policy": "Prune with pnpm when available; future installs may download packages again.",
        },
        {
            "label": "Legacy pnpm store",
            "path": home / ".pnpm-store",
            "tier": "A",
            "policy": "Confirm the active pnpm store before cleanup.",
        },
        {
            "label": "Bun download cache",
            "path": home / ".bun" / "install" / "cache",
            "tier": "A",
            "policy": "Rebuildable; future installs download packages again.",
        },
        {
            "label": "uv cache",
            "path": home / ".cache" / "uv",
            "tier": "A",
            "policy": "Rebuildable; future installs download Python packages again.",
        },
        {
            "label": "Homebrew downloads",
            "path": home / "Library" / "Caches" / "Homebrew",
            "tier": "A",
            "policy": "Use brew cleanup when available.",
        },
        {
            "label": "Android virtual devices",
            "path": home / ".android" / "avd",
            "tier": "B",
            "policy": "Review AVDs individually; preserve active development devices.",
        },
    ]

    if include_personal:
        for label, relative in (
            ("Downloads", "Downloads"),
            ("Movies", "Movies"),
            ("Documents", "Documents"),
            ("Pictures", "Pictures"),
        ):
            specs.append(
                {
                    "label": label,
                    "path": home / relative,
                    "tier": "C",
                    "policy": "Size only. Review exact user files and prefer Trash.",
                }
            )
    return specs


def collect_df(path: Path) -> dict[str, Any]:
    result = run_command(["df", "-kP", str(path)])
    if result.get("status") != "ok":
        return result
    lines = result.get("stdout", "").splitlines()
    if len(lines) < 2:
        return {"status": "error", "error": "unexpected_df_output"}
    fields = lines[-1].split()
    if len(fields) < 6:
        return {"status": "error", "error": "unexpected_df_output"}
    try:
        return {
            "status": "ok",
            "filesystem": fields[0],
            "total_bytes": int(fields[1]) * 1024,
            "used_bytes": int(fields[2]) * 1024,
            "available_bytes": int(fields[3]) * 1024,
            "capacity": fields[4],
            "mount_point": " ".join(fields[5:]),
        }
    except ValueError:
        return {"status": "error", "error": "unexpected_df_output"}


def collect_diskutil(path: Path) -> dict[str, Any]:
    executable = shutil.which("diskutil")
    if executable is None:
        return {"status": "unavailable"}
    try:
        result = subprocess.run(
            [executable, "info", "-plist", str(path)],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "error": str(exc)}
    if result.returncode != 0:
        return {
            "status": "error",
            "returncode": result.returncode,
            "stderr": result.stderr.decode(errors="replace").strip(),
        }
    try:
        info = plistlib.loads(result.stdout)
    except plistlib.InvalidFileException as exc:
        return {"status": "error", "error": f"invalid_plist: {exc}"}
    return {
        "status": "ok",
        "device_identifier": info.get("DeviceIdentifier"),
        "mount_point": info.get("MountPoint"),
        "filesystem_type": info.get("FilesystemType"),
        "volume_name": info.get("VolumeName"),
        "capacity_in_use_bytes": info.get("CapacityInUse"),
        "container_size_bytes": info.get("APFSContainerSize") or info.get("TotalSize"),
        "container_free_bytes": info.get("APFSContainerFree"),
    }


def collect_volume(home: Path, target_gb: float | None) -> dict[str, Any]:
    data_mount = Path("/System/Volumes/Data")
    measured_path = data_mount if data_mount.is_dir() else home
    diskutil = collect_diskutil(measured_path)
    df = collect_df(measured_path)

    if diskutil.get("status") == "ok" and isinstance(diskutil.get("capacity_in_use_bytes"), int):
        used_bytes = int(diskutil["capacity_in_use_bytes"])
        available_bytes = diskutil.get("container_free_bytes")
        total_bytes = diskutil.get("container_size_bytes")
        method = "diskutil_apfs_data_capacity_in_use"
    elif df.get("status") == "ok":
        used_bytes = int(df["used_bytes"])
        available_bytes = int(df["available_bytes"])
        total_bytes = int(df["total_bytes"])
        method = "df_used_blocks"
    else:
        usage = shutil.disk_usage(home)
        used_bytes = usage.used
        available_bytes = usage.free
        total_bytes = usage.total
        method = "shutil_fallback_total_minus_free"

    result: dict[str, Any] = {
        "path": str(measured_path),
        "measurement_method": method,
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "available_bytes": available_bytes,
        "used_decimal_gb": round(used_bytes / DECIMAL_GB, 3),
        "used_binary_gib": round(used_bytes / BINARY_GIB, 3),
        "available_decimal_gb": round(available_bytes / DECIMAL_GB, 3) if available_bytes is not None else None,
        "available_binary_gib": round(available_bytes / BINARY_GIB, 3) if available_bytes is not None else None,
        "df": df,
        "apfs": diskutil,
    }
    if target_gb is not None:
        target_bytes = int(target_gb * DECIMAL_GB)
        result.update(
            {
                "target_used_decimal_gb": target_gb,
                "bytes_above_target": max(0, used_bytes - target_bytes),
                "decimal_gb_above_target": round(max(0, used_bytes - target_bytes) / DECIMAL_GB, 3),
                "target_reached": used_bytes < target_bytes,
            }
        )
    return result


def collect_candidates(home: Path, include_personal: bool, timeout: int) -> list[dict[str, Any]]:
    specs = candidate_specs(home, include_personal)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(specs))) as executor:
        futures = [executor.submit(directory_size, spec["path"], timeout) for spec in specs]
        measurements = [future.result() for future in futures]

    candidates: list[dict[str, Any]] = []
    for spec, measurement in zip(specs, measurements):
        entry = {key: value for key, value in spec.items() if key != "path"}
        entry.update(measurement)
        candidates.append(entry)
    candidates.sort(key=lambda item: item.get("bytes", -1), reverse=True)
    return candidates


def collect_tool_state(timeout: int) -> dict[str, Any]:
    return {
        "docker_disk_usage": run_command(["docker", "system", "df"], timeout=timeout),
        "xcode_runtimes": run_command(["xcrun", "simctl", "list", "runtimes", "--json"], timeout=timeout),
        "xcode_devices": run_command(["xcrun", "simctl", "list", "devices", "--json"], timeout=timeout),
        "time_machine_snapshots": run_command(["tmutil", "listlocalsnapshots", "/"], timeout=timeout),
    }


def render_markdown(report: dict[str, Any]) -> str:
    volume = report["volume"]
    lines = [
        "# Read-only macOS storage audit",
        "",
        f"Generated: {report['generated_at']}",
        f"Home: `{report['home']}`",
        f"Used: {human_decimal(volume['used_bytes'])} ({human_binary(volume['used_bytes'])})",
        f"Available: {human_decimal(volume['available_bytes'])} ({human_binary(volume['available_bytes'])})",
    ]
    if "target_used_decimal_gb" in volume:
        lines.extend(
            [
                f"Target: below {volume['target_used_decimal_gb']:.1f} GB used",
                f"Gap: {human_decimal(volume['bytes_above_target'])}",
                f"Target already reached: {'yes' if volume['target_reached'] else 'no'}",
            ]
        )

    lines.extend(["", "## Candidate paths", "", "| Candidate | Tier | Size | Policy |", "|---|---:|---:|---|"])
    for item in report["candidates"]:
        size = human_decimal(item.get("bytes")) if item.get("exists") else "not present"
        lines.append(f"| {item['label']} | {item['tier']} | {size} | {item['policy']} |")

    lines.extend(["", "## Optional tool state", ""])
    for name, state in report["tools"].items():
        lines.append(f"- {name}: {state['status']}")
    lines.extend(
        [
            "",
            "> This report is inventory only. It does not authorize or perform deletion.",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect a read-only macOS storage inventory. No files or tool state are modified."
    )
    parser.add_argument("--target-gb", type=float, help="Desired maximum used space in decimal GB.")
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home directory to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument(
        "--include-personal-summary",
        action="store_true",
        help="Measure personal top-level folders as protected Tier C candidates.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-command timeout in seconds (default: 30).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if platform.system() != "Darwin":
        message = {
            "ok": False,
            "error": "unsupported_platform",
            "message": "This helper supports macOS only and made no changes.",
        }
        print(json.dumps(message, indent=2) if args.json else message["message"])
        return 2

    home = args.home.expanduser().resolve()
    if not home.is_dir():
        message = {"ok": False, "error": "invalid_home", "path": str(home)}
        print(json.dumps(message, indent=2) if args.json else f"Invalid home directory: {home}")
        return 2

    if args.target_gb is not None and args.target_gb <= 0:
        message = {"ok": False, "error": "invalid_target", "target_gb": args.target_gb}
        print(json.dumps(message, indent=2) if args.json else "Target must be greater than zero.")
        return 2

    if args.timeout <= 0:
        message = {"ok": False, "error": "invalid_timeout", "timeout": args.timeout}
        print(json.dumps(message, indent=2) if args.json else "Timeout must be greater than zero.")
        return 2

    report = {
        "ok": True,
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "home": str(home),
        "read_only": True,
        "volume": collect_volume(home, args.target_gb),
        "candidates": collect_candidates(home, args.include_personal_summary, args.timeout),
        "tools": collect_tool_state(args.timeout),
        "notes": [
            "Candidate sizes are evidence, not deletion approval.",
            "APFS and sparse-image accounting can make estimated and actual recovery differ.",
            "Application Support, Containers, Group Containers, Docker volumes, and personal files are protected by default.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
