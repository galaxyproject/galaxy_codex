#!/usr/bin/env python

import json
from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

import pandas as pd
import requests


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


def get_request_json(url: str, headers: dict) -> dict:
    """
    Return JSON output using request

    :param url: galaxy tool id
    """
    r = requests.get(url, auth=None, headers=headers)
    r.raise_for_status()
    return r.json()


def format_date(date: str) -> str:
    return datetime.fromisoformat(date).strftime("%Y-%m-%d")


def shorten_tool_id(tool: str) -> str:
    """
    Shorten tool id
    """
    if "toolshed" in tool:
        return tool.split("/")[-2]
    else:
        return tool


def get_edam_operation_from_tools(selected_tools: list, all_tools: dict) -> List:
    """
    Get list of EDAM operations of the tools

    :param selected_tools: list of tool suite ids
    :param all_tools: dictionary with information about all tools
    """
    edam_operation = set()
    for t in selected_tools:
        if t in all_tools:
            edam_operation.update(set(all_tools[t]["EDAM operation"]))
        else:
            print(f"{t} not found in all tools")
    return list(edam_operation)
