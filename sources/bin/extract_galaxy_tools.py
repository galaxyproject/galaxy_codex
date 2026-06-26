#!/usr/bin/env python
import argparse
import json
import re
import subprocess
import sys
import traceback
import xml.etree.ElementTree as et
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor,
)
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
import requests
import shared
import yaml
from extract_galaxy_workflows import Workflows
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

stat_usage_date = "2025.08.31"
project_path = Path(__file__).resolve().parent.parent  # galaxy_tool_extractor folder
usage_stats_path = project_path.joinpath("data", "usage_stats", f"usage_stats_{ stat_usage_date }")
conf_path = project_path.joinpath("data", "conf.yml")
public_servers = project_path.joinpath("data", "available_public_servers.csv")


GALAXY_TOOL_STATS = {}
for server in ["eu", "org", "org.au", "fr"]:
    GALAXY_TOOL_STATS[f"Suite users (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_5y_until_{ stat_usage_date }.csv"
    )
    GALAXY_TOOL_STATS[f"Suite users (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_users_until_{ stat_usage_date }.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (last 5 years) (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_5y_until_{ stat_usage_date }.csv"
    )
    GALAXY_TOOL_STATS[f"Suite runs (usegalaxy.{ server })"] = usage_stats_path.joinpath(
        f"{ server }/tool_usage_until_{ stat_usage_date }.csv"
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


def get_tool_repositories(
    clone_dir: Path,
    repository_list: Optional[str] = None,
    run_test: bool = False,
    test_repository: str = "https://github.com/paulzierep/Galaxy-Tool-Metadata-Extractor-Test-Wrapper",
    add_extra_repositories: bool = True,
) -> List[str]:
    """
    Get list of tool GitHub repositories to parse by cloning planemo-monitor locally.

    :param clone_dir: directory to clone into
    :param repository_list: optional specific .list file to use (for CI splits)
    :param run_test: if True, return only the test repository
    :param test_repository: URL of the test repository
    :param add_extra_repositories: if True, add extra repos from config
    """
    if run_test:
        return [test_repository]

    planemo_monitor_url = "https://github.com/galaxyproject/planemo-monitor"
    dest = clone_dir / "planemo-monitor"
    if dest.exists():
        print(f"Updating planemo-monitor in {dest} ...")
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning planemo-monitor into {dest} ...")
        subprocess.run(["git", "clone", "--depth", "1", planemo_monitor_url, str(dest)], check=True)

    repo_list: List[str] = []
    for i in range(1, 5):
        list_file = f"repositories0{i}.list"
        list_path = dest / list_file
        if not list_path.exists():
            continue
        if repository_list and repository_list != list_file:
            continue
        lines = list_path.read_text().splitlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                repo_list.append(line)

    if add_extra_repositories and "extra-repositories" in configs:
        repo_list += configs["extra-repositories"]

    print("Parsing repositories from:")
    for r in repo_list:
        print("\t", r)

    return repo_list


def _repo_name_from_url(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) >= 3:
        org = parts[-2]
        repo = parts[-1]
        return f"{org}-{repo}"
    return parts[-1]


def _normalize_repo_url(url: str) -> str:
    """Normalize a repo URL for deduplication."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url


def clone_repositories(repo_list: List[str], clone_dir: Path, depth: Optional[int] = 1) -> List[Tuple[str, Path]]:
    """
    Clone or update GitHub repositories into a local directory.

    Duplicate URLs are skipped. Uses shallow clones by default for CI efficiency.

    :param repo_list: list of repository URLs
    :param clone_dir: directory to clone into
    :param depth: git clone depth (None for full history, default 1 for shallow)
    :returns: list of (original_url, local_path) tuples
    """
    clone_dir.mkdir(parents=True, exist_ok=True)
    results: List[Tuple[str, Path]] = []
    seen: set = set()
    total = len(repo_list)
    for i, url in enumerate(repo_list, 1):
        normalized = _normalize_repo_url(url)
        if normalized in seen:
            print(f"  [{i}/{total}] {url} (duplicate, skipped)", flush=True)
            continue
        seen.add(normalized)

        print(f"  [{i}/{total}] {url}", flush=True)
        name = _repo_name_from_url(url)
        dest = clone_dir / name
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"])
        else:
            clone_cmd = ["git", "clone"]
            if depth is not None:
                clone_cmd.extend(["--depth", str(depth)])
            clone_cmd.extend([url, str(dest)])
            subprocess.run(clone_cmd)
        results.append((url, dest))
    return results


def get_first_commit_for_local_folder(repo_path: Path, tool_rel_path: str) -> str:
    """
    Get the date of the first commit in the tool folder using git log.
    If the clone is shallow, try to fetch more history for the path.
    """

    def _git_log() -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--reverse", "--format=%ad", "--date=short", tool_rel_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:
                return lines[0]
        except Exception:
            pass
        return ""

    date = _git_log()
    if not date and (repo_path / ".git" / "shallow").exists():
        try:
            subprocess.run(
                ["git", "fetch", "--deepen", "1000", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            date = _git_log()
        except Exception:
            pass
    return date


def get_tool_metadata_from_local(tool_path: Path, repo_path: Path, repo_url: str = "") -> Optional[Dict[str, Any]]:
    """
    Get tool metadata from a locally cloned tool directory.
    Uses Galaxy's xml_macros to expand macros before parsing.
    """
    if not tool_path.is_dir():
        return None

    metadata: Dict[str, Any] = {
        "Suite ID": None,
        "Tool IDs": [],
        "Tool output formats": [],
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
        "Suite source": None,
        "Suite parsed folder": None,
        "bio.tool ID": None,
        "bio.tool name": None,
        "bio.tool description": None,
        "biii ID": None,
    }

    # extract .shed.yml
    shed_path = tool_path / ".shed.yml"
    if not shed_path.exists():
        return None
    with shed_path.open() as fh:
        shed_content = yaml.load(fh, Loader=yaml.FullLoader)
    metadata["Description"] = get_shed_attribute("description", shed_content, None)
    if metadata["Description"] is None:
        metadata["Description"] = get_shed_attribute("long_description", shed_content, None)
    if metadata["Description"] is not None:
        metadata["Description"] = metadata["Description"].replace("\n", "")
    metadata["Suite ID"] = get_shed_attribute("name", shed_content, None)
    metadata["Suite owner"] = get_shed_attribute("owner", shed_content, None)
    metadata["Suite source"] = get_shed_attribute("remote_repository_url", shed_content, None)
    if "homepage_url" in shed_content:
        metadata["Homepage"] = shed_content["homepage_url"]
    metadata["ToolShed categories"] = get_shed_attribute("categories", shed_content, [])
    if metadata["ToolShed categories"] is None:
        metadata["ToolShed categories"] = []

    # build repo URL for parsed folder
    tool_rel_path = str(tool_path.relative_to(repo_path))
    if repo_url:
        metadata["Suite parsed folder"] = repo_url.rstrip("/") + "/tree/master/" + tool_rel_path
    else:
        metadata["Suite parsed folder"] = str(tool_path)

    # first commit date
    metadata["Suite first commit date"] = get_first_commit_for_local_folder(repo_path, tool_rel_path)

    # parse macro files for token values, requirements, xrefs
    macro_tokens: Dict[str, str] = {}
    for entry in tool_path.iterdir():
        if "macro" in entry.name and entry.name.endswith("xml"):
            try:
                root = et.fromstring(entry.read_text())
                for child in root:
                    if "name" in child.attrib:
                        token_name = child.attrib["name"]
                        if child.text:
                            macro_tokens[token_name] = child.text
                        if token_name in ("@TOOL_VERSION@", "@VERSION@"):
                            metadata["Suite version"] = child.text
                        elif token_name == "requirements":
                            metadata["Suite conda package"] = get_conda_package(child)
                        biotools = get_xref(child, attrib_type="bio.tools")
                        if biotools is not None:
                            metadata["bio.tool ID"] = biotools
                        biii = get_xref(child, attrib_type="biii")
                        if biii is not None:
                            metadata["biii ID"] = biii
            except Exception:
                print(traceback.format_exc())

    def _resolve_macros(text: str) -> str:
        return re.sub(r"@(\w+)@", lambda m: macro_tokens.get(m.group(0), m.group(0)), text)

    # parse each tool XML with macro expansion
    for entry in sorted(tool_path.iterdir()):
        if entry.name.endswith("xml") and "macro" not in entry.name:
            try:
                tree = _load_tool_xml_with_macros(entry)
                if tree is None:
                    tree = _load_tool_xml_fallback(entry)
                if tree is None:
                    continue
                root = tree.getroot()
            except Exception:
                print(traceback.format_exc())
                continue

            # version
            if metadata["Suite version"] is None and "version" in root.attrib:
                raw_version = root.attrib["version"]
                metadata["Suite version"] = _resolve_macros(raw_version)

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

            # tool outputs
            formats = get_tool_outputs(root)
            for fmt in formats:
                if fmt not in metadata["Tool output formats"]:
                    metadata["Tool output formats"].append(fmt)

    # strip +galaxy suffix from version
    if metadata["Suite version"] is not None:
        metadata["Suite version"] = re.sub(r"\+galaxy\d+$", "", metadata["Suite version"])

    # set suite ID fallback
    if metadata["Suite ID"] is None:
        if metadata["bio.tool ID"] is not None:
            metadata["Suite ID"] = metadata["bio.tool ID"].lower()
        else:
            metadata["Suite ID"] = tool_path.name

    # get latest conda version
    if metadata["Suite conda package"] is not None:
        r = requests.get(f'https://api.anaconda.org/package/bioconda/{metadata["Suite conda package"]}', timeout=10)
        if r.status_code == requests.codes.ok:
            conda_info = r.json()
            if "latest_version" in conda_info:
                metadata["Latest suite conda package version"] = conda_info["latest_version"]
                if metadata["Latest suite conda package version"] == metadata["Suite version"]:
                    metadata["Suite version status"] = "Up-to-date"

    # get bio.tool information
    if metadata["bio.tool ID"] is not None:
        r = requests.get(f'{BIOTOOLS_API_URL}/api/tool/{metadata["bio.tool ID"]}/?format=json', timeout=10)
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


def _load_tool_xml_with_macros(xml_path: Path) -> Optional[Any]:
    """Try to load and expand macros using Galaxy's xml_macros (galaxy-util)."""
    try:
        from galaxy.util.xml_macros import load as _xml_macros_load

        return _xml_macros_load(str(xml_path))
    except Exception:
        return None


def _load_tool_xml_fallback(xml_path: Path) -> Optional[Any]:
    """Fallback: parse XML directly without macro expansion."""
    try:
        import xml.etree.ElementTree as _et

        tree = _et.parse(str(xml_path))
        return tree
    except Exception:
        return None


def parse_tools_from_local(repo_path: Path, workers: int = 1, repo_url: str = "") -> List[Dict[str, Any]]:
    """
    Parse tools from a locally cloned repository.
    """
    tools: List[Dict[str, Any]] = []

    # look for tool folders in tools/, wrappers/, tool_collections/
    search_dirs = ["tools", "wrappers", "tool_collections"]
    found = False
    for sd in search_dirs:
        candidate = repo_path / sd
        if candidate.is_dir():
            found = True
            items = [p for p in sorted(candidate.iterdir()) if p.is_dir()]
            # collect all tool paths (handle nested .shed.yml)
            tool_paths: List[Path] = []
            for item in items:
                if (item / ".shed.yml").exists():
                    tool_paths.append(item)
                else:
                    for sub in sorted(item.iterdir()):
                        if sub.is_dir():
                            tool_paths.append(sub)

            total = len(tool_paths)
            print(f"    Parsing {total} tools...", flush=True)

            def _process_one(p: Path) -> Optional[Dict[str, Any]]:
                return get_tool_metadata_from_local(p, repo_path, repo_url=repo_url)

            if workers > 1:
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    fut_to_path = {executor.submit(_process_one, p): p for p in tool_paths}
                    for idx, future in enumerate(as_completed(fut_to_path), 1):
                        path = fut_to_path[future]
                        print(f"    [{idx}/{total}] {path.name}", flush=True)
                        try:
                            metadata = future.result()
                            if metadata is not None:
                                tools.append(metadata)
                        except Exception:
                            print(f"      Error parsing {path.name}", file=sys.stderr)
                            print(traceback.format_exc())
            else:
                for idx, p in enumerate(tool_paths, 1):
                    print(f"    [{idx}/{total}] {p.name}", flush=True)
                    try:
                        metadata = _process_one(p)
                        if metadata is not None:
                            tools.append(metadata)
                    except Exception:
                        print(f"      Error parsing {p.name}", file=sys.stderr)
                        print(traceback.format_exc())

    if not found:
        print("No tool folder found", file=sys.stderr)

    return tools


def get_tool_outputs(el: et.Element) -> list[str]:
    """
    Find tool outputs by format from the outputs XML.
    Only uses the output defined in format of the outputs xml.
    Not implemented: Outputs that use format from input. Could be done but requires macro extension.
    Returns list of formats.

    :param el: Element object
    """

    outputs = el.find("outputs")

    formats: list[str] = []

    outputs = el.find("outputs")
    if outputs is not None:
        for output in outputs.findall("data"):
            fmt = output.attrib.get("format")
            if fmt:
                formats.append(fmt)

    return formats


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


@lru_cache  # need to run this for each suite, so just cache it
def get_all_installed_tool_ids_on_server(galaxy_url: str) -> List[str]:
    """
    Get all tool ids from a Galaxy server

    :param galaxy_url: URL of Galaxy instance
    """
    galaxy_url = galaxy_url.rstrip("/")
    base_url = f"{galaxy_url}/api"

    try:
        r = requests.get(f"{base_url}/tools", params={"in_panel": False}, timeout=30)
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

    if tools:  # Only proceed if 'tools' is not empty
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
            df["Tool output formats"] = shared.format_list_column(df["Tool output formats"])
        if to_keep_columns is not None:
            df = df[to_keep_columns]
    else:  # Create a DataFrame with the specified headers and save it
        df = pd.DataFrame(columns=["Suite ID", "bio.tool name", "EDAM operations", "EDAM topics"])

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

    # Some tools are not associated with EDAM operations and therefore not shown in the table even if they are used a lot.
    # To avoid that, we create a new category "No associated EDAM operation"

    # Step 0 : Add the string "No associated EDAM operation" in all the empty cells of the "EDAM operations" column
    tools["EDAM operations"] = tools["EDAM operations"].fillna("No associated EDAM operation").astype(str)

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
        df_unique.sort_values(by=["Category", count_column], ascending=[True, False])
        .groupby("Category", as_index=False)
        .head(top_tool_nb)
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
            wrapper_id = row["Suite ID"]

            # Split the tool IDs by comma if it's a valid string, otherwise handle as an empty list
            tool_ids_list = tool_ids.split(",") if isinstance(tool_ids, str) else []

            # Create the base URL template for each tool link
            url_template = "/?tool_id={tool_id}"

            # Build HTML list items with links
            description += "\n<ul>\n"
            for tool_id in tool_ids_list:
                tool_id = tool_id.strip()  # Trim whitespace
                # Format the URL with owner, wrapper ID, and tool ID
                url = "{{ galaxy_base_url }}" + url_template.format(tool_id=tool_id)
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
                "heading_md": f"Top 10 most used tools* for the EDAM operation: {group_id} <br> *based on usage statistics from Galaxy’s main servers over the last five years",
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

    # Add a new column with all zeros, this will create a Local_Galaxy.yml that has all tools of the Lab
    tools["Number of tools on Local_Galaxy"] = 0

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


def export_tools_to_yml(tools: List[Dict], yml_output_path: str) -> None:
    """
    Export to YAML for rendering on the website
    """
    for tool in tools:
        availability = {}
        for field in tool:
            field_value = tool[field]
            availability_match_string = "[Nn]umber of tools"
            if re.search(availability_match_string, field):
                instance_match_string = "[Uu]se[Gg]alaxy\.[a-z]{2}"
                if re.search(instance_match_string, field):
                    match = re.search(instance_match_string, field)
                    if match:
                        field_name = match.group(0)
                        if field_value != 0:
                            availability[field_name] = field_value
        tool["availability"] = availability
    shared.export_to_yml(tools, yml_output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy tools from GitHub repositories together with biotools and conda metadata"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tools
    extract = subparser.add_parser("extract", help="Extract tools")
    extract.add_argument("--all", "-o", required=True, help="Filepath to JSON with all extracted tools")
    extract.add_argument("--all-tsv", "-j", required=True, help="Filepath to TSV with all extracted tools")
    extract.add_argument("--all-yml", "-y", required=True, help="Filepath to yml with all extracted tools")
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
    extract.add_argument(
        "--repo-dir",
        default="~/.galaxy_tool_repos",
        help="Directory to clone repositories into (default: ~/.galaxy_tool_repos)",
    )
    extract.add_argument(
        "--repo-url",
        action="append",
        dest="repo_urls",
        default=None,
        help="Specific repo URL(s) to process (can be specified multiple times). Overrides planemo-monitor list.",
    )
    extract.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for tool parsing (default: 1, sequential)",
    )
    extract.add_argument(
        "--clone-depth",
        type=int,
        default=None,
        help="Git clone depth for tool repositories (default: shallow=1; 0 for full history)",
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
    curatetools.add_argument("--yml", "-y", required=True, help="Filepath to yml with community extracted tools")

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
        repo_dir = Path(args.repo_dir).expanduser()
        if args.repo_urls:
            repo_list = args.repo_urls
            print("Using specified repositories:")
            for r in repo_list:
                print("\t", r)
        elif args.test:
            repo_list = get_tool_repositories(
                clone_dir=repo_dir,
                run_test=True,
                add_extra_repositories=False,
            )
        else:
            repo_list = get_tool_repositories(
                clone_dir=repo_dir,
                repository_list=args.planemo_repository_list,
                add_extra_repositories=not args.avoid_extra_repositories,
            )

        edam_ontology = get_ontology("https://edamontology.org/EDAM_1.25.owl").load()

        print(f"Cloning repositories into {repo_dir} ...")
        clone_depth = None if args.clone_depth == 0 else (args.clone_depth or 1)
        cloned = clone_repositories(repo_list, repo_dir, depth=clone_depth)
        tools: List[Dict] = []
        for url, repo_path in cloned:
            print(f"Parsing tools from: {url} ({repo_path})")
            tools.extend(parse_tools_from_local(repo_path, workers=args.workers, repo_url=url))
        if args.all_workflows:
            tools = add_workflow_ids_to_tools(tools, args.all_workflows)
        if args.all_tutorials:
            tools = add_tutorial_ids_to_tools(tools, args.all_tutorials)
        for tool in tools:
            tool.setdefault("Related Workflows", [])
            tool.setdefault("Related Tutorials", [])
        for tool in tools:
            tool["EDAM reduced operations"] = reduce_ontology_terms(tool["EDAM operations"], ontology=edam_ontology)
            tool["EDAM reduced topics"] = reduce_ontology_terms(tool["EDAM topics"], ontology=edam_ontology)
            if args.test:
                tool["Number of tools on UseGalaxy.eu"] = check_tools_on_servers(
                    tool["Tool IDs"], USEGALAXY_SERVER_URLS["UseGalaxy.eu"]
                )
            else:
                for name, url in USEGALAXY_SERVER_URLS.items():
                    tool[f"Number of tools on {name}"] = check_tools_on_servers(tool["Tool IDs"], url)
                public_servers_df = pd.read_csv(public_servers, sep="\t")
                for _index, row in public_servers_df.iterrows():
                    name = row["name"]
                    if name.lower() not in [n.lower() for n in USEGALAXY_SERVER_URLS.keys()]:
                        url = row["url"]
                        tool[f"Number of tools on {name}"] = check_tools_on_servers(tool["Tool IDs"], url)
            for name, path in GALAXY_TOOL_STATS.items():
                tool_stats_df = pd.read_csv(path)
                mode: Literal["sum", "max"]
                if "Suite users" in name:
                    mode = "max"
                else:
                    mode = "sum"
                tool[name] = get_tool_stats_from_stats_file(tool_stats_df, tool["Tool IDs"], mode=mode)
            tool = aggregate_tool_stats(tool, STATS_SUM)

        export_tools_to_json(tools, args.all)
        export_tools_to_tsv(tools, args.all_tsv, format_list_col=True)
        export_tools_to_yml(tools, args.all_yml)

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
            export_tools_to_yml(curated_tools, args.yml)
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
