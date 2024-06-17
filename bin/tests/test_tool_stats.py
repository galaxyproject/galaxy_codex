import os
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from extract_galaxy_tools import GALAXY_TOOL_STATS


def get_last_url_position(toot_id: str) -> str:
    """
    Returns the last url position of the toot_id, if the value is not a
    url it returns the toot_id. So works for local and toolshed
    installed tools.

    :param tool_id: galaxy tool id
    """

    if "/" in toot_id:
        toot_id = toot_id.split("/")[-1]
    return toot_id


def get_tool_stats_from_stats_file(tool_stats_df: pd.DataFrame, tool_ids: str) -> int:
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

    return int(agg_count)


tools_stats_df = pd.read_csv(GALAXY_TOOL_STATS["Total tool usage (usegalaxy.eu)"])

tool_ids = ["nextclade"]

counts = get_tool_stats_from_stats_file(tools_stats_df, tool_ids)

print(counts)
