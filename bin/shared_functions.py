#!/usr/bin/env python

import json
from pathlib import Path
from typing import (
    Any,
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


def load_json(input_df: str):
    """
    Read a JSON file
    """
    with Path(input_df).open("r") as t:
        content = json.load(t) 
    return content