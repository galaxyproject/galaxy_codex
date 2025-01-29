# python ./sources/bin/populate_labs.py --tool_tsv communities/microgalaxy/resources/curated_tools.tsv --tool_yml communities/microgalaxy/lab/sections/4_tools.yml

import argparse
from pathlib import Path

import pandas as pd
import shared
from ruamel.yaml import YAML as yaml


def group_workflows(wf_fp: str) -> dict:
    """
    Split workflows in 4 levels of development
    """
    grouped_wfs = {}

    wf_df = pd.read_csv(wf_fp, sep="\t")
    grouped_wfs["peer_reviewed_wfs"] = wf_df.query(
        "Source == 'WorkflowHub' and Projects == 'Intergalactic Workflow Commission (IWC)'"
    )
    grouped_wfs["other_fair_wfs"] = wf_df.query(
        "Source == 'WorkflowHub' and Projects != 'Intergalactic Workflow Commission (IWC)'"
    )
    grouped_wfs["training_wfs"] = wf_df.query("Source == 'dev.WorkflowHub'")
    grouped_wfs["public_wfs"] = wf_df.query("Source != 'dev.WorkflowHub' and Source != 'WorkflowHub'")

    return grouped_wfs


def format_wfs(wf_df: pd.DataFrame) -> list:
    """
    Format workflows in a dataframe for YAML
    """
    formatted_wfs = []
    for _index, row in wf_df.iterrows():
        wf = {
            "title_md": row["Name"],
            "description_md": f"Workflow covering operations related to {row['EDAM operations']} on topics related to {row['EDAM topics']}",
            "button_link": row["Link"],
            "button_tip": "View workflow",
            "button_icon": "view",
        }
        description = ""
        prefix = "Workflow covering"
        if row["EDAM operations"] != "" or row["EDAM operations"] is not None:
            description += f"{ prefix } operations related to {row['EDAM operations']}"
            prefix = "on"
        if row["EDAM topics"] != "" or row["EDAM topics"] is not None:
            description += f"{ prefix } topics related to {row['EDAM topics']}"
        wf["description_md"] = description
        formatted_wfs.append(wf)
    return formatted_wfs


def fill_yaml_data_structure(yaml_data: dict, workflows: dict) -> dict:
    """
    Build structure for YAML
    """
    for element in yaml_data["tabs"]:
        if element["id"] in ["peer_reviewed_wfs", "other_fair_wfs", "training_wfs"]:
            content = [
                {
                    "title_md": "Import workflows from WorkflowHub",
                    "description_md": "WorkflowHub is a workflow management system which allows workflows to be FAIR (Findable, Accessible, Interoperable, and Reusable), citable, have managed metadata profiles, and be openly available for review and analytics.",
                    "button_tip": "Read Tips",
                    "button_icon": "tutorial",
                    "button_link": "https://training.galaxyproject.org/training-material/faqs/galaxy/workflows_import.html",
                },
            ]
            content.extend(format_wfs(workflows[element["id"]]))
            element["content"] = content
        elif element["id"] == "public_wfs":
            content = [
                {
                    "title_md": "Importing a workflow",
                    "description_md": "Import a workflow from URL or a workflow file",
                    "button_tip": "Read Tips",
                    "button_icon": "tutorial",
                    "button_link": "https://training.galaxyproject.org/training-material/faqs/galaxy/workflows_import.html",
                },
            ]
            content.extend(format_wfs(workflows["public_wfs"]))
            element["content"] = content

    return yaml_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Create workflows.yml for a community Lab from workflows.tsv.")

    # Adding positional arguments with short options
    parser.add_argument(
        "-c", "--tsv", type=str, required=True, help="Path to the TSV file (e.g., curated_workflows.tsv)"
    )
    parser.add_argument("-y", "--yml", type=str, required=True, help="Path to the lab YAML file (e.g., workflows.yml)")

    args = parser.parse_args()

    workflows = group_workflows(args.tsv)
    yaml_data = shared.load_yaml(args.yml)
    yaml_data = fill_yaml_data_structure(yaml_data, workflows)

    # Write the YAML data to the output file
    with Path(args.yml).open("w") as f:
        yaml().dump(yaml_data, f)

    print(f"Data successfully written to '{args.yml}'")


if __name__ == "__main__":
    main()
