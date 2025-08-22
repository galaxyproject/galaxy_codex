#!/usr/bin/env python

import argparse
import time
from datetime import date
from typing import (
    Dict,
    List,
)

import pandas as pd
import shared
import yt_dlp
from owlready2 import get_ontology

PLAUSIBLE_REQUEST_NB = 0


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
            tuto["short_tools"].add(shared.shorten_tool_id(tool))
    tuto["short_tools"] = list(tuto["short_tools"])


def get_edam_topics(tuto: dict, edam_ontology: dict) -> None:
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
        tuto["edam_operation"] = shared.get_edam_operation_from_tools(tuto["short_tools"], tools)


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
    global PLAUSIBLE_REQUEST_NB
    headers = {"Authorization": f"Bearer {plausible_api}"}
    if PLAUSIBLE_REQUEST_NB > 400:
        time.sleep(3600)
        PLAUSIBLE_REQUEST_NB = 0
    results = shared.get_request_json(url, headers)
    PLAUSIBLE_REQUEST_NB += 1
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
        "quiet": True,
        "skip_download": True,
    }
    recordings = []
    if "recordings" in tuto and tuto["recordings"]:
        recordings = tuto["recordings"]
        tuto["video"] = True
    elif "slides_recordings" in tuto and tuto["slides_recordings"]:
        recordings = tuto["slides_recordings"]
        tuto["video"] = True
    tuto["video_versions"] = len(recordings)
    for v in recordings:
        url = f"https://www.youtube.com/watch?v={v['youtube_id']}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            info = ydl.sanitize_info(info)
            if info:
                tuto["video_view"] += info["view_count"]


def format_tutorial(tuto: dict, edam_ontology: dict, tools: dict, feedback: dict, plausible_api: str) -> Dict:
    tuto["url"] = f'https://training.galaxyproject.org/{tuto["url"]}'
    tuto["mod_date"] = shared.format_date(tuto["mod_date"])
    tuto["pub_date"] = shared.format_date(tuto["pub_date"])
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
    feedback = shared.get_request_json("https://training.galaxyproject.org/training-material/api/feedback2.json", {})
    feedback_per_tuto = {}  # type: dict
    for tutorials in feedback.values():
        for tuto, feedback in tutorials.items():
            for f in feedback:
                feedback_per_tuto.setdefault(tuto, {"number": 0, "mean rating": 0})
                feedback_per_tuto[tuto]["number"] += 1
                feedback_per_tuto[tuto]["mean rating"] += int(f["rating"])
    for tuto in feedback_per_tuto:
        feedback_per_tuto[tuto]["mean rating"] /= feedback_per_tuto[tuto]["number"]
    return feedback_per_tuto


def test_in_tuto_list(tuto: dict, tutos: list) -> bool:
    """
    Test if tutorial in a list of tutorial
    """
    for t in tutos:
        if t["tutorial_name"] == tuto["tutorial_name"] and t["topic_name"] == tuto["topic_name"]:
            return True
    return False


def get_tutorials(
    tool_fp: str,
    plausible_api: str,
    run_test: bool,
) -> List[Dict]:
    """
    Extract training material from the GTN API, format them, extract EDAM operations from tools, feedback stats, view stats, etc
    """
    tools = shared.read_suite_per_tool_id(tool_fp)
    feedback = get_feedback_per_tutorials()
    edam_ontology = get_ontology("https://edamontology.org/EDAM_unstable.owl").load()
    topics = shared.get_request_json("https://training.galaxyproject.org/training-material/api/topics.json", {})
    if run_test:
        topics = {"microbiome": topics["microbiome"]}
    tutos: list[dict] = []
    for topic in topics:
        topic_information = shared.get_request_json(
            f"https://training.galaxyproject.org/training-material/api/topics/{topic}.json", {}
        )
        for tuto in topic_information["materials"]:
            if tuto is None:
                continue
            format_tutorial(tuto, edam_ontology, tools, feedback, plausible_api)
            if not test_in_tuto_list(tuto, tutos):
                tutos.append(tuto)
    return tutos


def filter_tutorials(tutorials: dict, tags: List) -> List:
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


def export_tutorials_to_tsv(tutorials: list, output_fp: str) -> None:
    """
    Export tutorials to a TSV file
    """
    df = pd.DataFrame(tutorials).assign(
        Workflows=lambda df: df.workflows.notna(),
        exact_supported_servers=lambda df: df.exact_supported_servers.fillna("").apply(list),
        inexact_supported_servers=lambda df: df.inexact_supported_servers.fillna("").apply(list),
        visit_duration=lambda df: df.visit_duration / 60,
    )

    for col in ["exact_supported_servers", "inexact_supported_servers", "short_tools", "edam_operation", "edam_topic"]:
        df[col] = shared.format_list_column(df[col])

    df = (
        df.rename(
            columns={
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
                "video_view": "Video views",
            }
        )
        .fillna("")
        .reindex(
            columns=[
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
                "Video views",
            ]
        )
    )
    df.to_csv(output_fp, sep="\t", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Galaxy Training Materials from GTN API together with statistics"
    )
    subparser = parser.add_subparsers(dest="command")
    # Extract tutorials
    extract = subparser.add_parser("extract", help="Extract all training materials")
    extract.add_argument("--all", "-o", required=True, help="Filepath to JSON with all extracted training materials")
    extract.add_argument(
        "--tools",
        "-t",
        required=True,
        help="Filepath to JSON with all extracted tools, generated by extractools command",
    )
    extract.add_argument("--api", "-a", required=True, help="Plausible access token")
    extract.add_argument(
        "--test",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test case only on one topic",
    )

    # Filter tutorials
    filtertuto = subparser.add_parser("filter", help="Filter training materials based on their tags")
    filtertuto.add_argument(
        "--all",
        "-a",
        required=True,
        help="Filepath to JSON with all extracted tutorials, generated by extracttutorials command",
    )
    filtertuto.add_argument(
        "--filtered",
        "-f",
        required=True,
        help="Filepath to TSV with filtered tutorials",
    )
    filtertuto.add_argument(
        "--tags",
        "-t",
        help="Path to a file with tags to keep in the extraction (one per line)",
    )

    args = parser.parse_args()

    if args.command == "extract":
        tutorials = get_tutorials(args.tools, args.api, args.test)
        shared.export_to_json(tutorials, args.all)

    elif args.command == "filter":
        all_tutorials = shared.load_json(args.all)
        # get categories and training to exclude
        tags = shared.read_file(args.tags)
        # filter training lists
        filtered_tutorials = filter_tutorials(all_tutorials, tags)
        export_tutorials_to_tsv(filtered_tutorials, args.filtered)
