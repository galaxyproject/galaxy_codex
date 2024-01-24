#!/usr/bin/env bash

mkdir -p 'results/'

python bin/create_interactive_table.py \
        --table "results/all_tools.tsv" \
        --template "data/interactive_table_template.html" \
        --output "results/index.html"

python bin/create_wordcloud.py \
        --table "results/all_tools.tsv" \
        --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
        --output "results/all_tools_wordcloud.png" \
        --stats_column "https://usegalaxy.eu usage"