"""Optional static checks: requires PyYAML and Jinja2 on validation workstation."""
import ipaddress
import json
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
topology = yaml.safe_load((ROOT / 'topology.yml').read_text())
names = [item['name'] for key in ('hosts', 'routers', 'networks') for item in topology[key]]
assert len(set(names)) == len(names), 'Duplicate topology names'
networks = {item['name']: ipaddress.ip_network(item['cidr']) for item in topology['networks']}
subnets = list(networks.values()) + [ipaddress.ip_network('100.100.100.0/24')]
assert all(not a.overlaps(b) for index, a in enumerate(subnets) for b in subnets[index + 1:])
for mapping in topology['net_mappings'] + topology['router_mappings']:
    assert ipaddress.ip_address(mapping['ip']) in networks[mapping['network']]
assert {host['name'] for host in topology['hosts']} == {'sqli-web', 'checker'}

for path in ROOT.rglob('*.yml'):
    yaml.safe_load(path.read_text(encoding='utf-8'))
yaml.safe_load((ROOT / 'integrations/forcad-config.yml.example').read_text())

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / 'provisioning/templates'),
                               undefined=jinja2.StrictUndefined, trim_blocks=True)
environment.filters['bool'] = bool
environment.filters['to_nice_json'] = lambda value: json.dumps(value, indent=2)
variables = {'sqli_checker_targets': {'sqli-web': '10.20.10.10:8080'},
             'sqli_checker_keep': 5, 'sqli_search_fixed': False}
for fixed in (False, True):
    rendered = environment.get_template('sqli-web.service.j2').render(
        **{**variables, 'sqli_target': '10.20.10.10:8080', 'sqli_search_fixed': fixed})
    lines = rendered.splitlines()
    exec_line = next(line for line in lines if line.startswith('ExecStart='))
    assert 'Restart=' not in exec_line, 'Jinja whitespace merged systemd directives'
    assert 'Restart=on-failure' in lines
    assert (' --fixed' in exec_line) == fixed

target_config = environment.get_template('checker-targets.json.j2').render(**variables)
assert yaml.safe_load(target_config) == {'targets': variables['sqli_checker_targets'], 'keep': 5}
print('Topology invariants, YAML parsing, service template and checker target config: OK')
