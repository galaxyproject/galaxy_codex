#!/usr/bin/env python

import argparse
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
import shared
from ruamel.yaml import YAML as ruamelyaml


class Workflow:
    """
    Class for workflow
    """

    def __init__(self) -> None:
        self.source = ""
        self.id = 0
        self.link = ""
        self.name = ""
        self.creators: List[str] = []
        self.tags: List[str] = []
        self.create_time = ""
        self.update_time = ""
        self.latest_version = 0
        self.versions = 0
        self.number_of_steps = 0
        self.tools: List[str] = []
        self.edam_operation: List[str] = []
        self.edam_topic: List[str] = []
        self.license = ""
        self.doi = ""
        self.projects: List[str] = []
        self.keep = True
        self.deprecated = False

    def init_by_importing(self, wf: dict) -> None:
        self.source = wf["source"]
        self.id = wf["id"]
        self.link = wf["link"]
        self.name = wf["name"]
        self.creators = wf["creators"]
        self.tags = wf["tags"]
        self.create_time = wf["create_time"]
        self.update_time = wf["update_time"]
        self.latest_version = wf["latest_version"]
        self.versions = wf["versions"]
        self.number_of_steps = wf["number_of_steps"]
        self.tools = wf["tools"]
        self.edam_operation = wf["edam_operation"]
        self.edam_topic = wf["edam_topic"]
        self.license = wf["license"]
        self.doi = wf["doi"]
        self.projects = wf["projects"]
        if "keep" in wf:
            self.keep = wf["keep"]
        if "deprecated" in wf:
            self.deprecated = wf["deprecated"]

    def init_from_search(self, wf: dict, source: str, tools: dict) -> None:
        self.source = source
        if "WorkflowHub" in self.source:
            self.id = wf["data"]["id"]
            self.link = f"https://{ source.lower() }.eu{ wf['data']['links']['self'] }"
            self.name = wf["data"]["attributes"]["title"]
            self.tags = [w.lower() for w in wf["data"]["attributes"]["tags"]]
            self.create_time = shared.format_date(wf["data"]["attributes"]["created_at"])
            self.update_time = shared.format_date(wf["data"]["attributes"]["updated_at"])
            self.latest_version = wf["data"]["attributes"]["latest_version"]
            self.versions = len(wf["data"]["attributes"]["versions"])
            internals = wf["data"]["attributes"].get("internals", {})
            steps = internals.get("steps")
            if steps is not None:
                self.number_of_steps = len(steps)
            else:
                self.number_of_steps = 0
            self.license = wf["data"]["attributes"]["license"]
            self.doi = wf["data"]["attributes"]["doi"]
            self.edam_topic = [t["label"] for t in wf["data"]["attributes"]["topic_annotations"]]
        else:
            self.id = wf["id"]
            self.link = f"{ source }/published/workflow?id={ wf['id'] }"
            self.name = wf["name"]
            self.add_creators(wf)
            self.number_of_steps = wf["number_of_steps"] if "number_of_steps" in wf else len(wf["steps"].keys())
            self.tags = [w.lower() for w in wf["tags"]]
            self.create_time = shared.format_date(wf["create_time"])
            self.update_time = shared.format_date(wf["update_time"])
            self.latest_version = wf["version"]
            self.versions = wf["version"]
            self.license = wf["license"]

        self.add_creators(wf)
        self.add_tools(wf)
        self.edam_operation = shared.get_edam_operation_from_tools(self.tools, tools)
        self.add_projects(wf)

    def add_creators(self, wf: dict) -> None:
        """
        Get workflow creators
        """
        self.creators = []
        if "WorkflowHub" in self.source:
            creators = wf["data"]["attributes"]["creators"]
            if len(creators) == 0:
                other = wf["data"]["attributes"]["other_creators"]
                if other and len(other) > 0:
                    self.creators.extend(wf["data"]["attributes"]["other_creators"].split(","))
            else:
                self.creators.extend([f"{c['given_name']} {c['family_name']}" for c in creators])
        else:
            if "creator" in wf and wf["creator"] is not None:
                self.creators.extend([c["name"] for c in wf["creator"]])

    def add_tools(self, wf: dict) -> None:
        """
        Extract list of tool ids from workflow
        """
        tools = set()
        if "WorkflowHub" in self.source:
            internals = wf["data"]["attributes"].get("internals", {})
            steps = internals.get("steps")
            if steps is not None:
                for tool in steps:
                    if tool.get("description") is not None:
                        tools.add(shared.shorten_tool_id(tool["description"]))
        else:
            for step in wf["steps"].values():
                if "tool_id" in step and step["tool_id"] is not None:
                    tools.add(shared.shorten_tool_id(step["tool_id"]))
        self.tools = list(tools)

    def add_projects(self, wf: dict) -> None:
        """
        Extract projects associated to workflow on WorkflowHub
        """
        if "WorkflowHub" in self.source:
            for project in wf["data"]["relationships"]["projects"]["data"]:
                wfhub_project = shared.get_request_json(
                    f"https://{ self.source.lower() }.eu/projects/{project['id']}",
                    {"Accept": "application/json"},
                )
                if "attributes" in wfhub_project["data"] and "title" in wfhub_project["data"]["attributes"]:
                    self.projects.append(wfhub_project["data"]["attributes"]["title"])

    def get_source_tags(self, tags: dict) -> list:
        """
        Get tags based on source
        """
        if "WorkflowHub" in self.source:
            source = "workflowhub"
        else:
            source = "public"
        return tags[source]

    def test_tags(self, tags: dict) -> bool:
        """
        Test if there are overlap between workflow tags and target tags
        """
        matches = set(self.tags) & set(self.get_source_tags(tags))
        return len(matches) != 0

    def test_name(self, tags: dict) -> bool:
        """
        Test if there are overlap between workflow tags and target tags
        """
        for tag in self.get_source_tags(tags):
            if tag in self.name:
                return True
        return False

    def update_status(self, wf: dict) -> None:
        """
        Update status from status table
        """
        self.keep = wf["To keep"]
        self.deprecated = wf["Deprecated"]

    def get_import_link(self) -> str:
        """
        Get import link
        """
        if "WorkflowHub" in self.source:
            return (
                "{{ galaxy_base_url }}"
                + f"/workflows/trs_import?trs_server={ self.source.lower() }.eu&run_form=true&trs_id={ self.id }"
            )
        else:
            # to replace with "{{ galaxy_base_url }}" + f"/workflows/import/{ self.link }/download?format=json-download"
            return self.link

    def get_description(self) -> str:
        """
        Get description with EDAM operations and EDAM topics
        """
        description = ""
        prefix = "Workflow covering"
        if len(self.edam_operation) > 0:
            description += f"{ prefix } operations related to { ','.join(self.edam_operation) }"
            prefix = "on"
        if len(self.edam_topic) > 0:
            description += f"{ prefix } topics related to { ','.join(self.edam_topic) }"
        return description


