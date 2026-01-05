#!/usr/bin/env bash

# stop on error
set -e 

for com_data_fp in communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                if [[ ! -z $1  && $1 == "test" && "$community" != "microgalaxy" ]]; then
                        continue
                fi;

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
                                        --w-biotools "communities/$community/resources/curated_tools_w_biotools.tsv"\
                                        --yml "communities/$community/resources/curated_tools.yml"

                                if [[ -e "communities/$community/resources/curated_tools.yml" ]]; then
                                        mkdir -p _data/communities/$community/
                                        ln -sf ../../../communities/$community/resources/curated_tools.yml _data/communities/$community/curated_tools.yml
                                fi;

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


