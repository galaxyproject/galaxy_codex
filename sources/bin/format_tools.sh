#!/usr/bin/env bash

python sources/bin/create_interactive_table.py \
        --input "communities/all/resources/tools.tsv" \
        --template "sources/data/interactive_table_template.html" \
        --output "communities/all/resources/tools.html"

python sources/bin/create_wordcloud.py \
        --input "communities/all/resources/tools.tsv" \
        --name-col "Galaxy wrapper id" \
        --stat-col "No. of tool users (2022-2023) (usegalaxy.eu)" \
        --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
        --output "communities/all/resources/tools_wordcloud.png" \