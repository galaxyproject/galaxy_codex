#!/usr/bin/env python

import argparse
import base64
import json
import sys
import time
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
import yaml
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from owlready2 import get_ontology

# Config variables
BIOTOOLS_API_URL = "https://bio.tools"
# BIOTOOLS_API_URL = "https://130.226.25.21"

USEGALAXY_SERVER_URLS = {
    "UseGalaxy.org (Main)": "https://usegalaxy.org",
    "UseGalaxy.org.au": "https://usegalaxy.org.au",
    "UseGalaxy.eu": "https://usegalaxy.eu",
    "UseGalaxy.fr": "https://usegalaxy.fr",
}

project_path = Path(__file__).resolve().parent.parent  # galaxy_tool_extractor folder
usage_stats_path = project_path.joinpath("data", "usage_stats")
conf_path = project_path.joinpath("data", "conf.yml")
public_servers = project_path.joinpath("data", "available_public_servers.csv")

GALAXY_TOOL_STATS = {
    "No. of tool users (2022-2023) (usegalaxy.eu)": usage_stats_path.joinpath("tool_usage_per_user_2022_23_EU.csv"),
    "Total tool usage (usegalaxy.eu)": usage_stats_path.joinpath("total_tool_usage_EU.csv"),
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


# def add_tool_stats_to_tools(tools_df: pd.DataFrame, tool_stats_path: Path, column_name: str) -> pd.DataFrame:
#     """
#     Adds the usage statistics to the community tool table

#     :param tool_stats_path: path to the table with
#         the tool stats (csv,
#         must include "tool_name" and "count")
#     :param tools_path: path to the table with
#         the tools (csv,
#         must include "Galaxy wrapper id")
#     :param output_path: path to store the new table
#     :param column_name: column to add for the tool stats,
#         different columns could be added for the main servers
#     """

#     # parse csvs
#     tool_stats_df = pd.read_csv(tool_stats_path)

#     # extract tool id
#     tool_stats_df["Galaxy wrapper id"] = tool_stats_df["tool_name"].apply(get_last_url_position)

#     # group local and toolshed tools into one entry
#     grouped_tool_stats_tools = tool_stats_df.groupby("Galaxy wrapper id", as_index=False)["count"].sum()

#     # keep all rows of the tools table (how='right'), also for those where no stats are available
#     community_tool_stats = pd.merge(grouped_tool_stats_tools, tools_df, how="right", on="Galaxy wrapper id")
#     community_tool_stats.rename(columns={"count": column_name}, inplace=True)

#     return community_tool_stats


def get_tool_stats_from_stats_file(tool_stats_df: pd.DataFrame, tool_ids: str) -> pd.DataFrame:
    """
    Adds the usage statistics to the community tool table

    :param tools_stats_df: df with tools stats in the form `toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter,3394539`
    :tool_ids: tool ids to get statistics for and aggregate
    """

    # extract tool id
    tool_stats_df["Galaxy wrapper id"] = tool_stats_df["tool_name"].apply(get_last_url_position)
    # print(tool_stats_df["Galaxy wrapper id"].to_list())

    agg_count = 0
    for tool_id in tool_ids:
        if tool_id in tool_stats_df["Galaxy wrapper id"].to_list():

            # get stats of the tool for all versions
            counts = tool_stats_df.loc[(tool_stats_df["Galaxy wrapper id"] == tool_id), "count"]
            agg_versions = counts.sum()

            # aggregate all counts for all tools in the suite
            agg_count += agg_versions

    return agg_count


# def add_usage_stats_for_all_server(tools_df: pd.DataFrame) -> pd.DataFrame:
#     for column, path in GALAXY_TOOL_STATS.items():
#         tools_df = add_tool_stats_to_tools(tools_df, path, column)
#     return tools_df


def read_file(filepath: Optional[str]) -> List[str]:
    """
    Read an optional file with 1 element per line

    :param filepath: path to a file
    """
    if filepath is None:
        return []
    fp = Path(filepath)
    if fp.is_file():
        with fp.open("r") as f:
            return [x.rstrip() for x in f.readlines()]
    else:
        return []


def get_string_content(cf: ContentFile) -> str:
    """
    Get string of the content from a ContentFile

    :param cf: GitHub ContentFile object
    """
    return base64.b64decode(cf.content).decode("utf-8")


def get_tool_github_repositories(
    g: Github, repository_list: Optional[str], run_test: bool, add_extra_repositories: bool = True
) -> List[str]:
    """
    Get list of tool GitHub repositories to parse

    :param g: GitHub instance
    :param repository_list: The selection to use from the repository (needed to split the process for CI jobs)
    :param run_test: for testing only parse the repository
    """

    if run_test:
        return ["https://github.com/paulzierep/Galaxy-Tool-Metadata-Extractor-Test-Wrapper"]

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

    # the folder of the tool is used as Galaxy wrapper id (maybe rather use the .shed.yml name)
    metadata = {
        "Galaxy wrapper id": tool.name,
        "Galaxy tool ids": [],
        "Description": None,
        "bio.tool id": None,
        "bio.tool ids": set(),  # keep track of multi IDs
        "biii": None,
        "bio.tool name": None,
        "bio.tool description": None,
        "EDAM operation": [],
        "EDAM topic": [],
        "Status": "To update",
        "Source": None,
        "ToolShed categories": [],
        "ToolShed id": None,
        "Galaxy wrapper owner": None,
        "Galaxy wrapper source": None,  # this is what it written in the .shed.yml
        "Galaxy wrapper parsed folder": None,  # this is the actual parsed file
        "Galaxy wrapper version": None,
        "Conda id": None,
        "Conda version": None,
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
        metadata["ToolShed id"] = get_shed_attribute("name", yaml_content, None)
        metadata["Galaxy wrapper owner"] = get_shed_attribute("owner", yaml_content, None)
        metadata["Galaxy wrapper source"] = get_shed_attribute("remote_repository_url", yaml_content, None)
        if "homepage_url" in yaml_content:
            metadata["Source"] = yaml_content["homepage_url"]
        metadata["ToolShed categories"] = get_shed_attribute("categories", yaml_content, [])
        if metadata["ToolShed categories"] is None:
            metadata["ToolShed categories"] = []

    # get all files in the folder
    file_list = repo.get_contents(tool.path)
    assert isinstance(file_list, list)

    # store the github location where the folder was parsed
    metadata["Galaxy wrapper parsed folder"] = tool.html_url

    # find and parse macro file
    for file in file_list:
        if "macro" in file.name and file.name.endswith("xml"):
            file_content = get_string_content(file)
            root = et.fromstring(file_content)
            for child in root:
                if "name" in child.attrib:
                    if child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@":
                        metadata["Galaxy wrapper version"] = child.text
                    elif child.attrib["name"] == "requirements":
                        metadata["Conda id"] = get_conda_package(child)
                    # bio.tools
                    biotools = get_xref(child, attrib_type="bio.tools")
                    if biotools is not None:
                        metadata["bio.tool id"] = biotools
                        metadata["bio.tool ids"].add(biotools)
                    # biii
                    biii = get_xref(child, attrib_type="biii")
                    if biii is not None:
                        metadata["biii"] = biii

    # parse XML file and get meta data from there
    for file in file_list:
        if file.name.endswith("xml") and "macro" not in file.name:
            file_content = get_string_content(file)
            try:
                root = et.fromstring(file_content)
            except Exception:
                print(file_content, sys.stderr)
            else:
                # version
                if metadata["Galaxy wrapper version"] is None:
                    if "version" in root.attrib:
                        version = root.attrib["version"]
                        if "VERSION@" not in version:
                            metadata["Galaxy wrapper version"] = version
                        else:
                            macros = root.find("macros")
                            if macros is not None:
                                for child in macros:
                                    if "name" in child.attrib and (
                                        child.attrib["name"] == "@TOOL_VERSION@" or child.attrib["name"] == "@VERSION@"
                                    ):
                                        metadata["Galaxy wrapper version"] = child.text

                # bio.tools
                biotools = get_xref(root, attrib_type="bio.tools")
                if biotools is not None:
                    metadata["bio.tool id"] = biotools
                    metadata["bio.tool ids"].add(biotools)

                # biii
                if metadata["biii"] is None:
                    biii = get_xref(root, attrib_type="biii")
                    if biii is not None:
                        metadata["biii"] = biii

                # conda package
                if metadata["Conda id"] is None:
                    reqs = get_conda_package(root)
                    if reqs is not None:
                        metadata["Conda id"] = reqs
                # tool ids
                if "id" in root.attrib:
                    metadata["Galaxy tool ids"].append(root.attrib["id"])

    # get latest conda version and compare to the wrapper version
    if metadata["Conda id"] is not None:
        r = requests.get(f'https://api.anaconda.org/package/bioconda/{metadata["Conda id"]}')
        if r.status_code == requests.codes.ok:
            conda_info = r.json()
            if "latest_version" in conda_info:
                metadata["Conda version"] = conda_info["latest_version"]
                if metadata["Conda version"] == metadata["Galaxy wrapper version"]:
                    metadata["Status"] = "Up-to-date"

    # get bio.tool information
    if metadata["bio.tool id"] is not None:
        r = requests.get(f'{BIOTOOLS_API_URL}/api/tool/{metadata["bio.tool id"]}/?format=json')
        if r.status_code == requests.codes.ok:
            biotool_info = r.json()
            if "function" in biotool_info:
                for func in biotool_info["function"]:
                    if "operation" in func:
                        for op in func["operation"]:
                            metadata["EDAM operation"].append(op["term"])
            if "topic" in biotool_info:
                for t in biotool_info["topic"]:
                    metadata["EDAM topic"].append(t["term"])
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


def format_list_column(col: pd.Series) -> pd.Series:
    """
    Format a column that could be a list before exporting
    """
    return col.apply(lambda x: ", ".join(str(i) for i in x))


def export_tools_to_json(tools: List[Dict], output_fp: str) -> None:
    """
    Export tool metadata to TSV output file

    :param tools: dictionary with tools
    :param output_fp: path to output file
    """
    with Path(output_fp).open("w") as f:
        json.dump(tools, f, default=list, indent=4)


def export_tools_to_tsv(
    tools: List[Dict], output_fp: str, format_list_col: bool = False, add_usage_stats: bool = False
) -> None:
    """
    Export tool metadata to TSV output file

    :param tools: dictionary with tools
    :param output_fp: path to output file
    :param format_list_col: boolean indicating if list columns should be formatting
    """
    df = pd.DataFrame(tools).sort_values("Galaxy wrapper id")
    if format_list_col:
        df["ToolShed categories"] = format_list_column(df["ToolShed categories"])
        df["EDAM operation"] = format_list_column(df["EDAM operation"])
        df["EDAM topic"] = format_list_column(df["EDAM topic"])

        df["EDAM operation (no superclasses)"] = format_list_column(df["EDAM operation (no superclasses)"])
        df["EDAM topic (no superclasses)"] = format_list_column(df["EDAM topic (no superclasses)"])

        df["bio.tool ids"] = format_list_column(df["bio.tool ids"])

        # the Galaxy tools need to be formatted for the add_instances_to_table to work
        df["Galaxy tool ids"] = format_list_column(df["Galaxy tool ids"])

    # if add_usage_stats:
    #     df = add_usage_stats_for_all_server(df)

    df.to_csv(output_fp, sep="\t", index=False)


def filter_tools(
    tools: List[Dict],
    ts_cat: List[str],
    tool_status: Dict,
) -> tuple:
    """
    Filter tools for specific ToolShed categories and add information if to keep or to exclude

    :param tools: dictionary with tools and their metadata
    :param ts_cat: list of ToolShed categories to keep in the extraction
    :param tool_status: dictionary with tools and their 2 status: Keep and Deprecated
    """
    ts_filtered_tools = []
    filtered_tools = []
    for tool in tools:
        # filter ToolShed categories and leave function if not in expected categories
        if check_categories(tool["ToolShed categories"], ts_cat):
            name = tool["Galaxy wrapper id"]
            tool["Reviewed"] = name in tool_status
            keep = None
            deprecated = None
            if name in tool_status:
                keep = tool_status[name][1]
                deprecated = tool_status[name][2]
            tool["Deprecated"] = deprecated
            if keep:  # only add tools that are manually marked as to keep
                filtered_tools.append(tool)
            tool["To keep"] = keep
            ts_filtered_tools.append(tool)
    return ts_filtered_tools, filtered_tools


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy tools from GitHub repositories together with biotools and conda metadata"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tools
    extractools = subparser.add_parser("extractools", help="Extract tools")
    extractools.add_argument("--api", "-a", required=True, help="GitHub access token")
    extractools.add_argument("--all-tools-json", "-j", required=True, help="Filepath to JSON with all extracted tools")
    extractools.add_argument("--all-tools", "-o", required=True, help="Filepath to TSV with all extracted tools")
    extractools.add_argument(
        "--planemo-repository-list",
        "-pr",
        required=False,
        help="Repository list to use from the planemo-monitor repository",
    )
    extractools.add_argument(
        "--avoid-extra-repositories",
        "-e",
        action="store_true",
        default=False,
        required=False,
        help="Do not parse extra repositories in conf file",
    )
    extractools.add_argument(
        "--test",
        "-t",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test case using only the repository: https://github.com/TGAC/earlham-galaxytools",
    )

    # Filter tools
    filtertools = subparser.add_parser("filtertools", help="Filter tools")
    filtertools.add_argument(
        "--tools",
        "-i",
        required=True,
        help="Filepath to JSON with all extracted tools, generated by extractools command",
    )
    filtertools.add_argument(
        "--ts-filtered-tools",
        "-t",
        required=True,
        help="Filepath to TSV with tools filtered based on ToolShed category",
    )
    filtertools.add_argument(
        "--filtered-tools",
        "-f",
        required=True,
        help="Filepath to TSV with tools filtered based on ToolShed category and manual curation",
    )
    filtertools.add_argument(
        "--categories",
        "-c",
        help="Path to a file with ToolShed category to keep in the extraction (one per line)",
    )
    filtertools.add_argument(
        "--status",
        "-s",
        help="Path to a TSV file with tool status - 3 columns: ToolShed ids of tool suites, Boolean with True to keep and False to exclude, Boolean with True if deprecated and False if not",
    )
    args = parser.parse_args()

    if args.command == "extractools":
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

        #######################################################
        # add additional information to the List[Dict] object
        #######################################################

        edam_ontology = get_ontology("https://edamontology.org/EDAM_1.25.owl").load()

        for tool in tools:

            # add EDAM terms without superclass
            tool["EDAM operation (no superclasses)"] = reduce_ontology_terms(
                tool["EDAM operation"], ontology=edam_ontology
            )
            tool["EDAM topic (no superclasses)"] = reduce_ontology_terms(tool["EDAM topic"], ontology=edam_ontology)

            # add availability for UseGalaxy servers
            for name, url in USEGALAXY_SERVER_URLS.items():
                tool[f"Available on {name}"] = check_tools_on_servers(tool["Galaxy tool ids"], url)
            # add availability for all UseGalaxy servers
            for name, url in USEGALAXY_SERVER_URLS.items():
                tool[f"Tools available on {name}"] = check_tools_on_servers(tool["Galaxy tool ids"], url)

            # add all other available servers
            public_servers_df = pd.read_csv(public_servers, sep="\t")
            for _index, row in public_servers_df.iterrows():
                name = row["name"]

                if name.lower() not in [
                    n.lower() for n in USEGALAXY_SERVER_URLS.keys()
                ]:  # do not query UseGalaxy servers again

                    url = row["url"]
                    tool[f"Tools available on {name}"] = check_tools_on_servers(tool["Galaxy tool ids"], url)

            # add tool stats
            for name, path in GALAXY_TOOL_STATS.items():
                tool_stats_df = pd.read_csv(path)
                tool[name] = get_tool_stats_from_stats_file(tool_stats_df, tool["Galaxy tool ids"])

        export_tools_to_json(tools, args.all_tools_json)
        export_tools_to_tsv(tools, args.all_tools, format_list_col=True, add_usage_stats=True)

    elif args.command == "filtertools":
        with Path(args.tools).open() as f:
            tools = json.load(f)
        # get categories and tools to exclude
        categories = read_file(args.categories)
        try:
            status = pd.read_csv(args.status, sep="\t", index_col=0, header=None).to_dict("index")
        except Exception as ex:
            print(f"Failed to load tool_status.tsv file with:\n{ex}")
            print("Not assigning tool status for this community !")
            status = {}

        # filter tool lists
        ts_filtered_tools, filtered_tools = filter_tools(tools, categories, status)

        export_tools_to_tsv(ts_filtered_tools, args.ts_filtered_tools, format_list_col=True)

        # if there are no filtered tools return the ts filtered tools
        if filtered_tools:
            export_tools_to_tsv(filtered_tools, args.filtered_tools, format_list_col=True)
        else:
            export_tools_to_tsv(ts_filtered_tools, args.filtered_tools, format_list_col=True)
