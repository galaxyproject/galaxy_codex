#!/usr/bin/env python

import argparse
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import pandas as pd
import shared
from ruamel.yaml import YAML as yaml


def matches_filter(text: str, words: List[str], logic: str) -> bool:
    """
    Determines if the given text matches the filter logic:
    - 'include': Includes the text if it matches any word in the filter.
    - 'exclude': Excludes the text if it matches any word in the filter.

    Args:
        text (str): The text to check.
        words (List[str]): A list of words to search for.
        logic (str): The filter logic, either 'include' or 'exclude'.

    Returns:
        bool: True if the text matches the filter logic, False otherwise.
    """
    # Convert text and words to lowercase for case-insensitive comparison
    text = text.lower()
    words = [word.lower() for word in words]

    if logic == "include":
        # Include if the text contains any word from the filter
        return any(word in text for word in words)

    elif logic == "exclude":
        # Exclude if the text contains any word from the filter
        return not any(word in text for word in words)

    # Default to False if the logic is not recognized
    return False


def main() -> None:
    """
    Main function to create a YAML file from a TSV file based on specified filters and logic.
    """
    # Initialize argument parser
    parser = argparse.ArgumentParser(
        description="Fill in tutorial section in a lab community *.yml from tutorials.tsv."
    )
    # Define required arguments
    parser.add_argument("-c", "--tsv", type=str, required=True, help="Path to the TSV file (e.g., curated_tools.tsv)")
    parser.add_argument("-y", "--yml", type=str, required=True, help="Path to the output YAML file (e.g., tools.yml)")
    # Columns and filter details
    parser.add_argument("-tc", "--title-column", type=str, required=True, help="Column to use as title.")
    parser.add_argument("-dc", "--description-column", type=str, required=True, help="Column to use as description.")
    parser.add_argument(
        "-blc", "--button-link-column", type=str, required=True, help="Column to use as link for the button."
    )
    parser.add_argument("-fc", "--filter-column", type=str, required=True, help="Column to use as filter.")
    parser.add_argument("-fi", "--filter", type=str, required=True, help="Comma-separated list of words for filtering.")
    parser.add_argument(
        "-fl",
        "--filter-logic",
        type=str,
        required=True,
        choices=["include", "exclude"],
        help="Specify the filter logic: 'include' to include matches, 'exclude' to exclude matches.",
    )
    args = parser.parse_args()

    # Check if the TSV file exists
    if not Path(args.tsv).exists():
        print(f"Error: The file '{args.tsv}' does not exist.")
        return

    # Split the filter string into a list of words
    filter_words = args.filter.split(",")

    data_df: pd.DataFrame = pd.read_csv(args.tsv, sep="\t")
    tutorial_content = []
    # Iterate through each row in the DataFrame
    for _index, row in data_df.iterrows():
        # Apply the filter logic
        if matches_filter(str(row[args.filter_column]), filter_words, args.filter_logic):
            # Only add rows that satisfy the filter logic
            entry: Dict[str, Any] = {
                "title_md": row[args.title_column],
                "description_md": f"Tutorial stored in {row['Topic']} topic on the Galaxy Training Network and covering topics related to {row['EDAM topic']}",
                "button_link": row[args.button_link_column],
                "button_tip": "View tutorial",
                "button_icon": "tutorial",
            }
            tutorial_content.append(entry)

    # Initialize the YAML data structure to remplace with new content
    yaml_data = shared.load_yaml(args.yml)
    found = False
    for element in yaml_data["tabs"]:
        if element["id"] == "tutorials":
            found = True
            element["content"] = tutorial_content
    if not found:
        yaml_data["tabs"].append(
            {
                "id": "tutorials",
                "title": "Tutorials",
                "heading_md": "Tutorials to train you to perform microbial data analysis",
                "content": tutorial_content,
            }
        )

    # Write the constructed YAML data to the output file
    with Path(args.yml).open("w") as f:
        yaml().dump(yaml_data, f)

    print(f"Data successfully written to '{args.yml}'")


if __name__ == "__main__":
    main()
