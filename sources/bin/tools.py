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
from tool import Tool
import yaml
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from owlready2 import get_ontology


DATA_PATH = Path(__file__).resolve().parent.parent.joinpath("data")


class Tools:
    """
    Class Tools
    """

    def __init__(self, test: bool = False) -> None:
        self.tools: List[Tool] = []
        self.test = test
        self.github = Github()
        self.github_repositories: List[str] = []

    def init_by_importing(self, tools: dict) -> None:
        for t in tools:
            tool = Tool()
            tool.init_by_importing(t)
            self.tools.append(tool)

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

        tool_stats: dict = {}
        servers_with_stats = ["eu", "org", "org.au"]
        usage_stats_path = DATA_PATH.joinpath("usage_stats", f"usage_stats_{STAT_DATE}")
        for server in servers_with_stats:
            fp = usage_stats_path.joinpath(f"{ server }/tool_users_5y_until_{STAT_DATE}.csv")
            tool_stats["users"]["last_5_years"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(f"{ server }/tool_users_until_{STAT_DATE}.csv")
            tool_stats["users"]["all_time"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(f"{ server }/tool_usage_5y_until_{STAT_DATE}.csv")
            tool_stats["runs"]["last_5_years"][server] = pd.read_csv(fp)
            fp = usage_stats_path.joinpath(f"{ server }/tool_usage_until_{STAT_DATE}.csv")
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

    def add_tools_from_repo(self, repo: Repository) -> None:
        """
        Parse tools in a GitHub repository, extract them and their metadata

        :param repo: GitHub Repository object
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
                remaining = self.github.get_rate_limit().core.remaining
                if remaining < 200:
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
    ) -> None:
        """
        Filter tools for specific ToolShed categories

        :param ts_cat: list of ToolShed categories to keep in the extraction
        :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
        """
        filtered_tools = []
        for to in self.tools:
            # filter ToolShed categories and leave function if not in expected categories
            if to.check_categories(ts_cat):
                to.add_status(tool_status)
                filtered_tools.append(to)
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
        for to in self.tools:
            to.add_status(tool_status)
            if to.community_status["to_keep"]:  # only add tools that are manually marked as to keep
                curated_tools.append(to)
                if to.biotools["id"] is None:
                    tools_wo_biotools.append(to)
                else:
                    tools_with_biotools.append(to)
        self.tools = curated_tools
        return tools_wo_biotools, tools_with_biotools

    def export_tools_to_dict(self) -> List:
        """
        Export tools as dictionary
        """
        return [t.__dict__ for t in self.tools]

    def export_tools_to_tsv(
        self, output_fp: str, format_list_col: bool = False, to_keep_columns: Optional[List[str]] = None
    ) -> None:
        """
        Export workflows to a TSV file

        :param output_fp: path to output file
        :param format_list_col: boolean indicating if list columns should be formatting
        :param to_keep_columns:
        """
        renaming = (
            pd.read_csv(DATA_PATH.joinpath("available_public_servers.tsv"), sep="\t", index_col=0)  # load the mapping
            .drop(columns=["Description"])
            .to_dict("index")
        )
        df = (
            pd.DataFrame(self.export_tools_to_dict())
            .rename(columns=renaming)
            .fillna("")
            .reindex(columns=list(renaming.values()))
        )

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
