#!/usr/bin/env python3
"""Fill section tabs (tools/workflows/tutorials) of lab section files.

Reads a master item list (e.g. sections/_tools.yml) and a classification
table (e.g. mappings/tools.tsv) and rewrites the ``content`` of the given
tab in each numbered section file (e.g. sections/2_LCMS.yml) as a
``subsections`` mapping, grouping the accordion items per subsection.

Each mapping row assigns one item (matched by ``title_md`` in the master
file) to one (section, subsection) pair. An item may appear in several
sections but in exactly one subsection per section. Subsections are
rendered in order of first appearance in the mapping file.

Mapping files are TAB-separated with header ``name<TAB>section<TAB>
subsection``; names may contain spaces (e.g. tutorial titles).

Master files may list the same title several times with different links
(e.g. one workflow published on several servers); the first occurrence
is used.

Section files are rewritten with ruamel.yaml so all other content,
comments and formatting styles are preserved.

Usage (from the lab directory):

    python scripts/fill_tab_subsections.py --tab tools      [--dry-run]
    python scripts/fill_tab_subsections.py --tab workflows  [--dry-run]
    python scripts/fill_tab_subsections.py --tab tutorials  [--dry-run]
"""

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString

LAB_DIR = Path(__file__).resolve().parent.parent
SECTIONS_DIR = LAB_DIR / "sections"
MAPPING_DIR = LAB_DIR / "mappings"

# Files that provide raw tool/workflow/tutorial data rather than page layout.
DATA_PREFIX = "_"

# Tab id -> (master file in sections/, mapping file in mappings/, tab title)
TABS = {
    "tools": ("_tools.yml", "tools.tsv", "Tools"),
    "workflows": ("_workflows.yml", "workflows.tsv", "Workflows"),
    "tutorials": ("_tutorials.yml", "tutorials.tsv", "Tutorials"),
}


def normalize_name(name):
    """Collapse all whitespace runs to single spaces for name matching.

    Titles in the master files differ only by trailing spaces or
    line-folding (e.g. duplicated across published servers), so both
    master titles and mapping names are compared normalized.
    """
    return re.sub(r"\s+", " ", str(name)).strip()


def load_items(master_file):
    """Return {normalized_title_md: item_dict} from a master file.

    The same title may occur several times with different links (e.g. a
    workflow published on several servers); the first occurrence wins.
    """
    with open(master_file) as fh:
        data = yaml.safe_load(fh)
    items = OrderedDict()
    for tab in data.get("tabs", []):
        for item in tab.get("content") or []:
            title = item.get("title_md")
            if title is None:
                raise ValueError(
                    f"{master_file.name}: tab {tab.get('id')!r} has an item "
                    "without title_md")
            key = normalize_name(title)
            if key in items:
                # Same title on several servers/sources: keep first.
                continue
            items[key] = item
    return items


def load_mapping(items, mapping_file, master_file):
    """Return {section_id: OrderedDict(subsection_id: [item, ...])}.

    Warns about mapping rows whose item is not in the master file and
    errors on an item assigned to several subsections of one section.
    """
    mapping = {}
    items_per_section = {}
    with open(mapping_file) as fh:
        lines = fh.read().splitlines()
    if not lines:
        raise ValueError(f"{mapping_file.name}: file is empty")
    header = lines[0].split("\t")
    required = ["name", "section", "subsection"]
    if header[:3] != required:
        raise ValueError(
            f"{mapping_file.name}: header must be "
            f"{chr(9).join(required)!r}, got {header!r}")
    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(
                f"{mapping_file.name} line {lineno}: expected 3 "
                f"TAB-separated columns, got {len(fields)}: {line!r}")
        name, section, subsection = (f.strip() for f in fields)
        name = normalize_name(name)
        if name not in items:
            print(f"warning: line {lineno}: item {name!r} is not in "
                  f"{master_file.name}; row skipped", file=sys.stderr)
            continue
        assigned = items_per_section.setdefault(section, {})
        previous = assigned.get(name)
        if previous and previous != subsection:
            raise ValueError(
                f"{mapping_file.name} line {lineno}: item {name!r} "
                f"assigned to subsections {previous!r} and "
                f"{subsection!r} in section {section!r}; an item may "
                "have only one subsection per section")
        assigned[name] = subsection
        subsections = mapping.setdefault(section, OrderedDict())
        content = subsections.setdefault(subsection, [])
        if items[name] not in content:
            content.append(items[name])
    return mapping


