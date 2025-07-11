#!/usr/bin/env python
import argparse
import base64
import json
import re
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
    Literal,
    Optional,
    Pattern,
    Union,
)

import numpy as np
import pandas as pd
import requests
import shared
import yaml
from extract_galaxy_workflows import Workflows
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from owlready2 import get_ontology
from ruamel.yaml import YAML as ruamelyaml
from ruamel.yaml.scalarstring import LiteralScalarString

# Config variables
BIOTOOLS_API_URL = "https://bio.tools"

USEGALAXY_SERVER_URLS = {
    "UseGalaxy.org (Main)": "https://usegalaxy.org",
    "UseGalaxy.org.au": "https://usegalaxy.org.au",
    "UseGalaxy.eu": "https://usegalaxy.eu",
    "UseGalaxy.fr": "https://usegalaxy.fr",
}

project_path = Path(__file__).resolve().parent.parent  # galaxy_tool_extractor folder
usage_stats_path = project_path.joinpath("data", "usage_stats", "usage_stats_31.01.2025")
conf_path = project_path.joinpath("data", "conf.yml")
public_servers = project_path.joinpath("data", "available_public_servers.csv")


GALAXY_TOOL_STATS = {}
for server in ["eu", "org", "org.au", "fr"]:
    GALAXY_TOOL_STATS[f"Suite users (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_5y_until_2025.01.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite users (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_until_2025.01.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_5y_until_2025.01.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_until_2025.01.31.csv"
    )


# We use a regex since Suite users matches Suite users (last 5 years) as well

STATS_SUM = {
    "Suite runs": re.compile(r"^Suite runs \((?!last 5 years\)).+\)$"),
    "Suite runs (last 5 years)": re.compile(r"^Suite runs \(last 5 years\) \(.+\)$"),
    "Suite users": re.compile(r"^Suite users \((?!last 5 years\)).+\)$"),
    "Suite users (last 5 years)": re.compile(r"^Suite users \(last 5 years\) \(.+\)$"),
}

# load the configs globally
with open(conf_path) as f:
    configs = yaml.safe_load(f)


def get_last_url_position(toot_id: str) -> str:
    """
    Returns the second last url position of the toot_id, if the value is not a
    url it returns the toot_id. So works for local and toolshed
    installed tools.

    :param tool_id: galaxy tool id
    """

    if "/" in toot_id:
        toot_id = toot_id.split("/")[-1]
    return toot_id


def get_tool_stats_from_stats_file(
    tool_stats_df: pd.DataFrame, tool_ids: List[str], mode: Literal["sum", "max"] = "sum"
) -> int:
    """
    Aggregates statistics for a list of tool IDs from a DataFrame, using either sum or max.
    Tool versions are not distinguished — tools are grouped by suite-level ID.

    :param tool_stats_df: DataFrame with 'tool_name' and 'count' columns. (toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter,3394539)
    :param tool_ids: List of tool suite IDs to match.
    :param mode: Aggregation mode: "sum" or "max".
    :return: Aggregated count based on mode.
    """
    # extract suite-level tool ID from full tool_name path
    tool_stats_df["Suite ID"] = tool_stats_df["tool_name"].apply(get_last_url_position)

    # Group by Suite ID and sum all version counts
    grouped = tool_stats_df.groupby("Suite ID")["count"].sum()

    # Get values for tool_ids that are present in grouped index
    relevant_counts: List[int] = [int(grouped[tid]) for tid in tool_ids if tid in grouped]

    if not relevant_counts:
        return 0

    return max(relevant_counts) if mode == "max" else sum(relevant_counts)


def get_string_content(cf: ContentFile) -> str:
    """
    Get string of the content from a ContentFile

    :param cf: GitHub ContentFile object
    """

    return base64.b64decode(cf.content).decode("utf-8")


def get_tool_github_repositories(
    g: Github,
    repository_list: Optional[str],
    run_test: bool,
    test_repository: str = "https://github.com/paulzierep/Galaxy-Tool-Metadata-Extractor-Test-Wrapper",
    add_extra_repositories: bool = True,
) -> List[str]:
    """
    Get list of tool GitHub repositories to parse

    :param g: GitHub instance
    :param repository_list: The selection to use from the repository (needed to split the process for CI jobs)
    :param run_test: for testing only parse the repository
    :test_repository: the link to the test repository to use for the test
    """

    if run_test:
        return [test_repository]

    repo = g.get_user("galaxyproject").get_repo("planemo-monitor")
    repo_list: List[str] = []
    for i in range(1, 5):
        repo_selection = f"repositories0{i}.list"
        if repository_list:  # only get these repositories
            if repository_list == repo_selection:
                repo_f = repo.get_contents(repo_selection)
                repo_l = get_string_content(repo_f).rstrip()
                repo_list.extend(repo_l.split("\n"))
        else:
            repo_f = repo.get_contents(repo_selection)
            repo_l = get_string_content(repo_f).rstrip()
            repo_list.extend(repo_l.split("\n"))

    if (
        add_extra_repositories and "extra-repositories" in configs
    ):  # add non planemo monitor repositories defined in conf
        repo_list = repo_list + configs["extra-repositories"]

    print("Parsing repositories from:")
    for repo in repo_list:
        print("\t", repo)

    return repo_list


