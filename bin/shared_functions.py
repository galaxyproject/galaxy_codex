#!/usr/bin/env python

import json
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

import pandas as pd


def format_list_column(col: pd.Series) -> pd.Series:
    """
    Format a column that could be a list before exporting
    """
    return col.apply(lambda x: ", ".join(str(i) for i in x))


def read_file(filepath: Optional[str]) -> List[str]:
    """
    Read an optional file with 1 element per line

    :param filepath: path to a file
    """
    if filepath is None:
        return []
    fp = Path(filepath)
    if fp.is_file():
        with fp.open("r") as f:
            return [x.rstrip() for x in f.readlines()]
    else:
        return []


def export_to_json(data: List[Dict], output_fp: str) -> None:
    """
    Export to a JSON file
    """
    with Path(output_fp).open("w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def load_json(input_df: str) -> Dict:
    """
    Read a JSON file
    """
    with Path(input_df).open("r") as t:
        content = json.load(t)
    return content


def read_suite_per_tool_id(tool_fp: str) -> Dict:
    """
    Read the tool suite table and extract a dictionary per tool id
    """
    tool_suites = load_json(tool_fp)
    tools = {}
    for suite in tool_suites:
        for tool in suite["Galaxy tool ids"]:
            tools[tool] = {
                "Galaxy wrapper id": suite["Galaxy wrapper id"],
                "Galaxy wrapper owner": suite["Galaxy wrapper id"],
                "EDAM operation": suite["EDAM operation"],
            }
    return tools
