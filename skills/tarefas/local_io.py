#!/usr/bin/env python3
"""Explicit portable backup/migration; preview is validated against an in-memory copy."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

from local_store import Store, LocalError, encode, fail, parse_json, identifier

COLLECTIONS = ('tasks', 'dias', 'arquivo', 'recorrentes', 'config')
MAX_PACKAGE = 20 * 1024 * 1024
MAX_DOCUMENTS = 25000


def load_package(path):
    with open(path, 'rb') as source:
        raw = source.read(MAX_PACKAGE + 1)
    if len(raw) > MAX_PACKAGE:
        fail('quota_exceeded', 'Package exceeds 20 MiB')
    package = parse_json(raw)
    if not isinstance(package, dict) or package.get('formato') != 'quadro-tarefas' or package.get('versao') != 1:
        fail('invalid_argument', 'Expected quadro-tarefas export version 1')
    if any(not isinstance(package.get(c), dict) for c in COLLECTIONS):
        fail('invalid_argument', 'A complete export needs tasks, days, archive, recurring and config collections')
    schema = package['config'].get('schema', {})
    if not isinstance(schema, dict) or schema.get('versao') != 4:
        fail('invalid_argument', 'Upgrade the source board to schema 4 before exporting')
    if sum(len(package[c]) for c in COLLECTIONS) > MAX_DOCUMENTS:
        fail('quota_exceeded', 'Package exceeds 25000 documents')
    return package, hashlib.sha256(raw).hexdigest()


def export_package(store, board):
    db = store.connect()
    try:
        db.execute('BEGIN')
        store._board(db, board)
        result = {'formato': 'quadro-tarefas', 'versao': 1, 'exportado_em': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        for collection in COLLECTIONS:
            result[collection] = {r['id']: json.loads(r['data']) for r in db.execute(
                'SELECT id,data FROM docs WHERE board=? AND collection=? AND data IS NOT NULL ORDER BY id', (board, collection))}
        result['escopo'] = result['config'].get('preferencias', {}).get('escopo', board)
        if len(encode(result).encode('utf-8')) > MAX_PACKAGE:
            fail('quota_exceeded', 'Export exceeds package limit')
        return result
    finally:
        db.rollback()
        db.close()


def import_package(store, board, package, digest, apply=False):
    source = store.connect()
    db = source
    if not apply:
        # A preview never issues INSERT/UPDATE/DELETE against the user's database.
        db = sqlite3.connect(':memory:', isolation_level=None)
        db.row_factory = sqlite3.Row
        source.backup(db)
        source.close()
    try:
        db.execute('BEGIN IMMEDIATE')
        info = store._board(db, board)
        used = db.execute("SELECT 1 FROM docs WHERE board=? AND (collection IN ('tasks','dias','arquivo','recorrentes') OR (collection='config' AND id='cortex_import')) LIMIT 1", (board,)).fetchone()
        if used:
            fail('conflict', 'Import requires a new empty destination board; source is never changed')
        for collection in COLLECTIONS:
            for docid, data in package[collection].items():
                identifier(docid)
                if not isinstance(data, dict):
                    fail('invalid_argument', 'Every exported document must be an object')
                if collection == 'config' and docid in {'schema', 'cortex_import'}:
                    continue
                current = store._get(db, board, collection, docid)
                request = {'op': 'set', 'collection': collection, 'id': docid, 'data': data}
                if current['exists']:
                    request['if_version'] = current['version']
                store._operation(db, board, request, info)
        store._operation(db, board, {'op': 'set', 'collection': 'config', 'id': 'cortex_import',
            'data': {'sha256': digest, 'em': datetime.datetime.now(datetime.timezone.utc).isoformat()}}, info)
        store._index(db, board)
        store._quota(db, board)
        db.execute('UPDATE boards SET revision=revision+1 WHERE id=?', (board,))
        summary = {'applied': apply, 'board': board, 'sha256': digest,
                   'documents': {c: len(package[c]) for c in COLLECTIONS}, 'source_preserved': True}
        if apply:
            db.commit()
        else:
            db.rollback()
        return summary
    except sqlite3.IntegrityError:
        db.rollback()
        fail('conflict', 'Package has duplicate task identities')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root')
    ap.add_argument('--board', required=True)
    sub = ap.add_subparsers(dest='command', required=True)
    exp = sub.add_parser('export'); exp.add_argument('--out', required=True)
    imp = sub.add_parser('import'); imp.add_argument('--input', required=True); imp.add_argument('--apply', action='store_true')
    args = ap.parse_args(argv)
    try:
        store = Store(args.root)
        if args.command == 'import':
            package, digest = load_package(args.input)
            result = import_package(store, args.board, package, digest, args.apply)
        else:
            package = export_package(store, args.board)
            target = Path(args.out).expanduser().absolute()
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as f:
                temp = f.name
                f.write(encode(package))
            try:
                os.replace(temp, target)
            finally:
                if os.path.exists(temp): os.unlink(temp)
            result = {'out': str(target), 'documents': {c: len(package[c]) for c in COLLECTIONS}}
        print(encode(result))
        return 0
    except LocalError as error:
        print(encode(error.as_dict()), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error):
        print(encode({'error': {'code': 'unavailable', 'message': 'Backup or migration unavailable'}}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
