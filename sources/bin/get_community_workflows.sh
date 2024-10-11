#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_galaxy_workflows.py \
                filter \
                --all "communities/all/resources/workflows.json" \
                --filtered "communities/microgalaxy/resources/workflows.tsv" \
                --tags "communities/microgalaxy/metadata/workflow_tags"

        python sources/bin/create_interactive_table.py \
                --input "communities/microgalaxy/resources/workflows.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/microgalaxy/resources/workflows.html"

else
        for com_data_fp in data/communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        echo "$community";

                        if [[ -f "data/communities/$community/workflow_tags" ]]; then
                                mkdir -p "results/$community/"

                                python sources/bin/extract_galaxy_workflows.py \
                                        filter \
                                        --all "communities/all/resources/workflows.json" \
                                        --filtered "communities/$community/resources/workflows.tsv" \
                                        --tags "communities/$community/metadata/workflow_tags"

                                python sources/bin/create_interactive_table.py \
                                        --input "communities/$community/resources/workflows.tsv" \
                                        --template "sources/data/interactive_table_template.html" \
                                        --output "communities/$community/resources/workflows.html"
                        fi;
                fi;
        done
fi
