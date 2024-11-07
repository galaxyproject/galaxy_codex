#!/usr/bin/env python
import argparse
import json
import sys
import time
import traceback
import xml.etree.ElementTree as et
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
import requests
import shared
import yaml
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from owlready2 import get_ontology

# Config variables
BIOTOOLS_API_URL = "https://bio.tools"

USEGALAXY_SERVER_URLS = {
    "UseGalaxy.org (Main)": "https://usegalaxy.org",
    "UseGalaxy.org.au": "https://usegalaxy.org.au",
    "UseGalaxy.eu": "https://usegalaxy.eu",
    "UseGalaxy.fr": "https://usegalaxy.fr",
}

DATA_PATH = Path(__file__).resolve().parent.parent.joinpath("data") # galaxy_tool_extractor folder
STAT_DATE = "2024.08.31"

# load the configs globally
conf_path = DATA_PATH.joinpath("conf.yml")
with open(conf_path) as f:
    configs = yaml.safe_load(f)


class Tool:
    """
    Class for tool
    """

    def __init__(self) -> None:
        self.parsed_folder = None
        self.toolshed = {
            "id": None,
            "categories": [],
            "description": "",
            "homepage": None,
            "owner": None,
            "source": None
        }
        self.tool_ids: List[str] = []
        self.first_commit = None
        self.version = None
        self.conda_package = {
            "name": None,
            "latest_version": None,
            "version_status": "To update"
        }
        self.edam = {
            "operations": {
                "full": [],
                "reduced": [],
            },
            "topics": {
                "full": [],
                "reduced": [],
            }   
        }
        self.biotools = {
            "id": None,
            "name": None,
            "description": None,
        }
        self.biii = {"ID": None}
        self.availability = {}
        self.stats = {
            "users": {
                "last_5_years": {
                    "main_servers": 0,
                },
                "all_time": {
                    "main_servers": 0,
                }
            },
            "runs": {
                "last_5_years": {
                    "main_servers": 0,
                },
                "all_time": {
                    "main_servers": 0,
                }
            },
        }
        self.community_status = {
            "to_keep": True,
            "deprecated": False,
        }

    def init_by_importing(self, tool: dict) -> None:
        self.parsed_folder = tool["parsed_folder"]
        self.toolshed = tool["toolshed"]
        self.tool_ids = tool["tool_ids"]
        self.first_commit = tool["first_commit"]
        self.version = tool["version"]
        self.conda_package = tool["conda_package"]
        self.edam = tool["edam"]
        self.biotool = tool["biotool"]
        self.biii = tool["biii"]
        self.tool_available = tool["tool_available"]
        self.stats = tool["stats"]
        self.community_status = tool["community_status"]

    def init_from_github(self, tool: ContentFile, repo: Repository) -> None:
        """
        Init tool from the .shed.yaml, requirements in the macros or xml
        file

        :param tool: GitHub ContentFile object
        :param repo: GitHub Repository object
        """
        if tool.type != "dir":
            return None
        try:
            shed = repo.get_contents(f"{tool.path}/.shed.yml")
        except Exception:
            return None
        else:
            self.get_toolshed_metadata(shed)
        
        self.parsed_folder = tool.html_url
        self.first_commit = shared.get_first_commit_for_folder(tool, repo)

        # get all files in the folder
        file_list = repo.get_contents(tool.path)
        assert isinstance(file_list, list)

        # find and parse macro file
        for file in file_list:
            if "macro" in file.name and file.name.endswith("xml"):
                self.extract_from_macro(file)
            if file.name.endswith("xml") and "macro" not in file.name:
                self.extract_from_xml(file)

    def init_toolshed_metadata(self, shed: ContentFile) -> None:
        """
        Init toolshed metadata from a shed.yml file

        :param shed: GitHub ContentFile object
        """
        file_content = shared.get_string_content(shed)
        yaml_content = yaml.load(file_content, Loader=yaml.FullLoader)
        self.toolshed["description"] = shared.get_shed_attribute("description", yaml_content, None)
        if self.toolshed["Description"] is None:
            self.toolshed["Description"] = shared.get_shed_attribute("long_description", yaml_content, None)
        if self.toolshed["Description"] is not None:
            self.toolshed["Description"] = metadata["Description"].replace("\n", "")
        self.toolshed["id"] = shared.get_shed_attribute("name", yaml_content, None)
        self.toolshed["owner"] = shared.get_shed_attribute("owner", yaml_content, None)
        self.toolshed["source"] = shared.get_shed_attribute("remote_repository_url", yaml_content, None)
        if "homepage_url" in yaml_content:
            self.toolshed["homepage"] = yaml_content["homepage_url"]
        self.toolshed["categories"] = shared.get_shed_attribute("categories", yaml_content, [])
        if self.toolshed["categories"] is None:
            self.toolshed["categories"] = []

    def get_xref(el: et.Element, attrib_type: str) -> Optional[str]:
        """
        Get xref information

        :param el: Element object
        :attrib_type: the type of the xref (e.g.: bio.tools or biii)
        """
        xrefs = el.find("xrefs")
        if xrefs is not None:
            xref_items = xrefs.findall("xref")  # check all xref items
            for xref in xref_items:
                if xref is not None and xref.attrib["type"] == attrib_type:
                    # should not contain any space of linebreak
                    xref_sanitized = str(xref.text).strip()
                    return xref_sanitized
        return None

    def extract_from_macro(self, file: ContentFile) -> None:
        """
        Extract information from the macro file

        :param file: GitHub ContentFile object
        """
        file_content = shared.get_string_content(file)
        root = et.fromstring(file_content)
        for child in root:
            if "name" in child.attrib:
                if child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@":
                    self.version = child.text
                elif child.attrib["name"] == "requirements":
                    self.add_conda_package(child)
                self.biotools["id"] = self.get_xref(child, attrib_type="bio.tools")
                self.biii["id"] = self.get_xref(child, attrib_type="biii")

    def add_conda_package(el: et.Element) -> Optional[str]:
        """
        Get conda package information

        :param el: Element object
        """
        reqs = el.find("requirements")
        name = None
        if reqs is not None:
            req = reqs.find("requirement")
            if req is not None:
                name = req.text
        self.conda_package["name"] = name

    def extract_from_xml(self, file: ContentFile) -> None:
        """
        Extract information from XML file

        :param file: GitHub ContentFile object
        """
        try:
            file_content = shared.get_string_content(file)
            root = et.fromstring(file_content)
        except Exception:
            print(traceback.format_exc())
        else:
            # version
            if self.version is None:
                if "version" in root.attrib:
                    version = root.attrib["version"]
                    if "VERSION@" not in version:
                        self.version = version
                    else:
                        macros = root.find("macros")
                        if macros is not None:
                            for child in macros:
                                if "name" in child.attrib and (
                                    child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@"
                                ):
                                    self.version = child.text

            # bio.tools
            if self.biotools["id"] is None:
                self.biotools["id"] = self.get_xref(root, attrib_type="bio.tools")
            # biii
            if self.biii["id"] is None:
                self.biii["id"] = self.get_xref(root, attrib_type="biii")

            # conda package
            if self.conda_package["name"] is None:
                self.add_conda_package(root)
            # tool ids
            if "id" in root.attrib:
                self.tool_ids.append(root.attrib["id"])
            
    def expand_conda_metadata(self) -> None:
        """
        Get recent conda version using conda API and compare to the wrapper version
        """
        if self.conda_package["name"] is not None:
            r = requests.get(f'https://api.anaconda.org/package/bioconda/{self.conda_package["name"]}')
            if r.status_code == requests.codes.ok:
                conda_info = r.json()
                if "latest_version" in conda_info:
                    self.conda_package["latest_version"] = conda_info["latest_version"]
                    if self.conda_package["latest_version"] == self.version:
                        self.conda_package["version_status"] = "Up-to-date"
        
    def add_biotools_metadata(self, edam: Any) -> None:
        """
        Get bio.tool information and EDAM annotations using bio.tools API,
        reduce EDAM 

        :param edam: Ontology
        """
        if self.biotools["id"] is not None:
            r = requests.get(f'{BIOTOOLS_API_URL}/api/tool/{self.biotools["id"]}/?format=json')
            if r.status_code == requests.codes.ok:
                biotool_info = r.json()
                if "name" in biotool_info:
                    self.biotools["name"] = biotool_info["name"]
                if "description" in biotool_info:
                    self.biotools["description"] = biotool_info["description"].replace("\n", "")
                if "function" in biotool_info:
                    for func in biotool_info["function"]:
                        if "operation" in func:
                            for op in func["operation"]:
                                self.edam["operations"]["full"].append(op["term"])
                if "topic" in biotool_info:
                    for t in biotool_info["topic"]:
                        self.edam["topics"]["full"].append(t["term"])
            
            if len(self.edam["operations"]["full"]) > 0:
                self.edam["operations"]["reduced"] = shared.reduce_ontology_terms(self.edam["operations"]["full"], ontology=edam_ontology)
            if len(self.edam["topics"]["full"]) > 0:
                self.edam["topics"]["reduced"] = shared.reduce_ontology_terms(self.edam["topics"]["full"], ontology=edam_ontology)

    def add_tool_number_on_a_server(self, name: str, url: str) -> int:
        """
        Add number of tools in tool_ids installed on a Galaxy server

        :param name: Galaxy server name
        :param url: Galaxy server url
        """
        assert all("/" not in tool_id for tool_id in tool_ids), "This function only works on short tool ids"

        installed_tool_ids = get_all_installed_tool_ids_on_server(galaxy_server_url)
        installed_tool_short_ids = [tool_id.split("/")[4] if "/" in tool_id else tool_id for tool_id in installed_tool_ids]

        counter = 0
        for tool_id in tool_ids:
            if tool_id in installed_tool_short_ids:
                counter += 1

        self.availability[name] = counter

    def add_availability(self, public_servers_df: DataFrame) -> None:
        """
        Add available for UseGalaxy servers and other public servers

        :param public_servers_df: DataFrame with public servers
        """
        # add availability for UseGalaxy servers
        for name, url in USEGALAXY_SERVER_URLS.items():
            self.check_tools_on_servers(url)

        # add all other available servers
        for _index, row in public_servers_df.iterrows():
            name = row["name"]
            if name.lower() not in [
                n.lower() for n in USEGALAXY_SERVER_URLS.keys()
            ]:  # do not query UseGalaxy servers again

                url = row["url"]
                self.check_tools_on_servers(url)

    def add_server_stat(self, stat_df, stat: str, time: str, server: str) -> None:
        """
        Computes a count for tool stats based on the tool id. The counts for local and toolshed installed tools are
        aggregated. All tool versions are also aggregated.

        :param stat_df: df with tools stats in the form `toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter,3394539`
        :param stat: stat type (users or runs)
        :param time: stat time (last_5_years or all_time)
        :param server: server name
        """
        # extract tool id
        stat_df["tool ID"] = stat_df["tool_name"].apply(shared.get_last_url_position)
        # print(tool_stats_df["Suite ID"].to_list())
        agg_count = 0
        for tool_id in self.tool_ids:
            if tool_id in stat_df["tool ID"].to_list():
                # get stats of the tool for all versions
                counts = stat_df.loc[(stat_df["tool ID"] == tool_id), "count"]
                agg_versions = counts.sum()
                # aggregate all counts for all tools in the suite
                agg_count += agg_versions
        self.stat[stat][time][server] = int(agg_count)

    def add_stats(self, tool_stats: Dict) -> None:
        """
        Add tool stats

        :param tool_stats: nested dictionary with stat dataframes
        """
        for stat, stat_dict in tool_stats:
            for t, time_stat in stat_dict:
                summed_stat = 0
                for server, stat_df in time_stat:
                    self.add_server_stat(stat_df, stat, t, server)
                    summed_stat += self.stat[stat][time][server]
                self.stat[stat][t]["main servers"] = summed_stat

    def check_categories(self, ts_cat: List[str]) -> bool:
        """
        Check if tool fit in ToolShed categories to keep

        :param ts_cat: list of ToolShed categories to keep in the extraction
        """
        if not ts_cat:
            return True
        if not self.toolshed["categories"]:
            return False
        return bool(set(ts_cat) & set(self.toolshed["categories"]))

