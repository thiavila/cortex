"""Optional host routing by folder and/or account. Rules belong to each board's config, never to skills."""
import json
import os
from pathlib import Path
import subprocess
import sqlite3

from local_store import Store, LocalError


class RoutingError(Exception):
    pass


def _folders(rule, board_id):
    folders = rule.get('pastas')
    if folders is None:
        return None
    if not isinstance(folders, list) or not folders:
        raise RoutingError('invalid_routing: invalid folders in board ' + board_id)
    paths = []
    for folder in folders:
        if not isinstance(folder, str) or not folder.strip():
            raise RoutingError('invalid_routing: invalid folders in board ' + board_id)
        path = Path(folder.strip()).expanduser()
        if not path.is_absolute():
            raise RoutingError('invalid_routing: folders must be absolute in board ' + board_id)
        paths.append(path)
    return paths


def configured_rules(store, host):
    rules = []
    try:
        boards = store.boards()
        for board in boards:
            doc = store.dispatch(board['board'], {'op':'get', 'collection':'config', 'id':'roteamento'})
            if not doc['exists']:
                continue
            config = doc['data']
            if not isinstance(config, dict) or type(config.get('versao')) is not int or config['versao'] != 1 or not isinstance(config.get('regras'), list):
                raise RoutingError('invalid_routing: repair routing in board ' + board['board'])
            for rule in config['regras']:
                if not isinstance(rule, dict):
                    raise RoutingError('invalid_routing: invalid rule in board ' + board['board'])
                if rule.get('host') == host and rule.get('ativo') is True:
                    folders = _folders(rule, board['board'])
                    account = rule.get('conta')
                    if account is not None or folders is None:
                        if not isinstance(account, str) or not account.strip():
                            raise RoutingError('invalid_routing: missing account in board ' + board['board'])
                    org = rule.get('organizacao')
                    if org is not None and (not isinstance(org, str) or not org.strip()):
                        raise RoutingError('invalid_routing: invalid organization in board ' + board['board'])
                    rules.append((board, rule))
    except (LocalError, sqlite3.Error, OSError):
        raise RoutingError('routing_unavailable: could not read local routing configuration')
    return rules


def _checked_identity(identity):
    if not isinstance(identity, dict) or identity.get('verified') is not True:
        raise RoutingError('identity_required: authenticate the host before selecting a board')
    email = identity.get('email')
    if not isinstance(email, str) or not email.strip():
        raise RoutingError('identity_required: host did not provide an account identity')
    return identity


def _account_matches(rule, identity):
    if rule['conta'].strip().casefold() != identity['email'].strip().casefold():
        return False
    org = rule.get('organizacao')
    actual_org = identity.get('organization')
    return org is None or (isinstance(actual_org, str) and org.strip() == actual_org.strip())


def _folder_depth(rule, cwd):
    """Depth of the deepest rule folder containing cwd, or None."""
    best = None
    for folder in _folders(rule, '') or []:
        folder = Path(os.path.realpath(folder))
        if cwd == folder or folder in cwd.parents:
            best = max(best or 0, len(folder.parts))
    return best


def _selected(store, host, board, selected_by, **extra):
    return {'backend':'local', 'board':board['board'], 'name':board['name'],
            'root':str(store.root), 'selected_by':selected_by, 'host':host, **extra}


def select_board(store, host, identity_fn, cwd=None, rules=None):
    """Folder rules containing cwd win (deepest folder first); then account-only rules.

    identity_fn is only called when a rule with an account has to be checked, so
    folder-only policies never depend on the host login.
    """
    rules = configured_rules(store, host) if rules is None else rules
    if not rules:
        return {'routing':'unconfigured', 'host':host}
    cache = []

    def identity():
        if not cache:
            cache.append(_checked_identity(identity_fn()))
        return cache[0]

    if cwd is not None:
        cwd = Path(os.path.realpath(cwd))
        found = []
        for board, rule in rules:
            if rule.get('pastas') is None:
                continue
            depth = _folder_depth(rule, cwd)
            if depth is None:
                continue
            if rule.get('conta') is not None and not _account_matches(rule, identity()):
                continue
            found.append((depth, board))
        if found:
            deepest = max(depth for depth, _ in found)
            boards = []
            for depth, board in found:
                if depth == deepest and board not in boards:
                    boards.append(board)
            if len(boards) != 1:
                raise RoutingError('routing_ambiguous: ask the user to select a board')
            return _selected(store, host, boards[0], 'folder', pasta=str(cwd))
    account_rules = [(board, rule) for board, rule in rules if rule.get('pastas') is None]
    if not account_rules:
        raise RoutingError('routing_not_found: no board matches this folder; ask the user')
    matches = []
    for board, rule in account_rules:
        if _account_matches(rule, identity()) and board not in matches:
            matches.append(board)
    if len(matches) != 1:
        raise RoutingError('routing_ambiguous: ask the user to select a board' if matches else
                           'routing_not_found: no board matches this folder or authenticated host account; ask the user')
    return _selected(store, host, matches[0], 'authenticated_host_identity')


def match_identity(store, host, identity, rules=None, cwd=None):
    return select_board(store, host, lambda: identity, cwd=cwd, rules=rules)


def _claude_identity():
    # Inherit the actual host environment. Never choose a Claude config directory ourselves.
    try:
        result = subprocess.run(['claude', 'auth', 'status'], capture_output=True,
                                text=True, timeout=20)
        status = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise RoutingError('identity_unavailable: could not verify the current host account')
    if result.returncode or not isinstance(status, dict) or status.get('loggedIn') is not True:
        raise RoutingError('identity_unavailable: authenticate the current host account')
    return {'verified':True, 'email':status.get('email'), 'organization':status.get('orgId')}


def resolve_host(root, host, cwd=None):
    if host != 'claude':
        raise RoutingError('unsupported_host: use explicit profile selection for this host')
    store = Store(root)
    rules = configured_rules(store, host)
    if not rules:
        return {'routing':'unconfigured', 'host':host}
    return select_board(store, host, _claude_identity,
                        cwd=os.getcwd() if cwd is None else cwd, rules=rules)