class Workflows:
    """
    Class Workflows
    """

    def __init__(self, test: bool = False) -> None:
        self.workflows: List[Workflow] = []
        self.tools: Dict[Any, Any] = {}
        self.test = test
        self.grouped_workflows: Dict[Any, Any] = {}

    def init_by_searching(self, tool_fp: str) -> None:
        self.tools = shared.read_suite_per_tool_id(tool_fp)
        self.add_workflows_from_workflowhub()
        self.add_workflows_from_workflowhub("dev.")
        self.add_workflows_from_public_servers()

    def init_by_importing(self, wfs: dict) -> None:
        """
        Loads the workflows from a dict following the structure in communities/all/resources/test_workflows.json
        (the json created by init_by_searching)
        """
        for iwf in wfs:
            wf = Workflow()
            wf.init_by_importing(iwf)
            self.workflows.append(wf)

    def add_workflows_from_workflowhub(self, prefix: str = "") -> None:
        """
        Add workflows from WorkflowHub
        """
        header = {"Accept": "application/json"}
        wfhub_wfs = shared.get_request_json(
            f"https://{ prefix }workflowhub.eu/workflows?filter[workflow_type]=galaxy",
            header,
        )
        print(f"Workflows from WorkflowHub: {len(wfhub_wfs['data'])}")
        data = wfhub_wfs["data"]
        print(data)
        if self.test:
            data = data[:10]
        for wf in data:
            wfhub_wf = shared.get_request_json(
                f"https://{ prefix }workflowhub.eu{wf['links']['self']}",
                header,
            )
            if wfhub_wf:
                wf = Workflow()
                wf.init_from_search(wf=wfhub_wf, source=f"{ prefix }WorkflowHub", tools=self.tools)
                self.workflows.append(wf)
        print(len(self.workflows))

    def add_workflows_from_a_server(self, server: str) -> None:
        """
        Extract public workflows from a server
        """
        header = {"Accept": "application/json"}
        server_wfs = shared.get_request_json(
            f"{server}/api/workflows/",
            header,
        )

        # test max 50 wfs
        if self.test:
            if len(server_wfs) > 50:
                server_wfs = server_wfs[:50]

        count = 0
        for wf in server_wfs:
            if wf["published"] and wf["importable"] and not wf["deleted"] and not wf["hidden"]:
                count += 1
                server_wf = shared.get_request_json(
                    f"{server}/api/workflows/{wf['id']}",
                    header,
                )
                wf = Workflow()
                wf.init_from_search(wf=server_wf, source=server, tools=self.tools)
                self.workflows.append(wf)
        print(f"Workflows from {server}: {count}")

    def add_workflows_from_public_servers(self) -> None:
        """
        Extract workflows from UseGalaxy servers
        """
        server_urls = [
            "https://usegalaxy.fr",
            "https://usegalaxy.cz",
            "https://usegalaxy.eu",
            "https://usegalaxy.org",
            "https://usegalaxy.org.au",
        ]
        if self.test:
            server_urls = server_urls[2:3]
        for url in server_urls:
            print(url)
            self.add_workflows_from_a_server(url)

    def export_workflows_to_dict(self) -> List:
        """
        Export workflows as dictionary
        """
        return [w.__dict__ for w in self.workflows]

    def filter_workflows_by_tags(self, tags: dict, status: Dict) -> None:
        """
        Filter workflows by tags
        """
        to_keep_wf = []
        for w in self.workflows:
            if w.link in status:
                w.update_status(status[w.link])
            if w.test_tags(tags) or w.test_name(tags):
                to_keep_wf.append(w)
        self.workflows = to_keep_wf

    def curate_workflows(self, status: Dict) -> None:
        """
        Curate workflows based on community feedback
        """
        curated_wfs = []
        for w in self.workflows:
            if w.link in status and status[w.link]["To keep"]:
                w.update_status(status[w.link])
                curated_wfs.append(w)
        self.workflows = curated_wfs

    def export_workflows_to_tsv(self, output_fp: str, to_keep_columns: Optional[List[str]] = None) -> None:
        """
        Export workflows to a TSV file
        """
        renaming = {
            "name": "Name",
            "source": "Source",
            "id": "ID",
            "link": "Link",
            "creators": "Creators",
            "tags": "Tags",
            "create_time": "Creation time",
            "update_time": "Update time",
            "latest_version": "Latest version",
            "versions": "Versions",
            "number_of_steps": "Number of steps",
            "tools": "Tools",
            "edam_operation": "EDAM operations",
            "edam_topic": "EDAM topics",
            "license": "License",
            "doi": "DOI",
            "projects": "Projects",
            "keep": "To keep",
            "deprecated": "Deprecated",
        }

        df = pd.DataFrame(self.export_workflows_to_dict())

        for col in ["tools", "edam_operation", "edam_topic", "creators", "tags", "projects"]:
            df[col] = shared.format_list_column(df[col])

        df = (
            df.sort_values(by=["source", "projects"])
            .rename(columns=renaming)
            .fillna("")
            .reindex(columns=list(renaming.values()))
        )

        if to_keep_columns is not None:
            df = df[to_keep_columns]

        df_iwc = df.query("Projects == 'Intergalactic Workflow Commission (IWC)'")
        df_no_iwc = df.query("Projects != 'Intergalactic Workflow Commission (IWC)'")
        pd.concat([df_iwc, df_no_iwc]).to_csv(output_fp, sep="\t", index=False)

    def group_workflows(self) -> None:
        """
        Split workflows in 4 levels of development
        """
        self.grouped_workflows = {
            "iwc": [],
            "other_workflowhub": [],
            "gtn": [],
            "public": [],
        }

        for wf in self.workflows:
            if wf.source == "WorkflowHub":
                if "Intergalactic Workflow Commission (IWC)" in wf.projects:
                    self.grouped_workflows["iwc"].append(wf)
                else:
                    self.grouped_workflows["other_workflowhub"].append(wf)
            elif wf.source == "dev.WorkflowHub":
                self.grouped_workflows["gtn"].append(wf)
            else:
                self.grouped_workflows["public"].append(wf)

    def format_wfs(self, el_id: str) -> list:
        """
        Format workflows for YAML
        """
        formatted_wfs = []
        for wf in self.grouped_workflows[el_id]:
            formatted_wfs.append(
                {
                    "title_md": wf.name,
                    "description_md": wf.get_description(),
                    "button_link": wf.get_import_link(),
                    "button_tip": "View workflow",
                    "button_icon": "view",
                }
            )
        return formatted_wfs

    def fill_lab_section(self, lab_fp: str) -> None:
        """
        Fill lab section with grouped workflows
        """
        lab_section = shared.load_yaml(lab_fp)

        for element in lab_section["tabs"]:
            if element["id"] in ["iwc", "other_workflowhub", "gtn"]:
                content = [
                    {
                        "title_md": "Import workflows from WorkflowHub",
                        "description_md": "WorkflowHub is a workflow management system which allows workflows to be FAIR (Findable, Accessible, Interoperable, and Reusable), citable, have managed metadata profiles, and be openly available for review and analytics.",
                        "button_tip": "Read Tips",
                        "button_icon": "tutorial",
                        "button_link": "https://training.galaxyproject.org/training-material/faqs/galaxy/workflows_import.html",
                    },
                ]
                content.extend(self.format_wfs(element["id"]))
                element["content"] = content
            elif element["id"] == "public":
                content = [
                    {
                        "title_md": "Importing a workflow",
                        "description_md": "Import a workflow from URL or a workflow file",
                        "button_tip": "Read Tips",
                        "button_icon": "tutorial",
                        "button_link": "https://training.galaxyproject.org/training-material/faqs/galaxy/workflows_import.html",
                    },
                ]
                content.extend(self.format_wfs("public"))
                element["content"] = content

        with open(lab_fp, "w") as lab_f:
            ruamelyaml().dump(lab_section, lab_f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Galaxy Workflows from WorkflowHub and public servers")
    subparser = parser.add_subparsers(dest="command")

    # Extract Workflows
    extract = subparser.add_parser("extract", help="Extract all workflows")
    extract.add_argument("--all", "-o", required=True, help="Filepath to JSON with all extracted workflows")
    extract.add_argument(
        "--tools",
        "-t",
        required=True,
        help="Filepath to JSON with all extracted tools, generated by extractools command",
    )
    extract.add_argument(
        "--test",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test case only on one topic",
    )

    # Filter workflows
    filterwf = subparser.add_parser("filter", help="Filter workflows based on their tags")
    filterwf.add_argument(
        "--all",
        "-a",
        required=True,
        help="Filepath to JSON with all extracted workflows, generated by extract command",
    )
    filterwf.add_argument(
        "--filtered",
        "-f",
        required=True,
        help="Filepath to JSON with filtered workflows",
    )
    filterwf.add_argument(
        "--tsv-filtered",
        "-t",
        required=True,
        help="Filepath to TSV with filtered workflows",
    )
    filterwf.add_argument(
        "--tags",
        "-c",
        help="Path to a YAML file with tags (different for public or WorkflowHub wfs) to keep in the extraction",
    )
    filterwf.add_argument(
        "--status",
        "-s",
        help="Path to a TSV file with workflow status",
    )

    # Curate workflow
    curatewf = subparser.add_parser("curate", help="Curate workflows based on community review")
    curatewf.add_argument(
        "--filtered",
        "-f",
        required=True,
        help="Filepath to JSON with workflows filtered based on tags",
    )
    curatewf.add_argument(
        "--curated",
        "-c",
        required=True,
        help="Filepath to JSON with curated workflows",
    )
    curatewf.add_argument(
        "--tsv-curated",
        "-t",
        required=True,
        help="Filepath to TSV with curated workflows",
    )
    curatewf.add_argument(
        "--status",
        "-s",
        help="Path to a TSV file with workflow status",
    )

    # Curate tools categories
    labpop = subparser.add_parser("popLabSection", help="Fill in Lab section workflows")
    labpop.add_argument(
        "--curated",
        "-c",
        required=True,
        help="Filepath to JSON with curated workflows",
    )
    labpop.add_argument(
        "--lab",
        required=True,
        help="Filepath to YAML files for Lab section",
    )

    args = parser.parse_args()

    if args.command == "extract":
        wfs = Workflows(test=args.test)
        wfs.init_by_searching(args.tools)
        shared.export_to_json(wfs.export_workflows_to_dict(), args.all)

    elif args.command == "filter":
        wfs = Workflows()
        wfs.init_by_importing(wfs=shared.load_json(args.all))
        tags = shared.load_yaml(args.tags)
        # get status if file provided
        if args.status:
            try:
                status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
            except Exception:
                status = {}
        else:
            status = {}
        wfs.filter_workflows_by_tags(tags, status)
        shared.export_to_json(wfs.export_workflows_to_dict(), args.filtered)
        wfs.export_workflows_to_tsv(args.tsv_filtered)
        wfs.export_workflows_to_tsv(
            args.status,
            to_keep_columns=[
                "Link",
                "Name",
                "Source",
                "Projects",
                "Creators",
                "Creation time",
                "Update time",
                "To keep",
                "Deprecated",
            ],
        )

    elif args.command == "curate":
        wfs = Workflows()
        wfs.init_by_importing(wfs=shared.load_json(args.filtered))
        try:
            status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
        except Exception as ex:
            print(f"Failed to load {args.status} file with:\n{ex}")
            print("Not assigning tool status for this community !")
            status = {}
        wfs.curate_workflows(status)
        shared.export_to_json(wfs.export_workflows_to_dict(), args.curated)
        wfs.export_workflows_to_tsv(args.tsv_curated)

    elif args.command == "popLabSection":
        wfs = Workflows()
        wfs.init_by_importing(wfs=shared.load_json(args.curated))
        wfs.group_workflows()
        wfs.fill_lab_section(args.lab)
