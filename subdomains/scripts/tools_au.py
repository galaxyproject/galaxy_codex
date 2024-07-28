"""Convert YAML files for install on AU.

Assumes that wdir contains tool yaml files.
"""

import yaml
from pathlib import Path

WDIR = Path(__file__).parent
EXCLUDE_KEYS = [
    'install_repository_dependencies',
    'tool_panel_section_label',
]
OUTPUT_FILE = WDIR / 'usegalaxy.org.au.yml'


def parse():
    data = {'tools': []}
    for f in WDIR.glob('*.yml.lock'):
        if not f.name.endswith('.yml.lock'):
            continue
        print(f"Extracting data from {f}...")
        with open(f, 'r') as handle:
            section_data = yaml.safe_load(handle)
        section_data['tools'] = [
            _transcribe_to_au(x) for x in section_data['tools']
        ]
        for key in EXCLUDE_KEYS:
            section_data.pop(key)
        data['tools'] += section_data['tools']
    for key in ('install_resolver_dependencies', 'install_tool_dependencies'):
        data[key] = section_data[key]
    write_data(data)
    print(f'Data transcribed and written to {OUTPUT_FILE}')


def _transcribe_to_au(tool):
    tool['tool_panel_section_label'] = 'Single-Cell'
    tool.pop('tool_panel_section_id')
    return tool


def write_data(data):
    with open(OUTPUT_FILE, 'w') as handle:
        yaml.dump(data, handle, default_flow_style=False)


if __name__ == '__main__':
    parse()
