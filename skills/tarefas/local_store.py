"""Local document store shared by CLI, HTTP and MCP. Python standard library only."""
import base64
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

MAX_BODY = 2 * 1024 * 1024
MAX_DOC = 256 * 1024
MAX_DOCUMENTS = 25000
MAX_BOARD_BYTES = 64 * 1024 * 1024
MAX_RECEIPTS = 10000
COLLECTIONS = {'tasks', 'dias', 'arquivo', 'recorrentes', 'config', 'indice'}
READS = {'get', 'list', 'query', 'info'}
WRITES = {'set', 'update', 'delete', 'batch', 'rebuild-index'}
# Evidence/context may be shared by several cards. Tracker IDs remain exclusive.
SHARED_KEY_PREFIXES = {'conversa', 'pr', 'branch', 'gsd', 'repo'}


class LocalError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)

    def as_dict(self):
        return {'error': {'code': self.code, 'message': self.message}}


def fail(code, message):
    raise LocalError(code, message)


def default_root():
    if os.environ.get('CORTEX_LOCAL_DIR'):
        return Path(os.environ['CORTEX_LOCAL_DIR']).expanduser()
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Cortex'
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'Cortex'
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'cortex'


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'), sort_keys=True)


def check_json(value, depth=0):
    if depth > 24:
        fail('invalid_argument', 'JSON nesting exceeds 24 levels')
    if isinstance(value, dict):
        for key, val in value.items():
            if not isinstance(key, str):
                fail('invalid_argument', 'Object keys must be strings')
            check_json(val, depth + 1)
    elif isinstance(value, list):
        for val in value:
            check_json(val, depth + 1)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        fail('invalid_argument', 'Unsupported JSON value')


