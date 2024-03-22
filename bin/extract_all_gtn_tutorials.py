#!/usr/bin/env python

import argparse
from datetime import datetime, date
from pathlib import Path
import requests
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
from owlready2 import get_ontology, Thing
import yt_dlp

import shared_functions


def get_request_json(url: str, headers: dict = {}) -> dict:
    """
    Return JSON output using request

    :param url: galaxy tool id
    """
    r = requests.get(url, auth=None, headers=headers)
    r.raise_for_status()
    return r.json()


def format_date(date: str) -> str:
    return datetime.fromisoformat(date).strftime("%Y-%m-%d")


def add_supported_servers(tuto: dict) -> None:
    """
    Split supported_servers into 2 lists there
    """
    if "supported_servers" in tuto:
        if "exact" in tuto["supported_servers"]:
            tuto["exact_supported_servers"] = [server["name"] for server in tuto["supported_servers"]["exact"]]
        if "inexact" in tuto["supported_servers"]:
            tuto["inexact_supported_servers"] = [server["name"] for server in tuto["supported_servers"]["inexact"]]


def get_short_tool_ids(tuto: dict) -> None:
    """
    Get tool ids without toolshed URL
    """
    tuto["short_tools"] = set()
    if "tools" in tuto:    
        for tool in tuto["tools"]:
            if "toolshed" in tool:
                tuto["short_tools"].add(tool.split("/")[-2])
            else:
                tuto["short_tools"].add(tool)
    tuto["short_tools"] = list(tuto["short_tools"])


def get_edam_topics(tuto: dict, edam_ontology) -> None:
    """
    Get EDAM topics instead of EDAM ids
    """
    tuto["edam_topic"] = []
    if "edam_ontology" in tuto:
        for term in tuto["edam_ontology"]:
            if "topic" in term and edam_ontology[term]:
                tuto["edam_topic"] += edam_ontology[term].label


def get_edam_operations(tuto: dict, tools: dict) -> None:
    """
    Get EDAM operations from the tools
    """
    tuto["edam_operation"] = []
    if "short_tools" in tuto:
        edam_operation = set()
        for t in tuto["short_tools"]:
            if t in tools:
                edam_operation.update(set(tools[t]["EDAM operation"]))
            else:
                print(f"{t} not found in all tools")
        tuto["edam_operation"] = list(edam_operation)


def get_feedback(tuto: dict, feedback: dict) -> None:
    """
    Get feedback for tutorial
    """
    tuto["feedback_number"] = 0
    tuto["feedback_mean_note"] = None
    title = tuto["title"]
    if title in feedback:
        tuto["feedback_number"] = feedback[title]["number"]
        tuto["feedback_mean_note"] = feedback[title]["mean note"]


def get_visit_results(url: str, tuto: dict, plausible_api: str) -> None:
    """
    Extract visit results from Plausible URL
    """
    headers = {
       'Authorization' : f"Bearer {plausible_api}"
    }
    results = get_request_json(url, headers)
    if "results" in results:
        for metric in ["visitors", "pageviews", "visit_duration"]:
            tuto[metric] += results["results"][metric]["value"]


def get_visits(tuto: dict, plausible_api: str) -> None:
    """
    Extract tutorial visitors and pageviews from Plausible
    """
    tuto["visitors"] = 0
    tuto["pageviews"] = 0
    tuto["visit_duration"] = 0
    url_prefix = f"https://plausible.galaxyproject.eu/api/v1/stats/aggregate?site_id=training.galaxyproject.org&period=custom&date={tuto['pub_date']},{date.today()}&metrics=visitors,pageviews,visit_duration&filters=event:page%3D%3D%2Ftraining-material%2Ftopics%2F{tuto['topic_name']}%2Ftutorials%2F{tuto['tutorial_name']}"
    if tuto["hands_on"]:
        url = f"{url_prefix}%2Ftutorial.html"
        get_visit_results(url, tuto, plausible_api)
    if tuto["slides"]:
        url = f"{url_prefix}%slides.html"
        get_visit_results(url, tuto, plausible_api)


def get_youtube_stats(tuto: dict) -> None:
    """
    Get YouTube stats
    """
    tuto["video_versions"] = 0
    tuto["video_view"] = 0
    ydl_opts = {
        "ignoreerrors": True,
        "quiet": True
    }
    if "video_library" in tuto and tuto["video_library"]["tutorial"]:
        tuto["video_versions"] = len(tuto["video_library"]["tutorial"]["versions"])
        for v in tuto["video_library"]["tutorial"]["versions"]:
            url = f"https://www.youtube.com/watch?v={v['link']}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(info)
                if info:
                    tuto["video_view"] += info["view_count"]

 
def format_tutorial(tuto: dict, edam_ontology, tools: dict, feedback: dict, plausible_api: str) -> None:
    tuto["url"] = f'https://training.galaxyproject.org/{tuto["url"]}'
    tuto["mod_date"] = format_date(tuto["mod_date"])
    tuto["pub_date"] = format_date(tuto["pub_date"])
    add_supported_servers(tuto)
    get_short_tool_ids(tuto)
    get_edam_topics(tuto, edam_ontology)
    get_edam_operations(tuto, tools)
    get_visits(tuto, plausible_api)
    get_feedback(tuto, feedback)
    get_youtube_stats(tuto)
    return tuto