def get_github_repo(url: str, g: Github) -> Repository:
    """
    Get a GitHub Repository object from an URL

    :param url: URL to a GitHub repository
    :param g: GitHub instance
    """
    if not url.startswith("https://github.com/"):
        raise ValueError
    if url.endswith("/"):
        url = url[:-1]
    if url.endswith(".git"):
        url = url[:-4]
    u_split = url.split("/")
    return g.get_user(u_split[-2]).get_repo(u_split[-1])


def get_shed_attribute(attrib: str, shed_content: Dict[str, Any], empty_value: Any) -> Any:
    """
    Get a shed attribute

    :param attrib: attribute to extract
    :param shed_content: content of the .shed.yml
    :param empty_value: value to return if attribute not found
    """
    if attrib in shed_content:
        return shed_content[attrib]
    else:
        return empty_value


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


def get_conda_package(el: et.Element) -> Optional[str]:
    """
    Get conda package information

    :param el: Element object
    """
    reqs = el.find("requirements")
    if reqs is not None:
        req = reqs.find("requirement")
        if req is not None:
            return req.text
        # for req in reqs.findall('requirement'):
        #    if 'version' in req.attrib:
        #        if req.attrib['version'] == '@VERSION@' or req.attrib['version'] == '@TOOL_VERSION@':
        #            return req.text
        #        elif req.attrib['version']
        #    elif 'version' in req.attrib:
        #        return req.text
        #    else:
        #        return req.text
    return None


def check_categories(ts_categories: str, ts_cat: List[str]) -> bool:
    """
    Check if tool fit in ToolShed categories to keep

    :param ts_categories: tool ToolShed categories
    :param ts_cat: list of ToolShed categories to keep in the extraction
    """
    if not ts_cat:
        return True
    if not ts_categories:
        return False
    ts_cats = ts_categories
    return bool(set(ts_cat) & set(ts_cats))


def get_suite_ID_fallback(metadata: Dict, tool: ContentFile) -> Dict:
    """
    Set suite ID fallbacks

    :param metadata: the metadata dict
    """

    # when `name` not in .shed.yml file
    if metadata["Suite ID"] is None:
        if metadata["bio.tool ID"] is not None:
            metadata["Suite ID"] = metadata["bio.tool ID"].lower()
        else:
            metadata["Suite ID"] = tool.path.split("/")[-1]

    return metadata


