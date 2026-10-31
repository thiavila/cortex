#!/usr/bin/env python3
"""Optional local service: multiple boards, one process, no polling while idle."""
import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from local import make_server
from local_store import Store


def write_status(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as out:
            name = out.name
            json.dump(value, out)
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def serve(config_path, status_path):
    config = json.loads(config_path.read_text())
    entries = config['boards']
    if not isinstance(entries, dict) or not 1 <= len(entries) <= 20:
        raise ValueError('Expected 1 to 20 configured boards')
    store = Store(config.get('root'))
    servers = []
    selector = selectors.DefaultSelector()
    metadata = {'pid':os.getpid(), 'boards':{}}
    def stop(*_args):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for name, entry in entries.items():
            port = entry.get('port', 0)
            if type(port) is not int or not 0 <= port <= 65535:
                raise ValueError('Invalid port')
            server = make_server(store, entry['board'], port)
            servers.append(server)
            selector.register(server, selectors.EVENT_READ)
            metadata['boards'][name] = {'board':entry['board'], 'url':server.url}
        # Credentials stay in this private local file, never stdout/logs.
        write_status(status_path, metadata)
        while True:
            # Blocks in the OS: no timer, busy loop, database polling or browser.
            for key, _ in selector.select():
                key.fileobj.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        selector.close()
        for server in servers:
            server.server_close()
        try:
            if json.loads(status_path.read_text()).get('pid') == os.getpid():
                status_path.unlink()
        except (OSError, ValueError):
            pass


def open_board(status_path, name):
    for _ in range(50):
        try:
            data = json.loads(status_path.read_text())
            os.kill(data['pid'], 0)
            url = data['boards'][name]['url']
            parsed = urlsplit(url)
            if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password:
                raise ValueError('Expected local board URL')
            subprocess.run(['open', url], check=True)
            return
        except (FileNotFoundError, ProcessLookupError):
            time.sleep(0.1)
    raise RuntimeError('Local service is not running')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--status', type=Path, required=True)
    parser.add_argument('--open', dest='board')
    args = parser.parse_args()
    try:
        if args.board:
            open_board(args.status, args.board)
        elif args.config:
            serve(args.config, args.status)
        else:
            parser.error('--config is required when serving')
        return 0
    except Exception:
        # Config/status can contain private paths and credentials: keep logs generic.
        print('Cortex local service unavailable; check local configuration.', file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
