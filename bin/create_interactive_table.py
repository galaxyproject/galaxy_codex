#!/usr/bin/env python

import argparse

import pandas as pd

# TODO maybe allow communities to modify
COLUMNS = [
    "Expand",
    "Galaxy wrapper id",
    "Galaxy wrapper version",
    "Conda version",
    "Conda id",
    "Status",
    "bio.tool id",
    "bio.tool name",
    "EDAM operation",
    "EDAM topic",
    "Description",
    "bio.tool description",
    "biii",
    "Status",
    "Source",
    "ToolShed categories",
    "ToolShed id",
    "Galaxy wrapper owner",
    "Galaxy wrapper source",
]


def generate_table(
    tsv_path: str,
    template_path: str,
    output_path: str,
) -> None:
    df = pd.read_csv(tsv_path, sep="\t").assign(Expand=lambda df: "").fillna("")
    if "To keep" in df.columns:
        df["To keep"] = df["To keep"].replace("", True)
        df = df.query("`To keep`")
    df = df.loc[:, COLUMNS].reindex(columns=COLUMNS)
    table = df.to_html(border=0, table_id="dataframe", classes=["display", "nowrap"], index=False)

    with open(template_path) as template_file:
        template = template_file.read()

    final_html_output = template.replace("COMMUNITY_TABLE", table)

    with open(output_path, "w") as output:
        output.write(final_html_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create interactive table from \
            TSV file using a template, where COMMUNITY_TABLE is replaced \
            by the rendered table"
    )
    parser.add_argument(
        "--table",
        "-ta",
        required=True,
        help="Path to TSV file with tools",
    )
    parser.add_argument(
        "--template",
        "-te",
        required=True,
        help="Path to HTML template",
    )
    parser.add_argument(
        "--output",
        "-out",
        required=True,
        help="Path to HTML output",
    )

    args = parser.parse_args()
    generate_table(args.table, args.template, args.output)
