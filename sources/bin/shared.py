#!/usr/bin/env python

import json
import time
from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

import pandas as pd
import requests
from github.ContentFile import ContentFile
from github.Repository import Repository
from requests.exceptions import ConnectionError


def get_first_commit_for_folder(tool: ContentFile, repo: Repository) -> str:
    """
    Get the date of the first commit in the tool folder

    :param commit_date: date of the first commit
    """

    # Get commits related to the specific folder
    commits = repo.get_commits(path=tool.path)

    # Get the last commit in the history (which is the first commit made to the folder)
    first_commit = commits.reversed[0]

    # Extract relevant information about the first commit
    commit_date = first_commit.commit.author.date.date()

    return str(commit_date)


def format_list_column(col: pd.Series) -> pd.Series:
    """
    Format a column that could be a list before exporting
    """
    return col.apply(lambda x: ", ".join(str(i) for i in x))


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


def export_to_json(data: List[Dict], output_fp: str) -> None:
    """
    Export to a JSON file
    """
    with Path(output_fp).open("w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def load_json(input_df: str) -> Dict:
    """
    Read a JSON file
    """
    with Path(input_df).open("r") as t:
        content = json.load(t)
    return content


def read_suite_per_tool_id(tool_fp: str) -> Dict:
    """
    Read the tool suite table and extract a dictionary per tool id
    """
    tool_suites = load_json(tool_fp)
    tools = {}
    for suite in tool_suites:
        for tool in suite["Suite ID"]:
            tools[tool] = {
                "Suite ID": suite["Suite ID"],
                "Suite owner": suite["Suite owner"],
                "EDAM operations": suite["EDAM operations"],
            }
    return tools


def get_request_json(url: str, headers: dict, retries: int = 3, delay: float = 2.0) -> dict:
    """
    Perform a GET request to retrieve JSON output from a specified URL, with retry on ConnectionError.

    :param url: URL to send the GET request to.
    :param headers: Headers to include in the GET request.
    :param retries: Number of retry attempts in case of a ConnectionError (default is 3).
    :param delay: Delay in seconds between retries (default is 2.0 seconds).
    :return: JSON response as a dictionary, or None if all retries fail.
    :raises ConnectionError: If all retry attempts fail due to a connection error.
    :raises SystemExit: For any other request-related errors.
    """
    attempt = 0  # Track the number of attempts

    while attempt < retries:
        try:
            r = requests.get(url, auth=None, headers=headers)
            r.raise_for_status()  # Raises an HTTPError for unsuccessful status codes
            return r.json()  # Return JSON response if successful
        except ConnectionError as e:
            attempt += 1
            if attempt == retries:
                raise ConnectionError(
                    "Connection aborted after multiple retries: Remote end closed connection without response"
                ) from e
            print(f"Connection error on attempt {attempt}/{retries}. Retrying in {delay} seconds...")
            time.sleep(delay)  # Wait before retrying
        except requests.exceptions.RequestException as e:
            # Handles all other exceptions from the requests library
            raise SystemExit(f"Request failed: {e}")
        except ValueError as e:
            # Handles cases where the response isn't valid JSON
            raise ValueError("Response content is not valid JSON") from e

    # Return None if all retries are exhausted and no response is received
    return {}


def format_date(date: str) -> str:
    return datetime.fromisoformat(date).strftime("%Y-%m-%d")


def shorten_tool_id(tool: str) -> str:
    """
    Shorten tool id
    """
    if "toolshed" in tool:
        return tool.split("/")[-2]
    else:
        return tool


def get_edam_operation_from_tools(selected_tools: list, all_tools: dict) -> List:
    """
    Get list of EDAM operations of the tools

    :param selected_tools: list of tool suite ids
    :param all_tools: dictionary with information about all tools
    """
    edam_operation = set()
    for t in selected_tools:
        if t in all_tools:
            edam_operation.update(set(all_tools[t]["EDAM operations"]))
        else:
            print(f"{t} not found in all tools")
    return list(edam_operation)
