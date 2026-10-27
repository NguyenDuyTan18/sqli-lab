import importlib.util, io, json, tempfile, unittest
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portal_sqli', ROOT / 'app/portal.py')
portal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portal)

class SQLILabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.app = portal.create_app(Path(self.tmp.name) / 'db', 'secret', 'team')
    def request(self, path, data=None, cookie=''):
        body = urlencode(data or {}).encode(); result = {}
        env = {'PATH_INFO': path, 'REQUEST_METHOD': 'POST' if data is not None else 'GET', 'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body), 'HTTP_COOKIE': cookie}
        result['body'] = b''.join(self.app(env, lambda status, headers: result.update(status=int(status.split()[0]), headers=dict(headers))))
        return result
    def test_sqli_search_and_object_access(self):
        login = self.request('/login', {'username': 'alice', 'password': 'secret'})
        cookie = login['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('/api/tickets/1401', cookie=cookie)['status'], 403)
        normal = self.request('/api/search', {'query': 'Laptop'}, cookie)
        self.assertEqual([x['id'] for x in json.loads(normal['body'])], [1201])
        injected = self.request('/api/search', {'query': "' OR 1=1 -- "}, cookie)
        self.assertEqual({x['id'] for x in json.loads(injected['body'])}, {1201, 1401})
        self.assertEqual(self.request('/api/search', {'query': "'"}, cookie)['status'], 400)
        self.assertEqual(self.request('/api/search', {'query': 'Laptop'})['status'], 401)