def build_subsections_seq(subsections):
    """Build a ruamel CommentedMap for a tab's `content` value."""
    seq = CommentedSeq()
    for sub_id, sub_items in subsections.items():
        subsection = CommentedMap()
        subsection["id"] = sub_id
        subsection["title"] = sub_id.replace("_", " ").capitalize()
        content_seq = CommentedSeq()
        for item in sub_items:
            item_map = CommentedMap()
            for key, value in item.items():
                if key == "description_md" and "\n" in str(value):
                    # Keep real line breaks as a literal block scalar
                    # instead of ruamel's quoted one-line dump.
                    value = LiteralScalarString(value)
                item_map[key] = value
            content_seq.append(item_map)
        subsection["content"] = content_seq
        seq.append(subsection)
    wrapper = CommentedMap()
    wrapper["subsections"] = seq
    return wrapper


def update_section(path, subsections, tab_id, tab_title, dry_run):
    """Rewrite one tab's content of one section file. Return status."""
    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 1000  # keep long single-line descriptions unwrapped
    with open(path) as fh:
        data = ryaml.load(fh)

    tabs = data.get("tabs")
    if tabs is None:
        tabs = CommentedSeq()
        data["tabs"] = tabs
    tab = next((t for t in tabs if t.get("id") == tab_id), None)
    created = tab is None
    if created:
        tab = CommentedMap()
        tab["id"] = tab_id
        tab["title"] = tab_title
        tab["heading_md"] = ""
        # Insert after the overview tab if there is one, else append.
        insert_at = len(tabs)
        for i, existing in enumerate(tabs):
            if existing.get("id") == "overview":
                insert_at = i + 1
                break
        tabs.insert(insert_at, tab)

    new_content = build_subsections_seq(subsections)
    if created:
        note = f"created {tab_id} tab"
    elif "subsections" in (tab.get("content") or {}):
        old_ids = [s.get("id") for s in tab["content"]["subsections"]]
        note = f"overwrote existing subsections {old_ids}"
    else:
        note = "replaced flat item list"

    if dry_run:
        counts = {k: len(v) for k, v in subsections.items()}
        return f"would {note}: {counts}"

    tab["content"] = new_content
    with open(path, "w") as fh:
        ryaml.dump(data, fh)
    return note


def collect_section_files(sections_dir):
    """Map section id -> file path for all non-master section files."""
    section_files = {}
    for path in sorted(sections_dir.glob("*.yml")):
        if path.name.startswith(DATA_PREFIX):
            continue
        with open(path) as fh:
            section_id = (yaml.safe_load(fh) or {}).get("id")
        if not section_id:
            raise ValueError(f"{path.name}: no `id` key")
        if section_id in section_files:
            raise ValueError(
                f"duplicate section id {section_id!r} in "
                f"{section_files[section_id].name} and {path.name}")
        section_files[section_id] = path
    return section_files


def fill_tab(tab_id, sections_dir=SECTIONS_DIR, mapping_dir=MAPPING_DIR,
             dry_run=False):
    """Classify items of one kind and fill the tab of every mapped section."""
    master_name, mapping_name, tab_title = TABS[tab_id]
    master_file = sections_dir / master_name
    mapping_file = mapping_dir / mapping_name
    if not master_file.exists():
        raise SystemExit(f"error: master file not found: {master_file}")
    if not mapping_file.exists():
        print(f"{mapping_file.name}: no mapping file, skipping")
        return

    items = load_items(master_file)
    mapping = load_mapping(items, mapping_file, master_file)
    section_files = collect_section_files(sections_dir)

    unknown_sections = sorted(set(mapping) - set(section_files))
    if unknown_sections:
        raise SystemExit(
            "error: mapping references unknown section ids: "
            + ", ".join(unknown_sections))

    for section_id, subsections in mapping.items():
        status = update_section(
            section_files[section_id], subsections, tab_id, tab_title,
            dry_run)
        print(f"{section_files[section_id].name}: {status}")

    skipped = sorted(set(section_files) - set(mapping))
    for section_id in skipped:
        print(f"{section_files[section_id].name}: no mapping rows, untouched")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tab", required=True, choices=sorted(TABS),
                        help="which tab kind to fill")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    parser.add_argument("--sections-dir", type=Path, default=SECTIONS_DIR)
    parser.add_argument("--mapping-dir", type=Path, default=MAPPING_DIR)
    args = parser.parse_args()
    fill_tab(
        args.tab,
        sections_dir=args.sections_dir,
        mapping_dir=args.mapping_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
