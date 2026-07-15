#!/usr/bin/env python3
"""
Collect release statistics for Galaxy Codex.

Compares current resource counts against a previous git ref (tag or commit)
and outputs a markdown summary suitable for release notes.

Usage:
    python3 collect_release_stats.py [--ref <git-ref>] [--output <file>]

If --ref is not given, the most recent tag is used.
If --output is not given, stdout is used.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


COMMUNITIES_DIR = Path("communities")
RESOURCE_FILES = {
    "tools": "tools.json",
    "workflows": "workflows.json",
    "tutorials": "tutorials.json",
}
COMMUNITY_TOOL_FILE = "tools_filtered_by_ts_categories.json"
COMMUNITY_WF_FILES = ["curated_workflows.json", "tag_filtered_workflows.json"]


def run_git(*args):
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def count_json_items(filepath):
    """Return the number of items in a JSON array file, or 0 if missing."""
    try:
        with open(filepath) as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def count_file_lines(filepath):
    """Count lines in a file via git show (for a given ref)."""
    try:
        output = run_git("show", f"{get_ref()}:{filepath}")
        return len(output.strip().splitlines()) if output.strip() else 0
    except subprocess.CalledProcessError:
        return 0


def get_ref():
    """Get the most recent tag if no explicit ref is given."""
    try:
        return run_git("tag", "-l", "--sort=-version:refname").splitlines()[0]
    except (IndexError, subprocess.CalledProcessError):
        return None


def count_items_at_ref(ref, filepath):
    """Count items in a JSON file at a specific git ref."""
    try:
        content = run_git("show", f"{ref}:{filepath}")
        data = json.loads(content)
        return len(data) if isinstance(data, list) else 0
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return 0


def collect_global_stats(ref=None):
    """Collect global resource counts and deltas."""
    stats = {}
    for resource, filename in RESOURCE_FILES.items():
        filepath = f"communities/all/resources/{filename}"
        current = count_json_items(filepath)
        previous = count_items_at_ref(ref, filepath) if ref else 0
        stats[resource] = {
            "current": current,
            "previous": previous,
            "delta": current - previous,
        }
    return stats


def collect_community_stats(ref=None):
    """Collect per-community resource counts."""
    stats = {}
    for community_dir in sorted(COMMUNITIES_DIR.iterdir()):
        if not community_dir.is_dir():
            continue
        name = community_dir.name
        if name == "all" or name == "index.html":
            continue
        resources_dir = community_dir / "resources"
        if not resources_dir.is_dir():
            continue

        # Tools: use tools_filtered_by_ts_categories.json
        tools_file = resources_dir / COMMUNITY_TOOL_FILE
        tools_current = count_json_items(tools_file)
        tools_previous = count_items_at_ref(ref, str(tools_file)) if ref else 0

        # Workflows: combine curated + tag_filtered
        wf_current = 0
        wf_previous = 0
        for wf_file in COMMUNITY_WF_FILES:
            wf_path = resources_dir / wf_file
            wf_current += count_json_items(wf_path)
            if ref:
                wf_previous += count_items_at_ref(ref, str(wf_path))

        # Tutorials: check for tutorials.json or tutorials.tsv
        tut_file = resources_dir / "tutorials.json"
        tut_current = count_json_items(tut_file)
        tut_previous = count_items_at_ref(ref, str(tut_file)) if ref else 0

        if tools_current or wf_current or tut_current:
            stats[name] = {
                "tools": {"current": tools_current, "delta": tools_current - tools_previous},
                "workflows": {"current": wf_current, "delta": wf_current - wf_previous},
                "tutorials": {"current": tut_current, "delta": tut_current - tut_previous},
            }
    return stats


def format_delta(delta):
    if delta > 0:
        return f"+{delta}"
    elif delta < 0:
        return str(delta)
    return "0"


def render_markdown(global_stats, community_stats, ref=None):
    lines = []
    lines.append("## Galaxy Codex Monthly Release\n")

    # Global summary
    lines.append("### Global Resource Counts\n")
    lines.append("| Resource | Total | Change |")
    lines.append("|----------|------:|-------:|")
    for resource in ["tools", "workflows", "tutorials"]:
        s = global_stats[resource]
        delta_str = format_delta(s["delta"])
        label = resource.capitalize()
        lines.append(f"| {label} | {s['current']:,} | {delta_str} |")
    lines.append("")

    # Per-community breakdown
    lines.append("### Per-Community Breakdown\n")
    lines.append("| Community | Tools | Workflows | Tutorials |")
    lines.append("|-----------|------:|----------:|----------:|")
    for name, counts in sorted(community_stats.items()):
        t = format_delta(counts["tools"]["delta"])
        w = format_delta(counts["workflows"]["delta"])
        u = format_delta(counts["tutorials"]["delta"])
        lines.append(
            f"| {name} | {counts['tools']['current']:,} ({t}) "
            f"| {counts['workflows']['current']:,} ({w}) "
            f"| {counts['tutorials']['current']:,} ({u}) |"
        )
    lines.append("")

    if ref:
        lines.append(f"*Compared against ref: `{ref}`*\n")

    lines.append("---")
    lines.append("*Browse the full catalog: https://galaxyproject.github.io/galaxy_codex/*\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Collect Galaxy Codex release stats")
    parser.add_argument("--ref", help="Git ref to compare against (default: most recent tag)")
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    ref = args.ref or get_ref()
    if ref:
        print(f"Comparing against ref: {ref}", file=sys.stderr)
    else:
        print("No previous ref found, showing current counts only.", file=sys.stderr)

    global_stats = collect_global_stats(ref)
    community_stats = collect_community_stats(ref)

    md = render_markdown(global_stats, community_stats, ref)

    if args.output:
        with open(args.output, "w") as f:
            f.write(md)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
