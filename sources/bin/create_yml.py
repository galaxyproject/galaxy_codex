import json
import re
import os

import yaml


def create_tool_yml(data_source: str, yml_output_path: str) -> None:

    with open(data_source, encoding="utf-8") as file:
        data = json.load(file)

    ### https://stackoverflow.com/a/12595082
    ### https://stackoverflow.com/a/15340694
    for tool in range(len(data)):
        availability = {}
        for field in data[tool]:
            field_value = data[tool][field]
            availability_match_string = "[Nn]umber of tools"
            if re.search(availability_match_string, field):
                instance_match_string = "[Uu]se[Gg]alaxy\.[a-z]{2}"
                if re.search(instance_match_string, field):
                    # field_name = re.search(instance_match_string, field).group(0)
                    match = re.search(instance_match_string, field)
                    if match:
                        field_name = match.group(0)
                        if field_value != 0:
                            availability[field_name] = field_value
        data[tool]["availability"] = availability

    with open(yml_output_path, "w") as file:
        yaml.dump(data, file, default_flow_style=False)


create_tool_yml(
    data_source="./communities/all/resources/tools.json",
    yml_output_path="./communities/all/resources/tools.yml"
)
os.symlink("./../../communities/all/resources/tools.yml", "./website/_data/tools.yml")


def create_yml(data_source: str, yml_output_path: str) -> None:

    with open(data_source, encoding="utf-8") as file:
        data = json.load(file)

    with open(yml_output_path, "w") as file:
        yaml.dump(data, file, default_flow_style=False)


create_yml(
    data_source="./communities/all/resources/workflows.json",
    yml_output_path="./communities/all/resources/workflows.yml"
)
os.symlink("./../../communities/all/resources/workflows.yml", "./website/_data/workflows.yml")
create_yml(
    data_source="./communities/all/resources/tutorials.json",
    yml_output_path="./communities/all/resources/tutorials.yml"
)
os.symlink("./../../communities/all/resources/tutorials.yml", "./website/_data/tutorials.yml")