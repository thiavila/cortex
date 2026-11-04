import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('codex_installer', ROOT / 'scripts/install_codex_hooks.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CodexHooksTests(unittest.TestCase):
    def run_hook(self, payload, script=None):
        result = subprocess.run([sys.executable, str(script or ROOT / 'hooks/codex-tarefas.py')],
                                input=json.dumps(payload), text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout) if result.stdout else None

    def test_prompt_context_has_identity_and_permissions_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, CORTEX_LOCAL_DIR=td)
            before = list(Path(td).iterdir())
            result = subprocess.run([sys.executable, str(ROOT / 'hooks/codex-tarefas.py')],
                                    input=json.dumps({'hook_event_name': 'UserPromptSubmit',
                                        'session_id': 'test-123', 'prompt': 'Implement checkout'}),
                                    text=True, capture_output=True, check=True, env=env)
            text = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
            for required in ['conversa:codex:test-123', 'read-only', 'before the final answer', 'explicitly selected']:
                self.assertIn(required, text)
            self.assertEqual(before, list(Path(td).iterdir()))

    def test_resume_compact_and_startup(self):
        for source in ['startup', 'resume', 'compact']:
            d = self.run_hook({'hook_event_name': 'SessionStart', 'session_id': 'id', 'source': source})
            self.assertEqual(d['hookSpecificOutput']['hookEventName'], 'SessionStart')
        self.assertIsNone(self.run_hook({'hook_event_name': 'SessionStart', 'session_id': 'id', 'source': 'fork'}))

    def test_excludes_notifications_routines_and_delegation(self):
        for prompt in ['', '/tarefas buscar x', '/cortex:bom-dia', '<scheduled-task>daily</scheduled-task>']:
            self.assertIsNone(self.run_hook({'hook_event_name': 'UserPromptSubmit', 'session_id': 'id', 'prompt': prompt}))
        self.assertIsNone(self.run_hook({'hook_event_name': 'UserPromptSubmit', 'session_id': 'id',
                                      'prompt': 'review', 'parent_thread_id': 'parent'}))
        for invalid in [[], None, {'session_id': '../../x'}, {'hook_event_name': 'Stop', 'session_id': 'id'}]:
            self.assertIsNone(self.run_hook(invalid))

    def test_native_manifest_uses_codex_adapter(self):
        manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())
        config = json.loads((ROOT / manifest['hooks']).read_text())
        self.assertEqual(set(config['hooks']), {'UserPromptSubmit', 'SessionStart'})
        self.assertIn('${PLUGIN_ROOT}', config['hooks']['UserPromptSubmit'][0]['hooks'][0]['command'])
        command = config['hooks']['UserPromptSubmit'][0]['hooks'][0]['command']
        p = subprocess.run(command, shell=True, env=dict(os.environ, PLUGIN_ROOT=str(ROOT)),
            input=json.dumps({'hook_event_name': 'UserPromptSubmit', 'session_id': 'native', 'prompt': 'work'}),
            capture_output=True, text=True, check=True)
        self.assertIn('conversa:codex:native', p.stdout)

    def test_install_idempotent_preserves_and_uninstalls(self):
        with tempfile.TemporaryDirectory(prefix='cortex space ') as td:
            home = Path(td).resolve()
            original = {'description': 'User config', 'hooks': {'SessionStart': [{'hooks': [
                {'type': 'command', 'command': 'existing'}]}], 'Stop': []}}
            (home / 'hooks.json').write_text(json.dumps(original))
            first = installer.install(home)
            self.assertEqual(json.loads(Path(first['backup']).read_text()), original)
            runtime = Path(first['runtime'])
            script = runtime / 'hooks/codex-tarefas.py'
            out = self.run_hook({'hook_event_name': 'UserPromptSubmit', 'session_id': 'id', 'prompt': 'work'}, script)
            self.assertIn(str(runtime / 'skills/tarefas/SKILL.md'), out['hookSpecificOutput']['additionalContext'])
            config = json.loads((home / 'hooks.json').read_text())
            handler = config['hooks']['UserPromptSubmit'][0]['hooks'][0]
            # Exercise actual shell quoting, including an installation path with spaces.
            p = subprocess.run(handler['command'], shell=True, input=json.dumps({
                'hook_event_name': 'SessionStart', 'session_id': 'id', 'source': 'compact'}),
                capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['hookEventName'], 'SessionStart')
            self.assertFalse(installer.install(home)['changed'])
            installer.install(home, remove=True)
            remaining = json.loads((home / 'hooks.json').read_text())
            self.assertEqual(remaining['hooks']['SessionStart'], original['hooks']['SessionStart'])
            self.assertEqual(remaining['hooks']['Stop'], [])
            self.assertEqual(remaining['description'], original['description'])
            self.assertFalse(installer.install(home, remove=True)['changed'])

    def test_rejects_malformed_config_without_overwrite(self):
        for content in ['not json', '[]', '{"hooks": []}', '{"hooks":{"SessionStart":{}}}']:
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / 'hooks.json'
                path.write_text(content)
                with self.assertRaises(ValueError):
                    installer.install(td)
                self.assertEqual(path.read_text(), content)

    def test_manual_edits_and_snapshot_tampering_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            first = installer.install(td)
            path = Path(td) / 'hooks.json'
            value = json.loads(path.read_text())
            value['hooks']['UserPromptSubmit'][0]['hooks'][0]['command'] = 'edited'
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                installer.install(td, remove=True)
        with tempfile.TemporaryDirectory() as td:
            first = installer.install(td)
            (Path(first['runtime']) / 'hooks/codex-tarefas.py').write_text('edited')
            with self.assertRaises(ValueError):
                installer.install(td)

    def test_removed_config_can_be_reinstalled_or_uninstalled(self):
        with tempfile.TemporaryDirectory() as td:
            installer.install(td)
            (Path(td) / 'hooks.json').unlink()
            installer.install(td, remove=True)
            installer.install(td)
            self.assertEqual(len(json.loads((Path(td) / 'hooks.json').read_text())['hooks']['UserPromptSubmit']), 1)

    def test_update_and_interrupted_updates_recover_without_duplicates(self):
        import shutil
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as source:
            home = Path(td).resolve()
            first = installer.install(home)
            root = Path(source)
            shutil.copytree(ROOT / 'skills/tarefas', root / 'skills/tarefas')
            (root / 'hooks').mkdir()
            hook = root / 'hooks/codex-tarefas.py'
            hook.write_text((ROOT / 'hooks/codex-tarefas.py').read_text() + '\n# update one\n')
            real_write = installer.write
            def interrupted(path, value):
                if path == home / 'hooks.json':
                    raise OSError('simulated interruption before config replacement')
                real_write(path, value)
            with patch.object(installer, 'ROOT', root), patch.object(installer, 'write', interrupted):
                with self.assertRaises(OSError):
                    installer.install(home)
            self.assertTrue((home / 'cortex-hooks/install.json').exists())
            # Source can advance again before the interrupted installation resumes.
            hook.write_text(hook.read_text() + '# update two\n')
            with patch.object(installer, 'ROOT', root):
                second = installer.install(home)
                self.assertNotEqual(first['runtime'], second['runtime'])
                self.assertFalse(installer.install(home)['changed'])
            cfg = json.loads((home / 'hooks.json').read_text())
            self.assertEqual(len(cfg['hooks']['UserPromptSubmit']), 1)
            installer.install(home, remove=True)
            self.assertEqual(json.loads((home / 'hooks.json').read_text())['hooks']['UserPromptSubmit'], [])


if __name__ == '__main__':
    unittest.main()
