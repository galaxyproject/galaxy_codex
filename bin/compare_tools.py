#!/usr/bin/env python

import argparse
from pathlib import Path
from typing import (
    List,
    Set,
)

import pandas as pd

import shared_functions


def get_tutorials_tool_suites(tuto_fp: str, tool_fp: str) -> Set:
    """
    Get tool suite ids for all tools in tutorials
    """
    tutorials = pd.read_csv(tuto_fp, sep="\t", keep_default_na=False).to_dict("records")
    all_tools = shared_functions.read_suite_per_tool_id(tool_fp)
    print(all_tools)
    tuto_tool_suites = set()
    for tuto in tutorials:
        tools = tuto["Tools"].split(", ")
        for t in tools:
            if t in all_tools:
                tuto_tool_suites.add(all_tools[t]["Galaxy wrapper id"])
            else:
                print(f"{t} not found in all tools")
    return tuto_tool_suites


def write_tool_list(tools: Set, fp: str) -> None:
    """
    Write tool list with 1 element per row in a file
    """
    tools = list(tools)
    tools.sort()
    with Path(fp).open("w") as f:
        f.write("\n".join(tools))


def update_excl_keep_tool_lists(tuto_tool_suites: Set, excl_tool_fp: str, keep_tool_fp: str) -> List:
    """
    Update the lists in to keep and exclude with tool suites in tutorials
    """
    # exclude from the list of tools to exclude the tools that are in tutorials
    excl_tools = set(shared_functions.read_file(excl_tool_fp)) - tuto_tool_suites
    write_tool_list(excl_tools, excl_tool_fp)
    # add from the list of tools to keep the tools that are in tutorials
    keep_tools = set(shared_functions.read_file(keep_tool_fp)) | tuto_tool_suites
    write_tool_list(keep_tools, keep_tool_fp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update community-curated list of tools to keep and exclude with tools in community-curated tutorials"
    )
    parser.add_argument(
        "--filtered_tutorials",
        "-t",
        required=True,
        help="Filepath to TSV with filtered tutorials",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        help="Path to a file with ids of tools to exclude (one per line)",
    )
    parser.add_argument(
        "--keep",
        "-k",
        help="Path to a file with ids of tools to keep (one per line)",
    )
    parser.add_argument(
        "--all_tools",
        "-a",
        required=True,
        help="Filepath to TSV with all extracted tools, generated by extractools command",
    )
    args = parser.parse_args()

    tuto_tools = get_tutorials_tool_suites(args.filtered_tutorials, args.all_tools)
    update_excl_keep_tool_lists(tuto_tools, args.exclude, args.keep)
    
    