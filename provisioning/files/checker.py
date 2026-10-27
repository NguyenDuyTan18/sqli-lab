#!/usr/bin/env python3
"""ForcAD/Hackerdom checker: check, put, get. Uses Python standard library only."""
import http.cookiejar
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

OK, CORRUPT, MUMBLE, DOWN, CHECK_FAILED = 101, 102, 103, 104, 110


class Verdict(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def base_url(target):
    parsed = urllib.parse.urlsplit(target if '://' in target else 'http://' + target)
    if parsed.scheme != 'http' or not parsed.hostname or parsed.username or parsed.password:
        raise Verdict(CHECK_FAILED, 'Target must be an HTTP host, optionally with port')
    if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise Verdict(CHECK_FAILED, 'Target must not include a path, query or fragment')
    try:
        port = parsed.port or 8080
    except ValueError as error:
        raise Verdict(CHECK_FAILED, 'Invalid target port') from error
    host = f'[{parsed.hostname}]' if ':' in parsed.hostname else parsed.hostname
    return f'http://{host}:{port}'


class Client:
    def __init__(self, target):
        self.url = base_url(target)
        # Do not send lab traffic through workstation HTTP_PROXY settings.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, data=None, expected=200):
        body = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(self.url + path, data=body, headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=3) as response:
                if response.status != expected:
                    raise Verdict(MUMBLE, f'Unexpected HTTP status at {path}')
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise Verdict(MUMBLE, 'Service response too large')
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise Verdict(MUMBLE, 'Service returned a non-object response')
                return value
        except urllib.error.HTTPError as error:
            error.close()
            raise Verdict(MUMBLE, f'HTTP {error.code} at {path}') from error
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            raise Verdict(DOWN, 'Service connection failed or timed out') from error
        except (ValueError, UnicodeError) as error:
            raise Verdict(MUMBLE, 'Invalid JSON response') from error


def check(target):
    client = Client(target)
    if client.request('/health').get('status') != 'ok':
        raise Verdict(MUMBLE, 'Health check failed')
    rows = client.request('/search?q=book').get('results')
    if not isinstance(rows, list) or not any(isinstance(row, dict) and row.get('name') == 'Notebook' for row in rows):
        raise Verdict(MUMBLE, 'Product search failed')


def put(target, flag):
    client = Client(target)
    credentials = {'username': 'checker_' + secrets.token_hex(12), 'password': secrets.token_urlsafe(24)}
    client.request('/register', credentials, expected=201)
    client.request('/login', credentials)
    result = client.request('/notes', {'body': flag}, expected=201)
    if not isinstance(result.get('id'), int):
        raise Verdict(MUMBLE, 'Service did not return note ID')
    return {'owner': credentials['username'], 'note_id': result['id']}, {**credentials, 'note_id': result['id']}


def get(target, private, flag):
    if not isinstance(private, dict) or not all(key in private for key in ('username', 'password', 'note_id')):
        raise Verdict(CHECK_FAILED, 'Invalid private flag data')
    client = Client(target)
    client.request('/login', {'username': private['username'], 'password': private['password']})
    rows = client.request('/notes').get('notes')
    if not isinstance(rows, list):
        raise Verdict(MUMBLE, 'Invalid notes response')
    if not any(isinstance(row, dict) and row.get('id') == private['note_id'] and row.get('body') == flag for row in rows):
        raise Verdict(CORRUPT, 'Flag missing or modified')


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(args) == 2 and args[0] == 'check':
            check(args[1])
            print('OK')
        elif len(args) == 5 and args[0] == 'put':
            public, private = put(args[1], args[3])
            print(json.dumps(public, separators=(',', ':')))
            print(json.dumps(private, separators=(',', ':')), file=sys.stderr)
        elif len(args) == 5 and args[0] == 'get':
            get(args[1], json.loads(args[2]), args[3])
            print('OK')
        else:
            raise Verdict(CHECK_FAILED, 'Usage: checker.py check HOST | put/get HOST FLAG_ID FLAG VULN')
        return OK
    except Verdict as error:
        print(error.message)
        return error.status
    except (ValueError, TypeError, KeyError):
        print('Invalid checker arguments or malformed service response')
        return CHECK_FAILED


if __name__ == '__main__':
    sys.exit(main())
