#!/usr/bin/env bash

# stop on error
set -e 

if [[ ! -z $1  && $1 == "test" ]]; then
        python sources/bin/extract_galaxy_tools.py \
                filter \
                --all "communities/all/resources/tools.json" \
                --ts-filtered "communities/microgalaxy/resources/tools_filtered_by_ts_categories.tsv" \
                --filtered "communities/microgalaxy/resources/tools.tsv" \
                --categories "communities/microgalaxy/metadata/categories" \
                --status "communities/microgalaxy/metadata/tool_status.tsv"

        python sources/bin/create_interactive_table.py \
                --input "communities/microgalaxy/resources/tools.tsv" \
                --remove-col "Reviewed" \
                --remove-col "To keep" \
                --filter-col "To keep" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/microgalaxy/resources/tools.html"

        python sources/bin/create_wordcloud.py \
                --input  "communities/microgalaxy/resources/tools.tsv" \
                --name-col "Galaxy wrapper id" \
                --stat-col "No. of tool users (5 years) - all main servers" \
                --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                --output "communities/microgalaxy/resources/tools_wordcloud.png"

else
        for com_data_fp in communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        if [ "$community" != "all" ]; then

                                echo "$community";

                                mkdir -p "communities/$community/resources"

                                python sources/bin/extract_galaxy_tools.py \
                                        filter \
                                        --all "communities/all/resources/tools.json" \
                                        --ts-filtered "communities/$community/resources/tools_filtered_by_ts_categories.tsv" \
                                        --filtered "communities/$community/resources/tools.tsv" \
                                        --categories "communities/$community/metadata/categories" \
                                        --status "communities/$community/metadata/tool_status.tsv"

                                python sources/bin/create_interactive_table.py \
                                        --input "communities/$community/resources/tools.tsv" \
                                        --remove-col "Reviewed" \
                                        --remove-col "To keep" \
                                        --filter-col "To keep" \
                                        --template "sources/data/interactive_table_template.html" \
                                        --output "communities/$community/resources/tools.html"

                                python sources/bin/create_wordcloud.py \
                                        --input  "communities/$community/resources/tools.tsv" \
                                        --name-col "Galaxy wrapper id" \
                                        --stat-col "No. of tool users (5 years) - all main servers" \
                                        --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                                        --output "communities/$community/resources/tools_wordcloud.png"
                        fi;
                fi;
        done
fi


