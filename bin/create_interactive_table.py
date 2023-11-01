import argparse

import pandas as pd


def generate_table(
    tsv_path: str,
    template_path: str,
    output_path: str,
) -> None:
    df = pd.read_csv(tsv_path, sep="\t")

    # need extra colum to allow expand
    df["Expand"] = ""

    df = df.fillna("")

    # TODO maybe allow comunities to modify
    columns = [
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
        "Status",
        "Source",
        "ToolShed categories",
        "ToolShed id",
        "Galaxy wrapper owner",
        "Galaxy wrapper source",
    ]

    df = df[df["To keep"]]

    df = df.loc[:, columns]
    df = df.reindex(columns=columns)

    df.to_html("temp_tools_table.html", border=0, table_id="dataframe", classes=["display", "nowrap"], index=False)

    with open(template_path) as template:
        template = template.read()

    with open("temp_tools_table.html") as table:
        table = table.read()

    final_html_output = template.replace("COMMUNITY_TABLE", table)

    with open(output_path, "w") as output:
        output.write(final_html_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create interactive table from \
            tsv using a template, where COMMUNITY_TABLE is replaced \
            by the rendered table"
    )
    parser.add_argument(
        "--table",
        "-ta",
        required=True,
        help="Path to table",
    )
    parser.add_argument(
        "--template",
        "-te",
        required=True,
        help="Path to html template",
    )
    parser.add_argument(
        "--output",
        "-out",
        required=True,
        help="Path to html output",
    )

    args = parser.parse_args()
    generate_table(args.table, args.template, args.output)
