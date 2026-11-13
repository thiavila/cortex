import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/tarefas'))
import codex_harness as harness
from local_store import Store
from setup import configure
spec = importlib.util.spec_from_file_location('harness_installer', ROOT / 'scripts/install_codex_hooks.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def native(cwd, trust='trusted', enabled=True):
    return {'data': [{'cwd': str(cwd), 'errors': [], 'warnings': [], 'hooks': [
        {'eventName': event, 'statusMessage': harness.MARKER, 'trustStatus': trust,
         'enabled': enabled, 'key': event} for event in ('sessionStart', 'userPromptSubmit')]}]}


class HarnessTests(unittest.TestCase):
    def board(self, root):
        selection = configure(root, 'example', ['codex'], 'Example', 'en-US', 'UTC')
        return Store(root), selection['board']

    def add_task(self, store, board, session='session-123', conversations=True):
        data = {'titulo': 'Example work', 'status': 'fazendo', 'proximo_passo': 'Verify the change',
                'chaves': ['conversa:codex:' + session],
                'conversas': [{'id': 'codex:' + session}] if conversations else []}
        store.dispatch(board, {'op': 'set', 'collection': 'tasks', 'id': 'example-work', 'data': data})

    def emit(self, home, session='session-123', payload=None):
        directory = home / 'cortex-hooks/observations'
        data = payload or {'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'prompt': 'PRIVATE_PROMPT_MUST_NOT_BE_STORED'}
        result = subprocess.run([sys.executable, str(ROOT / 'hooks/codex-tarefas.py'), '--observe-dir', str(directory)],
                                input=json.dumps(data), text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, '')
        return directory

    def test_native_protocol_ignores_notifications_and_never_starts_a_thread(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            executable = root / 'fake-codex'
            executable.write_text("#!" + sys.executable + "\n" +
                "import sys,json\n" +
                "for line in sys.stdin:\n" +
                " r=json.loads(line)\n" +
                " if 'id' not in r: continue\n" +
                " if r['method'] not in ('initialize','hooks/list'): raise RuntimeError('unexpected mutating method')\n" +
                " result={'data':[{'cwd':r['params']['cwds'][0],'hooks':[],'warnings':[],'errors':[]}]} if r['method']=='hooks/list' else {}\n" +
                " print(json.dumps({'method':'notification'})+'\\n'+json.dumps({'id':r['id'],'result':result}),flush=True)\n")
            executable.chmod(0o700)
            result = harness.native_hooks(root, root, str(executable), timeout=2)
            self.assertEqual(result['data'][0]['cwd'], str(root))

    def test_installer_never_claims_readiness_or_grants_trust(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            result = installer.install(home, observe=True)
            self.assertTrue(result['installed'])
            self.assertFalse(result['ready'])
            self.assertEqual(result['status'], 'verification_required')
            self.assertFalse((home / 'config.toml').exists())
            self.assertIn('--observe-dir', json.dumps(json.loads((home / 'hooks.json').read_text())))
            self.assertEqual(harness.runtime_check(home, ROOT)['status'], 'current')

    def test_remove_leaves_no_invalid_standalone_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            installer.install(home)
            installer.install(home, remove=True)
            result = harness.runtime_check(home, ROOT)
            self.assertEqual(result['status'], 'native_version_unverified')
            self.assertIsNone(result['matches_source'])

    def test_malformed_native_json_and_timeout_fail_safely(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            executable = root / 'fake-codex'
            for body, error in (("print('[]',flush=True)", ValueError),
                                ("import time; time.sleep(10)", TimeoutError)):
                executable.write_text('#!' + sys.executable + '\n' + body + '\n')
                executable.chmod(0o700)
                with self.assertRaises(error):
                    harness.native_hooks(root, root, str(executable), timeout=2 if error is ValueError else 0.5)

    def test_native_trust_disabled_duplicate_and_wrong_scope_are_not_ready(self):
        cwd = Path.cwd()
        self.assertTrue(harness.assess_hooks(native(cwd), cwd)['ready'])
        for trust in ('untrusted', 'modified', 'unknown'):
            self.assertFalse(harness.assess_hooks(native(cwd, trust), cwd)['ready'])
        self.assertFalse(harness.assess_hooks(native(cwd, enabled=False), cwd)['ready'])
        duplicate = native(cwd)
        duplicate['data'][0]['hooks'].append(duplicate['data'][0]['hooks'][0])
        self.assertFalse(harness.assess_hooks(duplicate, cwd)['ready'])
        self.assertFalse(harness.assess_hooks(native(cwd), cwd / 'another')['ready'])
        error = native(cwd)
        error['data'][0]['errors'] = [{'message': 'invalid', 'path': 'example'}]
        self.assertFalse(harness.assess_hooks(error, cwd)['ready'])

    def test_old_snapshot_cannot_be_reported_current(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as source:
            installer.install(home)
            source = Path(source)
            shutil.copytree(ROOT / 'skills/tarefas', source / 'skills/tarefas')
            (source / 'hooks').mkdir()
            (source / 'hooks/codex-tarefas.py').write_text((ROOT / 'hooks/codex-tarefas.py').read_text() + '\n# newer\n')
            result = harness.runtime_check(Path(home), source)
            self.assertEqual(result['status'], 'outdated')
            self.assertIn('hooks/codex-tarefas.py', result['different_files'])

    def test_verify_reads_actual_card_and_does_not_change_database(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store, board = self.board(root)
            self.add_task(store, board)
            before = store.path.read_bytes()
            result = harness.verify_link(root, 'session-123', root, 'example')
            self.assertTrue(result['registered'])
            self.assertEqual(result['tasks'][0]['id'], 'example-work')
            self.assertEqual(before, store.path.read_bytes())
            self.assertFalse(harness.verify_link(root, 'other-session', root, 'example')['registered'])

    def test_index_key_without_conversation_is_not_a_verified_link(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store, board = self.board(root)
            self.add_task(store, board, conversations=False)
            self.assertFalse(harness.verify_link(root, 'session-123', root, 'example')['registered'])

    def test_missing_selection_never_creates_board(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'not-created'
            with self.assertRaises(Exception):
                harness.verify_link(Path(td), 'session-123', root, 'absent')
            self.assertFalse(root.exists())

    def test_receipt_does_not_store_prompt_session_or_task_content(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            directory = self.emit(home)
            text = next(directory.glob('*.json')).read_text()
            self.assertNotIn('PRIVATE_PROMPT', text)
            self.assertNotIn('session-123', text)
            self.assertNotIn('Example work', text)
            self.assertTrue(harness.observed_delivery(home, 'session-123')['observed'])
            self.assertFalse(harness.observed_delivery(home, 'unknown')['observed'])

    def test_skipped_delegation_has_no_emitted_receipt_or_task_write(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            self.emit(home, payload={'hook_event_name': 'UserPromptSubmit', 'session_id': 'session-123',
                                    'parent_thread_id': 'parent', 'prompt': 'review'})
            self.assertFalse(harness.observed_delivery(home, 'session-123')['observed'])
            self.assertEqual([p.name for p in home.iterdir()], ['cortex-hooks'])

    def test_receipts_for_old_code_or_old_events_are_not_delivery_proof(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            path = next(self.emit(home).glob('*.json'))
            value = json.loads(path.read_text())
            value['hook_sha256'] = '0' * 64
            path.write_text(json.dumps(value))
            self.assertFalse(harness.observed_delivery(home, 'session-123')['observed'])
            value['hook_sha256'] = hashlib.sha256((ROOT / 'hooks/codex-tarefas.py').read_bytes()).hexdigest()
            value['at'] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat()
            path.write_text(json.dumps(value))
            self.assertFalse(harness.observed_delivery(home, 'session-123')['observed'])

    def test_doctor_requires_runtime_trust_delivery_and_card_independently(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            home, root = base / 'host', base / 'board'
            home.mkdir()
            installer.install(home, observe=True)
            store, board = self.board(root)
            args = dict(cwd=base, home=home, root=root, profile='example', session_id='session-123')
            result = harness.doctor(**args, discovery=native(base))
            self.assertTrue(result['runtime_ready'])
            self.assertFalse(result['ready'])
            self.add_task(store, board)
            self.assertFalse(harness.doctor(**args, discovery=native(base))['ready'])
            self.emit(home)
            before = store.path.read_bytes()
            result = harness.doctor(**args, discovery=native(base))
            self.assertTrue(result['ready'])
            self.assertFalse(result['writes_board'])
            self.assertEqual(before, store.path.read_bytes())
            self.assertFalse(harness.doctor(**args, discovery=native(base, 'untrusted'))['ready'])

    def test_observation_symlink_does_not_overwrite_unrelated_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actual = root / 'actual'
            actual.mkdir()
            link = root / 'observations'
            link.symlink_to(actual, target_is_directory=True)
            p = subprocess.run([sys.executable, str(ROOT / 'hooks/codex-tarefas.py'), '--observe-dir', str(link)],
                input=json.dumps({'hook_event_name': 'UserPromptSubmit', 'session_id': 'id', 'prompt': 'work'}),
                text=True, capture_output=True, check=True)
            self.assertIn('metadata unavailable', p.stderr)
            self.assertEqual(list(actual.iterdir()), [])
            self.assertIn('additionalContext', p.stdout)

    def test_verify_argument_errors_do_not_mutate_anything(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, str(ROOT / 'skills/tarefas/codex_harness.py'), 'verify', '--cwd', 'relative'],
                               text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(list(Path(td).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