class Tools:
    """
    Class Tools
    """
    def __init__(self, test: bool = False) -> None:
        self.tools: List[Tool] = []
        self.test = test
        self.github = None
        self.github_repositories = []

    def init_by_importing(self, tools: dict) -> None:
        for t in tools:
            tool = Tool()
            tool.init_by_importing(t)
            self.workflows.append(tool)

    def init_by_searching(
        self, 
        github_api: str,
        repository_list: Optional[str],
        avoid_extra_repositories: bool = True,
    ) -> None:
        """
        Parse tools in GitHub repositories to extract metadata,
        filter by TS categories, additional information
        """
        self.github = Github(github_api)
        self.get_tool_github_repositories(
            repository_list=repository_list,
            add_extra_repositories=not avoid_extra_repositories,
        )
        self.parse_github_repositories()
        
        edam_ontology = get_ontology("https://edamontology.org/EDAM_1.25.owl").load()

        public_servers = DATA_PATH.joinpath("available_public_servers.csv")
        public_servers_df = pd.read_csv(public_servers, sep="\t")

        tool_stats = {}
        servers_with_stats = ["eu", "org", "org.au"]
        usage_stats_path = DATA_PATH.joinpath("usage_stats", f"usage_stats_{STAT_DATE}")
        for server in servers_with_stats:
            fp = usage_stats_path.joinpath(
                f"{ server }/tool_users_5y_until_{STAT_DATE}.csv"
            )
            tool_stats["users"]["last_5_years"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(
                f"{ server }/tool_users_until_{STAT_DATE}.csv"
            )
            tool_stats["users"]["all_time"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(
                f"{ server }/tool_usage_5y_until_{STAT_DATE}.csv"
            )
            tool_stats["runs"]["last_5_years"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(
                f"{ server }/tool_usage_until_{STAT_DATE}.csv"
            )
            tool_stats["runs"]["all_time"][server] = pd.read_csv(fp)

        # add additional information to tools
        for tool in self.tools:
            tool.expand_conda_metadata()
            tool.add_biotools_metadata(edam_ontology)
            tool.add_availability(public_servers_df)
            tool.add_stats(tool_stats)

    def get_tool_github_repositories(
        self,
        repository_list: Optional[str],
        add_extra_repositories: bool = True,
    ) -> None:
        """
        Get list of tool GitHub repositories to parse

        :param github_api: GitHub API key
        :param repository_list: The selection to use from the repository (needed to split the process for CI jobs)
        :param run_test: for testing only parse the repository
        :test_repository: the link to the test repository to use for the test
        """
        if self.test:
            self.github_repositories = ["https://github.com/paulzierep/Galaxy-Tool-Metadata-Extractor-Test-Wrapper"]
        else:
            repo = self.github.get_user("galaxyproject").get_repo("planemo-monitor")
            repo_list: List[str] = []
            for i in range(1, 5):
                repo_selection = f"repositories0{i}.list"
                if repository_list:  # only get these repositories
                    if repository_list == repo_selection:
                        repo_f = repo.get_contents(repo_selection)
                        repo_l = shared.get_string_content(repo_f).rstrip()
                        repo_list.extend(repo_l.split("\n"))
                else:
                    repo_f = repo.get_contents(repo_selection)
                    repo_l = shared.get_string_content(repo_f).rstrip()
                    repo_list.extend(repo_l.split("\n"))

            if (
                add_extra_repositories and "extra-repositories" in configs
            ):  # add non planemo monitor repositories defined in conf
                repo_list = repo_list + configs["extra-repositories"]
            print("Parsing repositories from:")
            for repo in repo_list:
                print("\t", repo)
            self.github_repositories = repo_list

    def parse_github_repositories(self) -> None:
        """
        Parse GitHub repositories to extract tools
        """
        for r in self.github_repositories:
            print("Parsing tools from:", (r))
            if "github" not in r:
                continue
            try:
                repo = shared.get_github_repo(r, self.github)
                self.add_tools_from_repo(repo)
            except Exception as e:
                print(
                    f"Error while extracting tools from repo {r}: {e}",
                    file=sys.stderr,
                )
                print(traceback.format_exc())

    def add_tools_from_repo(self, repo) -> None:
        """
        Parse tools in a GitHub repository, extract them and their metadata

        :param repo: GitHub Repository object
        :param g: GitHub
        """
        # get tool folders
        tool_folders: List[List[ContentFile]] = []
        try:
            repo_tools = repo.get_contents("tools")
        except Exception:
            try:
                repo_tools = repo.get_contents("wrappers")
            except Exception:
                print("No tool folder found", sys.stderr)
                return []
        assert isinstance(repo_tools, list)
        tool_folders.append(repo_tools)
        try:
            repo_tools = repo.get_contents("tool_collections")
        except Exception:
            pass
        else:
            assert isinstance(repo_tools, list)
            tool_folders.append(repo_tools)

        # tool_folders will contain a list of all folders in the
        # repository named wrappers/tools/tool_collections

        # parse folders
        tools = []
        for folder in tool_folders:
            for tool in folder:
                # to avoid API request limit issue, wait for one hour
                if self.github.get_rate_limit().core.remaining < 200:
                    print("WAITING for 1 hour to retrieve GitHub API request access !!!")
                    print()
                    time.sleep(60 * 60)

                # parse tool
                # if the folder (tool) has a .shed.yml file run get get_tool_metadata on that folder,
                # otherwise go one level down and check if there is a .shed.yml in a subfolder
                try:
                    repo.get_contents(f"{tool.path}/.shed.yml")
                except Exception:
                    if tool.type != "dir":
                        continue
                    file_list = repo.get_contents(tool.path)
                    assert isinstance(file_list, list)
                    for content in file_list:
                        tool = Tool()
                        status = tool.init_from_github(content, repo)
                        if status is not None:
                            tools.append(tool)
                else:
                    tool = Tool()
                    status = tool.init_from_github(content, repo)
                    if status is not None:
                        tools.append(tool)

        self.tools.extend(tools)

    def filter_tools(
        self,
        ts_cat: List[str],
        tool_status: Dict,
    ) -> list:
        """
        Filter tools for specific ToolShed categories

        :param ts_cat: list of ToolShed categories to keep in the extraction
        :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
        """
        filtered_tools = []
        for tool in self.tools:
            # filter ToolShed categories and leave function if not in expected categories
            if tool.check_categories(ts_cat):
                tool.add_status(tool_status)
                filtered_tools.append(tool)
        self.tools = filtered_tools

    def curate_tools(
        self,
        tool_status: Dict,
    ) -> tuple:
        """
        Filter tools for specific ToolShed categories

        :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
        """
        curated_tools = []
        tools_wo_biotools = []
        tools_with_biotools = []
        for tool in tools:
            tool.add_status(tool_status)
            if tool.status["to_keep"]:  # only add tools that are manually marked as to keep
                curated_tools.append(tool)
                if tool.biottols["id"] is None:
                    tools_wo_biotools.append(tool)
                else:
                    tools_with_biotools.append(tool)
        self.tools = curated_tools
        return tools_wo_biotools, tools_with_biotools

    def export_tools_to_dict(self) -> List:
        """
        Export tools as dictionary
        """
        return [t.__dict__ for t in self.tools]

    def export_tools_to_tsv(self, output_fp: str, format_list_col: bool = False, to_keep_columns: Optional[List[str]] = None) -> None:
        """
        Export workflows to a TSV file

        :param output_fp: path to output file
        :param format_list_col: boolean indicating if list columns should be formatting
        :param to_keep_columns: 
        """
        renaming = (
            pd.read_csv(DATA_PATH.joinpath("available_public_servers.tsv"), sep="\t", index_col=0) # load the mapping
            .drop(columns=["Description"])
            .to_dict('index')
        )
        df = pd.DataFrame(self.export_workflows_to_dict()).rename(columns=renaming).fillna("").reindex(columns=list(renaming.values()))
        
        if format_list_col:
            col_to_format = [
                "ToolShed categories",
                "EDAM operations",
                "EDAM topics",
                "EDAM reduced operations",
                "EDAM reduced topics",
                "Tool IDs",
            ]
            for col in col_to_format:
                df[col] = shared.format_list_column(df[col])

        if to_keep_columns is not None:
            df = df[to_keep_columns]
        
        df.to_csv(output_fp, sep="\t", index=False)





@lru_cache  # need to run this for each suite, so just cache it
def get_all_installed_tool_ids_on_server(galaxy_url: str) -> List[str]:
    """
    Get all tool ids from a Galaxy server

    :param galaxy_url: URL of Galaxy instance
    """
    galaxy_url = galaxy_url.rstrip("/")
    base_url = f"{galaxy_url}/api"

    try:
        r = requests.get(f"{base_url}/tools", params={"in_panel": False})
        r.raise_for_status()
        tool_dict_list = r.json()
        tools = [tool_dict["id"] for tool_dict in tool_dict_list]
        return tools
    except Exception as ex:
        print(f"Server query failed with: \n {ex}")
        print(f"Could not query tools on server {galaxy_url}, all tools from this server will be set to 0!")
        return []

def add_status(tool: Dict, tool_status: Dict) -> None:
    """
    Add status to tool

    :param tool: dictionary with tools and their metadata
    :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
    """
    name = tool["Suite ID"]
    if name in tool_status:
        tool["To keep"] = tool_status[name]["To keep"]
        tool["Deprecated"] = tool_status[name]["Deprecated"]
    else:
        tool["To keep"] = None
        tool["Deprecated"] = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy tools from GitHub repositories together with biotools and conda metadata"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tools
    extract = subparser.add_parser("extract", help="Extract tools")
    extract.add_argument("--api", "-a", required=True, help="GitHub access token")
    extract.add_argument("--all", "-o", required=True, help="Filepath to JSON with all extracted tools")
    extract.add_argument("--all-tsv", "-j", required=True, help="Filepath to TSV with all extracted tools")
    extract.add_argument(
        "--planemo-repository-list",
        "-pr",
        required=False,
        help="Repository list to use from the planemo-monitor repository",
    )
    extract.add_argument(
        "--avoid-extra-repositories",
        "-e",
        action="store_true",
        default=False,
        required=False,
        help="Do not parse extra repositories in conf file",
    )
    extract.add_argument(
        "--test",
        "-t",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test case using only the repository: https://github.com/TGAC/earlham-galaxytools",
    )

    # Filter tools based on ToolShed categories
    filtertools = subparser.add_parser("filter", help="Filter tools based on ToolShed categories")
    filtertools.add_argument(
        "--all",
        "-a",
        required=True,
        help="Filepath to JSON with all extracted tools, generated by extractools command",
    )
    filtertools.add_argument(
        "--categories",
        "-c",
        help="Path to a file with ToolShed category to keep in the extraction (one per line)",
    )
    filtertools.add_argument(
        "--filtered",
        "-f",
        required=True,
        help="Filepath to JSON with tools filtered based on ToolShed category",
    )
    filtertools.add_argument(
        "--tsv-filtered",
        "-t",
        required=True,
        help="Filepath to TSV with tools filtered based on ToolShed category",
    )
    filtertools.add_argument(
        "--status",
        "-s",
        help="Path to a TSV file with tool status - at least 3 columns: IDs of tool suites, Boolean with True to keep and False to exclude, Boolean with True if deprecated and False if not",
    )

    # Curate tools categories
    curatetools = subparser.add_parser("curate", help="Curate tools based on community review")
    curatetools.add_argument(
        "--filtered",
        "-f",
        required=True,
        help="Filepath to JSON with tools filtered based on ToolShed category",
    )
    curatetools.add_argument(
        "--curated",
        "-c",
        required=True,
        help="Filepath to TSV with curated tools",
    )
    curatetools.add_argument(
        "--wo-biotools",
        required=True,
        help="Filepath to TSV with tools not linked to bio.tools",
    )
    curatetools.add_argument(
        "--w-biotools",
        required=True,
        help="Filepath to TSV with tools linked to bio.tools",
    )
    curatetools.add_argument(
        "--status",
        "-s",
        help="Path to a TSV file with tool status - at least 3 columns: IDs of tool suites, Boolean with True to keep and False to exclude, Boolean with True if deprecated and False if not",
    )
    args = parser.parse_args()

    if args.command == "extract":
        tools = Tools(test=args.test)
        tools.init_by_searching(
            g=args.api,
            repository_list=args.planemo_repository_list,
            add_extra_repositories=not args.avoid_extra_repositories,
        )
        shared.export_to_json(tools.export_tools_to_dict(), args.all)
        tools.export_tools_to_tsv(args.all_tsv, format_list_col=True)

    elif args.command == "filter":
        tools = Tools()
        tools.init_by_importing(tools=shared.load_json(args.all))
        # get categories and tools to exclude
        categories = shared.read_file(args.categories)
        # get status if file provided
        if args.status:
            status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
        else:
            status = {}
        # filter tool lists
        tools.filter_tools(categories, status)
        if tools.tools:
            shared.export_to_json(tools.export_tools_to_dict(), args.filtered)
            tools.export_tools_to_tsv(
                args.tsv_filtered,
                format_list_col=True,
                to_keep_columns=["Suite ID", "Description", "To keep", "Deprecated"],
            )
        else:
            # if there are no ts filtered tools
            print(f"No tools found for category {args.filtered}")

    elif args.command == "curate":
        tools = Tools()
        tools.init_by_importing(tools=shared.load_json(args.all))
        try:
            status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
        except Exception as ex:
            print(f"Failed to load tool_status.tsv file with:\n{ex}")
            print("Not assigning tool status for this community !")
            status = {}

        tools_wo_biotools, tools_with_biotools = tools.curate_tools(status)
        if tools.tools:
            tools.export_tools_to_tsv(
                args.curated,
                format_list_col=True,
            )
            tools_wo_biotools.export_tools_to_tsv(
                tools_wo_biotools,
                args.wo_biotools,
                format_list_col=True,
                to_keep_columns=["Suite ID", "Homepage", "Suite source"],
            )
            tools_with_biotools.export_tools_to_tsv(
                args.w_biotools,
                format_list_col=True,
                to_keep_columns=["Suite ID", "bio.tool name", "EDAM operations", "EDAM topics"],
            )
        else:
            # if there are no ts filtered tools
            print("No tools left after curation")
