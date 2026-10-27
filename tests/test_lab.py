import contextlib
import http.cookiejar
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request
from wsgiref.simple_server import make_server, WSGIRequestHandler

FILES = Path(__file__).resolve().parents[1] / 'provisioning' / 'files'
sys.path.insert(0, str(FILES))
import app
import checker
import monitor


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *_args):
        pass


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'lab.db'
        self.server = make_server('127.0.0.1', 0, app.create_app(self.db), handler_class=QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = f'127.0.0.1:{self.server.server_port}'
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, client=None):
        request = urllib.request.Request(f'http://{self.host}{path}')
        if data is not None:
            request.data = json.dumps(data).encode()
            request.add_header('Content-Type', 'application/json')
        try:
            response = (client or self.client).open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def account(self, name='learner'):
        self.assertEqual(self.request('/register', {'username': name, 'password': 'test-password-123'})[0], 201)
        self.assertEqual(self.request('/login', {'username': name, 'password': 'test-password-123'})[0], 200)

    def checker(self, *args):
        return subprocess.run([sys.executable, str(FILES / 'checker.py'), *args], capture_output=True, text=True, timeout=15)

    def test_health_and_benign_search(self):
        self.assertEqual(self.request('/health')[0], 200)
        self.assertEqual(self.request('/search?q=book')[1]['results'][0]['name'], 'Notebook')

    def test_auth_and_private_notes(self):
        self.assertEqual(self.request('/notes')[0], 401)
        self.account()
        self.assertEqual(self.request('/notes', {'body': 'private-marker'})[0], 201)
        self.assertEqual(self.request('/notes')[1]['notes'][0]['body'], 'private-marker')
        self.account('another')
        self.assertEqual(self.request('/notes')[1]['notes'], [])
        self.assertEqual(self.request('/login', {'username': "' OR 1=1 --", 'password': 'bad'})[0], 401)

    def test_sql_injection_and_parameterized_fix(self):
        self.account()
        self.request('/notes', {'body': 'SQLI-SECRET-MARKER'})
        query = "' UNION SELECT id, owner, body FROM notes -- "
        path = '/search?' + urllib.parse.urlencode({'q': query})
        anonymous = urllib.request.build_opener()
        self.assertIn('SQLI-SECRET-MARKER', json.dumps(self.request(path, client=anonymous)[1]))
        fixed_app = app.create_app(self.db, fixed=True)
        with make_server('127.0.0.1', 0, fixed_app, handler_class=QuietHandler) as server:
            worker = threading.Thread(target=server.handle_request)
            worker.start()
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}{path}', timeout=5) as response:
                self.assertNotIn('SQLI-SECRET-MARKER', response.read().decode())
            worker.join()

    def test_validation_and_error_responses(self):
        self.assertEqual(self.request('/missing')[0], 404)
        self.assertEqual(self.request('/register', {'username': '', 'password': 'x'})[0], 400)
        self.account()
        self.assertEqual(self.request('/register', {'username': 'learner', 'password': 'test-password-123'})[0], 409)
        self.assertEqual(self.request('/notes', {'body': ''})[0], 400)
        self.assertEqual(self.request('/search?q=%27')[0], 400)
        self.assertEqual(self.request('/login', {'username': [], 'password': {}})[0], 400)
        self.assertEqual(self.request('/register', [1, 2])[0], 400)

    def test_checker_cli_and_down_malformed_service(self):
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main(['check', self.host]), 101)
            self.assertEqual(checker.main(['check', 'https://invalid.test']), 110)
            self.assertEqual(checker.main(['check', 'http://host/path']), 110)
            self.assertEqual(checker.main(['check', '127.0.0.1:bad']), 110)
            self.assertEqual(checker.main(['get', self.host, '{}', 'flag', '1']), 110)
            self.assertEqual(checker.main(['unknown']), 110)
            public_output, private_output = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(public_output), contextlib.redirect_stderr(private_output):
                self.assertEqual(checker.main(['put', self.host, 'seed', 'FLAG', '1']), 101)
            self.assertEqual(checker.main(['get', self.host, private_output.getvalue().strip(), 'FLAG', '1']), 101)
        client = checker.Client(self.host)
        with self.assertRaises(checker.Verdict) as error:
            client.request('/missing')
        self.assertEqual(error.exception.status, checker.MUMBLE)
        with mock.patch.object(client.opener, 'open', side_effect=urllib.error.URLError('down')):
            with self.assertRaises(checker.Verdict) as error:
                client.request('/health')
            self.assertEqual(error.exception.status, checker.DOWN)
        with mock.patch.object(checker.Client, 'request', return_value={'status': 'wrong'}):
            with self.assertRaises(checker.Verdict):
                checker.check(self.host)
        with mock.patch.object(checker.Client, 'request', side_effect=[{'status': 'ok'}, {'results': []}]):
            with self.assertRaises(checker.Verdict):
                checker.check(self.host)

    def test_cli_app_and_monitor_end_to_end(self):
        # Reserve a port, then start the actual app CLI and independent monitor process.
        import socket
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        command = [sys.executable, str(FILES / 'app.py'), '--port', str(port),
                   '--db', str(Path(self.temp.name) / 'cli.db'), '--fixed']
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            target = f'127.0.0.1:{port}'
            for _ in range(40):
                try:
                    checker.check(target)
                    break
                except checker.Verdict:
                    if process.poll() is not None:
                        self.fail('App CLI exited before health check')
                    time.sleep(0.1)
            else:
                self.fail('App CLI did not become healthy')
            result = subprocess.run([sys.executable, str(FILES / 'monitor.py'), '--target', target,
                '--state', str(Path(self.temp.name) / 'cli-state.json'), '--once'],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'OK')
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_checker_forcad_contract_and_persistence(self):
        self.assertEqual(self.checker('check', self.host).returncode, 101)
        put = self.checker('put', self.host, 'seed', 'S' * 31 + '=', '1')
        self.assertEqual(put.returncode, 101, put.stderr)
        self.assertTrue(json.loads(put.stdout)['owner'].startswith('checker_'))
        private = put.stderr.strip()
        self.assertEqual(self.checker('get', self.host, private, 'S' * 31 + '=', '1').returncode, 101)
        self.assertEqual(self.checker('get', self.host, private, 'wrong', '1').returncode, 102)
        self.assertEqual(self.checker('get', self.host, 'bad-json', 'flag', '1').returncode, 110)
        self.assertEqual(self.checker('unknown', self.host).returncode, 110)
        # Recreate the app over the same SQLite file: data survives process restart.
        app.create_app(self.db)
        self.assertEqual(self.checker('get', self.host, private, 'S' * 31 + '=', '1').returncode, 101)

    def test_monitor_roundtrip_and_previous_flag_detection(self):
        state = Path(self.temp.name) / 'state.json'
        result = monitor.run_round(self.host, state, keep=2)
        self.assertEqual(result['status'], 'OK')
        monitor.run_round(self.host, state, keep=2)
        monitor.run_round(self.host, state, keep=2)
        self.assertEqual(len(json.loads(state.read_text())['flags']), 2)
        with self.assertRaises(ValueError):
            monitor.run_round(self.host, state, keep=0)
        with self.assertRaises(ValueError):
            monitor.run_round('another-target', state, keep=2)
        import sqlite3
        with contextlib.closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE notes SET body = 'tampered'")
        before = state.read_bytes()
        with self.assertRaises(Exception):
            monitor.run_round(self.host, state, keep=2)
        self.assertEqual(state.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
