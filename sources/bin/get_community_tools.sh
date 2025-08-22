#!/usr/bin/env bash

# stop on error
set -e 

if [[ ! -z $1  && $1 == "test" ]]; then
        python sources/bin/extract_galaxy_tools.py \
                filter \
                --all "communities/all/resources/test_tools.json" \
                --categories "communities/microgalaxy/metadata/categories" \
                --filtered "communities/microgalaxy/resources/tools_filtered_by_ts_categories.json" \
                --status "communities/microgalaxy/metadata/tool_status.tsv"
   
        python sources/bin/extract_galaxy_tools.py \
                curate \
                --filtered "communities/microgalaxy/resources/tools_filtered_by_ts_categories.json" \
                --status "communities/microgalaxy/metadata/tool_status.tsv" \
                --curated "communities/microgalaxy/resources/curated_tools.tsv" \
                --wo-biotools "communities/microgalaxy/resources/curated_tools_wo_biotools.tsv" \
                --w-biotools "communities/microgalaxy/resources/curated_tools_w_biotools.tsv"

        python sources/bin/create_wordcloud.py \
                --input  "communities/microgalaxy/resources/curated_tools.tsv" \
                --name-col "Suite ID" \
                --stat-col "Suite runs (last 5 years) on main servers" \
                --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                --output "communities/microgalaxy/resources/tools_wordcloud.png"

else
        for com_data_fp in communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        if [[ "$community" != "all" && -f "communities/$community/metadata/categories" ]]; then
                                echo "$community";
                                mkdir -p "communities/$community/resources"

                                python sources/bin/extract_galaxy_tools.py \
                                        filter \
                                        --all "communities/all/resources/tools.json" \
                                        --categories "communities/$community/metadata/categories" \
                                        --filtered "communities/$community/resources/tools_filtered_by_ts_categories.json" \
                                        --status "communities/$community/metadata/tool_status.tsv"

                                if [[ -e "communities/$community/metadata/tool_status.tsv" ]]; then
                                        python sources/bin/extract_galaxy_tools.py \
                                                curate \
                                                --filtered "communities/$community/resources/tools_filtered_by_ts_categories.json" \
                                                --status "communities/$community/metadata/tool_status.tsv" \
                                                --curated "communities/$community/resources/curated_tools.tsv" \
                                                --wo-biotools "communities/$community/resources/curated_tools_wo_biotools.tsv" \
                                                --w-biotools "communities/$community/resources/curated_tools_w_biotools.tsv"

                                        if [[ -e "communities/$community/resources/curated_tools.tsv" ]]; then
                                                python sources/bin/create_wordcloud.py \
                                                        --input "communities/$community/resources/curated_tools.tsv" \
                                                        --name-col "Suite ID" \
                                                        --stat-col "Suite runs (last 5 years) on main servers" \
                                                        --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                                                        --output "communities/$community/resources/tools_wordcloud.png"
                                        fi;
                                fi;
                        fi;
                fi;
        done
fi


