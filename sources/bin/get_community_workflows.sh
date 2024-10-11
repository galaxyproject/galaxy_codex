#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python bin/extract_galaxy_workflows.py \
                filter \
                --all "results/workflows.json" \
                --filtered "results/microgalaxy/test_workflows.tsv" \
                --tags "data/communities/microgalaxy/workflow_tags"

        python bin/create_interactive_table.py \
                --input "results/microgalaxy/workflows.tsv" \
                --template "data/interactive_table_template.html" \
                --output "results/microgalaxy/workflows.html"

else
        for com_data_fp in data/communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        echo "$community";

                        if [[ -f "data/communities/$community/workflow_tags" ]]; then
                                mkdir -p "results/$community/"

                                python bin/extract_galaxy_workflows.py \
                                        filter \
                                        --all "results/workflows.json" \
                                        --filtered "results/$community/workflows.tsv" \
                                        --tags "data/communities/$community/workflow_tags"

                                python bin/create_interactive_table.py \
                                        --input "results/$community/workflows.tsv" \
                                        --template "data/interactive_table_template.html" \
                                        --output "results/$community/workflows.html"
                        fi;
                fi;
        done
fi
