#!/usr/bin/env python
"""Merge TSV files by column name (columns missing in a file are left empty)."""

import argparse

import pandas as pd

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="TSV files to merge")
    parser.add_argument("--output", "-o", required=True, help="Merged TSV")
    args = parser.parse_args()
    tables = [pd.read_csv(fp, sep="\t", dtype=str, keep_default_na=False) for fp in sorted(args.inputs)]
    pd.concat(tables, ignore_index=True).fillna("").to_csv(args.output, sep="\t", index=False)
