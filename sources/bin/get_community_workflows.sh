#!/usr/bin/env bash

#for com_data_fp in communities/* ; do
#        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
#                community=`basename "$com_data_fp"`

                if [[ ! -z $1  && $1 == "test" && "$COMMUNITY" != "microgalaxy" ]]; then
                        continue
                fi;
                

                if [[ "$COMMUNITY" != "all" &&  -f "communities/$COMMUNITY/metadata/workflow_tags" ]]; then
                        echo "$COMMUNITY";
                        python sources/bin/extract_galaxy_workflows.py \
                                filter \
                                --all "communities/all/resources/workflows.json" \
                                --filtered "communities/$COMMUNITY/resources/tag_filtered_workflows.json" \
                                --tsv-filtered "communities/$COMMUNITY/resources/tag_filtered_workflows.tsv" \
                                --tags "communities/$COMMUNITY/metadata/workflow_tags" \
                                --status "communities/$COMMUNITY/metadata/workflow_status.tsv"

                        if [[ -f "communities/$COMMUNITY/metadata/workflow_status.tsv" ]]; then
                                python sources/bin/extract_galaxy_workflows.py \
                                        curate \
                                        --filtered "communities/$COMMUNITY/resources/tag_filtered_workflows.json" \
                                        --status "communities/$COMMUNITY/metadata/workflow_status.tsv" \
                                        --curated "communities/$COMMUNITY/resources/curated_workflows.json" \
                                        --tsv-curated "communities/$COMMUNITY/resources/curated_workflows.tsv" \
                                        --yml "communities/$COMMUNITY/resources/curated_workflows.yml"

                                if [[ -f "communities/$COMMUNITY/metadata/curated_workflows.yml" ]]; then
                                        mkdir -p _data/communities/$COMMUNITY/
                                        ln -sf ../../../communities/$COMMUNITY/resources/curated_workflows.yml _data/communities/$COMMUNITY/curated_workflows.yml
                                fi;

                                if [[ -e "communities/$COMMUNITY/resources/curated_workflows.tsv" ]]; then                        
                                        python sources/bin/create_interactive_table.py \
                                                --input "communities/$COMMUNITY/resources/curated_workflows.tsv" \
                                                --template "sources/data/interactive_table_template.html" \
                                                --output "communities/$COMMUNITY/resources/workflows.html"
                                fi;
                        fi;
                fi
#        fi;
#done
