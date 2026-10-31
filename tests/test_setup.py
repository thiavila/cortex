import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tarefas"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("cortex_setup", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
BOARD = "59bf3890-fd06-4b1b-933e-69a9c094e80b"


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self, agents, **kwargs):
        return setup.configure(self.root, "test", agents, "Board", "en-US", "UTC", **kwargs)

    def init_mock(self):
        return patch.object(setup.subprocess, "run", return_value=SimpleNamespace(
            returncode=0, stdout=json.dumps({"board": BOARD})))

    def test_claude_only_does_not_initialize_database(self):
        with self.init_mock() as initialize:
            value = self.configure(["Claude Code"])
        self.assertEqual(value["backend"], "artifact")
        self.assertNotIn("board", value)
        initialize.assert_not_called()

    def test_any_other_agent_selects_local(self):
        for agents in (["codex"], ["claude", "codex"], ["Some Future Agent"]):
            with self.subTest(agents=agents), self.init_mock():
                value = self.configure(agents)
                self.assertEqual(value["backend"], "local")
                self.assertEqual(value["board"], BOARD)

    def test_repeated_setup_keeps_board_even_with_new_agent(self):
        with self.init_mock() as initialize:
            first = self.configure(["codex"])
            second = self.configure(["claude", "codex", "gemini"])
        self.assertEqual(first["board"], second["board"])
        self.assertEqual(initialize.call_count, 1)

    def test_switch_needs_explicit_confirmation_and_preserves_selection(self):
        original = self.configure(["claude"])
        with self.init_mock() as initialize, self.assertRaises(setup.SetupError):
            self.configure(["codex"])
        initialize.assert_not_called()
        self.assertEqual(setup.read_selection(setup.profile_path(self.root, "test")), original)
        with self.init_mock():
            self.assertEqual(self.configure(["codex"], replace=True)["backend"], "local")

    def test_status_absent_is_read_only(self):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), "--root", str(self.root),
                               "--profile", "test", "status"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["configured"])
        self.assertFalse(self.root.exists())

    def test_profile_is_explicit_and_not_a_path(self):
        for profile in (None, "../other", "/tmp/other", "Mixed Case"):
            with self.subTest(profile=profile), self.assertRaises(setup.SetupError):
                setup.profile_path(self.root, profile)

    def test_invalid_selection_never_falls_back(self):
        path = setup.profile_path(self.root, "test")
        path.parent.mkdir(parents=True)
        path.write_text('{"backend":"local","version":1,"board":"../../other"}')
        with self.assertRaises(setup.SetupError), self.init_mock() as initialize:
            self.configure(["codex"])
        initialize.assert_not_called()

    def test_failed_initialization_does_not_switch_existing_selection(self):
        original = self.configure(["claude"])
        with patch.object(setup.subprocess, "run", return_value=SimpleNamespace(returncode=2, stdout="")):
            with self.assertRaises(setup.SetupError):
                self.configure(["codex"], replace=True)
        self.assertEqual(setup.read_selection(setup.profile_path(self.root, "test")), original)

    def test_missing_agent_answer_is_not_defaulted(self):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), "--root", str(self.root),
                               "--profile", "test", "configure"], input="", capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("agents_required", proc.stderr)
        self.assertFalse(self.root.exists())

    def test_profiles_do_not_share_selection_implicitly(self):
        self.configure(["claude"])
        self.assertIsNone(setup.read_selection(setup.profile_path(self.root, "other")))

    def test_mcp_config_uses_real_board_and_installed_path(self):
        with self.init_mock():
            self.configure(["codex"])
        proc = subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), "--root", str(self.root),
                               "--profile", "test", "mcp-config"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        config = json.loads(proc.stdout)["mcpServers"]["cortex"]
        self.assertTrue(Path(config["command"]).is_absolute())
        self.assertEqual(config["args"][-3:], ["--board", BOARD, "mcp"])
        self.assertEqual(config["args"][0], str(SCRIPTS / "local.py"))

    def test_claude_config_dir_is_not_local_storage(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/unrelated/claude"}, clear=True):
            self.assertNotIn("/unrelated/claude", str(setup.root_path()))


if __name__ == "__main__":
    unittest.main()
