#!/usr/bin/env bash

mkdir -p 'results/'

python bin/create_interactive_table.py \
        --table "results/all_tools.tsv" \
        --template "data/interactive_table_template.html" \
        --output "results/index.html"

python bin/create_wordcloud.py \
        --table "results/all_tools.tsv" \
        --name_col "Galaxy wrapper id" \
        --stat_col "No. of tool users (2022-2023) (usegalaxy.eu)" \
        --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
        --output "results/all_tools_wordcloud.png" \