def parse_json(text):
    try:
        value = json.loads(text, parse_constant=lambda _: fail('invalid_argument', 'Non-finite JSON number'))
        check_json(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        fail('invalid_argument', 'Invalid JSON')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def merge(old, patch):
    out = dict(old)
    for key, val in patch.items():
        out[key] = merge(out[key], val) if isinstance(val, dict) and isinstance(out.get(key), dict) else val
    return out


def identifier(value):
    if not isinstance(value, str) or not value or len(value) > 200 or '/' in value or '\\' in value or any(ord(c) < 32 for c in value):
        fail('invalid_argument', 'Invalid document identifier')
    return value


class Store:
    def __init__(self, root=None, create=False):
        self.root = Path(root or default_root()).expanduser().absolute()
        self.path = self.root / 'cortex.sqlite3'
        if create:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with closing(self.connect(create=True)) as db:
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS boards (id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE IF NOT EXISTS docs (board TEXT NOT NULL, collection TEXT NOT NULL, id TEXT NOT NULL,
                      data TEXT, version INTEGER NOT NULL, PRIMARY KEY(board,collection,id));
                    CREATE TABLE IF NOT EXISTS task_keys (board TEXT NOT NULL, key TEXT NOT NULL, id TEXT NOT NULL, PRIMARY KEY(board,key));
                    CREATE TABLE IF NOT EXISTS receipts (board TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(board,id));
                ''')
            if os.name != 'nt':
                os.chmod(self.path, 0o600)

    def connect(self, create=False):
        if not create and not self.path.is_file():
            fail('setup_required', 'Configure a local board first')
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        return db

    def boards(self):
        if not self.path.is_file():
            return []
        db = self.connect()
        try:
            return [dict(r) for r in db.execute('SELECT id AS board,name,revision FROM boards ORDER BY id')]
        finally:
            db.close()

    def init(self, name, locale, fuso):
        for val in (name, locale, fuso):
            if not isinstance(val, str) or not val.strip() or len(val) > 200:
                fail('invalid_argument', 'Name, locale and time zone are required')
        if not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', locale):
            fail('invalid_argument', 'Invalid locale')
        if not re.fullmatch(r'[A-Za-z0-9_+\-/]+', fuso):
            fail('invalid_argument', 'Invalid time zone')
        board = str(uuid.uuid4())
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO boards(id,name) VALUES (?,?)', (board, name))
            docs = {
                'schema': {'formato': 'quadro-tarefas', 'versao': 4, 'backend': 'local'},
                'preferencias': {'nome': name, 'escopo': board, 'idioma': locale, 'locale': locale, 'fuso': fuso,
                    'areas': [{'id': 'geral', 'nome': 'Geral' if locale.startswith('pt') else 'General'}], 'area_padrao': 'geral',
                    'card_por_conversa': {'ativo': True, 'modo': 'perguntar', 'ignorar_titulos': [], 'ignorar_cwd': []},
                    'automacao': {'encaminhar_plano': 'perguntar', 'renomear_conversas': False, 'arquivar_conversas': 'propor'},
                    'codigo': {'usa_git': False}, 'fechar': {'modo': 'perguntar'}},
                'fontes': {}, 'gestor': {'tipo': 'nenhum'}, 'projetos': {}, 'tema': {'fontes_externas': False},
            }
            for docid, data in docs.items():
                self._put(db, board, 'config', docid, data, 1)
            self._index(db, board)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return {'board': board, 'name': name, 'root': str(self.root)}

    def _board(self, db, board):
        if not isinstance(board, str) or not board:
            fail('setup_required', 'Select an explicit local board')
        row = db.execute('SELECT id AS board,name,revision FROM boards WHERE id=?', (board,)).fetchone()
        if row is None:
            fail('not_found', 'Board not found')
        return dict(row)

    def _get(self, db, board, collection, docid):
        row = db.execute('SELECT data,version FROM docs WHERE board=? AND collection=? AND id=?', (board, collection, docid)).fetchone()
        return {'id': docid, 'exists': bool(row and row['data'] is not None),
                'data': json.loads(row['data']) if row and row['data'] is not None else None,
                'version': row['version'] if row else None}

    def _put(self, db, board, collection, docid, data, version):
        db.execute('INSERT INTO docs VALUES (?,?,?,?,?) ON CONFLICT(board,collection,id) DO UPDATE SET data=excluded.data,version=excluded.version',
                   (board, collection, docid, encode(data) if data is not None else None, version))

    def _index(self, db, board):
        items = {}
        for row in db.execute("SELECT id,data FROM docs WHERE board=? AND collection='tasks' AND data IS NOT NULL", (board,)):
            data = json.loads(row['data'])
            items[row['id']] = {'t': data.get('titulo', ''), 's': data.get('status', 'entrada'), 'p': data.get('projeto', ''),
                'ps': data.get('projetos', []), 'tags': data.get('tags', []), 'k': data.get('chaves', []), 'pai': data.get('pai'), 'u': data.get('atualizado_em')}
        old = self._get(db, board, 'indice', 'ativos')
        self._put(db, board, 'indice', 'ativos', {'itens': items, 'atualizado_em': now()}, (old['version'] or 0) + 1)

    def dispatch(self, board, request):
        if not isinstance(request, dict):
            fail('invalid_argument', 'Request must be an object')
        check_json(request)
        try:
            packed = encode(request)
        except (ValueError, TypeError):
            fail('invalid_argument', 'Invalid JSON value')
        if len(packed.encode('utf-8')) > MAX_BODY:
            fail('quota_exceeded', 'Request too large')
        if not isinstance(request.get('op'), str) or request['op'] not in READS | WRITES:
            fail('invalid_argument', 'Unsupported operation')
        mutation = request['op'] in WRITES
        receipt = request.get('mutation_id')
        if receipt is not None:
            identifier(receipt)
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE' if mutation else 'BEGIN')
            info = self._board(db, board)
            digest = hashlib.sha256(packed.encode()).hexdigest()
            if mutation and receipt:
                old = db.execute('SELECT digest,result FROM receipts WHERE board=? AND id=?', (board, receipt)).fetchone()
                if old:
                    if old['digest'] != digest:
                        fail('conflict', 'mutation_id already used for different request')
                    db.commit()
                    return json.loads(old['result'])
            result = self._operation(db, board, request, info)
            if mutation:
                self._quota(db, board)
                self._index(db, board)
                db.execute('UPDATE boards SET revision=revision+1 WHERE id=?', (board,))
                if receipt:
                    if db.execute('SELECT COUNT(*) FROM receipts WHERE board=?', (board,)).fetchone()[0] >= MAX_RECEIPTS:
                        fail('quota_exceeded', 'Mutation receipt limit reached; export to a new board')
                    packed_result = encode(result)
                    receipt_bytes = db.execute('SELECT COALESCE(SUM(LENGTH(CAST(result AS BLOB))),0) FROM receipts WHERE board=?', (board,)).fetchone()[0]
                    if receipt_bytes + len(packed_result.encode('utf-8')) > MAX_BOARD_BYTES:
                        fail('quota_exceeded', 'Mutation receipt storage limit reached; export to a new board')
                    db.execute('INSERT INTO receipts VALUES (?,?,?,?)', (board, receipt, digest, packed_result))
            db.commit()
            return result
        except sqlite3.IntegrityError:
            db.rollback()
            fail('conflict', 'External identity already belongs to another task')
        except sqlite3.OperationalError:
            db.rollback()
            fail('unavailable', 'Local database is busy or unavailable; retry later')
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _operation(self, db, board, req, info):
        op = req.get('op')
        allowed = {'op', 'collection', 'id', 'data', 'if_version', 'mutation_id', 'filters', 'limit', 'cursor', 'operations'}
        if set(req) - allowed:
            fail('invalid_argument', 'Unknown request fields')
        if op == 'info':
            return info
        if op == 'rebuild-index':
            return {'rebuilt': True}
        if op == 'batch':
            operations = req.get('operations')
            if not isinstance(operations, list) or not 1 <= len(operations) <= 100:
                fail('invalid_argument', 'Batch needs 1 to 100 operations')
            if any(not isinstance(x, dict) or not isinstance(x.get('op'), str) or x['op'] not in {'set', 'update', 'delete'} or 'mutation_id' in x for x in operations):
                fail('invalid_argument', 'Batch contains invalid operation')
            return {'results': [self._operation(db, board, x, info) for x in operations]}
        collection = req.get('collection')
        if not isinstance(collection, str) or collection not in COLLECTIONS:
            fail('invalid_argument', 'Unknown collection')
        if op in {'list', 'query'}:
            return self._list(db, board, collection, req, info)
        docid = identifier(req.get('id'))
        current = self._get(db, board, collection, docid)
        if op == 'get':
            return current
        if op not in {'set', 'update', 'delete'}:
            fail('invalid_argument', 'Unsupported operation')
        if collection == 'indice':
            fail('invalid_argument', 'Index is derived; use rebuild-index')
        if collection == 'config' and docid == 'schema':
            fail('invalid_argument', 'Schema is managed by the runtime')
        version = req.get('if_version')
        if version is not None and (type(version) is not int or version < 1):
            fail('invalid_argument', 'if_version must be a positive integer')
        if current['version'] is not None:
            if not current['exists']:
                fail('conflict', 'Deleted IDs cannot be reused')
            if version != current['version']:
                fail('conflict', 'Document changed; reread before updating')
        elif op != 'set' or version is not None:
            fail('not_found', 'Document does not exist')
        if collection == 'config' and docid == 'preferencias' and op == 'delete':
            fail('invalid_argument', 'Board preferences cannot be deleted')
        data = None
        if op != 'delete':
            data = req.get('data')
            if not isinstance(data, dict):
                fail('invalid_argument', 'Document data must be an object')
            if op == 'update':
                data = merge(current['data'], data)
            if len(encode(data).encode('utf-8')) > MAX_DOC:
                fail('quota_exceeded', 'Document exceeds 256 KiB')
            if collection == 'tasks':
                self._validate_task(data)
            if collection == 'config' and docid == 'preferencias':
                for key in ('nome', 'locale', 'fuso'):
                    if not isinstance(data.get(key), str) or not data[key]:
                        fail('invalid_argument', 'Preferences require name, locale and time zone')
        if collection == 'tasks':
            db.execute('DELETE FROM task_keys WHERE board=? AND id=?', (board, docid))
            for key in (data or {}).get('chaves', []):
                if key.split(':', 1)[0] not in SHARED_KEY_PREFIXES:
                    db.execute('INSERT INTO task_keys VALUES (?,?,?)', (board, key, docid))
        self._put(db, board, collection, docid, data, (current['version'] or 0) + 1)
        return self._get(db, board, collection, docid)

    def _quota(self, db, board):
        count, size = db.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(data AS BLOB))),0) FROM docs WHERE board=? AND collection!='indice'", (board,)).fetchone()
        if count > MAX_DOCUMENTS or size > MAX_BOARD_BYTES:
            fail('quota_exceeded', 'Board storage limit reached; export or archive data')

    def _validate_task(self, data):
        if not isinstance(data.get('titulo'), str) or not data['titulo'].strip():
            fail('invalid_argument', 'Task title is required')
        if not isinstance(data.get('status', 'entrada'), str) or data.get('status', 'entrada') not in {'entrada', 'a_fazer', 'fazendo', 'esperando', 'feito'}:
            fail('invalid_argument', 'Invalid task status')
        for key in ('chaves', 'tags', 'projetos', 'relacionadas'):
            val = data.get(key, [])
            if not isinstance(val, list) or any(not isinstance(x, str) or not x for x in val) or len(set(val)) != len(val):
                fail('invalid_argument', 'Task string arrays must contain unique nonempty strings')
        for key in ('historico', 'links', 'conversas'):
            val = data.get(key, [])
            if not isinstance(val, list) or any(not isinstance(x, dict) for x in val):
                fail('invalid_argument', 'Invalid task object array')

    def _list(self, db, board, collection, req, info):
        filters = req.get('filters', [])
        if not isinstance(filters, list) or len(filters) > 20:
            fail('invalid_argument', 'Invalid filters')
        if filters and isinstance(filters[0], str):
            filters = [filters]
        ops = {'==', '!=', 'in', 'array-contains', '<', '<=', '>', '>='}
        for f in filters:
            if not isinstance(f, list) or len(f) != 3 or not isinstance(f[0], str) or not isinstance(f[1], str) or f[1] not in ops:
                fail('invalid_argument', 'Unsupported filter')
            if f[1] == 'in' and (not isinstance(f[2], list) or len(f[2]) > 100):
                fail('invalid_argument', 'in needs an array of at most 100 values')
        limit = req.get('limit', 100)
        if type(limit) is not int or not 1 <= limit <= 1000:
            fail('invalid_argument', 'limit must be between 1 and 1000')
        signature = hashlib.sha256(encode([board, collection, filters]).encode()).hexdigest()
        after = ''
        cursor = req.get('cursor')
        if cursor:
            try:
                if not isinstance(cursor, str) or len(cursor) > 2048:
                    raise ValueError()
                saved = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                if saved['q'] != signature or saved['revision'] != info['revision'] or not isinstance(saved['after'], str):
                    fail('conflict', 'Query changed; restart pagination')
                after = saved['after']
            except (ValueError, KeyError, TypeError, UnicodeError):
                fail('invalid_argument', 'Invalid cursor')
        docs, size, more = [], 0, False
        for row in db.execute('SELECT id,data,version FROM docs WHERE board=? AND collection=? AND data IS NOT NULL AND id>? ORDER BY id', (board, collection, after)):
            data = json.loads(row['data'])
            if all(self._matches(data, f) for f in filters):
                row_size = len(row['data'].encode('utf-8')) + 256
                if docs and (len(docs) >= limit or size + row_size > MAX_BODY):
                    more = True
                    break
                size += row_size
                docs.append({'id': row['id'], 'exists': True, 'data': data, 'version': row['version']})
        next_cursor = base64.urlsafe_b64encode(encode({'q': signature, 'revision': info['revision'], 'after': docs[-1]['id']}).encode()).decode() if more else None
        return {'docs': docs, 'next_cursor': next_cursor, 'revision': info['revision']}

    @staticmethod
    def _matches(data, rule):
        field, op, expected = rule
        value = data
        for part in field.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
        if op == '==': return value == expected
        if op == '!=': return value != expected
        if op == 'in': return value in expected
        if op == 'array-contains': return isinstance(value, list) and expected in value
        try:
            return {'<': lambda: value < expected, '<=': lambda: value <= expected,
                    '>': lambda: value > expected, '>=': lambda: value >= expected}[op]()
        except TypeError:
            return False
