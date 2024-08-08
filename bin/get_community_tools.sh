#!/usr/bin/env bash

# stop on error
set -e 

if [[ ! -z $1  && $1 == "test" ]]; then
        python bin/extract_galaxy_tools.py \
                filter \
                --all "results/all_tools.json" \
                --ts-filtered "results/microgalaxy/tools_filtered_by_ts_categories.tsv" \
                --filtered "results/microgalaxy/tools.tsv" \
                --categories "data/communities/microgalaxy/categories" \
                --status "data/communities/microgalaxy/tool_status.tsv"

        python bin/create_interactive_table.py \
                --input "results/microgalaxy/tools.tsv" \
                --remove-col "Reviewed" \
                --remove-col "To keep" \
                --filter-col "To keep" \
                --template "data/interactive_table_template.html" \
                --output "results/microgalaxy/tools.html"

        python bin/create_wordcloud.py \
                --input  "results/microgalaxy/tools.tsv" \
                --name-col "Galaxy wrapper id" \
                --stat-col "No. of tool users (2022-2023) (usegalaxy.eu)" \
                --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
                --output "results/microgalaxy/tools_wordcloud.png"

else
        for com_data_fp in data/communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        echo "$community";

                        mkdir -p "results/$community"

                        python bin/extract_galaxy_tools.py \
                                filter \
                                --all "results/all_tools.json" \
                                --ts-filtered "results/$community/tools_filtered_by_ts_categories.tsv" \
                                --filtered "results/$community/tools.tsv" \
                                --categories "data/communities/$community/categories" \
                                --status "data/communities/$community/tool_status.tsv"

                        python bin/create_interactive_table.py \
                                --input "results/$community/tools.tsv" \
                                --remove-col "Reviewed" \
                                --remove-col "To keep" \
                                --filter-col "To keep" \
                                --template "data/interactive_table_template.html" \
                                --output "results/$community/tools.html"

                        python bin/create_wordcloud.py \
                                --input  "results/$community/tools.tsv" \
                                --name-col "Galaxy wrapper id" \
                                --stat-col "No. of tool users (2022-2023) (usegalaxy.eu)" \
                                --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
                                --output "results/$community/tools_wordcloud.png"

                fi;
        done
fi