def get_tool_metadata(tool: ContentFile, repo: Repository) -> Optional[Dict[str, Any]]:
    """
    Get tool metadata from the .shed.yaml, requirements in the macros or xml
    file,  bio.tools information if available in the macros or xml, EDAM
    annotations using bio.tools API, recent conda version using conda API

    :param tool: GitHub ContentFile object
    :param repo: GitHub Repository object
    """
    if tool.type != "dir":
        return None

    metadata: dict = {
        "Suite ID": None,
        "Tool IDs": [],
        "Description": None,
        "Suite first commit date": None,
        "Homepage": None,
        "Suite version": None,
        "Suite conda package": None,
        "Latest suite conda package version": None,
        "Suite version status": "To update",
        "ToolShed categories": [],
        "EDAM operations": [],
        "EDAM reduced operations": [],
        "EDAM topics": [],
        "EDAM reduced topics": [],
        "Suite owner": None,
        "Suite source": None,  # this is what it written in the .shed.yml
        "Suite parsed folder": None,  # this is the actual parsed file
        "bio.tool ID": None,
        "bio.tool name": None,
        "bio.tool description": None,
        "biii ID": None,
    }
    # extract .shed.yml information and check macros.xml
    try:
        shed = repo.get_contents(f"{tool.path}/.shed.yml")
    except Exception:
        return None
    # parse the .shed.yml
    else:
        file_content = get_string_content(shed)
        yaml_content = yaml.load(file_content, Loader=yaml.FullLoader)
        metadata["Description"] = get_shed_attribute("description", yaml_content, None)
        if metadata["Description"] is None:
            metadata["Description"] = get_shed_attribute("long_description", yaml_content, None)
        if metadata["Description"] is not None:
            metadata["Description"] = metadata["Description"].replace("\n", "")
        metadata["Suite ID"] = get_shed_attribute("name", yaml_content, None)
        metadata["Suite owner"] = get_shed_attribute("owner", yaml_content, None)
        metadata["Suite source"] = get_shed_attribute("remote_repository_url", yaml_content, None)
        if "homepage_url" in yaml_content:
            metadata["Homepage"] = yaml_content["homepage_url"]
        metadata["ToolShed categories"] = get_shed_attribute("categories", yaml_content, [])
        if metadata["ToolShed categories"] is None:
            metadata["ToolShed categories"] = []

    # get all files in the folder
    file_list = repo.get_contents(tool.path)
    assert isinstance(file_list, list)

    # store the github location where the folder was parsed
    metadata["Suite parsed folder"] = tool.html_url

    # get the first commit date
    metadata["Suite first commit date"] = shared.get_first_commit_for_folder(tool, repo)

    # find and parse macro file
    for file in file_list:
        if "macro" in file.name and file.name.endswith("xml"):
            file_content = get_string_content(file)
            root = et.fromstring(file_content)
            for child in root:
                if "name" in child.attrib:
                    if child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@":
                        metadata["Suite version"] = child.text
                    elif child.attrib["name"] == "requirements":
                        metadata["Suite conda package"] = get_conda_package(child)
                    # bio.tools
                    biotools = get_xref(child, attrib_type="bio.tools")
                    if biotools is not None:
                        metadata["bio.tool ID"] = biotools
                    # biii
                    biii = get_xref(child, attrib_type="biii")
                    if biii is not None:
                        metadata["biii ID"] = biii

    # parse XML file and get meta data from there
    for file in file_list:
        if file.name.endswith("xml") and "macro" not in file.name:
            try:
                file_content = get_string_content(file)
                root = et.fromstring(file_content)
            except Exception:
                print(traceback.format_exc())
            else:
                # version
                if metadata["Suite version"] is None:
                    if "version" in root.attrib:
                        version = root.attrib["version"]
                        if "VERSION@" not in version:
                            metadata["Suite version"] = version
                        else:
                            macros = root.find("macros")
                            if macros is not None:
                                for child in macros:
                                    if "name" in child.attrib and (
                                        child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@"
                                    ):
                                        metadata["Suite version"] = child.text

                # bio.tools
                biotools = get_xref(root, attrib_type="bio.tools")
                if biotools is not None:
                    metadata["bio.tool ID"] = biotools

                # biii
                if metadata["biii ID"] is None:
                    biii = get_xref(root, attrib_type="biii")
                    if biii is not None:
                        metadata["biii ID"] = biii

                # conda package
                if metadata["Suite conda package"] is None:
                    reqs = get_conda_package(root)
                    if reqs is not None:
                        metadata["Suite conda package"] = reqs
                # tool ids
                if "id" in root.attrib:
                    metadata["Tool IDs"].append(root.attrib["id"])

    metadata = get_suite_ID_fallback(metadata, tool)

    # get latest conda version and compare to the wrapper version
    if metadata["Suite conda package"] is not None:
        r = requests.get(f'https://api.anaconda.org/package/bioconda/{metadata["Suite conda package"]}')
        if r.status_code == requests.codes.ok:
            conda_info = r.json()
            if "latest_version" in conda_info:
                metadata["Latest suite conda package version"] = conda_info["latest_version"]
                if metadata["Latest suite conda package version"] == metadata["Suite version"]:
                    metadata["Suite version status"] = "Up-to-date"

    # get bio.tool information
    if metadata["bio.tool ID"] is not None:
        r = requests.get(f'{BIOTOOLS_API_URL}/api/tool/{metadata["bio.tool ID"]}/?format=json')
        if r.status_code == requests.codes.ok:
            biotool_info = r.json()
            if "function" in biotool_info:
                for func in biotool_info["function"]:
                    if "operation" in func:
                        for op in func["operation"]:
                            metadata["EDAM operations"].append(op["term"])
            if "topic" in biotool_info:
                for t in biotool_info["topic"]:
                    metadata["EDAM topics"].append(t["term"])
            if "name" in biotool_info:
                metadata["bio.tool name"] = biotool_info["name"]
            if "description" in biotool_info:
                metadata["bio.tool description"] = biotool_info["description"].replace("\n", "")
    return metadata


