from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from audit_agent_readiness import audit
from cold_inventory import build_inventory
from compare_candidates import compare
from lint_instruction_stack import lint
from snapshot_instruction_stack import snapshot
from trace_instruction_chain import trace


class AgentInstructionScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "package.json").write_text(
            json.dumps({"scripts": {"test": "node --test"}}), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_snapshot_excludes_content_and_records_symlink(self) -> None:
        (self.repo / "CLAUDE.md").write_text(
            "# Private\nsecret body\n", encoding="utf-8"
        )
        os.symlink("CLAUDE.md", self.repo / "AGENTS.md")

        result = snapshot(self.repo, include_content=False)

        self.assertEqual(result["summary"]["files"], 2)
        self.assertEqual(result["summary"]["symlinks"], 1)
        self.assertTrue(all("content" not in item for item in result["files"]))
        agents = next(item for item in result["files"] if item["path"] == "AGENTS.md")
        self.assertEqual(agents["symlink_target"], "CLAUDE.md")

    def test_cold_inventory_does_not_emit_instruction_body(self) -> None:
        (self.repo / "AGENTS.md").write_text(
            "DO_NOT_LEAK_THIS_BODY\n", encoding="utf-8"
        )
        (self.repo / "README.md").write_text("# Sample\n", encoding="utf-8")

        result = build_inventory(self.repo)
        rendered = json.dumps(result)

        self.assertNotIn("DO_NOT_LEAK_THIS_BODY", rendered)
        self.assertIn("README.md", result["documentation"])

    def test_cold_inventory_finds_root_authorities_and_ignores_tool_skill_docs(
        self,
    ) -> None:
        (self.repo / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
        hidden = self.repo / ".agents" / "skills" / "foreign"
        hidden.mkdir(parents=True)
        (hidden / "DESIGN.md").write_text("# Foreign design\n", encoding="utf-8")

        result = build_inventory(self.repo)

        self.assertIn("ARCHITECTURE.md", result["documentation"])
        self.assertNotIn(".agents/skills/foreign/DESIGN.md", result["documentation"])

    def test_lint_reports_broken_import_private_data_and_unknown_script(self) -> None:
        proposed = self.repo / "proposed"
        proposed.mkdir()
        (proposed / "CLAUDE.md").write_text("@MISSING.md\n", encoding="utf-8")
        (proposed / "AGENTS.md").write_text(
            "# Rules\n\n- Email owner@example.invalid.\n- Run `npm run lint`.\n",
            encoding="utf-8",
        )

        result = lint(self.repo, proposed, 32 * 1024)
        codes = {item["code"] for item in result["issues"]}

        self.assertIn("broken-import", codes)
        self.assertIn("private-data", codes)
        self.assertIn("unknown-package-script", codes)
        self.assertFalse(result["summary"]["valid"])

    def test_compare_reports_reduction_and_rule_changes(self) -> None:
        current = self.repo / "current"
        proposed = self.repo / "proposed"
        current.mkdir()
        proposed.mkdir()
        (current / "AGENTS.md").write_text(
            "# Rules\n\n- Run every test after every edit because all changes are risky.\n- Write clean code and follow best practices everywhere.\n",
            encoding="utf-8",
        )
        (proposed / "AGENTS.md").write_text(
            "# Rules\n\n- When changing auth, run integration tests because unit tests skip RLS.\n",
            encoding="utf-8",
        )

        result = compare(current, proposed)

        self.assertLess(
            result["proposed"]["summary"]["words"],
            result["current"]["summary"]["words"],
        )
        self.assertEqual(len(result["rule_diff"]["added"]), 1)
        self.assertEqual(len(result["rule_diff"]["removed"]), 2)

    def test_lint_allows_a_missing_path_used_as_a_prohibition(self) -> None:
        proposed = self.repo / "proposed"
        proposed.mkdir()
        (proposed / "AGENTS.md").write_text(
            "# Trap\n\n- Do not create `src/app/layout.tsx`; a route group owns the document.\n",
            encoding="utf-8",
        )

        result = lint(self.repo, proposed, 32 * 1024)

        self.assertNotIn("missing-path", {item["code"] for item in result["issues"]})

    def test_readiness_audit_disambiguates_design_and_ignores_installed_skill_docs(
        self,
    ) -> None:
        (self.repo / "AGENTS.md").write_text(
            "# Map\n\n- UI: `DESIGN.md`.\n- Architecture: `docs/design.md`.\n",
            encoding="utf-8",
        )
        (self.repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        (self.repo / "DESIGN.md").write_text("# UI design\n", encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "design.md").write_text(
            "# Architecture\n", encoding="utf-8"
        )
        (self.repo / "README.md").write_text("# Sample\n", encoding="utf-8")
        hidden = self.repo / ".claude" / "skills" / "foreign"
        hidden.mkdir(parents=True)
        (hidden / "security.md").write_text(
            "# Foreign security notes\n", encoding="utf-8"
        )

        result = audit(self.repo)
        codes = {item["code"] for item in result["findings"]}

        self.assertEqual(result["dimensions"]["context_routing"]["status"], "strong")
        self.assertIn("multiple-design-names-disambiguated", codes)
        self.assertNotIn(
            ".claude/skills/foreign/security.md", result["authorities"]["security"]
        )

    def test_readiness_audit_flags_nested_agents_without_claude_adapter(self) -> None:
        (self.repo / "AGENTS.md").write_text("# Root\n", encoding="utf-8")
        nested = self.repo / "apps" / "api"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("# API\n", encoding="utf-8")

        result = audit(self.repo)
        finding = next(
            item
            for item in result["findings"]
            if item["code"] == "nested-claude-routing-gap"
        )

        self.assertEqual(finding["scopes"], ["apps/api"])

    def test_trace_models_root_to_subtree_candidates_per_host(self) -> None:
        (self.repo / "AGENTS.md").write_text("# Root\n", encoding="utf-8")
        (self.repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        nested = self.repo / "apps" / "api"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("# API\n", encoding="utf-8")
        (nested / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")

        codex = trace(self.repo, nested, "codex")
        claude = trace(self.repo, nested, "claude")

        self.assertEqual(
            [item["path"] for item in codex["instruction_candidates"]],
            ["AGENTS.md", "apps/api/AGENTS.md"],
        )
        self.assertEqual(
            [item["path"] for item in claude["instruction_candidates"]],
            ["CLAUDE.md", "apps/api/CLAUDE.md"],
        )


if __name__ == "__main__":
    unittest.main()
