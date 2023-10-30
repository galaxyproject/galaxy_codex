#!/usr/bin/env bash

mkdir -p 'results/'

python bin/generate_tool_stats.py \
        --tools 'results/all_tools.tsv' \
        --tool_stats 'data/usage_stats/tool_usage_per_user_2022_23_EU.csv' \
        --label 'Tools usage (usegalaxy.eu)' \
        --stats_output 'results/all_tools.tsv' #overwrite with new column

#TODO add stats for .org / .org.au