def parse_tools(repo: Repository) -> List[Dict[str, Any]]:
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
            if g.get_rate_limit().core.remaining < 200:
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
                    metadata = get_tool_metadata(content, repo)
                    if metadata is not None:
                        tools.append(metadata)
            else:
                metadata = get_tool_metadata(tool, repo)
                if metadata is not None:
                    tools.append(metadata)
    return tools


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


def check_tools_on_servers(tool_ids: List[str], galaxy_server_url: str) -> int:
    """
    Return number of tools in tool_ids installed on galaxy_server_url

    :param tool_ids: galaxy tool ids
    """
    assert all("/" not in tool_id for tool_id in tool_ids), "This function only works on short tool ids"

    installed_tool_ids = get_all_installed_tool_ids_on_server(galaxy_server_url)
    installed_tool_short_ids = [tool_id.split("/")[4] if "/" in tool_id else tool_id for tool_id in installed_tool_ids]

    counter = 0
    for tool_id in tool_ids:
        if tool_id in installed_tool_short_ids:
            counter += 1

    return counter


def export_tools_to_json(tools: List[Dict], output_fp: str) -> None:
    """
    Export tool metadata to TSV output file

    :param tools: dictionary with tools
    :param output_fp: path to output file
    """
    with Path(output_fp).open("w") as f:
        json.dump(tools, f, default=list, indent=4)


def export_tools_to_tsv(
    tools: List[Dict], output_fp: str, format_list_col: bool = False, to_keep_columns: Optional[List[str]] = None
) -> None:
    """
    Export tool metadata to TSV output file

    :param tools: dictionary with tools
    :param output_fp: path to output file
    :param format_list_col: boolean indicating if list columns should be formatting
    """

    df = pd.DataFrame(tools).sort_values("Suite ID")
    if format_list_col:
        df["ToolShed categories"] = shared.format_list_column(df["ToolShed categories"])
        df["EDAM operations"] = shared.format_list_column(df["EDAM operations"])
        df["EDAM topics"] = shared.format_list_column(df["EDAM topics"])

        df["EDAM reduced operations"] = shared.format_list_column(df["EDAM reduced operations"])
        df["EDAM reduced topics"] = shared.format_list_column(df["EDAM reduced topics"])

        df["Related Workflows"] = shared.format_list_column(df["Related Workflows"])
        df["Related Tutorials"] = shared.format_list_column(df["Related Tutorials"])

        # the Galaxy tools need to be formatted for the add_instances_to_table to work
        df["Tool IDs"] = shared.format_list_column(df["Tool IDs"])

    if to_keep_columns is not None:
        df = df[to_keep_columns]

    df.to_csv(output_fp, sep="\t", index=False)


def add_status(tool: Dict, tool_status: pd.DataFrame) -> None:
    """
    Add status to tool

    :param tool: dictionary with tools and their metadata
    :param tool_status: dataframe with suite ID and owner and their 2 status: Keep and Deprecated
    """
    name = tool["Suite ID"]
    owner = tool["Suite owner"]
    if "Suite owner" in tool_status:
        query = tool_status.query(f"`Suite ID` == '{name}' and `Suite owner` == '{owner}'")
    else:
        query = tool_status.query(f"`Suite ID` == '{name}'")
    if query.empty:
        tool["To keep"] = None
        tool["Deprecated"] = None
    else:
        selected_query = query.iloc[0]
        tool["To keep"] = bool(selected_query["To keep"]) if selected_query["To keep"] is not None else None
        tool["Deprecated"] = bool(selected_query["Deprecated"]) if selected_query["Deprecated"] is not None else None


def filter_tools(
    tools: List[Dict],
    ts_cat: List[str],
    tool_status: pd.DataFrame,
) -> list:
    """
    Filter tools for specific ToolShed categories

    :param tools: dictionary with tools and their metadata
    :param ts_cat: list of ToolShed categories to keep in the extraction
    :param tool_status: dataframe with suite ID and owner and their 2 status: Keep and Deprecated
    """
    filtered_tools = []
    for tool in tools:
        # filter ToolShed categories and leave function if not in expected categories
        if check_categories(tool["ToolShed categories"], ts_cat):
            filtered_tools.append(tool)
            add_status(tool, tool_status)
    return filtered_tools


