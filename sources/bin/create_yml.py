
import yaml
import json
import re

def create_tool_yml(data_source: str, yml_output_path: str):

    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)

    ### https://stackoverflow.com/a/12595082
    ### https://stackoverflow.com/a/15340694
    for tool in range(len(data)):
        availability = {}
        for field in data[tool]:
            field_value = data[tool][field]
            availability_match_string = "[Aa]vailable on"
            if re.search(availability_match_string, field):
                instance_match_string = "[Uu]se[Gg]alaxy\.[a-z]{2}"
                if re.search(instance_match_string, field):
                    field_name = re.search(instance_match_string, field).group(0)
                if field_value != 0:
                    availability[field_name] = field_value
        data[tool]["availability"] = availability

    with open(yml_output_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

create_tool_yml(data_source = "./communities/all/resources/tools.json", yml_output_path = "./docs/_data/tools.yml")

def create_yml(data_source: str, yml_output_path: str):

    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)

    with open(yml_output_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

create_yml(data_source = "./communities/all/resources/workflows.json", yml_output_path = "./docs/_data/workflows.yml")