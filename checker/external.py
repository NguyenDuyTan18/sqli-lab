"""CyberRange-side SSH client; private keys and known-hosts remain operator managed."""
import argparse
import json
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True, help='CyberRange SSH private key path')
    parser.add_argument('--known-hosts', required=True, help='Trusted SSH host keys')
    parser.add_argument('--port', type=int, default=22)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', args.host) or not 1 <= args.port <= 65535:
        parser.error('invalid host or port')
    cmd = ['ssh', '-i', args.key, '-p', str(args.port), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + args.known_hosts, 'user-access@' + args.host, '/usr/bin/python3 /opt/idor-free-lab/sqli-checker.py']
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=False)
        try:
            result = json.loads(proc.stdout)
            if not isinstance(result, dict):
                raise ValueError()
        except ValueError:
            result = {'service': 'unknown', 'authentication': 'unknown', 'sqli': 'unknown', 'error': 'ssh_or_checker_failure'}
        print(json.dumps(result))
        return 0 if proc.returncode == 0 else 1
    except (OSError, subprocess.TimeoutExpired):
        print(json.dumps({'service': 'unknown', 'authentication': 'unknown', 'sqli': 'unknown', 'error': 'ssh_unavailable'}))
        return 1

if __name__ == '__main__':
    sys.exit(main())