def curate_tools(
    tools: List[Dict],
    tool_status: pd.DataFrame,
) -> tuple:
    """
    Filter tools for specific ToolShed categories

    :param tools: dictionary with tools and their metadata
    :param tool_status: dataframe with suite ID and owner and their 2 status: Keep and Deprecated
    """
    curated_tools = []
    tools_wo_biotools = []
    tools_with_biotools = []
    for tool in tools:
        add_status(tool, tool_status)
        if tool["To keep"]:  # only add tools that are manually marked as to keep
            curated_tools.append(tool)
            if tool["bio.tool ID"] is None:
                tools_wo_biotools.append(tool)
            else:
                tools_with_biotools.append(tool)
    return curated_tools, tools_wo_biotools, tools_with_biotools


def reduce_ontology_terms(terms: List, ontology: Any) -> List:
    """
    Reduces a list of Ontology terms, to include only terms that are not super-classes of one of the other terms.
    In other terms all classes that have a subclass in the terms are removed.

    :terms: list of terms from that ontology
    :ontology: Ontology
    """
    # if list is empty do nothing
    if not terms:
        return terms

    classes = [ontology.search_one(label=term) for term in terms]
    check_classes = [cla for cla in classes if cla is not None]  # Remove None values

    new_classes = []
    for cla in check_classes:
        try:
            # get all subclasses
            subclasses = list(cla.subclasses())

            # check if any of the other classes is a subclass
            include_class = True
            for subcla in subclasses:
                for cla2 in check_classes:
                    if subcla == cla2:
                        include_class = False

            # only keep the class if it is not a parent class
            if include_class:
                new_classes.append(cla)

        except Exception as e:
            print(f"Error processing class {cla}: {e}")

    # convert back to terms, skipping None values
    new_terms = [cla.label[0] for cla in new_classes if cla is not None]
    # print(f"Terms: {len(terms)}, New terms: {len(new_terms)}")
    return new_terms


def aggregate_tool_stats(
    tool: Dict[str, Union[int, float]],
    stats_sum: Dict[str, Pattern[str]],
) -> Dict[str, Union[int, float]]:
    """
    Aggregate tool stats by applying sum aggregation
    according to the provided regex patterns.

    Args:
        tool: A dict of tool stats with keys as stat names.
        stats_sum: Dict mapping stat base names to regex patterns for sum aggregation.

    Returns:
        The original tool dict updated with aggregated stats added.
    """

    for stat_name, pattern in stats_sum.items():
        matching_values = [
            value for key, value in tool.items() if pattern.match(key) and isinstance(value, (int, float))
        ]
        tool[f"{stat_name} on main servers"] = sum(matching_values)

    return tool


def get_tools(
    repo_list: list, all_workflows: str = "", all_tutorials: str = "", edam_ontology: Optional[Dict] = None
) -> List[Dict]:
    """
    Parse tools in GitHub repositories to extract metadata,
    filter by TS categories, additional information
    """
    tools: List[Dict] = []
    for r in repo_list:
        print("Parsing tools from:", (r))
        if "github" not in r:
            continue
        try:
            repo = get_github_repo(r, g)
            tools.extend(parse_tools(repo))
        except Exception as e:
            print(
                f"Error while extracting tools from repo {r}: {e}",
                file=sys.stderr,
            )
            print(traceback.format_exc())

    # add additional information to tools
    for tool in tools:
        # add EDAM terms without superclass
        tool["EDAM reduced operations"] = reduce_ontology_terms(tool["EDAM operations"], ontology=edam_ontology)
        tool["EDAM reduced topics"] = reduce_ontology_terms(tool["EDAM topics"], ontology=edam_ontology)

        # add availability for UseGalaxy servers
        for name, url in USEGALAXY_SERVER_URLS.items():
            tool[f"Number of tools on {name}"] = check_tools_on_servers(tool["Tool IDs"], url)

        # add all other available servers
        public_servers_df = pd.read_csv(public_servers, sep="\t")
        for _index, row in public_servers_df.iterrows():
            name = row["name"]

            if name.lower() not in [
                n.lower() for n in USEGALAXY_SERVER_URLS.keys()
            ]:  # do not query UseGalaxy servers again

                url = row["url"]
                tool[f"Number of tools on {name}"] = check_tools_on_servers(tool["Tool IDs"], url)

        # add tool stats
        for name, path in GALAXY_TOOL_STATS.items():
            tool_stats_df = pd.read_csv(path)

            # we take the max for suite users being conservative, since one user can use multiple tools
            # in the suite
            mode: Literal["sum", "max"]
            if "Suite users" in name:
                mode = "max"
            else:
                mode = "sum"

            tool[name] = get_tool_stats_from_stats_file(tool_stats_df, tool["Tool IDs"], mode=mode)

        # sum up tool stats
        tool = aggregate_tool_stats(tool, STATS_SUM)

    tools = add_workflow_ids_to_tools(tools, all_workflows)
    tools = add_tutorial_ids_to_tools(tools, all_tutorials)

    return tools


