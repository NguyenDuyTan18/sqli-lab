#!/usr/bin/env python3
"""Standalone checker loop; independent from ForcAD scoring and flag submission."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import string
import sys
import time

import checker


def run_round(target, state, keep=5):
    if keep < 1:
        raise ValueError('keep must be positive')
    state = Path(state)
    normalized = checker.base_url(target)
    previous = json.loads(state.read_text()) if state.exists() else {'target': normalized, 'flags': []}
    if previous.get('target') != normalized or not isinstance(previous.get('flags'), list):
        raise ValueError('State belongs to another target or has an invalid format; choose a different state file')
    checker.check(target)
    for item in previous['flags']:
        checker.get(target, item['private'], item['flag'])
    flag = 'S' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(30)) + '='
    _public, private = checker.put(target, flag)
    checker.get(target, private, flag)
    flags = (previous['flags'] + [{'flag': flag, 'private': private}])[-keep:]
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = state.with_suffix(state.suffix + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        json.dump({'target': normalized, 'flags': flags}, handle)
    temporary.replace(state)
    return {'status': 'OK', 'checked_previous': len(previous['flags']), 'retained_flags': len(flags)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, help='Service host or HOST:PORT')
    parser.add_argument('--state', type=Path, default=Path('runtime/checker-state.json'))
    parser.add_argument('--interval', type=int, default=60)
    parser.add_argument('--keep', type=int, default=5)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.interval < 1 or args.keep < 1:
        parser.error('interval and keep must be positive')
    try:
        while True:
            try:
                result = run_round(args.target, args.state, args.keep)
                code = 0
            except checker.Verdict as error:
                result, code = {'status': 'FAIL', 'checker_code': error.status, 'message': error.message}, 1
            except (ValueError, KeyError, TypeError, OSError):
                result, code = {'status': 'ERROR', 'message': 'Cannot use checker state; check file permissions/format/target'}, 1
            print(json.dumps({'time': datetime.now(timezone.utc).isoformat(), **result}), flush=True)
            if args.once:
                return code
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    sys.exit(main())
