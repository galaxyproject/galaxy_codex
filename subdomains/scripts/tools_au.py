"""Convert YAML files for install on AU.

Assumes that wdir contains tool yaml files produced by the
parse_tools_to_produce_yml_files.py script, they should look like:
<tool_section_1>.yml
<tool_section_1>.yml.lock
<tool_section_2>.yml
<tool_section_2>.yml.lock
...

See subdomains/singlecell/tool_panel for example.
"""

from pathlib import Path

import yaml

WDIR = Path(__file__).parent
EXCLUDE_KEYS = [
    "install_repository_dependencies",
    "tool_panel_section_label",
]
OUTPUT_FILE = WDIR / "usegalaxy.org.au.yml"


def parse() -> None:
    """Parse tools list from YAML files."""
    data = {"tools": []}
    for f in WDIR.glob("*.yml.lock"):
        if not f.name.endswith(".yml.lock"):
            continue
        print(f"Extracting data from {f}...")
        with open(f) as handle:
            section_data = yaml.safe_load(handle)
        section_data["tools"] = [_transcribe_to_au(x) for x in section_data["tools"]]
        for key in EXCLUDE_KEYS:
            section_data.pop(key)
        data["tools"] += section_data["tools"]
    for key in ("install_resolver_dependencies", "install_tool_dependencies"):
        data[key] = section_data[key]
    write_data(data)
    print(f"Data transcribed and written to {OUTPUT_FILE}")


def _transcribe_to_au(tool: dict) -> dict:
    """Convert keys to AU installation format."""
    tool["tool_panel_section_label"] = "Single-Cell"
    tool.pop("tool_panel_section_id")
    return tool


def write_data(data: dict) -> None:
    """Write data to YAML output file."""
    with open(OUTPUT_FILE, "w") as handle:
        yaml.dump(data, handle, default_flow_style=False)


if __name__ == "__main__":
    parse()