def add_workflow_ids_to_tools(tools: List[Dict[str, Any]], all_workflows: str) -> List[Dict[str, Any]]:
    """
    Add related workflow links to the tools dict.

    :param tools: List of tool dictionaries.
    :param all_workflows: Path to a JSON file containing all workflows.
    :return: Updated list of tool dictionaries with Related Workflows added.
    """
    workflow_path = Path(all_workflows)
    tool_to_workflow_links: Dict[str, List[str]] = {}

    if workflow_path.exists():
        try:
            wfs = Workflows()
            wfs.init_by_importing(wfs=shared.load_json(all_workflows))

            for workflow in wfs.workflows:
                link = workflow.link  # todo: change workflow funcs. to use link as ID
                for tool_id in workflow.tools:
                    tool_to_workflow_links.setdefault(tool_id, []).append(link)
        except Exception as e:
            print(f"Failed to load workflows from {workflow_path}: {e}")
    else:
        print(f"Workflows file '{workflow_path}' does not exist. Skipping workflow mapping.")

    for tool in tools:
        related = set()
        for tool_id in tool.get("Tool IDs", []):
            related.update(tool_to_workflow_links.get(tool_id, []))
        tool["Related Workflows"] = sorted(related)

    return tools


def add_tutorial_ids_to_tools(tools: List[Dict[str, Any]], all_tutorials: str) -> List[Dict[str, Any]]:
    """
    Add related tutorial IDs to the tools dict.

    :param tools: List of tool dictionaries.
    :param all_tutorials: Path to a JSON file containing all tutorials.
    :return: Updated list of tool dictionaries with Related Tutorial IDs added.
    """
    tutorial_path = Path(all_tutorials)
    tool_to_tutorial_ids: Dict[str, List[str]] = {}

    if tutorial_path.exists():
        try:
            with tutorial_path.open("r", encoding="utf-8") as f:
                tutorials = json.load(f)

            # Expecting tutorials to be a list
            for tutorial_data in tutorials:
                tutorial_id = tutorial_data.get("id")
                if tutorial_id:
                    for tool_name in tutorial_data.get("short_tools", []):
                        if tool_name:
                            tool_to_tutorial_ids.setdefault(tool_name, []).append(tutorial_id)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Failed to load tutorials from {tutorial_path}: {e}")
    else:
        print(f"Tutorials file '{tutorial_path}' does not exist. Skipping tutorial mapping.")

    for tool in tools:
        related = set()
        for tool_id in tool.get("Tool IDs", []):
            related.update(tool_to_tutorial_ids.get(tool_id, []))
        tool["Related Tutorials"] = sorted(related)

    return tools


def extract_top_tools_per_category(
    tool_fp: str, count_column: str = "Suite runs on main servers", category_nb: int = 10, top_tool_nb: int = 10
) -> pd.DataFrame:
    """
    Extract top tools per categories
    """
    tools = pd.read_csv(tool_fp, sep="\t")

    # Step 1: Split the categories into separate rows and strip whitespace
    df = tools.assign(Category=tools["EDAM operations"].str.split(",")).explode("Category")
    df["Category"] = df["Category"].str.strip()  # Strip whitespace

    # Step 2: Group by category to calculate total count and item count
    grouped = (
        df.groupby("Category")
        .agg(
            total_count=(count_column, "sum"),
            item_count=("Suite ID", "size"),  # Count distinct items if necessary, use 'nunique'
        )
        .reset_index()
    )

    # Step 3: Filter categories with at least 5 items
    filtered = grouped[grouped["item_count"] >= 5]

    # Step 4: Sort by total count in descending order
    top_categories = filtered.sort_values(by="total_count", ascending=False).head(category_nb)["Category"]

    # Step 5: Assign each tool to the first category it appears in
    # Sort by 'Galaxy wrapper id' to ensure we assign based on first appearance
    df_unique = df[df["Category"].isin(top_categories)]  # Filter rows for top 5 categories
    df_unique = df_unique.sort_values(by=["Suite ID", "Category"])  # Sort by tool ID to keep first category only

    # Step 6: Remove duplicates, keeping the first appearance of each tool
    df_unique = df_unique.drop_duplicates(subset=["Suite ID"], keep="first")

    # Step 7: Extract top X items per category based on total count
    top_tools_per_category = (
        df_unique.groupby("Category", group_keys=False)  # Group by category
        .apply(lambda group: group.nlargest(top_tool_nb, count_column))  # Get top items per category
        .reset_index(drop=True)  # Reset index for clean output
    )
    return top_tools_per_category


