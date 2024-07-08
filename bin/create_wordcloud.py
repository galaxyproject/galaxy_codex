#!/usr/bin/env python

import argparse
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from wordcloud import WordCloud


def prepare_data(table_path: str, name_col: str, stat_col: str) -> Dict:
    """
    Prepare data to create dictionary with key being the name and
    value the stat/counts

    :param table_path: Path TSV file with name and stats
        have the columns "Galaxy wrapper id" and `stats_column`
    :param name_col: Name of the column with name for wordcloud
    :param stat_col: Name of columns with usage/count
    """
    table = pd.read_csv(table_path, sep="\t")

    assert stat_col in table, f"Stat column: {stat_col} not found in table!"
    assert name_col in table, f"Name column: {name_col} not found in table!"

    # some tools are not used at all
    table[stat_col] = table[stat_col].fillna(value=0)

    # create dictionary with key being the name and value the stat/counts
    freq = pd.Series(table[stat_col].values, index=table[name_col]).to_dict()

    return freq


def generate_wordcloud(freq: dict, mask_figure: str) -> WordCloud:
    """
    Generate a wordcloud based on counts

    :param freq: Dictionary with key being the name and
    value the stat/counts
    :param mask_figure: a figure that is used to render the wordcloud
        E.g. a nice shape to highlight your community
    """
    mask = np.array(Image.open(mask_figure))
    mask[mask == 0] = 255  # set 0 in array to 255 to work with wordcloud

    wc = WordCloud(
        mask=mask,
        background_color="rgba(255, 255, 255, 0)",
        random_state=42,
    )
    wc.generate_from_frequencies(freq)
    return wc


def export_wordcloud(wc: WordCloud, wordcloud_output_path: str) -> None:
    """
    Export wordcloud to file

    :param wordcloud_output_path: Path to store the wordcloud
    """
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.imshow(wc)
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(wordcloud_output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create wordcloud from TSV file")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to TSV file with name and stats",
    )
    parser.add_argument(
        "--name-col",
        "-n",
        required=True,
        help="Name of the column with name to use in wordcloud",
    )
    parser.add_argument(
        "--stat-col",
        "-s",
        required=True,
        help="Name of the column with statistic to build the wordcloud",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to HTML output",
    )
    parser.add_argument("--wordcloud_mask", "-wcm", required=False, help="Mask figure to generate the wordcloud")

    args = parser.parse_args()
    frec = prepare_data(args.input, args.name_col, args.stat_col)
    wc = generate_wordcloud(frec, args.wordcloud_mask)
    export_wordcloud(wc, args.output)
