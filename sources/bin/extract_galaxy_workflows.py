#!/usr/bin/env python

import argparse
from typing import (
    Any,
    Dict,
    List,
)

import pandas as pd
import shared


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

    def init_from_search(self, wf: dict, source: str, tools: dict) -> None:
        self.source = source
        if self.source == "WorkflowHub":
            self.id = wf["data"]["id"]
            self.link = f"https://workflowhub.eu{ wf['data']['links']['self'] }"
            self.name = wf["data"]["attributes"]["title"]
            self.tags = wf["data"]["attributes"]["tags"]
            self.create_time = shared.format_date(wf["data"]["attributes"]["created_at"])
            self.update_time = shared.format_date(wf["data"]["attributes"]["updated_at"])
            self.latest_version = wf["data"]["attributes"]["latest_version"]
            self.versions = len(wf["data"]["attributes"]["versions"])
            self.number_of_steps = len(wf["data"]["attributes"]["internals"]["steps"])
            self.license = wf["data"]["attributes"]["license"]
            self.doi = wf["data"]["attributes"]["doi"]
            self.edam_topic = [t["label"] for t in wf["data"]["attributes"]["topic_annotations"]]
        else:
            self.id = wf["id"]
            self.link = f"{ source }/published/workflow?id={ wf['id'] }"
            self.name = wf["name"]
            self.add_creators(wf)
            self.number_of_steps = wf["number_of_steps"] if "number_of_steps" in wf else len(wf["steps"].keys())
            self.tags = wf["tags"]
            self.create_time = shared.format_date(wf["create_time"])
            self.update_time = shared.format_date(wf["update_time"])
            self.latest_version = wf["version"]
            self.versions = wf["version"]
            self.license = wf["license"]

        self.add_creators(wf)
        self.add_tools(wf)
        self.edam_operation = shared.get_edam_operation_from_tools(self.tools, tools)

    def add_creators(self, wf: dict) -> None:
        """
        Get workflow creators
        """
        self.creators = []
        if self.source == "WorkflowHub":
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
        if self.source == "WorkflowHub":
            for tool in wf["data"]["attributes"]["internals"]["steps"]:
                if tool["description"] is not None:
                    tools.add(shared.shorten_tool_id(tool["description"]))
        else:
            for step in wf["steps"].values():
                if "tool_id" in step and step["tool_id"] is not None:
                    tools.add(shared.shorten_tool_id(step["tool_id"]))
        self.tools = list(tools)


class Workflows:
    """
    Class Workflows
    """

    def __init__(self, test: bool = False) -> None:
        self.workflows: List[Workflow] = []
        self.tools: Dict[Any, Any] = {}
        self.test = test

    def init_by_searching(self, tool_fp: str) -> None:
        self.tools = shared.read_suite_per_tool_id(tool_fp)
        self.add_workflows_from_workflowhub()
        self.add_workflows_from_public_servers()

    def init_by_importing(self, wfs: dict) -> None:
        for iwf in wfs:
            wf = Workflow()
            wf.init_by_importing(iwf)
            self.workflows.append(wf)

    def add_workflows_from_workflowhub(self) -> None:
        """
        Add workflows from WorkflowHub
        """
        header = {"Accept": "application/json"}
        wfhub_wfs = shared.get_request_json(
            "https://workflowhub.eu/workflows?filter[workflow_type]=galaxy",
            header,
        )
        print(f"Workflows from WorkflowHub: {len(wfhub_wfs['data'])}")
        data = wfhub_wfs["data"]
        if self.test:
            data = data[:10]
        for wf in data:
            wfhub_wf = shared.get_request_json(
                f"https://workflowhub.eu{wf['links']['self']}",
                header,
            )
            if wfhub_wf:
                wf = Workflow()
                wf.init_from_search(wf=wfhub_wf, source="WorkflowHub", tools=self.tools)
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

    def filter_workflows_by_tags(self, tags: list) -> None:
        """
        Filter workflows by tags
        """
        to_keep_wf = []
        for w in self.workflows:
            wf_tags = [w.lower() for w in w.tags]
            matches = set(wf_tags) & set(tags)
            if len(matches) != 0:
                to_keep_wf.append(w)
        self.workflows = to_keep_wf

    def export_workflows_to_tsv(self, output_fp: str) -> None:
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
        }

        df = pd.DataFrame(self.export_workflows_to_dict())

        for col in ["tools", "edam_operation", "edam_topic", "creators", "tags"]:
            df[col] = shared.format_list_column(df[col])

        df = df.rename(columns=renaming).fillna("").reindex(columns=list(renaming.values()))
        df.to_csv(output_fp, sep="\t", index=False)


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
        help="Filepath to TSV with filtered tutorials",
    )
    filterwf.add_argument(
        "--tags",
        "-c",
        help="Path to a file with tags to keep in the extraction (one per line)",
    )

    args = parser.parse_args()

    if args.command == "extract":
        wfs = Workflows(test=args.test)
        wfs.init_by_searching(args.tools)
        shared.export_to_json(wfs.export_workflows_to_dict(), args.all)

    elif args.command == "filter":
        wfs = Workflows()
        wfs.init_by_importing(wfs=shared.load_json(args.all))
        tags = shared.read_file(args.tags)
        wfs.filter_workflows_by_tags(tags)
        wfs.export_workflows_to_tsv(args.filtered)