def fill_lab_tool_section(
    lab_section: dict, top_items_per_category: pd.DataFrame, count_column: str = "Suite runs on main servers"
) -> dict:
    """
    Fill Lab tool section
    """
    tabs = []
    for element in lab_section["tabs"]:
        if element["id"] == "more_tools":
            tabs.append(element)

    for grp_id, group in top_items_per_category.groupby("Category"):
        group_id = str(grp_id)
        tool_entries = []
        for _index, row in group.iterrows():

            # Prepare the description with an HTML unordered list and links for each Galaxy tool ID
            description = f"{row['Description']}\n (Tool usage: {row[count_column]})"
            tool_ids = row["Tool IDs"]
            owner = row["Suite owner"]
            wrapper_id = row["Suite ID"]

            # Split the tool IDs by comma if it's a valid string, otherwise handle as an empty list
            tool_ids_list = tool_ids.split(",") if isinstance(tool_ids, str) else []

            # Create the base URL template for each tool link
            url_template = "/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2F{owner}%2F{wrapper_id}%2F{tool_id}"

            # Build HTML list items with links
            description += "\n<ul>\n"
            for tool_id in tool_ids_list:
                tool_id = tool_id.strip()  # Trim whitespace
                # Format the URL with owner, wrapper ID, and tool ID
                url = "{{ galaxy_base_url }}" + url_template.format(owner=owner, wrapper_id=wrapper_id, tool_id=tool_id)
                description += f'  <li><a href="{url}">{tool_id}</a></li>\n'
            description += "</ul>"

            # Use LiteralScalarString to enforce literal block style for the description
            description_md = LiteralScalarString(description.strip())

            # Create the tool entry
            tool_entry = {
                "title_md": wrapper_id,
                "description_md": description_md,
            }

            tool_entries.append(tool_entry)

        # Create table entry for each EDAM
        tabs.append(
            {
                "id": group_id.replace(" ", "_").lower(),
                "title": group_id,
                "heading_md": f"Top 10 for the EDAM operation: {group_id}",
                "content": tool_entries,
            }
        )

    new_lab_section = {
        "id": lab_section["id"],
        "title": lab_section["title"],
        "tabs": tabs,
    }
    return new_lab_section


def extract_missing_tools_per_servers(tool_fp: str) -> dict:
    """
    Extract missing tools per servers that could be installed in a Lab
    """
    top_tools_per_category = extract_top_tools_per_category(tool_fp)
    tools = pd.read_csv(tool_fp, sep="\t").fillna("")

    servers = [col.replace("Number of tools on ", "") for col in tools.filter(regex="Number of tools on").columns]
    missing_tools: dict[str, dict] = {}
    for _index, tool in tools.iterrows():
        tool_ids = tool["Tool IDs"].split(", ")
        # individual tools to install
        to_install = [{"name": t_id, "owner": tool["Suite owner"], "tool_panel_section_id": ""} for t_id in tool_ids]
        # identify servers missing tools
        for server in servers:
            if tool[f"Number of tools on { server }"] < len(tool_ids):  # Missing tools condition
                if server not in missing_tools:
                    missing_tools[server] = {"all": [], "top": []}
                missing_tools[server]["all"].extend(to_install)
                if sum(top_tools_per_category["Suite ID"].str.contains(tool["Suite ID"])) == 1:
                    missing_tools[server]["top"].extend(to_install)
    return missing_tools


def export_missing_tools_to_yaml(server_f: Path, tools: list) -> None:
    """
    Export missing tools in a YAML file
    """
    tool_dict = {
        "install_tool_dependencies": True,
        "install_repository_dependencies": True,
        "install_resolver_dependencies": True,
        "tools": tools,
    }
    with server_f.open("w") as output:
        yaml.dump(tool_dict, output, default_flow_style=False)


