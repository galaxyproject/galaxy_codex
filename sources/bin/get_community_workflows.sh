#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_galaxy_workflows.py \
                filter \
                --all "communities/all/resources/test_workflows.json" \
                --filtered "communities/microgalaxy/resources/test_workflows.json" \
                --tsv-filtered "communities/microgalaxy/resources/test_workflows.tsv" \
                --tags "communities/microgalaxy/metadata/workflow_tags" \
                --status "communities/microgalaxy/metadata/test_workflow_status.tsv"

        python sources/bin/extract_galaxy_workflows.py \
                curate \
                --filtered "communities/microgalaxy/resources/test_workflows.json" \
                --status "communities/microgalaxy/metadata/test_workflow_status.tsv" \
                --curated "communities/microgalaxy/resources/test_curated_workflows.tsv" \
                --tsv-curated "communities/microgalaxy/resources/test_curated_workflows.tsv" \
                --yml "communities/microgalaxy/resources/test_curated_workflows.yml"
else
        for com_data_fp in communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        

                        if [[ "$community" != "all" &&  -f "communities/$community/metadata/workflow_tags" ]]; then
                                echo "$community";
                                python sources/bin/extract_galaxy_workflows.py \
                                        filter \
                                        --all "communities/all/resources/workflows.json" \
                                        --filtered "communities/$community/resources/tag_filtered_workflows.json" \
                                        --tsv-filtered "communities/$community/resources/tag_filtered_workflows.tsv" \
                                        --tags "communities/$community/metadata/workflow_tags" \
                                        --status "communities/$community/metadata/workflow_status.tsv"

                                if [[ -f "communities/$community/metadata/workflow_status.tsv" ]]; then
                                        python sources/bin/extract_galaxy_workflows.py \
                                                curate \
                                                --filtered "communities/$community/resources/tag_filtered_workflows.json" \
                                                --status "communities/$community/metadata/workflow_status.tsv" \
                                                --curated "communities/$community/resources/curated_workflows.json" \
                                                --tsv-curated "communities/$community/resources/curated_workflows.tsv" \
                                                --yml "communities/$community/resources/curated_workflows.yml"

                                        if [[ -f "communities/$community/metadata/curated_workflows.yml" ]]; then
                                                mkdir -p _data/communities/$community/
                                                ln -sf ../../../communities/$community/resources/curated_workflows.yml _data/communities/$community/curated_workflows.yml
                                        fi;
                                fi;
                        fi;
                fi;
        done
fi
