#!/usr/bin/env python

import argparse
from pathlib import Path

import pandas as pd


def load_table(tsv_path: str) -> pd.DataFrame:
    """
    Load TSV as dataframe

    :param tsv_path: Path to TSV file with table
    """
    df = pd.read_csv(tsv_path, sep="\t").fillna("")
    df.insert(0, "Expand", "")  # the column where the expand button is shown
    return df


def filter_table(df: pd.DataFrame, filter_col: list, remove_col: list) -> pd.DataFrame:
    """
    Filter table by values and columns

    :param df: dataframe to filter
    :param filter_col: list of columns used to filter
    :param remove_col: list of columns to remove from table
    """
    for col in filter_col:
        if col in df.columns:
            df[col] = df[col].replace("", True)
            df = df.query(f"`{col}`")

    if set(remove_col).issubset(df.columns):
        df = df.drop(remove_col, axis=1)
    else:
        removable_col = []
        for col in remove_col:
            if col not in df.columns:
                print(f"{col} NOT in table")
                print(df)
            else:
                removable_col.append(col)
        df = df.drop(removable_col, axis=1)

    return df


def generate_html_table(df: pd.DataFrame, template_fp: str) -> str:
    """
    Genereate the HTML table using a template

    :param df: DataFrame
    :param template_fp: Path to template file
    """
    html_table = df.to_html(border=0, table_id="dataframe", classes=["display", "nowrap"], index=False)

    with Path(template_fp).open("r") as template_f:
        template = template_f.read()

    final_html_output = template.replace("COMMUNITY_TABLE", html_table)

    return final_html_output


def export_html_table(html_table: str, output_fp: str) -> None:
    """
    Export HTML table to a file

    :param html_table: string representing the table in HTML
    :param output_fp: path to output file
    """
    with Path(output_fp).open("w") as output_f:
        output_f.write(html_table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create interactive table in HTML from TSV file using a HTML template")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to a TSV file with the table to make interactive",
    )
    parser.add_argument(
        "--remove-col",
        "-r",
        action="append",
        default=[],
        help="Name of columns to remove",
    )
    parser.add_argument(
        "--filter-col",
        "-f",
        action="append",
        default=[],
        help="Name of columns used to filter the rows (must contain boolean values). Only rows with True in this column will be used.",
    )
    parser.add_argument(
        "--template",
        "-t",
        required=True,
        help="Path to HTML template",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to HTML output",
    )

    args = parser.parse_args()
    table_df = load_table(args.input)
    table_df = filter_table(table_df, args.filter_col, args.remove_col)
    html_table = generate_html_table(table_df, args.template)
    export_html_table(html_table, args.output)
