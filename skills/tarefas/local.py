#!/usr/bin/env python3
"""Cortex local CLI and loopback board server. No dependencies or global daemon."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

from local_store import Store, LocalError, MAX_BODY, encode, fail, parse_json

HERE = Path(__file__).resolve().parent


def make_server(store, board, port=0):
    info = store.dispatch(board, {'op': 'info'})
    prefs = store.dispatch(board, {'op': 'get', 'collection': 'config', 'id': 'preferencias'})['data'] or {}
    theme = store.dispatch(board, {'op': 'get', 'collection': 'config', 'id': 'tema'})['data'] or {}
    title = prefs.get('nome') or info['name']
    css = theme.get('css', '')
    if not isinstance(css, str) or not isinstance(title, str):
        fail('invalid_argument', 'Invalid board title or theme CSS')
    with tempfile.TemporaryDirectory(prefix='cortex-board-') as folder:
        page = Path(folder) / 'board.html'
        command = [sys.executable, str(HERE / 'app' / 'build.py'), '--titulo', title,
                   '--sem-fontes-externas', '--out', str(page)]
        if css:
            theme_file = Path(folder) / 'theme.css'
            theme_file.write_text(css, encoding='utf-8')
            command += ['--tema-arquivo', str(theme_file)]
        # All persisted theme CSS passes through the existing build.py sanitizer.
        # External fonts remain disabled for the local board and its strict CSP.
        result = subprocess.run(command, capture_output=True, timeout=30)
        if result.returncode:
            fail('unavailable', 'Could not build board page')
        html = page.read_text(encoding='utf-8')
    bootstrap = '<script>window.CORTEX_LOCAL=' + encode({'board': board, 'api': '/api'}) + ';</script>\n<script src="/local-adapter.js"></script>\n'
    html = html.replace('<script>', bootstrap + '<script>', 1).encode('utf-8')
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'CortexLocal'
        sys_version = ''

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            pass  # Tokens, document data and browser requests are never logged.

        def reply(self, status, body, mime='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = encode(body).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def validate(self, api=False):
            expected = '127.0.0.1:' + str(self.server.server_port)
            if self.headers.get_all('Host') != [expected]:
                fail('unauthorized', 'Host not permitted')
            origins = self.headers.get_all('Origin')
            if origins is not None and origins != ['http://' + expected]:
                fail('unauthorized', 'Origin not permitted')
            if api:
                auth = self.headers.get_all('Authorization')
                if not auth or len(auth) != 1 or not secrets.compare_digest(auth[0], 'Bearer ' + token):
                    fail('unauthorized', 'Authorization required')

        def error(self, err):
            status = {'unauthorized': 401, 'conflict': 409, 'not_found': 404, 'quota_exceeded': 413,
                      'unavailable': 503}.get(err.code, 400)
            self.reply(status, err.as_dict())

        def do_GET(self):
            try:
                self.validate()
                if self.path == '/':
                    self.reply(200, html, 'text/html; charset=utf-8')
                elif self.path == '/local-adapter.js':
                    self.reply(200, (HERE / 'app' / 'local-adapter.js').read_bytes(), 'text/javascript; charset=utf-8')
                else:
                    fail('not_found', 'Route not found')
            except LocalError as err:
                self.error(err)
            except OSError:
                self.error(LocalError('unavailable', 'Board assets unavailable'))

        def do_POST(self):
            try:
                self.validate(api=True)
                if self.path != '/api':
                    fail('not_found', 'Route not found')
                if self.headers.get('Transfer-Encoding') or self.headers.get_content_type() != 'application/json':
                    fail('invalid_argument', 'Expected JSON with Content-Length')
                lengths = self.headers.get_all('Content-Length')
                if not lengths or len(lengths) != 1 or not lengths[0].isdigit():
                    fail('invalid_argument', 'Invalid Content-Length')
                length = int(lengths[0])
                if not 0 < length <= MAX_BODY:
                    fail('quota_exceeded', 'Request exceeds limit')
                body = self.rfile.read(length)
                if len(body) != length:
                    fail('invalid_argument', 'Incomplete request')
                self.reply(200, store.dispatch(board, parse_json(body)))
            except LocalError as err:
                self.error(err)
            except (TimeoutError, OSError):
                self.error(LocalError('unavailable', 'Request unavailable'))
            except Exception:
                self.error(LocalError('internal_error', 'Request failed'))

        def do_OPTIONS(self):
            self.reply(405, {'error': {'code': 'unauthorized', 'message': 'Cross-origin access is not supported'}})

    server = HTTPServer(('127.0.0.1', port), Handler)
    server.token = token
    server.board = board
    server.url = 'http://127.0.0.1:{}/#token={}'.format(server.server_port, token)
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root')
    ap.add_argument('--board')
    sub = ap.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--name', required=True)
    init.add_argument('--locale', required=True)
    init.add_argument('--fuso', required=True)
    sub.add_parser('boards', aliases=['list-boards'])
    sub.add_parser('call')
    serve = sub.add_parser('serve')
    serve.add_argument('--port', type=int, default=0)
    sub.add_parser('mcp')
    args = ap.parse_args(argv)
    try:
        if args.command == 'mcp':
            from local_mcp import run
            run(Store(args.root), args.board)
            return 0
        store = Store(args.root, create=args.command == 'init')
        if args.command == 'init':
            result = store.init(args.name, args.locale, args.fuso)
        elif args.command in {'boards', 'list-boards'}:
            result = {'boards': store.boards()}
        elif args.command == 'call':
            body = sys.stdin.buffer.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                fail('quota_exceeded', 'Request exceeds limit')
            result = store.dispatch(args.board, parse_json(body))
        elif args.command == 'serve':
            if not 0 <= args.port <= 65535:
                fail('invalid_argument', 'Invalid port')
            server = make_server(store, args.board, args.port)
            print(encode({'url': server.url, 'board': args.board, 'port': server.server_port}), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        print(encode(result))
        return 0
    except LocalError as err:
        print(encode(err.as_dict()), file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError):
        print(encode(LocalError('unavailable', 'Local runtime unavailable').as_dict()), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
