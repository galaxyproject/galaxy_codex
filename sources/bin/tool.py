#!/usr/bin/env python
import argparse
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
        self.toolshed: dict = {
            "id": "",
            "categories": [],
            "description": "",
            "homepage": "",
            "owner": "",
            "source": "",
        }
        self.tool_ids: List[str] = []
        self.first_commit: str = ""
        self.version = ""
        self.conda_package = {"name": "", "latest_version": "", "version_status": "To update"}
        self.edam: dict = {
            "operations": {
                "full": [],
                "reduced": [],
            },
            "topics": {
                "full": [],
                "reduced": [],
            },
        }
        self.biotools: dict = {
            "id": "",
            "name": "",
            "description": "",
        }
        self.biii: dict = {"ID": ""}
        self.availability: dict = {}
        self.stats: dict = {
            "users": {
                "last_5_years": {
                    "main_servers": 0,
                },
                "all_time": {
                    "main_servers": 0,
                },
            },
            "runs": {
                "last_5_years": {
                    "main_servers": 0,
                },
                "all_time": {
                    "main_servers": 0,
                },
            },
        }
        self.community_status: dict = {
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
            self.init_toolshed_metadata(shed)

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
            self.toolshed["Description"] = self.toolshed["Description"].replace("\n", "")
        self.toolshed["id"] = shared.get_shed_attribute("name", yaml_content, None)
        self.toolshed["owner"] = shared.get_shed_attribute("owner", yaml_content, None)
        self.toolshed["source"] = shared.get_shed_attribute("remote_repository_url", yaml_content, None)
        if "homepage_url" in yaml_content:
            self.toolshed["homepage"] = yaml_content["homepage_url"]
        self.toolshed["categories"] = shared.get_shed_attribute("categories", yaml_content, [])
        if self.toolshed["categories"] is None:
            self.toolshed["categories"] = []

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
                    self.version = child.text or ""
                elif child.attrib["name"] == "requirements":
                    self.add_conda_package(child)
                self.biotools["id"] = shared.get_xref(child, attrib_type="bio.tools")
                self.biii["id"] = shared.get_xref(child, attrib_type="biii")

    def add_conda_package(self, el: et.Element) -> None:
        """
        Get conda package information

        :param el: Element object
        """
        reqs = el.find("requirements")
        name = ""
        if reqs is not None:
            req = reqs.find("requirement")
            if req is not None:
                name = req.text or ""
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
            if self.version == "" and "version" in root.attrib:
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
                                self.version = child.text or ""

            # bio.tools
            if self.biotools["id"] == "":
                self.biotools["id"] = shared.get_xref(root, attrib_type="bio.tools")
            # biii
            if self.biii["id"] == "":
                self.biii["id"] = shared.get_xref(root, attrib_type="biii")

            # conda package
            if self.conda_package["name"] == "":
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
                self.edam["operations"]["reduced"] = shared.reduce_ontology_terms(
                    self.edam["operations"]["full"], ontology=edam
                )
            if len(self.edam["topics"]["full"]) > 0:
                self.edam["topics"]["reduced"] = shared.reduce_ontology_terms(
                    self.edam["topics"]["full"], ontology=edam
                )

    def add_tool_number_on_a_server(self, name: str, url: str) -> None:
        """
        Add number of tools in tool_ids installed on a Galaxy server

        :param name: Galaxy server name
        :param url: Galaxy server url
        """
        assert all("/" not in tool_id for tool_id in self.tool_ids), "This function only works on short tool ids"

        installed_tool_ids = get_all_installed_tool_ids_on_server(url)
        installed_tool_short_ids = [
            tool_id.split("/")[4] if "/" in tool_id else tool_id for tool_id in installed_tool_ids
        ]

        counter = 0
        for tool_id in self.tool_ids:
            if tool_id in installed_tool_short_ids:
                counter += 1

        self.availability[name] = counter

    def add_availability(self, public_servers_df: pd.DataFrame) -> None:
        """
        Add available for UseGalaxy servers and other public servers

        :param public_servers_df: DataFrame with public servers
        """
        # add availability for UseGalaxy servers
        for name, url in USEGALAXY_SERVER_URLS.items():
            self.add_tool_number_on_a_server(url, name)

        # add all other available servers
        for _index, row in public_servers_df.iterrows():
            name = row["name"]
            if name.lower() not in [
                n.lower() for n in USEGALAXY_SERVER_URLS.keys()
            ]:  # do not query UseGalaxy servers again

                url = row["url"]
                self.add_tool_number_on_a_server(url, name)

    def add_server_stat(self, stat_df: pd.DataFrame, stat: str, timing: str, server: str) -> int:
        """
        Computes a count for tool stats based on the tool id. The counts for local and toolshed installed tools are
        aggregated. All tool versions are also aggregated.

        :param stat_df: df with tools stats in the form `toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter,3394539`
        :param stat: stat type (users or runs)
        :param timing: stat time (last_5_years or all_time)
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
        self.stats[stat][timing][server] = int(agg_count)
        return self.stats[stat][timing][server]

    def add_stats(self, tool_stats: Dict) -> None:
        """
        Add tool stats

        :param tool_stats: nested dictionary with stat dataframes
        """
        for stat, stat_dict in tool_stats:
            for t, time_stat in stat_dict:
                summed_stat = 0
                for server, stat_df in time_stat:
                    stat = self.add_server_stat(stat_df, stat, t, server)
                    summed_stat += stat
                self.stats[stat][t]["main servers"] = summed_stat

    def add_status(self, tool_status: Dict[str, dict[str, bool]]) -> None:
        """
        Add status to tool

        :param tool: dictionary with tools and their metadata
        :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
        """
        name = self.toolshed["id"]
        if name in tool_status:
            self.community_status["to_keep"] = tool_status[name]["To keep"]
            self.community_status["deprecated"] = tool_status[name]["Deprecated"]

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
