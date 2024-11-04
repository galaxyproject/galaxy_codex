
import yaml
import json

def create_yml(data_source: str, yml_output_path: str):
    with open(data_source, mode="r", encoding="utf-8") as file:
        data = json.load(file)
    with open(yml_output_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

create_yml(data_source = "./communities/all/resources/tools.json", yml_output_path = "./docs/_data/data.yml")
