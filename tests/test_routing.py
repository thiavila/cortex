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
from routing import RoutingError, configured_rules, match_identity, resolve_host, select_board


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

    def rules(self, board, *rules):
        data = {'versao':1,'regras':[{'host':'claude','ativo':True,**rule} for rule in rules]}
        current = self.store.dispatch(board, {'op':'get','collection':'config','id':'roteamento'})
        request = ({'op':'update','if_version':current['version']} if current['exists'] else {'op':'set'})
        self.store.dispatch(board, {**request,'collection':'config','id':'roteamento','data':data})

    def folders(self):
        base = Path(self.tmp.name) / 'work'
        for sub in ('Company/app/.claude/worktrees/x', 'Company2', 'Personal/site', 'Company/personal-lab'):
            (base / sub).mkdir(parents=True)
        return base

    def test_folder_rules_select_without_host_login_and_deepest_wins(self):
        base = self.folders()
        self.rules(self.a, {'pastas':[str(base / 'Company')]})
        self.rules(self.b, {'pastas':[str(base / 'Personal'), str(base / 'Company/personal-lab')]})
        def no_login():
            raise AssertionError('folder rules must not need the host login')
        pick = lambda cwd: select_board(self.store, 'claude', no_login, cwd=cwd)
        result = pick(base / 'Company/app/.claude/worktrees/x')
        self.assertEqual((result['board'], result['selected_by']), (self.a, 'folder'))
        self.assertEqual(pick(base / 'Company')['board'], self.a)
        self.assertEqual(pick(base / 'Personal/site')['board'], self.b)
        self.assertEqual(pick(base / 'Company/personal-lab')['board'], self.b)
        for outside in (base / 'Company2', base, Path(self.tmp.name)):
            with self.assertRaisesRegex(RoutingError, 'routing_not_found'): pick(outside)
        link = Path(self.tmp.name) / 'link'
        link.symlink_to(base / 'Company/app')
        self.assertEqual(pick(link)['board'], self.a)

    def test_folder_beats_account_and_account_is_the_fallback(self):
        base = self.folders()
        self.rules(self.a, {'conta':'user@company.example'}, {'pastas':[str(base / 'Company')]})
        self.rules(self.b, {'conta':'me@personal.example'})
        me = {'verified':True, 'email':'me@personal.example'}
        self.assertEqual(match_identity(self.store, 'claude', me, cwd=base / 'Company/app')['board'], self.a)
        result = match_identity(self.store, 'claude', me, cwd=base / 'Personal')
        self.assertEqual((result['board'], result['selected_by']), (self.b, 'authenticated_host_identity'))
        self.assertEqual(match_identity(self.store, 'claude', me)['board'], self.b)

    def test_folder_rule_with_account_needs_that_account(self):
        base = self.folders()
        self.rules(self.a, {'conta':'user@company.example', 'pastas':[str(base / 'Company')]})
        self.rules(self.b, {'conta':'me@personal.example'})
        me = {'verified':True, 'email':'me@personal.example'}
        self.assertEqual(match_identity(self.store, 'claude', me, cwd=base / 'Company')['board'], self.b)
        user = {'verified':True, 'email':'USER@company.example'}
        self.assertEqual(match_identity(self.store, 'claude', user, cwd=base / 'Company')['board'], self.a)
        with self.assertRaisesRegex(RoutingError, 'identity_required'):
            match_identity(self.store, 'claude', {'verified':False}, cwd=base / 'Company')

    def test_same_folder_on_two_boards_is_ambiguous_and_bad_folders_are_invalid(self):
        base = self.folders()
        self.rules(self.a, {'pastas':[str(base / 'Company')]})
        self.rules(self.b, {'pastas':[str(base / 'Company') + '/']})
        with self.assertRaisesRegex(RoutingError, 'routing_ambiguous'):
            match_identity(self.store, 'claude', None, cwd=base / 'Company/app')
        for bad in ([], 'Company', ['relative/path'], [''], [3]):
            self.rules(self.b, {'pastas':bad})
            with self.assertRaisesRegex(RoutingError, 'invalid_routing'): configured_rules(self.store, 'claude')
        self.rules(self.b, {'pastas':[str(base)], 'conta':''})
        with self.assertRaisesRegex(RoutingError, 'invalid_routing'): configured_rules(self.store, 'claude')

    def test_resolve_passes_the_session_folder(self):
        base = self.folders()
        self.rules(self.a, {'pastas':[str(base / 'Company')]})
        with patch('routing.subprocess.run') as auth:
            self.assertEqual(resolve_host(self.tmp.name, 'claude', cwd=str(base / 'Company/app'))['board'], self.a)
            with patch('routing.os.getcwd', return_value=str(base / 'Company')):
                self.assertEqual(resolve_host(self.tmp.name, 'claude')['board'], self.a)
            auth.assert_not_called()


if __name__ == '__main__': unittest.main()
