import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills' / 'tarefas'))
from local_store import Store
CLI = ROOT / 'skills' / 'tarefas' / 'local.py'


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name, create=True)
        self.board = self.store.init('Example', 'en-US', 'UTC')['board']

    def run_messages(self, messages, board=True):
        cmd = [sys.executable, str(CLI), '--root', self.tmp.name]
        if board:
            cmd += ['--board', self.board]
        cmd += ['mcp']
        payload = '\n'.join(x if isinstance(x, str) else json.dumps(x) for x in messages) + '\n'
        result = subprocess.run(cmd, input=payload, text=True, capture_output=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('', result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def handshake(self):
        return [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'}]

    def test_protocol_and_persistent_tools(self):
        responses = self.run_messages(self.handshake() + [
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'cortex_write', 'arguments': {'op': 'set', 'collection': 'tasks', 'id': 'mcp', 'data': {'titulo': 'From MCP'}}}},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'cortex_read', 'arguments': {'op': 'get', 'collection': 'tasks', 'id': 'mcp'}}},
        ])
        self.assertEqual(4, len(responses))
        self.assertEqual('2025-06-18', responses[0]['result']['protocolVersion'])
        self.assertEqual({'cortex_read', 'cortex_write'}, {t['name'] for t in responses[1]['result']['tools']})
        self.assertFalse(responses[2]['result']['isError'])
        self.assertEqual('From MCP', responses[3]['result']['structuredContent']['data']['titulo'])
        self.assertTrue(self.store.dispatch(self.board, {'op': 'get', 'collection': 'tasks', 'id': 'mcp'})['exists'])

    def test_errors_do_not_break_transport(self):
        responses = self.run_messages(['bad json'] + self.handshake() + [
            {'jsonrpc': '2.0', 'id': 2, 'method': 'not-real'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'cortex_read', 'arguments': {'op': 'delete'}}},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'ping'},
        ])
        self.assertEqual(-32700, responses[0]['error']['code'])
        self.assertEqual(-32601, responses[2]['error']['code'])
        self.assertTrue(responses[3]['result']['isError'])
        self.assertEqual({}, responses[4]['result'])

    def test_semantically_invalid_json_does_not_crash_transport(self):
        messages = self.handshake()
        for val in ([], {}):
            messages += [
                {'jsonrpc': '2.0', 'id': 10, 'method': val},
                {'jsonrpc': '2.0', 'id': 11, 'method': 'tools/call', 'params': {'name': val}},
                {'jsonrpc': '2.0', 'id': 12, 'method': 'tools/call', 'params': {'name': 'cortex_read', 'arguments': {'op': val}}},
                {'jsonrpc': '2.0', 'id': 13, 'method': 'tools/call', 'params': {'name': 'cortex_read', 'arguments': {'op': 'query', 'collection': 'tasks', 'filters': [['status', val, 'feito']]}}},
                {'jsonrpc': '2.0', 'id': 14, 'method': 'tools/call', 'params': {'name': 'cortex_read', 'arguments': {'op': 'query', 'collection': 'tasks', 'filters': [['status', 'in', val]]}}},
            ]
        # Empty [] is a valid operand for 'in'; use a non-list value separately.
        messages.append({'jsonrpc': '2.0', 'id': 20, 'method': 'ping'})
        responses = self.run_messages(messages)
        self.assertEqual(12, len(responses))
        for offset in (1, 6):
            self.assertEqual(-32600, responses[offset]['error']['code'])
            self.assertEqual(-32602, responses[offset + 1]['error']['code'])
            self.assertTrue(responses[offset + 2]['result']['isError'])
            self.assertTrue(responses[offset + 3]['result']['isError'])
        self.assertTrue(responses[10]['result']['isError'])
        self.assertEqual({}, responses[-1]['result'])

    def test_missing_board_cannot_mutate(self):
        responses = self.run_messages(self.handshake() + [
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'cortex_write', 'arguments': {'op': 'set', 'collection': 'tasks', 'id': 'mcp', 'data': {'titulo': 'No board'}}}},
        ], board=False)
        self.assertEqual('setup_required', responses[-1]['result']['structuredContent']['error']['code'])
        self.assertFalse(self.store.dispatch(self.board, {'op': 'get', 'collection': 'tasks', 'id': 'mcp'})['exists'])


if __name__ == '__main__':
    unittest.main()
