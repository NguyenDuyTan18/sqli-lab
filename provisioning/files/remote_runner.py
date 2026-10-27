#!/usr/bin/env python3
"""Restricted SSH entry point for the external checker controller."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import checker
import monitor

TARGETS_FILE = Path('/etc/sqli-checker/targets.json')
STATE_DIR = Path('/var/lib/sqli-checker/targets')
LOCK_FILE = Path('/var/lib/sqli-checker/run.lock')
MAX_REQUEST_BYTES = 16 * 1024
SERVICE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')


def read_request():
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('Missing or oversized request')
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) - {'action', 'targets'}:
        raise ValueError('Invalid request fields')
    action = value.get('action')
    if action not in ('check', 'round'):
        raise ValueError('Action must be check or round')
    requested = value.get('targets')
    if requested is not None and (not isinstance(requested, list) or not requested):
        raise ValueError('Targets must be a non-empty list when provided')
    if requested is not None and (any(not isinstance(item, str) for item in requested)
                                  or len(set(requested)) != len(requested)):
        raise ValueError('Targets must be unique service IDs')
    return action, requested


def load_config():
    config = json.loads(TARGETS_FILE.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Invalid checker configuration')
    targets = config.get('targets')
    if not isinstance(targets, dict) or not targets:
        raise ValueError('No checker targets are configured')
    keep = config.get('keep')
    if not isinstance(keep, int) or isinstance(keep, bool) or keep < 1:
        raise ValueError('Invalid retained flag count')
    for service_id, target in targets.items():
        if not isinstance(service_id, str) or not SERVICE_ID.fullmatch(service_id):
            raise ValueError('Invalid service ID in checker configuration')
        if not isinstance(target, str):
            raise ValueError('Invalid target in checker configuration')
        checker.base_url(target)
    return targets, keep


def run_request(action, requested):
    targets, keep = load_config()
    selected = list(targets) if requested is None else requested
    unknown = [service_id for service_id in selected if service_id not in targets]
    if unknown:
        raise ValueError('Request contains an unconfigured service ID')

    results = []
    for service_id in selected:
        target = targets[service_id]
        try:
            if action == 'check':
                checker.check(target)
                result = {'service': service_id, 'status': 'OK'}
            else:
                state_id = hashlib.sha256(service_id.encode('utf-8')).hexdigest()
                details = monitor.run_round(target, STATE_DIR / f'{state_id}.json', keep)
                result = {'service': service_id, **details}
        except checker.Verdict as error:
            result = {'service': service_id, 'status': 'FAIL',
                      'checker_code': error.status, 'message': error.message}
        except (ValueError, KeyError, TypeError, OSError):
            result = {'service': service_id, 'status': 'ERROR',
                      'message': 'Checker state or configuration could not be used'}
        results.append(result)

    status = 'OK' if all(item['status'] == 'OK' for item in results) else 'FAIL'
    return {'time': datetime.now(timezone.utc).isoformat(), 'action': action,
            'status': status, 'results': results}


def main():
    try:
        action, requested = read_request()
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, 'r+') as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(json.dumps({'status': 'BUSY', 'message': 'Another checker cycle is running'}))
                return 1
            result = run_request(action, requested)
        print(json.dumps(result, separators=(',', ':')))
        return 0 if result['status'] == 'OK' else 1
    except (ValueError, OSError, json.JSONDecodeError):
        print(json.dumps({'status': 'ERROR', 'message': 'Invalid checker request or configuration'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
