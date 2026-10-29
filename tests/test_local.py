import concurrent.futures
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills' / 'tarefas'))
from local_store import LocalError, Store
from local import make_server

CLI = ROOT / 'skills' / 'tarefas' / 'local.py'


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name, create=True)
        self.board = self.store.init('Example', 'en-US', 'UTC')['board']

    def call(self, **req):
        return self.store.dispatch(self.board, req)

    def task(self, ident='a', **data):
        return self.call(op='set', collection='tasks', id=ident, data={'titulo': ident, **data})

    def cli(self, req):
        return subprocess.run([sys.executable, str(CLI), '--root', self.tmp.name, '--board', self.board, 'call'], input=json.dumps(req), text=True, capture_output=True)

    def test_persistence_index_merge_conflict_tombstone(self):
        a = self.task(chaves=['external:1'], status='entrada')
        b = Store(self.tmp.name).dispatch(self.board, {'op': 'get', 'collection': 'tasks', 'id': 'a'})
        self.assertEqual(a, b)
        index = self.call(op='get', collection='indice', id='ativos')
        self.assertEqual(index['data']['itens']['a']['k'], ['external:1'])
        self.call(op='update', collection='tasks', id='a', data={'contexto': 'changed'}, if_version=a['version'])
        with self.assertRaisesRegex(LocalError, 'Document changed'):
            self.call(op='update', collection='tasks', id='a', data={'titulo': 'lost'}, if_version=a['version'])
        with self.assertRaisesRegex(LocalError, 'External identity'):
            self.task('b', chaves=['external:1'])
        self.call(op='delete', collection='tasks', id='a', if_version=2)
        with self.assertRaisesRegex(LocalError, 'Deleted IDs'):
            self.task('a')
        self.assertNotIn('a', self.call(op='get', collection='indice', id='ativos')['data']['itens'])

    def test_atomic_batch_and_receipt(self):
        req = dict(op='batch', mutation_id='retry-1', operations=[{'op': 'set', 'collection': 'tasks', 'id': 'a', 'data': {'titulo': 'A'}}])
        first = self.call(**req)
        self.assertEqual(first, self.call(**req))
        self.assertEqual(1, self.call(op='get', collection='tasks', id='a')['version'])
        req['operations'][0]['data']['titulo'] = 'different'
        with self.assertRaisesRegex(LocalError, 'mutation_id'):
            self.call(**req)
        with self.assertRaises(LocalError):
            self.call(op='batch', operations=[{'op': 'set', 'collection': 'tasks', 'id': 'b', 'data': {'titulo': 'B'}}, {'op': 'update', 'collection': 'tasks', 'id': 'a', 'data': {'titulo': 'bad'}, 'if_version': 50}])
        self.assertFalse(self.call(op='get', collection='tasks', id='b')['exists'])
        self.assertNotIn('b', self.call(op='get', collection='indice', id='ativos')['data']['itens'])

    def test_two_processes_cannot_overwrite_same_version(self):
        self.task()
        req = {'op': 'update', 'collection': 'tasks', 'id': 'a', 'if_version': 1, 'data': {'titulo': 'changed'}}
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            outputs = list(executor.map(self.cli, [req, req]))
        self.assertEqual([0, 1], sorted(x.returncode for x in outputs))
        error = json.loads(next(x.stderr for x in outputs if x.returncode))
        self.assertEqual('conflict', error['error']['code'])
        self.assertEqual(2, self.call(op='get', collection='tasks', id='a')['version'])

    def test_query_pagination_and_scope(self):
        for ident in ['a', 'b', 'c']:
            self.task(ident, tags=['project:test'])
        req = dict(op='query', collection='tasks', filters=[['tags', 'array-contains', 'project:test']], limit=2)
        first = self.call(**req)
        self.assertEqual(['a', 'b'], [x['id'] for x in first['docs']])
        second = self.call(**req, cursor=first['next_cursor'])
        self.assertEqual(['c'], [x['id'] for x in second['docs']])
        other = self.store.init('Other', 'en-US', 'UTC')['board']
        self.assertFalse(self.store.dispatch(other, {'op': 'get', 'collection': 'tasks', 'id': 'a'})['exists'])
        with self.assertRaises(LocalError):
            self.store.dispatch(other, {**req, 'cursor': first['next_cursor']})
        self.task('d')
        with self.assertRaisesRegex(LocalError, 'Query changed'):
            self.call(**req, cursor=first['next_cursor'])
        with self.assertRaises(LocalError):
            self.call(op='query', collection='tasks', filters=[['tags', 'not-real', 'x']])

    def test_invalid_requests_leave_state_untouched(self):
        bad = [dict(op=[]), dict(op='get', collection='../data', id='x'),
               dict(op='set', collection='tasks', id='x', data={'titulo': 'A', 'status': []}),
               dict(op='set', collection='indice', id='ativos', data={}),
               dict(op='set', collection='config', id='schema', data={}),
               dict(op='set', collection='tasks', id='x', data={'titulo': 'A', 'chaves': [1]})]
        for req in bad:
            with self.subTest(req=req), self.assertRaises(LocalError):
                self.call(**req)
        self.assertEqual([], self.call(op='list', collection='tasks')['docs'])

    def test_http_auth_host_origin_and_shared_data(self):
        self.task()
        self.call(op='update', collection='config', id='preferencias', if_version=1, data={'nome': 'Renamed board'})
        self.call(op='update', collection='config', id='tema', if_version=1, data={'css': ':root { --accent: #123456; }'})
        server = make_server(self.store, self.board)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, data=None, headers=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            conn.request('POST' if data is not None else 'GET', path, json.dumps(data) if data is not None else None, headers or {})
            response = conn.getresponse()
            body = response.read()
            status = response.status
            conn.close()
            return status, body
        query = {'op': 'get', 'collection': 'tasks', 'id': 'a'}
        auth = {'Authorization': 'Bearer ' + server.token, 'Content-Type': 'application/json'}
        self.assertEqual(401, request('/api', query, {'Content-Type': 'application/json'})[0])
        self.assertEqual(401, request('/api', query, {**auth, 'Origin': 'https://unrelated.invalid'})[0])
        self.assertEqual(401, request('/api', query, {**auth, 'Host': 'unrelated.invalid'})[0])
        self.assertEqual(200, request('/api', query, auth)[0])
        self.assertEqual('a', json.loads(request('/api', query, auth)[1])['data']['titulo'])
        response = request('/')[1].decode()
        self.assertIn('window.CORTEX_LOCAL', response)
        self.assertIn('<title>Renamed board</title>', response)
        self.assertIn(':root { --accent: #123456; }', response)
        self.assertNotIn('fonts.googleapis.com', response)
        self.assertNotIn(server.token, response)
        self.assertEqual(404, request('/../../cortex.sqlite3')[0])
        self.assertEqual(400, request('/api', query, {'Authorization': 'Bearer ' + server.token, 'Content-Type': 'text/plain'})[0])
        update = {'op': 'update', 'collection': 'tasks', 'id': 'a', 'if_version': 1, 'data': {'titulo': 'Browser'}}
        self.assertEqual(200, request('/api', update, auth)[0])
        self.assertEqual('Browser', json.loads(self.cli(query).stdout)['data']['titulo'])

    def test_cli_serve_restart_preserves_data_and_rotates_token(self):
        self.assertEqual(0, self.cli({'op': 'set', 'collection': 'tasks', 'id': 'persist', 'data': {'titulo': 'Persistent'}}).returncode)
        previous_token = None
        for _ in range(2):
            with subprocess.Popen([sys.executable, str(CLI), '--root', self.tmp.name, '--board', self.board,
                                   'serve', '--port', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
                try:
                    startup = json.loads(proc.stdout.readline())
                    token = parse_qs(urlsplit(startup['url']).fragment)['token'][0]
                    self.assertNotEqual(previous_token, token)
                    previous_token = token
                    conn = http.client.HTTPConnection('127.0.0.1', startup['port'], timeout=5)
                    conn.request('POST', '/api', json.dumps({'op': 'get', 'collection': 'tasks', 'id': 'persist'}),
                                 {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
                    response = conn.getresponse()
                    self.assertEqual(200, response.status)
                    self.assertEqual('Persistent', json.loads(response.read())['data']['titulo'])
                    conn.close()
                finally:
                    proc.terminate()
                    proc.wait(timeout=10)

    def test_limits_roll_back_and_pagination_bounds(self):
        with patch('local_store.MAX_DOC', 100), self.assertRaises(LocalError):
            self.task('large', contexto='x' * 101)
        with patch('local_store.MAX_BOARD_BYTES', 1), self.assertRaises(LocalError):
            self.task('quota')
        self.assertEqual([], self.call(op='list', collection='tasks')['docs'])
        self.task('a', contexto='x' * 100)
        self.task('b', contexto='x' * 100)
        with patch('local_store.MAX_BODY', 600):
            first = self.call(op='list', collection='tasks', limit=100)
            self.assertEqual(1, len(first['docs']))
            self.assertTrue(first['next_cursor'])
        with patch('local_store.MAX_RECEIPTS', 0), self.assertRaises(LocalError):
            self.call(op='set', collection='tasks', id='receipt', data={'titulo': 'Receipt'}, mutation_id='r')
        self.assertFalse(self.call(op='get', collection='tasks', id='receipt')['exists'])

    def test_server_rejects_unsafe_persisted_theme(self):
        self.call(op='update', collection='config', id='tema', if_version=1, data={'css': ':root { background: url(https://unrelated.invalid); }'})
        with self.assertRaisesRegex(LocalError, 'Could not build board page'):
            make_server(self.store, self.board)

    def test_missing_setup_does_not_create_database(self):
        root = Path(self.tmp.name) / 'missing'
        store = Store(root)
        with self.assertRaises(LocalError):
            store.dispatch(None, {'op': 'info'})
        self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
