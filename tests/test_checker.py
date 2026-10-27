import importlib.util, json, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import make_server, WSGIRequestHandler
ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
portal = load('portal_check', 'app/portal.py')
checker = load('internal_check', 'checker/internal.py')
external = load('external_check', 'checker/external.py')
class Quiet(WSGIRequestHandler):
    def log_message(self, *args): pass
class CheckerTests(unittest.TestCase):
    def test_real_service_and_failed_authentication(self):
        with tempfile.TemporaryDirectory() as temp:
            app = portal.create_app(Path(temp) / 'db', 'secret', 'team')
            with make_server('127.0.0.1', 0, app, handler_class=Quiet) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                try:
                    url = 'http://127.0.0.1:' + str(server.server_port)
                    self.assertEqual(checker.check(url, 'secret', 'team'), {'identity':'team','service':'up','authentication':'ok','sqli':'vulnerable'})
                    self.assertEqual(checker.check(url, 'wrong', 'team')['authentication'], 'failed')
                    self.assertEqual(checker.check(url, 'secret', 'other')['service'], 'identity_mismatch')
                finally:
                    server.shutdown(); thread.join()
    def test_external_uses_strict_host_keys_and_passes_through_json(self):
        from types import SimpleNamespace
        with patch('sys.argv', ['external.py', '--host', '10.80.0.11', '--key', '/key', '--known-hosts', '/known']), patch.object(external.subprocess, 'run', return_value=SimpleNamespace(stdout='{"service":"up"}', returncode=0)) as run:
            self.assertEqual(external.main(), 0)
            cmd = run.call_args.args[0]
            self.assertIn('StrictHostKeyChecking=yes', cmd)
            self.assertIn('user-access@10.80.0.11', cmd)
    def test_provisioning_installs_checker_and_protects_password(self):
        import yaml
        plays = yaml.safe_load((ROOT / 'provisioning/playbook.yml').read_text(encoding='utf-8'))
        tasks = [t for play in plays for t in play.get('tasks', [])]
        config = next(t for t in tasks if t.get('name') == 'Configure the internal checker for this team')
        self.assertEqual(config['ansible.builtin.copy']['mode'], '0600')
        self.assertTrue(config['no_log'])
