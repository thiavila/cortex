"""Optional host identity routing. Rules belong to each board's config, never to skills."""
import json
import subprocess
import sqlite3

from local_store import Store, LocalError


class RoutingError(Exception):
    pass


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
                    if not isinstance(rule.get('conta'), str) or not rule['conta'].strip():
                        raise RoutingError('invalid_routing: missing account in board ' + board['board'])
                    org = rule.get('organizacao')
                    if org is not None and (not isinstance(org, str) or not org.strip()):
                        raise RoutingError('invalid_routing: invalid organization in board ' + board['board'])
                    rules.append((board, rule))
    except (LocalError, sqlite3.Error, OSError):
        raise RoutingError('routing_unavailable: could not read local routing configuration')
    return rules


def match_identity(store, host, identity, rules=None):
    rules = configured_rules(store, host) if rules is None else rules
    if not rules:
        return {'routing':'unconfigured', 'host':host}
    if not isinstance(identity, dict) or identity.get('verified') is not True:
        raise RoutingError('identity_required: authenticate the host before selecting a board')
    email = identity.get('email')
    if not isinstance(email, str) or not email.strip():
        raise RoutingError('identity_required: host did not provide an account identity')
    matches = []
    for board, rule in rules:
        if rule['conta'].strip().casefold() != email.strip().casefold():
            continue
        org = rule.get('organizacao')
        actual_org = identity.get('organization')
        if org is not None and (not isinstance(actual_org, str) or org.strip() != actual_org.strip()):
            continue
        if board not in matches:
            matches.append(board)
    if len(matches) != 1:
        raise RoutingError('routing_ambiguous: ask the user to select a board' if matches else
                           'routing_not_found: no board matches this authenticated host account; ask the user')
    board = matches[0]
    return {'backend':'local', 'board':board['board'], 'name':board['name'],
            'root':str(store.root), 'selected_by':'authenticated_host_identity', 'host':host}


def resolve_host(root, host):
    if host != 'claude':
        raise RoutingError('unsupported_host: use explicit profile selection for this host')
    store = Store(root)
    rules = configured_rules(store, host)
    if not rules:
        return {'routing':'unconfigured', 'host':host}
    # Inherit the actual host environment. Never choose a Claude config directory ourselves.
    try:
        result = subprocess.run(['claude', 'auth', 'status'], capture_output=True,
                                text=True, timeout=20)
        status = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise RoutingError('identity_unavailable: could not verify the current host account')
    if result.returncode or not isinstance(status, dict) or status.get('loggedIn') is not True:
        raise RoutingError('identity_unavailable: authenticate the current host account')
    return match_identity(store, host, {'verified':True, 'email':status.get('email'),
                                       'organization':status.get('orgId')}, rules=rules)
