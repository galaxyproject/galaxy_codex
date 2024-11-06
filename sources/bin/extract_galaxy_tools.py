#!/usr/bin/env python
import argparse
import base64
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

project_path = Path(__file__).resolve().parent.parent  # galaxy_tool_extractor folder
usage_stats_path = project_path.joinpath("data", "usage_stats", "usage_stats_31.08.2024")
conf_path = project_path.joinpath("data", "conf.yml")
public_servers = project_path.joinpath("data", "available_public_servers.csv")


GALAXY_TOOL_STATS = {}
for server in ["eu", "org", "org.au"]:
    GALAXY_TOOL_STATS[f"Suite users (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_5y_until_2024.08.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite users (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_until_2024.08.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_5y_until_2024.08.31.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_until_2024.08.31.csv"
    )

# all columns that contain the text will be summed up to a new column with summed up stats
GALAXY_TOOL_STATS_SUM = [
    "Suite users (last 5 years)",
    "Suite users",
    "Suite runs (last 5 years)",
    "Suite runs",
]

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


def get_tool_stats_from_stats_file(tool_stats_df: pd.DataFrame, tool_ids: List[str]) -> int:
    """
    Computes a count for tool stats based on the tool id. The counts for local and toolshed installed tools are
    aggregated. All tool versions are also aggregated.


    :param tools_stats_df: df with tools stats in the form `toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter,3394539`
    :tool_ids: tool ids to get statistics for and aggregate
    """

    # extract tool id
    tool_stats_df["Suite ID"] = tool_stats_df["tool_name"].apply(get_last_url_position)
    # print(tool_stats_df["Suite ID"].to_list())

    agg_count = 0
    for tool_id in tool_ids:
        if tool_id in tool_stats_df["Suite ID"].to_list():

            # get stats of the tool for all versions
            counts = tool_stats_df.loc[(tool_stats_df["Suite ID"] == tool_id), "count"]
            agg_versions = counts.sum()

            # aggregate all counts for all tools in the suite
            agg_count += agg_versions

    return int(agg_count)


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

        # the Galaxy tools need to be formatted for the add_instances_to_table to work
        df["Tool IDs"] = shared.format_list_column(df["Tool IDs"])

    if to_keep_columns is not None:
        df = df[to_keep_columns]

    df.to_csv(output_fp, sep="\t", index=False)


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


def filter_tools(
    tools: List[Dict],
    ts_cat: List[str],
    tool_status: Dict,
) -> list:
    """
    Filter tools for specific ToolShed categories

    :param tools: dictionary with tools and their metadata
    :param ts_cat: list of ToolShed categories to keep in the extraction
    :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
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
    tool_status: Dict,
) -> tuple:
    """
    Filter tools for specific ToolShed categories

    :param tools: dictionary with tools and their metadata
    :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
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


def get_tools(repo_list: list, edam_ontology: dict) -> List[Dict]:
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
            tool[name] = get_tool_stats_from_stats_file(tool_stats_df, tool["Tool IDs"])

        # sum up tool stats
        for names_to_match in GALAXY_TOOL_STATS_SUM:
            summed_stat = 0
            for col_name in tool.keys():
                if names_to_match in col_name:
                    summed_stat += tool[col_name]
            tool[f"{names_to_match} on main servers"] = summed_stat

    return tools


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
        tools = get_tools(repo_list, edam_ontology)
        export_tools_to_json(tools, args.all)
        export_tools_to_tsv(tools, args.all_tsv, format_list_col=True)

    elif args.command == "filter":
        with Path(args.all).open() as f:
            tools = json.load(f)
        # get categories and tools to exclude
        categories = shared.read_file(args.categories)
        # get status if file provided
        if args.status:
            status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
        else:
            status = {}
        # filter tool lists
        filtered_tools = filter_tools(tools, categories, status)
        if filtered_tools:
            export_tools_to_json(filtered_tools, args.filtered)
            export_tools_to_tsv(
                filtered_tools,
                args.tsv_filtered,
                format_list_col=True,
                to_keep_columns=["Suite ID", "Description", "To keep", "Deprecated"],
            )
        else:
            # if there are no ts filtered tools
            print(f"No tools found for category {args.filtered}")

    elif args.command == "curate":
        with Path(args.filtered).open() as f:
            tools = json.load(f)
        try:
            status = pd.read_csv(args.status, sep="\t", index_col=0).to_dict("index")
        except Exception as ex:
            print(f"Failed to load tool_status.tsv file with:\n{ex}")
            print("Not assigning tool status for this community !")
            status = {}

        curated_tools, tools_wo_biotools, tools_with_biotools = curate_tools(tools, status)
        if curated_tools:
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
