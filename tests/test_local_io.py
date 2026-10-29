import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills' / 'tarefas'))
from local_store import Store, LocalError
from local_io import export_package, import_package

class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name, create=True)
        self.source = self.store.init('Source', 'en-US', 'UTC')['board']
        self.dest = self.store.init('Destination', 'en-US', 'UTC')['board']
        self.store.dispatch(self.source, {'op':'set', 'collection':'tasks', 'id':'one', 'data':{
            'titulo':'Original', 'status':'fazendo', 'chaves':['conversa:codex:test'],
            'historico':[{'texto':'Kept'}], 'conversas':[{'id':'codex:test'}]}})
        self.package = export_package(self.store, self.source)
    def test_preview_no_writes_then_roundtrip_and_repeat_refused(self):
        before = export_package(self.store, self.dest)
        result = import_package(self.store, self.dest, self.package, 'digest')
        self.assertFalse(result['applied'])
        after = export_package(self.store, self.dest)
        self.assertEqual(before['config'], after['config']); self.assertEqual(after['tasks'], {})
        import_package(self.store, self.dest, self.package, 'digest', True)
        after = export_package(self.store, self.dest)
        self.assertEqual(after['tasks'], self.package['tasks'])
        self.assertEqual(after['config']['schema']['backend'], 'local')
        self.assertIn('one', self.store.dispatch(self.dest, {'op':'get','collection':'indice','id':'ativos'})['data']['itens'])
        with self.assertRaises(LocalError): import_package(self.store, self.dest, self.package, 'digest', True)
        self.assertEqual(export_package(self.store, self.source)['tasks'], self.package['tasks'])
    def test_invalid_package_rolls_back_entire_import(self):
        broken = copy.deepcopy(self.package)
        broken['tasks']['two'] = {'titulo':'Duplicate identity', 'chaves':['conversa:codex:test']}
        with self.assertRaises(LocalError): import_package(self.store, self.dest, broken, 'digest', True)
        self.assertEqual(export_package(self.store, self.dest)['tasks'], {})
    def test_import_over_one_hundred_documents_is_atomic(self):
        package = copy.deepcopy(self.package)
        package['tasks'] = {str(i): {'titulo':'Task '+str(i)} for i in range(125)}
        import_package(self.store, self.dest, package, 'large', True)
        self.assertEqual(len(export_package(self.store, self.dest)['tasks']), 125)

if __name__ == '__main__': unittest.main()
