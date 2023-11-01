#!/usr/bin/env python

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from wordcloud import WordCloud


def get_last_url_position(toot_id: str) -> str:
    """
    Returns the last url position of the toot_id, if the value is not a
    url it returns the toot_id. So works for local and toolshed
    installed tools.

    :param tool_id: galaxy tool id
    """

    toot_id = toot_id.split("/")[-1]
    return toot_id


def add_tool_stats_to_tools(tool_stats_path: str, tools_path: str, output_path: str, column_name: str) -> pd.DataFrame:
    """
    Adds the usage statistics to the community tool table

    :param tool_stats_path: path to the table with
        the tool stats (csv,
        must include "tool_name" and "count")
    :param tools_path: path to the table with
        the tools (csv,
        must include "Galaxy wrapper id")
    :param output_path: path to store the new table
    :param column_name: column to add for the tool stats,
        different columns could be added for the main servers
    """

    # parse csvs
    tool_stats_df = pd.read_csv(tool_stats_path)
    community_tools_df = pd.read_csv(tools_path, sep="\t")

    # extract tool id
    tool_stats_df["Galaxy wrapper id"] = tool_stats_df["tool_name"].apply(get_last_url_position)

    # group local and toolshed tools into one entry
    grouped_tool_stats_tools = tool_stats_df.groupby("Galaxy wrapper id", as_index=False)["count"].sum()

    # remove old stats entry with new stats
    if column_name in community_tools_df.columns:
        community_tools_df.drop(column_name, inplace=True, axis=1)

    community_tool_stats = pd.merge(grouped_tool_stats_tools, community_tools_df, on="Galaxy wrapper id")
    community_tool_stats.rename(columns={"count": column_name}, inplace=True)

    # store the merged file
    community_tool_stats.to_csv(output_path, sep="\t", index=False)

    return community_tool_stats


def get_wordcloud(community_tool_stats: pd.DataFrame, mask_figure: str, wordcloud_output_path: str) -> None: 
    """
    Generate a wordcloud based on the counts for each Galaxy wrapper id

    :param community_tool_stats: Dataframe that must
        have the columns "Galaxy wrapper id" and "count"
    :param mask_figure: a figure that is used to render the wordcloud
        E.g. a nice shape to highlight your community
    :param wordcloud_output_path: Path to store the wordcloud
    """

    # create the word cloud
    frec = pd.Series(community_tool_stats["count"].values, index=community_tool_stats["Galaxy wrapper id"]).to_dict()

    mask = np.array(Image.open(args.wordcloud_mask))
    mask[mask == 0] = 255  # set 0 in array to 255 to work with wordcloud

    wc = WordCloud(
        mask=mask_figure,
        background_color="rgba(255, 255, 255, 0)",
        random_state=42,
    )

    wc.generate_from_frequencies(frec)

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.imshow(wc)

    plt.axis("off")
    plt.tight_layout(pad=0)

    plt.savefig(wordcloud_output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge \
                                     tools list with tool stats"
    )
    parser.add_argument(
        "--tools",
        "-t",
        required=True,
        help="Path to community tool list in csv format \
        (must have column 'Galaxy wrapper id')",
    )
    parser.add_argument(
        "--tool_stats",
        "-ts",
        required=True,
        help="Path to tool stats list in csv format (must have \
              column 'tool_name' and 'count')",
    )
    parser.add_argument("--wordcloud_mask", "-wcm", required=False, help="Mask figure to generate the wordcloud")
    parser.add_argument(
        "--label",
        "-la",
        help="Label for the added \
                        column e.g. usegalaxy.eu tool usage",
    )
    parser.add_argument(
        "--stats_output", "-so", required=True, help="Output path to store the updated community list with stats"
    )
    parser.add_argument("--wc_output", "-wco", required=False, help="Output path to store the wordcloud.png")
    parser.add_argument(
        "--wordcloud", "-wc", action="store_true", default=False, help="Flag if wordcloud should be done"
    )
    args = parser.parse_args()

    community_tool_stats = add_tool_stats_to_tools(
        args.tool_stats,
        args.tools,
        args.stats_output,
        column_name=args.label,
    )

    if args.wordcloud:
        get_wordcloud(
            community_tool_stats,
            args.wordcloud_mask,
            args.wc_output,
        )
