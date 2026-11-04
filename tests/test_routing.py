import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/tarefas'))
from local_store import Store
from routing import RoutingError, match_identity, resolve_host


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name, create=True)
        self.a = self.store.init('First', 'en-US', 'UTC')['board']
        self.b = self.store.init('Second', 'en-US', 'UTC')['board']

    def bind(self, board, **rule):
        self.store.dispatch(board, {'op':'set','collection':'config','id':'roteamento',
            'data':{'versao':1,'regras':[{'host':'claude','ativo':True,'conta':'user@company.example',**rule}]}})

    def test_rules_live_in_board_and_scope_to_host_account_organization(self):
        self.bind(self.a, organizacao='org-a'); self.bind(self.b, organizacao='org-b')
        identity={'verified':True,'email':'USER@company.example','organization':'org-b'}
        self.assertEqual(match_identity(self.store,'claude',identity)['board'],self.b)
        self.assertEqual(match_identity(self.store,'codex',identity)['routing'],'unconfigured')
        with self.assertRaises(RoutingError): match_identity(self.store,'claude',{'verified':False,'email':identity['email']})
        with self.assertRaises(RoutingError): match_identity(self.store,'claude',{**identity,'organization':'other'})

    def test_missing_disabled_and_ambiguous_never_pick_first(self):
        identity={'verified':True,'email':'user@company.example'}
        self.assertEqual(match_identity(self.store,'claude',identity)['routing'],'unconfigured')
        self.bind(self.a,ativo=False)
        self.assertEqual(match_identity(self.store,'claude',identity)['routing'],'unconfigured')
        self.bind(self.b)
        self.assertEqual(match_identity(self.store,'claude',identity)['board'],self.b)
        self.store.dispatch(self.a,{'op':'update','collection':'config','id':'roteamento','if_version':1,
            'data':{'regras':[{'host':'claude','ativo':True,'conta':'user@company.example'}]}})
        with self.assertRaisesRegex(RoutingError,'ambiguous'): match_identity(self.store,'claude',identity)

    def test_unconfigured_needs_no_auth_and_corruption_is_structured(self):
        with patch('routing.subprocess.run') as auth:
            self.assertEqual(resolve_host(str(Path(self.tmp.name)/'absent'),'claude')['routing'],'unconfigured')
            auth.assert_not_called()
        self.bind(self.a)
        with self.assertRaisesRegex(RoutingError,'routing_not_found'):
            match_identity(self.store,'claude',{'verified':True,'email':'other@company.example'})
        from routing import configured_rules
        import sqlite3
        with patch.object(self.store,'boards',side_effect=sqlite3.DatabaseError('bad')):
            with self.assertRaisesRegex(RoutingError,'routing_unavailable'): configured_rules(self.store,'claude')
        self.store.dispatch(self.a,{'op':'update','collection':'config','id':'roteamento','if_version':1,'data':{'versao':True}})
        with self.assertRaisesRegex(RoutingError,'invalid_routing'): configured_rules(self.store,'claude')

    def test_adapter_uses_authenticated_account_without_setting_profile(self):
        self.bind(self.a)
        result=SimpleNamespace(returncode=0,stdout=json.dumps({'loggedIn':True,'email':'user@company.example'}))
        with patch('routing.subprocess.run',return_value=result) as run:
            self.assertEqual(resolve_host(self.tmp.name,'claude')['board'],self.a)
            self.assertEqual(run.call_args.args[0],['claude','auth','status'])
            self.assertNotIn('env',run.call_args.kwargs)
        for stdout, code in [('not json',0),('{}',0),(json.dumps({'loggedIn':False}),1)]:
            with patch('routing.subprocess.run',return_value=SimpleNamespace(returncode=code,stdout=stdout)):
                with self.assertRaises(RoutingError): resolve_host(self.tmp.name,'claude')
        self.assertFalse(self.store.dispatch(self.a,{'op':'get','collection':'tasks','id':'anything'})['exists'])


if __name__ == '__main__': unittest.main()
