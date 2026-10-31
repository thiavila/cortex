import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/tarefas'))
from local_store import Store


class ServiceTest(unittest.TestCase):
    def test_two_boards_one_process_private_status_restart_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            store = Store(path/'data', create=True)
            boards = {key:store.init(key,'en-US','UTC')['board'] for key in ['one','two']}
            store.dispatch(boards['one'], {'op':'set','collection':'tasks','id':'kept','data':{'titulo':'Kept'}})
            config, status = path/'service.json', path/'run/status.json'
            config.write_text(json.dumps({'root':str(store.root),'boards':{key:{'board':board,'port':0} for key,board in boards.items()}}))
            previous = None
            for _ in range(2):
                proc = subprocess.Popen([sys.executable,str(ROOT/'skills/tarefas/service.py'),
                    '--config',str(config),'--status',str(status)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    until = time.monotonic()+10
                    while not status.exists() and proc.poll() is None and time.monotonic()<until:
                        time.sleep(.05)
                    self.assertTrue(status.exists())
                    meta = json.loads(status.read_text())
                    self.assertEqual(meta['pid'],proc.pid)
                    if os.name!='nt': self.assertEqual(status.stat().st_mode & 0o777,0o600)
                    self.assertEqual(set(meta['boards']),{'one','two'})
                    for key,board in boards.items():
                        url = urlsplit(meta['boards'][key]['url'])
                        token = parse_qs(url.fragment)['token'][0]
                        conn = http.client.HTTPConnection(url.hostname,url.port,timeout=5)
                        conn.request('POST','/api',json.dumps({'op':'get','collection':'tasks','id':'kept'}),
                            {'Authorization':'Bearer '+token,'Content-Type':'application/json'})
                        response = conn.getresponse();data=json.loads(response.read());conn.close()
                        self.assertEqual(response.status,200)
                        self.assertEqual(data['exists'],key=='one')
                    current=meta['boards']['one']['url']
                    self.assertNotEqual(current,previous);previous=current
                finally:
                    proc.terminate();stdout,stderr=proc.communicate(timeout=5)
                self.assertEqual(proc.returncode,0,stderr.decode())
                self.assertEqual(stdout,b'')
                self.assertFalse(status.exists())
            self.assertTrue(store.dispatch(boards['one'],{'op':'get','collection':'tasks','id':'kept'})['exists'])


if __name__ == '__main__': unittest.main()
