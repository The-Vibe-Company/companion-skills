from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "setup_granite.py"
SPEC = importlib.util.spec_from_file_location("setup_granite", SCRIPT)
assert SPEC and SPEC.loader
setup_granite = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup_granite
SPEC.loader.exec_module(setup_granite)


class ManagedBlockTests(unittest.TestCase):
    def test_user_path_uses_overridden_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            self.assertEqual(setup_granite.resolve_user_path("~/.granite", home), home.resolve() / ".granite")

    def test_add_and_repeat_is_idempotent(self) -> None:
        first, change = setup_granite.replace_managed_block("# Project\n", setup_granite.GRANITE_RULE)
        self.assertEqual(change, "added")
        second, change = setup_granite.replace_managed_block(first, setup_granite.GRANITE_RULE)
        self.assertEqual(change, "unchanged")
        self.assertEqual(first, second)
        self.assertEqual(second.count(setup_granite.START_MARKER), 1)

    def test_managed_rule_makes_harness_and_no_dump_model_explicit(self) -> None:
        rule = setup_granite.GRANITE_RULE.lower()
        self.assertIn("llm-operated knowledge compiler", rule)
        self.assertIn("not a file dump", rule)
        self.assertIn("must use the granite mcp for every knowledge operation", rule)
        self.assertIn("do not use granite cli knowledge commands", rule)
        self.assertIn("do not edit vault markdown files directly", rule)
        self.assertIn("granite_capture_knowledge", rule)
        self.assertIn("do not declare the granite knowledge runtime verified", rule)
        self.assertIn("do not tell users to upload", rule)
        self.assertIn("analyze its meaning", rule)

    def test_incomplete_block_is_rejected(self) -> None:
        with self.assertRaises(setup_granite.SetupError):
            setup_granite.replace_managed_block(setup_granite.START_MARKER, setup_granite.GRANITE_RULE)

    def test_duplicate_blocks_are_rejected(self) -> None:
        text = f"{setup_granite.GRANITE_RULE}\n{setup_granite.GRANITE_RULE}\n"
        with self.assertRaises(setup_granite.SetupError):
            setup_granite.replace_managed_block(text, setup_granite.GRANITE_RULE)

    def test_mcp_match_requires_same_binary_and_vault(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / "granite"
            other = root / "other-granite"
            vault = root / ".granite"
            binary.touch()
            other.touch()
            output = f"command: {other}\nargs: mcp --vault {vault}\n"
            self.assertFalse(setup_granite.output_matches_mcp(output, binary, vault))
            output = f"command: {binary}\nargs: mcp --vault {vault}\n"
            self.assertTrue(setup_granite.output_matches_mcp(output, binary, vault))


class GraniteUpdateTests(unittest.TestCase):
    def test_fresh_install_dry_run_does_not_execute_predicted_binary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            predicted = Path(raw) / "bin" / "granite"
            actions: list[setup_granite.Action] = []
            binary, report, updated = setup_granite.update_granite(
                binary=predicted,
                requested=True,
                apply=False,
                explicit_binary=None,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertEqual(binary, predicted)
            self.assertFalse(updated)
            self.assertFalse(report["update_available"])
            self.assertIn("fresh granite-mem@latest installation", actions[0].detail)

    @mock.patch.object(setup_granite, "command_exists", return_value="/usr/bin/npm")
    @mock.patch.object(setup_granite, "run")
    def test_dry_run_plans_update_only_when_registry_is_newer(
        self,
        run_command: mock.Mock,
        _command_exists: mock.Mock,
    ) -> None:
        run_command.side_effect = [
            subprocess.CompletedProcess([], 0, "0.1.11\n"),
            subprocess.CompletedProcess([], 0, '"0.1.12"\n'),
        ]
        with tempfile.TemporaryDirectory() as raw:
            installed = Path(raw) / "granite"
            installed.touch()
            actions: list[setup_granite.Action] = []
            binary, report, updated = setup_granite.update_granite(
                binary=installed,
                requested=True,
                apply=False,
                explicit_binary=None,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertEqual(binary, installed)
            self.assertFalse(updated)
            self.assertTrue(report["update_available"])
            self.assertEqual(report["installed_version"], "0.1.11")
            self.assertEqual(report["latest_version"], "0.1.12")
            self.assertEqual(actions[0].status, "planned")
            self.assertEqual(actions[0].command[-1], "granite-mem@latest")

    @mock.patch.object(setup_granite, "command_exists", return_value="/usr/bin/npm")
    @mock.patch.object(setup_granite, "run")
    def test_current_version_does_not_reinstall(
        self,
        run_command: mock.Mock,
        _command_exists: mock.Mock,
    ) -> None:
        run_command.side_effect = [
            subprocess.CompletedProcess([], 0, "granite 0.1.12\n"),
            subprocess.CompletedProcess([], 0, '"0.1.12"\n'),
        ]
        actions: list[setup_granite.Action] = []
        _, report, updated = setup_granite.update_granite(
            binary=Path("/tmp/granite"),
            requested=True,
            apply=True,
            explicit_binary=None,
            env=dict(os.environ),
            actions=actions,
        )
        self.assertFalse(updated)
        self.assertFalse(report["update_available"])
        self.assertEqual(actions[0].status, "ok")
        self.assertEqual(run_command.call_count, 2)

    @mock.patch.object(setup_granite, "command_exists", return_value="/usr/bin/npm")
    @mock.patch.object(setup_granite, "run")
    def test_newer_installed_version_is_never_downgraded(
        self,
        run_command: mock.Mock,
        _command_exists: mock.Mock,
    ) -> None:
        run_command.side_effect = [
            subprocess.CompletedProcess([], 0, "0.1.14\n"),
            subprocess.CompletedProcess([], 0, '"0.1.13"\n'),
        ]
        actions: list[setup_granite.Action] = []
        _, report, updated = setup_granite.update_granite(
            binary=Path("/tmp/granite"),
            requested=True,
            apply=True,
            explicit_binary=None,
            env=dict(os.environ),
            actions=actions,
        )
        self.assertFalse(updated)
        self.assertFalse(report["update_available"])
        self.assertIn("no downgrade", actions[0].detail)
        self.assertEqual(run_command.call_count, 2)

    @mock.patch.object(setup_granite, "resolve_granite_binary", return_value=Path("/updated/granite"))
    @mock.patch.object(setup_granite, "command_exists", return_value="/usr/bin/npm")
    @mock.patch.object(setup_granite, "run")
    def test_apply_updates_and_verifies_installed_version(
        self,
        run_command: mock.Mock,
        _command_exists: mock.Mock,
        _resolve: mock.Mock,
    ) -> None:
        run_command.side_effect = [
            subprocess.CompletedProcess([], 0, "0.1.11\n"),
            subprocess.CompletedProcess([], 0, '"0.1.12"\n'),
            subprocess.CompletedProcess([], 0, "installed\n"),
            subprocess.CompletedProcess([], 0, "0.1.12\n"),
        ]
        actions: list[setup_granite.Action] = []
        binary, report, updated = setup_granite.update_granite(
            binary=Path("/old/granite"),
            requested=True,
            apply=True,
            explicit_binary=None,
            env=dict(os.environ),
            actions=actions,
        )
        self.assertEqual(binary, Path("/updated/granite"))
        self.assertTrue(updated)
        self.assertTrue(report["updated"])
        self.assertEqual(actions[0].status, "changed")
        self.assertEqual(run_command.call_args_list[2].args[0], ["/usr/bin/npm", "install", "-g", "granite-mem@latest"])


class WebDaemonTests(unittest.TestCase):
    def test_parse_daemon_status(self) -> None:
        output = """Granite daemon running (PID 123)
  Vault:   /tmp/home/.granite
  MCP:     http://127.0.0.1:3321/mcp
  Web:     http://127.0.0.1:4321
"""
        status = setup_granite.parse_daemon_status(output)
        self.assertIsNotNone(status)
        assert status
        self.assertEqual(status["web_port"], 4321)
        self.assertEqual(status["mcp_port"], 3321)

    @mock.patch.object(setup_granite, "read_daemon_status", return_value=None)
    @mock.patch.object(setup_granite, "port_available", return_value=True)
    def test_dry_run_plans_persistent_4321(self, _port: mock.Mock, _status: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / "granite"
            vault = root / ".granite"
            actions: list[setup_granite.Action] = []
            result = setup_granite.configure_web_daemon(
                binary=binary,
                vault=vault,
                apply=False,
                replace=False,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertTrue(result["persistent"])
            self.assertEqual(result["web_url"], "http://127.0.0.1:4321")
            self.assertEqual(actions[0].status, "planned")
            self.assertIn("daemon", actions[0].command)
            self.assertEqual(actions[0].environment, {"GRANITE_VAULT": str(vault)})

    @mock.patch.object(setup_granite, "http_responding", return_value=True)
    @mock.patch.object(setup_granite, "read_daemon_status")
    def test_existing_matching_daemon_is_idempotent(self, status: mock.Mock, _http: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            status.return_value = {
                "vault": str(vault.resolve()),
                "host": "127.0.0.1",
                "mcp_port": 3321,
                "web_port": 4321,
                "mcp_url": "http://127.0.0.1:3321/mcp",
                "web_url": "http://127.0.0.1:4321",
            }
            actions: list[setup_granite.Action] = []
            result = setup_granite.configure_web_daemon(
                binary=root / "granite",
                vault=vault,
                apply=True,
                replace=False,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(actions[0].status, "ok")

    @mock.patch.object(setup_granite, "wait_for_http", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_ports_available", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_daemon_status")
    @mock.patch.object(setup_granite, "http_responding", return_value=False)
    @mock.patch.object(setup_granite, "read_daemon_status")
    @mock.patch.object(setup_granite, "run")
    def test_matching_unhealthy_dashboard_is_restarted_and_verified(
        self,
        run_command: mock.Mock,
        status: mock.Mock,
        _http: mock.Mock,
        confirmed_status: mock.Mock,
        _ports: mock.Mock,
        _wait_http: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            desired = {
                "vault": str(vault.resolve()),
                "host": "127.0.0.1",
                "mcp_port": 3321,
                "web_port": 4321,
                "mcp_url": "http://127.0.0.1:3321/mcp",
                "web_url": "http://127.0.0.1:4321",
            }
            status.return_value = desired
            confirmed_status.return_value = desired
            run_command.return_value = subprocess.CompletedProcess([], 0, "")
            actions: list[setup_granite.Action] = []
            result = setup_granite.configure_web_daemon(
                binary=root / "granite",
                vault=vault,
                apply=True,
                replace=False,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(actions[0].status, "changed")
            self.assertIn("Restarted", actions[0].detail)
            self.assertEqual(run_command.call_args_list[0].args[0][-2:], ["daemon", "stop"])

    @mock.patch.object(setup_granite, "wait_for_http", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_ports_available", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_daemon_status")
    @mock.patch.object(setup_granite, "http_responding", return_value=True)
    @mock.patch.object(setup_granite, "read_daemon_status")
    @mock.patch.object(setup_granite, "run")
    def test_update_forces_healthy_daemon_restart(
        self,
        run_command: mock.Mock,
        status: mock.Mock,
        _http: mock.Mock,
        confirmed_status: mock.Mock,
        _ports: mock.Mock,
        _wait_http: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            desired = {
                "vault": str(vault.resolve()),
                "host": "127.0.0.1",
                "mcp_port": 3321,
                "web_port": 4321,
                "mcp_url": "http://127.0.0.1:3321/mcp",
                "web_url": "http://127.0.0.1:4321",
            }
            status.return_value = desired
            confirmed_status.return_value = desired
            run_command.return_value = subprocess.CompletedProcess([], 0, "")
            actions: list[setup_granite.Action] = []
            setup_granite.configure_web_daemon(
                binary=root / "granite",
                vault=vault,
                apply=True,
                replace=False,
                force_restart=True,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertEqual(actions[0].status, "changed")
            self.assertEqual(run_command.call_args_list[0].args[0][-2:], ["daemon", "stop"])

    @mock.patch.object(setup_granite, "read_daemon_status", return_value=None)
    @mock.patch.object(setup_granite, "port_available")
    def test_foreign_port_conflict_blocks(self, available: mock.Mock, _status: mock.Mock) -> None:
        available.side_effect = lambda _host, port: port != 4321
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            actions: list[setup_granite.Action] = []
            result = setup_granite.configure_web_daemon(
                binary=root / "granite",
                vault=root / ".granite",
                apply=False,
                replace=False,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertFalse(result["ok"])
            self.assertEqual(actions[0].status, "blocked")
            self.assertIn("4321", actions[0].detail)

    @mock.patch.object(setup_granite, "wait_for_http", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_ports_available", return_value=True)
    @mock.patch.object(setup_granite, "port_available", return_value=True)
    @mock.patch.object(setup_granite, "wait_for_daemon_status")
    @mock.patch.object(setup_granite, "read_daemon_status", return_value=None)
    @mock.patch.object(setup_granite, "run")
    def test_apply_starts_and_verifies_persistent_daemon(
        self,
        run_command: mock.Mock,
        _initial_status: mock.Mock,
        confirmed_status: mock.Mock,
        _port: mock.Mock,
        _ports: mock.Mock,
        _http: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            desired = {
                "vault": str(vault.resolve()),
                "host": "127.0.0.1",
                "mcp_port": 3321,
                "web_port": 4321,
                "mcp_url": "http://127.0.0.1:3321/mcp",
                "web_url": "http://127.0.0.1:4321",
            }
            confirmed_status.return_value = desired
            run_command.return_value = subprocess.CompletedProcess([], 0, "")
            actions: list[setup_granite.Action] = []
            result = setup_granite.configure_web_daemon(
                binary=root / "granite",
                vault=vault,
                apply=True,
                replace=False,
                web_port=4321,
                mcp_port=3321,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(actions[0].status, "changed")
            self.assertEqual(actions[0].environment, {"GRANITE_VAULT": str(vault)})
            command = run_command.call_args.args[0]
            self.assertEqual(command[-4:], ["--mcp-port", "3321", "--web-port", "4321"])
            self.assertEqual(run_command.call_args.kwargs["env"]["GRANITE_VAULT"], str(vault))


class GuidanceTests(unittest.TestCase):
    def test_symlinked_guidance_is_written_once(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "CLAUDE.md").write_text("# Rules\n", encoding="utf-8")
            (root / "AGENTS.md").symlink_to("CLAUDE.md")
            actions: list[setup_granite.Action] = []
            setup_granite.configure_guidance(root, True, actions)
            text = (root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertEqual(text.count(setup_granite.START_MARKER), 1)
            self.assertEqual(len(actions), 1)
            self.assertIn("AGENTS.md", actions[0].target)
            self.assertIn("CLAUDE.md", actions[0].target)


class CursorTests(unittest.TestCase):
    def test_cursor_merge_preserves_other_servers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".cursor" / "mcp.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"mcpServers": {"other": {"url": "https://example.test/mcp"}}}), encoding="utf-8")
            binary = home / "bin" / "granite"
            binary.parent.mkdir()
            binary.touch()
            vault = home / ".granite"
            actions: list[setup_granite.Action] = []
            setup_granite.configure_cursor(
                binary=binary,
                vault=vault,
                apply=True,
                replace=False,
                home=home,
                actions=actions,
            )
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertIn("other", data["mcpServers"])
            self.assertEqual(data["mcpServers"]["granite"]["command"], str(binary))

    def test_cursor_conflict_requires_replace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".cursor" / "mcp.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps({"mcpServers": {"granite": {"command": "old", "args": ["mcp"]}}}),
                encoding="utf-8",
            )
            binary = home / "granite"
            binary.touch()
            actions: list[setup_granite.Action] = []
            setup_granite.configure_cursor(
                binary=binary,
                vault=home / ".granite",
                apply=False,
                replace=False,
                home=home,
                actions=actions,
            )
            self.assertEqual(actions[0].status, "blocked")


class IntegrationTests(unittest.TestCase):
    def test_maintenance_mode_can_skip_mcp_hosts_and_guidance(self) -> None:
        with mock.patch.object(sys, "argv", [str(SCRIPT), "--skip-mcp", "--skip-guidance"]):
            args = setup_granite.build_parser().parse_args()
        self.assertTrue(args.skip_mcp)
        self.assertTrue(args.skip_guidance)

    def test_invalid_existing_vault_blocks_before_cursor_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            binary = root / "granite"
            cursor_config = home / ".cursor" / "mcp.json"
            vault = home / ".granite"
            home.mkdir()
            project.mkdir()
            cursor_config.parent.mkdir()
            vault.mkdir()
            (vault / "granite.yml").write_text("invalid: [\n", encoding="utf-8")
            original = {"mcpServers": {"granite": {"command": "/known/good/granite", "args": ["mcp"]}}}
            cursor_config.write_text(json.dumps(original), encoding="utf-8")
            binary.write_text(
                "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 9.9.9; exit 0; fi\nexit 8\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)

            command = [
                sys.executable,
                str(SCRIPT),
                "--home",
                str(home),
                "--project-root",
                str(project),
                "--hosts",
                "cursor",
                "--granite-bin",
                str(binary),
                "--replace-mcp",
                "--apply",
                "--skip-web",
                "--json",
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertIn("failed `granite status`", report["actions"][1]["detail"])
            self.assertEqual(json.loads(cursor_config.read_text(encoding="utf-8")), original)

    def test_broken_granite_binary_blocks_before_cursor_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            binary = root / "granite"
            cursor_config = home / ".cursor" / "mcp.json"
            vault = home / ".granite"
            home.mkdir()
            project.mkdir()
            cursor_config.parent.mkdir()
            vault.mkdir()
            (vault / "granite.yml").write_text("vault_name: Existing\n", encoding="utf-8")
            original = {"mcpServers": {"granite": {"command": "/known/good/granite", "args": ["mcp"]}}}
            cursor_config.write_text(json.dumps(original), encoding="utf-8")
            binary.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
            binary.chmod(0o755)

            command = [
                sys.executable,
                str(SCRIPT),
                "--home",
                str(home),
                "--project-root",
                str(project),
                "--hosts",
                "cursor",
                "--granite-bin",
                str(binary),
                "--replace-mcp",
                "--apply",
                "--json",
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertIn("`granite --version` failed", report["actions"][0]["detail"])
            self.assertEqual(json.loads(cursor_config.read_text(encoding="utf-8")), original)

    def test_missing_project_root_is_rejected_without_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            missing = root / "typo-project"
            command = [
                sys.executable,
                str(SCRIPT),
                "--home",
                str(root),
                "--project-root",
                str(missing),
                "--hosts",
                "cursor",
                "--skip-install",
                "--json",
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(missing.exists())
            self.assertIn("Project root does not exist", json.loads(result.stdout)["error"])

    def test_codex_failed_add_restores_config(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            bin_dir = root / "bin"
            config = home / ".codex" / "config.toml"
            binary = bin_dir / "granite"
            codex = bin_dir / "codex"
            vault = home / ".granite"
            bin_dir.mkdir()
            config.parent.mkdir(parents=True)
            vault.mkdir()
            binary.touch()
            original = 'original = "keep"\n'
            config.write_text(original, encoding="utf-8")
            codex.write_text(
                """#!/usr/bin/env python3
import os
import sys
from pathlib import Path

config = Path(os.environ["HOME"]) / ".codex" / "config.toml"
args = sys.argv[1:]
if args[:3] == ["mcp", "get", "granite"]:
    print("command: /old/granite")
    print(f"args: mcp --vault {Path(os.environ['HOME']) / '.granite'}")
elif args[:3] == ["mcp", "remove", "granite"]:
    config.write_text("removed\\n", encoding="utf-8")
elif args[:3] == ["mcp", "add", "granite"]:
    config.write_text("partial\\n", encoding="utf-8")
    raise SystemExit(7)
else:
    raise SystemExit(2)
""",
                encoding="utf-8",
            )
            codex.chmod(0o755)
            env = dict(os.environ)
            env["HOME"] = str(home)
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            actions: list[setup_granite.Action] = []
            with self.assertRaises(setup_granite.SetupError):
                setup_granite.configure_codex(
                    binary=binary,
                    vault=vault,
                    apply=True,
                    replace=True,
                    env=env,
                    actions=actions,
                )
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_minimal_template_omits_template_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            binary = root / "granite"
            binary.touch()
            actions: list[setup_granite.Action] = []
            setup_granite.initialize_vault(
                binary=binary,
                vault=vault,
                template="minimal",
                apply=False,
                skip_init=False,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertEqual(actions[0].command, [str(binary), "init"])
            self.assertNotIn("--template", actions[0].command)

    def test_nonempty_unknown_vault_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            vault = root / ".granite"
            vault.mkdir()
            (vault / "existing.md").write_text("keep me", encoding="utf-8")
            binary = root / "granite"
            binary.touch()
            actions: list[setup_granite.Action] = []
            setup_granite.initialize_vault(
                binary=binary,
                vault=vault,
                template="founder-os",
                apply=True,
                skip_init=False,
                env=dict(os.environ),
                actions=actions,
            )
            self.assertEqual(actions[0].status, "blocked")
            self.assertTrue((vault / "existing.md").exists())
            self.assertFalse((vault / "granite.yml").exists())

    def test_apply_new_cursor_setup_in_isolated_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            binary = root / "bin" / "granite"
            home.mkdir()
            project.mkdir()
            (home / ".cursor").mkdir()
            binary.parent.mkdir()
            binary.write_text(
                """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if args == ["--version"]:
    print("9.9.9-test")
elif args[:1] == ["init"]:
    vault = Path(os.environ["HOME"]) / ".granite"
    (vault / "notes").mkdir(parents=True, exist_ok=True)
    (vault / "granite.yml").write_text("vault_name: Test Vault\\n", encoding="utf-8")
    print(f"Vault initialized in {vault}")
elif args[:2] == ["status", "--json"]:
    print(json.dumps({"success": True, "data": {"note_count": 0}}))
elif args[:2] == ["wakeup", "--json"]:
    print(json.dumps({"success": True, "data": {"aaak": "VAULT: 0n"}}))
elif args[:2] == ["doctor", "--json"]:
    print(json.dumps({"success": True, "data": {"healthy": True}}))
else:
    print("unsupported", args, file=sys.stderr)
    raise SystemExit(2)
""",
                encoding="utf-8",
            )
            binary.chmod(0o755)

            command = [
                sys.executable,
                str(SCRIPT),
                "--home",
                str(home),
                "--project-root",
                str(project),
                "--hosts",
                "cursor",
                "--granite-bin",
                str(binary),
                "--apply",
                "--skip-web",
                "--json",
            ]
            env = dict(os.environ)
            result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["blocked"], 0)
            self.assertTrue(report["usage_model"]["harness_required"])
            self.assertEqual(report["usage_model"]["knowledge_interface"], "mcp")
            self.assertTrue(report["usage_model"]["mcp_required_for_knowledge_operations"])
            self.assertFalse(report["usage_model"]["cli_knowledge_operations_allowed"])
            self.assertEqual(
                report["usage_model"]["mcp_runtime_verification_requires"],
                ["granite_wakeup", "real_mcp_retrieval_against_intended_vault"],
            )
            self.assertFalse(report["usage_model"]["direct_file_upload_recommended"])
            self.assertIn("analyze_with_llm", report["usage_model"]["file_ingestion_flow"])
            self.assertNotIn("wakeup", report["verification"])
            self.assertTrue(report["verification"]["mcp_knowledge_runtime"]["pending"])
            self.assertTrue(report["verification"]["mcp_knowledge_runtime"]["required"])
            self.assertTrue((home / ".granite" / "granite.yml").exists())
            self.assertIn("granite", json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"])
            self.assertIn(setup_granite.START_MARKER, (project / "AGENTS.md").read_text())
            self.assertIn(setup_granite.START_MARKER, (project / "CLAUDE.md").read_text())
            self.assertNotIn("wakeup", report["verification"])
            self.assertNotIn("output", report["verification"]["mcp_knowledge_runtime"])


if __name__ == "__main__":
    unittest.main()
