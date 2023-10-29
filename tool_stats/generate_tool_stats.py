import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from wordcloud import WordCloud


def get_last_url_position(val):
    val = val.split("/")[-1]
    return(val)

def get_secondlast_url_position(val):
    if len(val.split("/")) == 1:
        return(val)
    else:
        val = val.split("/")[-2]
    return(val)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge community tools list with tool stats')
    parser.add_argument('--community_tools', 
                        '-ct', 
                        required=True, 
                        help="Path to community tool list in csv format (must have column 'Galaxy wrapper id')")
    parser.add_argument('--tool_stats', 
                        '-ts', 
                        required=True, 
                        help="Path to tool stats list in csv format (must have column 'tool_name' and 'count')")
    parser.add_argument('--wordcloud_mask', 
                        '-wcm', 
                        help="Mask figure to generate the wordcloud")
    parser.add_argument('--output', 
                        '-o', 
                        required=True, 
                        help="Output folder to store the wordcloud.png and community_tool_stats.csv")
    args = parser.parse_args()

    # parse csvs 
    tool_stats_df = pd.read_csv(args.tool_stats)
    community_tools_df = pd.read_csv(args.community_tools)

    # extract tool id and group (some tools ids exist multiple times, why ?)
    tool_stats_df["Galaxy wrapper id"] = tool_stats_df["tool_name"].apply(get_last_url_position)
    grouped_tool_stats_tools = tool_stats_df.groupby("Galaxy wrapper id", as_index=False)["count"].sum()

    community_tool_stats = pd.merge(grouped_tool_stats_tools, community_tools_df, on='Galaxy wrapper id')
    # community_tool_stats = merged_tool_stats.loc[:,["Galaxy wrapper id", "count", "Description"]]

    community_tool_stats_path = os.path.join(args.output, "community_tool_stats.csv")
    community_tool_stats.to_csv(community_tool_stats_path) #store the merged file

    #create the word cloud
    frec = pd.Series(community_tool_stats["count"].values,index=community_tool_stats["Galaxy wrapper id"]).to_dict()

    mask = np.array(Image.open(args.wordcloud_mask))
    mask[mask == 0] = 255 #set 0 in array to 255 to work with wordcloud

    wc = WordCloud(
               mask = mask, 
               background_color = "rgba(255, 255, 255, 0)",
               random_state = 42, 
               )

    wc.generate_from_frequencies(frec)

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.imshow(wc)

    plt.axis("off")
    plt.tight_layout(pad=0)
    wc_output_path = os.path.join(args.output,"wordcloud.png")
    plt.savefig(wc_output_path)
