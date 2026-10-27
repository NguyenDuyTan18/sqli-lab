#!/usr/bin/env python3
"""Intentionally vulnerable SQLi lab. All data is local to this training service."""
import argparse
from contextlib import closing
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
from pathlib import Path
import re
import secrets
from socketserver import ThreadingMixIn
import sqlite3
import time
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server, WSGIServer

HOME = b'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Range Shop - SQL injection lab</title>
<style>body{font:18px system-ui;max-width:760px;margin:60px auto;padding:20px}
input,button{font:inherit;padding:8px}code{background:#eee}</style>
<h1>Range Shop</h1><p>Find products in our training store.</p>
<form action="/search"><input name="q" value="book"><button>Search</button></form>
<h2>Private notes API</h2><p>Use POST /register, POST /login and GET/POST /notes
with JSON bodies. Keep the session cookie after login.</p>
<p>Objective: demonstrate how an unsafe product search can expose private notes,
then fix the SQL query while keeping normal features working.</p></html>'''


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 100000).hex()


def create_app(db_path, fixed=False):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users
                (username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions
                (token TEXT PRIMARY KEY, owner TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS notes
                (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS products
                (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
            INSERT OR IGNORE INTO products VALUES
                (1, 'Notebook', 'A notebook for the lab'),
                (2, 'Keyboard', 'A keyboard for your range workstation');
        ''')

    def application(environ, start_response):
        def respond(status, data, headers=None):
            body = json.dumps(data).encode()
            start_response(status, [('Content-Type', 'application/json; charset=utf-8'),
                                    ('Content-Length', str(len(body))),
                                    ('Cache-Control', 'no-store')] + (headers or []))
            return [body]

        path, method = environ.get('PATH_INFO', '/'), environ.get('REQUEST_METHOD', 'GET')
        if path == '/' and method == 'GET':
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'),
                                      ('Content-Length', str(len(HOME)))])
            return [HOME]
        if path == '/health' and method == 'GET':
            return respond('200 OK', {'status': 'ok', 'service': 'range-shop'})
        data = {}
        if method == 'POST':
            try:
                length = int(environ.get('CONTENT_LENGTH') or 0)
                if not 0 < length <= 4096:
                    return respond('400 Bad Request', {'error': 'JSON body required, maximum 4096 bytes'})
                data = json.loads(environ['wsgi.input'].read(length))
                if not isinstance(data, dict):
                    raise ValueError('Object required')
            except (ValueError, UnicodeError):
                return respond('400 Bad Request', {'error': 'Invalid JSON'})

        with closing(sqlite3.connect(db_path, timeout=5)) as connection, connection:
            connection.row_factory = sqlite3.Row
            if path == '/search' and method == 'GET':
                query = parse_qs(environ.get('QUERY_STRING', '')).get('q', [''])[0]
                if len(query) > 512:
                    return respond('400 Bad Request', {'error': 'Query too long'})
                try:
                    if fixed:
                        rows = connection.execute(
                            'SELECT id, name, description FROM products WHERE name LIKE ?',
                            ('%' + query + '%',)).fetchall()
                    else:
                        # TRAINING VULNERABILITY: attacker controls part of this SELECT.
                        rows = connection.execute(
                            f"SELECT id, name, description FROM products WHERE name LIKE '%{query}%'").fetchall()
                except sqlite3.Error:
                    return respond('400 Bad Request', {'error': 'Invalid search query'})
                return respond('200 OK', {'results': [dict(row) for row in rows]})

            if path in ('/register', '/login') and method == 'POST':
                username, password = data.get('username'), data.get('password')
                if not isinstance(username, str) or not isinstance(password, str):
                    return respond('400 Bad Request', {'error': 'Username and password must be strings'})
                if path == '/register':
                    if not re.fullmatch(r'[a-zA-Z0-9_]{3,64}', username) or not 12 <= len(password) <= 128:
                        return respond('400 Bad Request', {'error': 'Username 3-64 letters/digits/underscore; password 12-128 characters'})
                    salt = secrets.token_hex(16)
                    try:
                        connection.execute('INSERT INTO users VALUES (?, ?, ?)',
                                           (username, salt, password_hash(password, salt)))
                    except sqlite3.IntegrityError:
                        return respond('409 Conflict', {'error': 'Username already exists'})
                    return respond('201 Created', {'username': username})
                if len(username) > 64 or len(password) > 128:
                    return respond('401 Unauthorized', {'error': 'Invalid credentials'})
                row = connection.execute('SELECT salt, digest FROM users WHERE username = ?', (username,)).fetchone()
                if row is None or not hmac.compare_digest(row['digest'], password_hash(password, row['salt'])):
                    return respond('401 Unauthorized', {'error': 'Invalid credentials'})
                connection.execute('DELETE FROM sessions WHERE expires < ?', (int(time.time()),))
                token = secrets.token_hex(32)
                connection.execute('INSERT INTO sessions VALUES (?, ?, ?)', (token, username, int(time.time()) + 3600))
                return respond('200 OK', {'username': username},
                               [('Set-Cookie', f'session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600')])

            if path == '/notes' and method in ('GET', 'POST'):
                cookies = SimpleCookie()
                cookies.load(environ.get('HTTP_COOKIE', ''))
                token = cookies['session'].value if 'session' in cookies else ''
                session = connection.execute('SELECT owner FROM sessions WHERE token = ? AND expires >= ?',
                                             (token, int(time.time()))).fetchone()
                if session is None:
                    return respond('401 Unauthorized', {'error': 'Login required'})
                owner = session['owner']
                if method == 'POST':
                    body = data.get('body')
                    if not isinstance(body, str) or not 1 <= len(body) <= 512:
                        return respond('400 Bad Request', {'error': 'Note must contain 1-512 characters'})
                    cursor = connection.execute('INSERT INTO notes (owner, body) VALUES (?, ?)', (owner, body))
                    return respond('201 Created', {'id': cursor.lastrowid})
                rows = connection.execute('SELECT id, body FROM notes WHERE owner = ? ORDER BY id', (owner,)).fetchall()
                return respond('200 OK', {'notes': [dict(row) for row in rows]})
        return respond('404 Not Found', {'error': 'Not found'})

    return application


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True
    request_queue_size = 64

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--db', type=Path, default=Path('lab.db'))
    parser.add_argument('--fixed', action='store_true', help='Use parameterized search query')
    args = parser.parse_args()
    with make_server(args.host, args.port, create_app(args.db, args.fixed), server_class=ThreadedServer) as server:
        print(f'Range Shop listening on {args.host}:{args.port}', flush=True)
        server.serve_forever()
