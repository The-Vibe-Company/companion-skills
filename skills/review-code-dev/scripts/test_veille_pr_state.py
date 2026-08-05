#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("veille_pr_state.py")
spec = importlib.util.spec_from_file_location("veille_pr_state", SCRIPT)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class LedgerTests(unittest.TestCase):
    def test_baseline_claim_review_cycle(self):
        with tempfile.TemporaryDirectory(prefix="hermes-verify-veille-pr-") as temp:
            state_path = Path(temp) / "state.json"
            baseline = ledger.empty_state()
            baseline["initialized_at"] = ledger.iso_now()
            baseline["baseline"] = {
                ledger.pr_key("The-Vibe-Company/demo", 1): {
                    "repo": "The-Vibe-Company/demo",
                    "number": 1,
                    "url": "https://github.com/The-Vibe-Company/demo/pull/1",
                }
            }
            ledger.save_state(state_path, baseline)
            loaded = ledger.load_state(state_path)
            self.assertIn("the-vibe-company/demo#1", loaded["baseline"])

            key = ledger.pr_key("The-Vibe-Company/demo", 2)
            loaded["in_progress"][key] = {
                "repo": "The-Vibe-Company/demo",
                "number": 2,
                "url": "https://github.com/The-Vibe-Company/demo/pull/2",
                "claimed_at": ledger.iso_now(),
                "run_id": "test-run",
            }
            ledger.save_state(state_path, loaded)
            self.assertTrue(ledger.claim_is_active(ledger.load_state(state_path)["in_progress"][key]))

            reviewed = ledger.load_state(state_path)
            claim = reviewed["in_progress"].pop(key)
            reviewed["reviewed"][key] = {
                "repo": claim["repo"],
                "number": claim["number"],
                "url": claim["url"],
                "reviewed_at": ledger.iso_now(),
                "review_session": "session-test",
                "slack_message_id": "",
            }
            ledger.save_state(state_path, reviewed)
            final = ledger.load_state(state_path)
            self.assertNotIn(key, final["in_progress"])
            self.assertEqual("session-test", final["reviewed"][key]["review_session"])
            self.assertEqual(0o600, state_path.stat().st_mode & 0o777)

    def test_default_state_is_hermes_native(self):
        self.assertNotIn(".openclaw", str(ledger.DEFAULT_STATE))
        self.assertTrue(str(ledger.DEFAULT_STATE).endswith("/.hermes/state/veille-pr.json"))


if __name__ == "__main__":
    unittest.main()