def get_feedback_per_tutorials() -> Dict:
    """
    Get feedback from GTN API and group per tutorial
    """
    feedback = get_request_json("https://training.galaxyproject.org/training-material/api/feedback.json")
    feedback_per_tuto = {}
    for f in feedback:
        tuto = f["tutorial"]
        feedback_per_tuto.setdefault(tuto, {"number": 0, "mean note": 0})
        feedback_per_tuto[tuto]["number"] += 1
        feedback_per_tuto[tuto]["mean note"] += int(f["note"])
    for tuto in feedback_per_tuto:
        feedback_per_tuto[tuto]["mean note"] /= feedback_per_tuto[tuto]["number"]
    return feedback_per_tuto


def get_tutorials(tool_fp: str, plausible_api: str) -> List[Dict]:
    """
    Extract training material from the GTN API, format them, extract EDAM operations from tools, feedback stats, view stats, etc
    """
    tools = shared_functions.read_suite_per_tool_id(tool_fp) 
    feedback = get_feedback_per_tutorials()
    edam_ontology = get_ontology('https://edamontology.org/EDAM_unstable.owl').load()
    topics = get_request_json('https://training.galaxyproject.org/training-material/api/topics.json')
    tutos = []
    for topic in topics:
        topic_information = get_request_json(f"https://training.galaxyproject.org/training-material/api/topics/{topic}.json")
        for tuto in topic_information["materials"]:
            if tuto is None:
                continue
            format_tutorial(tuto, edam_ontology, tools, feedback, plausible_api)
            tutos.append(tuto)
    return tutos


def filter_tutorials(tutorials: List[Dict], tags: List) ->  List[Dict]:
    """
    Filter training based on a list of tags
    """
    filtered_tutorials = []
    for tuto in tutorials:
        to_keep = False
        if "tags" in tuto and tuto["tags"]:
            for t in tuto["tags"]:
                if t in tags:
                    to_keep = True
        if to_keep:
            filtered_tutorials.append(tuto)
    return filtered_tutorials


def export_tutorials_to_tsv(tutorials: List[Dict], output_fp: str) -> None:
    """
    Export tutorials to a TSV file
    """
    df = (pd.DataFrame(tutorials)
        .assign(
            Workflows=lambda df: df.workflows.notna(),
            exact_supported_servers= lambda df: df.exact_supported_servers.fillna("").apply(list),
            inexact_supported_servers= lambda df: df.inexact_supported_servers.fillna("").apply(list),
            visit_duration= lambda df: df.visit_duration/60
        )
    )

    for col in ["exact_supported_servers", "inexact_supported_servers", "short_tools", "edam_operation", "edam_topic"]:
        df[col] = shared_functions.format_list_column(df[col])
        
    df = (df
        .rename(columns = {
            "title": "Title",
            "hands_on": "Tutorial",
            "url": "Link",
            "slides": "Slides",
            "mod_date": "Last modification",
            "pub_date": "Creation",
            "version": "Version",
            "short_tools": "Tools",
            "exact_supported_servers": "Servers with precise tool versions",
            "inexact_supported_servers": "Servers with tool but different versions",
            "topic_name_human": "Topic",
            "video": "Video",
            "edam_topic": "EDAM topic",
            "edam_operation": "EDAM operation",
            "feedback_number": "Feedback number",
            "feedback_mean_note": "Feedback mean note",
            "visitors": "Visitors",
            "pageviews": "Page views",
            "visit_duration": "Visit duration",
            "video_versions": "Video versions",
            "video_view": "Video views"
        })
        .fillna("")
        .reindex(columns = [
            "Topic",
            "Title",
            "Link",
            "EDAM topic",
            "EDAM operation",
            "Creation",
            "Last modification",
            "Version",
            "Tutorial",
            "Slides",
            "Video",
            "Workflows",
            "Tools",
            "Servers with precise tool versions",
            "Servers with tool but different versions",
            "Feedback number",
            "Feedback mean note",
            "Visitors",
            "Page views",
            "Visit duration",
            "Video views"
        ])
    )
        
    df.to_csv(output_fp, sep="\t", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy Training Materials from GTN API together with statistics"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tutorials
    extracttutorials = subparser.add_parser("extracttutorials", help="Extract all training materials")
    extracttutorials.add_argument("--all_tutorials", "-o", required=True, help="Filepath to JSON with all extracted training materials")
    extracttutorials.add_argument(
        "--tools",
        "-t",
        required=True,
        help="Filepath to TSV with all extracted tools, generated by extractools command",
    )
    extracttutorials.add_argument("--api", "-a", required=True, help="Plausible access token")

    # Filter tutorials
    filtertutorials = subparser.add_parser("filtertutorials", help="Filter training materials based on their tags")
    filtertutorials.add_argument(
        "--all_tutorials",
        "-t",
        required=True,
        help="Filepath to JSON with all extracted tutorials, generated by extracttutorials command",
    )
    filtertutorials.add_argument(
        "--filtered_tutorials",
        "-f",
        required=True,
        help="Filepath to TSV with filtered tutorials",
    )
    filtertutorials.add_argument(
        "--tags",
        "-c",
        help="Path to a file with tags to keep in the extraction (one per line)",
    )

    args = parser.parse_args()

    if args.command == "extracttutorials":
        tutorials = get_tutorials(args.tools, args.api)
        shared_functions.export_to_json(tutorials, args.all_tutorials)

    elif args.command == "filtertutorials":
        tutorials = shared_functions.load_json(args.all_tutorials)
        # get categories and training to exclude
        tags = shared_functions.read_file(args.tags)
        # filter training lists
        filtered_tutorials = filter_tutorials(tutorials, tags)
        export_tutorials_to_tsv(filtered_tutorials, args.filtered_tutorials)

    