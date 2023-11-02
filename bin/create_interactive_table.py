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

    #we assume this column is here
    df = df[df["To keep"]]

    table_str = df.to_html(border=0, 
                           table_id="dataframe", 
                           classes=["display", "nowrap"], 
                           index=False)

    with open(template_path) as template_file:
        template = template_file.read()

    final_html_output = template.replace("COMMUNITY_TABLE", table_str)

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
