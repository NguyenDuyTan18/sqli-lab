"""Run locally on a team VM; emit a single JSON status object."""
import json
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, HTTPCookieProcessor, build_opener
from pathlib import Path


def check(base_url, password, expected_identity):
    result = {'identity': expected_identity, 'service': 'down', 'authentication': 'unknown', 'sqli': 'unknown'}
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    try:
        with client.open(base_url + '/health', timeout=5) as response:
            health = json.load(response)
        if health.get('status') != 'ok' or health.get('sandbox') != expected_identity:
            result['service'] = 'identity_mismatch'
            return result
        result['service'] = 'up'
        req = Request(base_url + '/login', data=urlencode({'username': 'alice', 'password': password}).encode())
        try:
            with client.open(req, timeout=5) as response:
                login = json.load(response)
            if login.get('user') != 'alice':
                result['authentication'] = 'failed'
                return result
            result['authentication'] = 'ok'
        except HTTPError as exc:
            exc.close()
            result['authentication'] = 'failed'
            return result
        req = Request(base_url + '/api/search', data=urlencode({'query': "' OR 1=1 -- "}).encode())
        try:
            with client.open(req, timeout=5) as response:
                rows = json.load(response)
            result['sqli'] = 'vulnerable' if any(row.get('owner') == 'bob' for row in rows) else 'not_detected'
        except HTTPError as exc:
            result['sqli'] = 'not_detected' if exc.code == 400 else 'unknown'
            exc.close()
    except (OSError, URLError, ValueError, TypeError, KeyError):
        pass
    return result


def main():
    try:
        config = json.loads(Path('/home/user-access/.sqli-checker.json').read_text(encoding='utf-8'))
        result = check('http://127.0.0.1:8080', config['password'], config['identity'])
        print(json.dumps(result))
        return 0 if result['service'] == 'up' and result['authentication'] == 'ok' else 1
    except (OSError, ValueError, KeyError):
        print(json.dumps({'service': 'unknown', 'authentication': 'unknown', 'sqli': 'unknown', 'error': 'checker_config_error'}))
        return 2

if __name__ == '__main__':
    sys.exit(main())
