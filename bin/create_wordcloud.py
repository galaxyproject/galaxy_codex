#!/usr/bin/env python

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from wordcloud import WordCloud


def get_wordcloud(community_tool_path: str, mask_figure: str, stats_column: str, wordcloud_output_path: str) -> None:
    """
    Generate a wordcloud based on the counts for each Galaxy wrapper id

    :param community_tool_path: Dataframe that must
        have the columns "Galaxy wrapper id" and `stats_column`
    :param mask_figure: a figure that is used to render the wordcloud
        E.g. a nice shape to highlight your community
    :param stats_column: Column name of the
        column with usage statistics in the table
    :param wordcloud_output_path: Path to store the wordcloud
    """

    community_tool_stats = pd.read_csv(community_tool_path, sep="\t")

    assert (
        stats_column in community_tool_stats
    ), f"Stats column: {stats_column} not found in table!"  # check if the stats column is there

    # some tools are not used at all
    community_tool_stats[stats_column] = community_tool_stats[stats_column].fillna(value=0)

    # create the word cloud
    frec = pd.Series(
        community_tool_stats[stats_column].values, index=community_tool_stats["Galaxy wrapper id"]
    ).to_dict()

    mask = np.array(Image.open(mask_figure))
    mask[mask == 0] = 255  # set 0 in array to 255 to work with wordcloud

    wc = WordCloud(
        mask=mask,
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
        description="Create wordcloud from \
            TSV file based on Galaxy usage statistics"
    )
    parser.add_argument(
        "--table",
        "-ta",
        required=True,
        help="Path to TSV file with tools and stats",
    )
    parser.add_argument(
        "--stats_column",
        "-sc",
        required=True,
        help="Name of the column with usage statistics",
    )
    parser.add_argument(
        "--output",
        "-out",
        required=True,
        help="Path to HTML output",
    )

    parser.add_argument("--wordcloud_mask", "-wcm", required=False, help="Mask figure to generate the wordcloud")

    args = parser.parse_args()
    get_wordcloud(args.table, args.wordcloud_mask, args.stats_column, args.output)
