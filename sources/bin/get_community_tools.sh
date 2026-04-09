#!/usr/bin/env bash

# stop on error
set -e 

#for com_data_fp in communities/* ; do
#        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
#                community=`basename "$com_data_fp"`

                if [[ ! -z $1  && $1 == "test" && "$COMMUNITY" != "microgalaxy" ]]; then
                        continue
                fi;

                if [[ "$COMMUNITY" != "all" && -f "communities/$COMMUNITY/metadata/categories" ]]; then
                        echo "$COMMUNITY";
                        mkdir -p "communities/$COMMUNITY/resources"

                        python sources/bin/extract_galaxy_tools.py \
                                filter \
                                --all "communities/all/resources/tools.json" \
                                --categories "communities/$COMMUNITY/metadata/categories" \
                                --filtered "communities/$COMMUNITY/resources/tools_filtered_by_ts_categories.json" \
                                --status "communities/$COMMUNITY/metadata/tool_status.tsv"

                        if [[ -e "communities/$COMMUNITY/metadata/tool_status.tsv" ]]; then
                                python sources/bin/extract_galaxy_tools.py \
                                        curate \
                                        --filtered "communities/$COMMUNITY/resources/tools_filtered_by_ts_categories.json" \
                                        --status "communities/$COMMUNITY/metadata/tool_status.tsv" \
                                        --curated "communities/$COMMUNITY/resources/curated_tools.tsv" \
                                        --wo-biotools "communities/$COMMUNITY/resources/curated_tools_wo_biotools.tsv" \
                                        --w-biotools "communities/$COMMUNITY/resources/curated_tools_w_biotools.tsv"\
                                        --yml "communities/$COMMUNITY/resources/curated_tools.yml"

                                if [[ -e "communities/$COMMUNITY/resources/curated_tools.yml" ]]; then
                                        mkdir -p _data/communities/$COMMUNITY/
                                        ln -sf ../../../communities/$COMMUNITY/resources/curated_tools.yml _data/communities/$COMMUNITY/curated_tools.yml
                                fi;

                                if [[ -e "communities/$COMMUNITY/resources/curated_tools.tsv" ]]; then
                                        python sources/bin/create_wordcloud.py \
                                                --input "communities/$COMMUNITY/resources/curated_tools.tsv" \
                                                --name-col "Suite ID" \
                                                --stat-col "Suite runs (last 5 years) on main servers" \
                                                --wordcloud_mask "sources/data/usage_stats/wordcloud_mask.png" \
                                                --output "communities/$COMMUNITY/resources/tools_wordcloud.png"

                                        python sources/bin/create_interactive_table.py \
                                                --input "communities/$COMMUNITY/resources/curated_tools.tsv" \
                                                --template "sources/data/interactive_table_template.html" \
                                                --output "communities/$COMMUNITY/resources/tools.html"
                                fi;
                        fi;
                fi
#        fi;
#done