def export_missing_tools(missing_tools: dict, tool_dp: str) -> None:
    """
    Export missing tools with a YAML per Galaxy server
    """
    all_d = Path(tool_dp) / Path("all")
    all_d.mkdir(parents=True, exist_ok=True)

    top_d = Path(tool_dp) / Path("top")
    top_d.mkdir(parents=True, exist_ok=True)

    for server, tools in missing_tools.items():
        server = server.replace("(", "").replace(")", "").replace(" ", "_").replace(".", "_")
        server_fn = f"{ server }.yaml"
        export_missing_tools_to_yaml(Path(all_d) / Path(server_fn), tools["all"])
        export_missing_tools_to_yaml(Path(top_d) / Path(server_fn), tools["top"])


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
        "--all-workflows",
        "-aw",
        required=False,
        help="Filepath to JSON with all extracted workflows. Created with extract --all command of workflows.",
    )
    extract.add_argument(
        "--all-tutorials",
        "-at",
        required=False,
        help="Filepath to JSON with all extracted trainings. Created with extract --all command of tutorials.",
    )
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

    # Curate tools categories
    labpop = subparser.add_parser("popLabSection", help="Fill in Lab section tools")
    labpop.add_argument(
        "--curated",
        "-c",
        required=True,
        help="Filepath to TSV with curated tools",
    )
    labpop.add_argument(
        "--lab",
        required=True,
        help="Filepath to YAML files for Lab section",
    )

    # Extract tools to install on servers
    labtools = subparser.add_parser("getLabTools", help="Extract tools to install on servers for a Lab")
    labtools.add_argument(
        "--curated",
        "-f",
        required=True,
        help="Filepath to TSV with curated tools",
    )
    labtools.add_argument(
        "--tools",
        required=True,
        help="Path to folder for generating subfolders (all, tools) with server YAML files with missing tools for a Lab",
    )

    args = parser.parse_args()

    if args.command == "extract":
        # connect to GitHub
        g = Github(args.api)
        # get list of GitHub repositories to parse
        repo_list = get_tool_github_repositories(
            g=g,
            repository_list=args.planemo_repository_list,
            run_test=args.test,
            add_extra_repositories=not args.avoid_extra_repositories,
        )
        # parse tools in GitHub repositories to extract metadata, filter by TS categories and export to output file
        edam_ontology = get_ontology("https://edamontology.org/EDAM_1.25.owl").load()
        tools = get_tools(repo_list, args.all_workflows, args.all_tutorials, edam_ontology)
        export_tools_to_json(tools, args.all)
        export_tools_to_tsv(tools, args.all_tsv, format_list_col=True)

    elif args.command == "filter":
        with Path(args.all).open() as f:
            tools = json.load(f)
        # get categories and tools to exclude
        categories = shared.read_file(args.categories)
        # get status if file provided
        if args.status and Path(args.status).exists():
            status = pd.read_csv(args.status, sep="\t").replace(np.nan, None)
        else:
            status = pd.DataFrame(columns=["Suite ID", "Suite owner", "Description", "To keep", "Deprecated"])
        # filter tool lists
        filtered_tools = filter_tools(tools, categories, status)
        if filtered_tools:
            export_tools_to_json(filtered_tools, args.filtered)
            export_tools_to_tsv(
                filtered_tools,
                args.status,
                format_list_col=True,
                to_keep_columns=["Suite ID", "Suite owner", "Description", "To keep", "Deprecated"],
            )
        else:
            # if there are no ts filtered tools
            print(f"No tools found for category {args.filtered}")

    elif args.command == "curate":
        with Path(args.filtered).open() as f:
            tools = json.load(f)
        try:
            status = pd.read_csv(args.status, sep="\t").replace(np.nan, None)
        except Exception as ex:
            print(f"Failed to load tool_status.tsv file with:\n{ex}")
            print("Not assigning tool status for this community !")
            status = pd.DataFrame(columns=["Suite ID", "Suite owner", "Description", "To keep", "Deprecated"])

        curated_tools, tools_wo_biotools, tools_with_biotools = curate_tools(tools, status)
        if curated_tools:
            export_tools_to_json(curated_tools, args.filtered)
            export_tools_to_tsv(
                curated_tools,
                args.curated,
                format_list_col=True,
            )
            export_tools_to_tsv(
                tools_wo_biotools,
                args.wo_biotools,
                format_list_col=True,
                to_keep_columns=["Suite ID", "Homepage", "Suite source"],
            )
            export_tools_to_tsv(
                tools_with_biotools,
                args.w_biotools,
                format_list_col=True,
                to_keep_columns=["Suite ID", "bio.tool name", "EDAM operations", "EDAM topics"],
            )
        else:
            # if there are no ts filtered tools
            print("No tools left after curation")

    elif args.command == "popLabSection":
        lab_section = shared.load_yaml(args.lab)
        top_tools_per_category = extract_top_tools_per_category(args.curated)
        lab_section = fill_lab_tool_section(lab_section, top_tools_per_category)

        with open(args.lab, "w") as lab_f:
            ruamelyaml().dump(lab_section, lab_f)

    elif args.command == "getLabTools":
        missing_tools = extract_missing_tools_per_servers(args.curated)
        export_missing_tools(missing_tools, args.tools)
