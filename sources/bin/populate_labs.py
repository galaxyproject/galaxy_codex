import argparse
import os
from typing import List

import oyaml as yaml
import pandas as pd

# import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Create community tools.yml from tool.tsv.")

    # Adding positional arguments with short options
    parser.add_argument(
        "-c", "--tool_tsv", type=str, required=True, help="Path to the TSV file (e.g., curated_tools.tsv)"
    )
    parser.add_argument(
        "-y", "--tool_yml", type=str, required=True, help="Path to the output YAML file (e.g., tools.yml)"
    )

    args = parser.parse_args()

    # Check if the tool TSV file exists
    if not os.path.exists(args.tool_tsv):
        print(f"Error: The file '{args.tool_tsv}' does not exist.")
        return

    try:
        # Read the TSV file with pandas (use tab delimiter)
        data = pd.read_csv(args.tool_tsv, sep="\t")

        # Construct the YAML data structure
        yaml_data = {
            "id": "tools",
            "title": "Community Tools",
            "tabs": [
                {"id": "tool_list", "title": "List of community curated tools available for microGalaxy", "content": []}
            ],
        }

        # Populate the content section with each row from the TSV
        for _, row in data.iterrows():
            # Use the first column (assumed to be the tool title) as the title_md
            title_md = row[data.columns[0]]  # Get the first column's value as title_md

            # Start the unordered list <ul> and construct each <li> for every other column in the row
            description = "<ul>"
            for column in data.columns[1:]:  # Skip the first column (since it's title_md)
                description += f"  <li>{column}: {row[column]}</li>\n"
            description += "</ul>"

            # Create the tool entry with the formatted HTML list
            tool_entry = {
                "title_md": title_md,
                "description_md": description,  # Directly insert the HTML string without escape sequences
            }
            yaml_data["tabs"][0]["content"].append(tool_entry)

        # Write the YAML data to the output file
        with open(args.tool_yml, "w") as yaml_file:
            yaml.dump(yaml_data, yaml_file, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"Data successfully written to '{args.tool_yml}'")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
