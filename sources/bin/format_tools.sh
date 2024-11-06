#!/usr/bin/env bash

if [[ ! -z $1  && $1 == "test" ]]; then
        python sources/bin/create_interactive_table.py \
                --input "communities/all/resources/test_tools.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/all/resources/tools.html"

        python sources/bin/create_wordcloud.py \
                --input "communities/all/resources/test_tools.tsv" \
                --name-col "Suite ID" \
                --stat-col "Suite users on main servers" \
                --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                --output "communities/all/resources/tools_wordcloud.png"
else
        python sources/bin/create_interactive_table.py \
                --input "communities/all/resources/tools.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/all/resources/tools.html"

        python sources/bin/create_wordcloud.py \
                --input "communities/all/resources/tools.tsv" \
                --name-col "Suite ID" \
                --stat-col "Suite users on main servers" \
                --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                --output "communities/all/resources/tools_wordcloud.png"
fi;