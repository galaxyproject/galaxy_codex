#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_gtn_tutorials.py \
                filter \
                --all "communities/all/resources/test_tutorials.json" \
                --filtered "communities/microgalaxy/resources/test_tutorials.tsv" \
                --tags "communities/microgalaxy/metadata/tutorial_tags"

        python sources/bin/create_interactive_table.py \
                --input "communities/microgalaxy/resources/tutorials.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/microgalaxy/resources/tutorials.html"

else
        for com_data_fp in data/communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        echo "$community";

                        if [[ -f "data/communities/$community/tutorial_tags" && -f "results/$community/tutorials.tsv" ]]; then

                                python sources/bin/extract_gtn_tutorials.py \
                                        filter \
                                        --all "communities/all/resources/tutorials.json" \
                                        --filtered "communities/$community/resources/tutorials.tsv" \
                                        --tags "communities/$community/metadata/tutorial_tags"

                                python sources/bin/create_interactive_table.py \
                                        --input "communities/$community/resources/tutorials.tsv" \
                                        --template "sources/data/interactive_table_template.html" \
                                        --output "communities/$community/resources/tutorials.html"
                        fi;
                fi;
        done
fi
