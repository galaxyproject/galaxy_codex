#!/usr/bin/env python

import argparse
import time
from datetime import date
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
import shared
import yt_dlp
from owlready2 import get_ontology
from ruamel.yaml import YAML as ruamelyaml
from ruamel.yaml.scalarstring import LiteralScalarString

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


def filter_tutorials(tutorials: Any, tags: Optional[List[Any]]) -> List[Any]:
    # def filter_tutorials(tutorials: dict, tags: List) -> List:
    """
    Filter training based on a list of tags
    If tags is None or an empty list, returns all tutorials.
    """
    # Normalize input: always work with a list
    if isinstance(tutorials, dict):
        tutorials = list(tutorials.values())
    if not tags:
        # No tags specified, return all tutorials
        return tutorials

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


def extract_top_tutorials_per_category(
    tutorial_fp: str, count_column: str = "Visitors", category_nb: int = 10, top_tutorial_nb: int = 10
) -> pd.DataFrame:
    """
    Extract top tutorials per categories
    """
    tutorials = pd.read_csv(tutorial_fp, sep="\t")

    # Step 1: Split the categories into separate rows and strip whitespace
    df = tutorials.assign(Category=tutorials["Topic"].str.split(",")).explode("Category")
    df["Category"] = df["Category"].str.strip()  # Strip whitespace

    # Step 2: Group by category to calculate total count and item count
    grouped = (
        df.groupby("Category")
        .agg(
            total_count=(count_column, "sum"),
            item_count=("Link", "size"),  # Count distinct items if necessary, use 'nunique'
        )
        .reset_index()
    )

    # Step 3: Filter categories with at least 5 items
    filtered = grouped[grouped["item_count"] >= 5]

    # Step 4: Sort by total count in descending order
    top_categories = filtered.sort_values(by="total_count", ascending=False).head(category_nb)["Category"]

    # Step 5: Assign each tutorial to the first category it appears in
    # Sort by 'Galaxy wrapper id' to ensure we assign based on first appearance
    df_unique = df[df["Category"].isin(top_categories)]  # Filter rows for top 5 categories
    df_unique = df_unique.sort_values(by=["Link", "Category"])  # Sort by tutorial ID to keep first category only

    # Step 6: Remove duplicates, keeping the first appearance of each tutorial
    df_unique = df_unique.drop_duplicates(subset=["Link"], keep="first")

    # Step 7: Extract top X items per category based on total count
    top_tutorials_per_category = (
        df_unique.groupby("Category", group_keys=False)  # Group by category
        .apply(lambda group: group.nlargest(top_tutorial_nb, count_column))  # Get top items per category
        .reset_index(drop=True)  # Reset index for clean output
    )
    return top_tutorials_per_category


def fill_lab_tutorial_section(
    lab_section: dict, top_items_per_category: pd.DataFrame, count_column: str = "Visitors"
) -> dict:
    """
    Fill Lab tutorial section
    """
    tabs = []
# If we want a static tab with static content : 
#    for element in lab_section["tabs"]:
#        if element["id"] == "more_tools":
#            tabs.append(element)

    for grp_id, group in top_items_per_category.groupby("Category"):
        group_id = str(grp_id)
        tutorial_entries = []
        for _index, row in group.iterrows():

            # Prepare the description with an HTML unordered list and links for each tutorial link (only unique id)
            title = f"{row['Title']}\n (Visitors: {row[count_column]})"
            tool_ids = row["Tools"]
            description = f"Tutorial stored in {row['Topic']} topic on the Galaxy Training Network and covering topics related to {row['EDAM topic']}",
            link = row["Link"]
            #owner = row["Suite owner"]
            #wrapper_id = row["Suite ID"]

            # Use LiteralScalarString to enforce literal block style for the description
            #description_md = LiteralScalarString(description.strip())

            # Create the tutorial entry
            tutorial_entry = {
                "title_md": title,
                "description_md": description,
                "button_link": link,
                "button_tip": "View tutorial",
                "button_icon": "tutorial",
            }

            tutorial_entries.append(tutorial_entry)

        # Create table entry for each Topic
        tabs.append(
            {
                "id": group_id.replace(" ", "_").lower(),
                "title": group_id,
                "heading_md": f"Top 10 most visited tutorials for the Topic : {group_id}",
                "content": tutorial_entries,
            }
        )

    new_lab_section = {
        "id": lab_section["id"],
        "title": lab_section["title"],
        "tabs": tabs,
    }
    return new_lab_section


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

    # Add tutorials to the lab section
    labpop = subparser.add_parser("popLabSection", help="Fill in Lab section tutorials")
    labpop.add_argument(
        "--tsv",
        "-t",
        required=True,
        help="Filepath to TSV with curated tutorials",
    )
    labpop.add_argument(
        "--lab",
        required=True,
        help="Filepath to YAML files for Lab section",
    )

    args = parser.parse_args()

    if args.command == "extract":
        tutorials = get_tutorials(args.tools, args.api, args.test)
        shared.export_to_json(tutorials, args.all)

    elif args.command == "filter":
        all_tutorials = shared.load_json(args.all)
        # get categories and training to exclude
        tags = shared.read_file(args.tags) if args.tags else None
        # filter training lists
        filtered_tutorials = filter_tutorials(all_tutorials, tags)
        export_tutorials_to_tsv(filtered_tutorials, args.filtered)

    elif args.command == "popLabSection":
        lab_section = shared.load_yaml(args.lab)
        top_tutorials_per_category = extract_top_tutorials_per_category(args.tsv)
        lab_section = fill_lab_tutorial_section(lab_section, top_tutorials_per_category)

        with open(args.lab, "w") as lab_f:
            ruamelyaml().dump(lab_section, lab_f)
