from pathlib import Path

import pandas as pd

#######################
# Remove the version after the last / only if not local tool
#######################

project_path = Path(__file__).resolve().parent  # galaxy_tool_extractor folder
tool_stats_path = project_path.joinpath(project_path, "tool_usage.csv")

tool_stats_df = pd.read_csv(tool_stats_path, sep=",")
tool_stats_df.columns = ["tool_name", "count"]


def remove_version(val):
    if "/" in val:
        split_val = val.split("/")
        val = "/".join(split_val[:-1])

    return val


tool_stats_df["tool_name"] = tool_stats_df["tool_name"].apply(remove_version)

tool_stats_df.to_csv(project_path.joinpath("total_tool_usage_EU.csv"), index=False)
