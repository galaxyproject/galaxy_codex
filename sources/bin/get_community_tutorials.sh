#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_gtn_tutorials.py \
                filter \
                --all "communities/all/resources/test_tutorials.json" \
                --yml "communities/microgalaxy/resources/test_tutorials.yml" \
                --filtered "communities/microgalaxy/resources/test_tutorials.tsv" \
                --tags "communities/microgalaxy/metadata/tutorial_tags"

        python sources/bin/create_interactive_table.py \
                --input "communities/microgalaxy/resources/tutorials.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/microgalaxy/resources/tutorials.html"

else
        for com_data_fp in communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`
                        if [ "$community" != "all" ]; then
                                echo "$community"

                                if [[ -f "communities/$community/metadata/tutorial_tags" ]]; then
                                        echo "Filter tutorials"

                                        python sources/bin/extract_gtn_tutorials.py \
                                                filter \
                                                --all "communities/all/resources/tutorials.json" \
                                                --yml "communities/$community/resources/tutorials.yml" \
                                                --filtered "communities/$community/resources/tutorials.tsv" \
                                                --tags "communities/$community/metadata/tutorial_tags"

                                        mkdir -p _data/communities/$community/
                                        ln -sf ../../../communities/$community/resources/tutorials.yml _data/communities/$community/tutorials.yml

                                        python sources/bin/create_interactive_table.py \
                                                --input "communities/$community/resources/tutorials.tsv" \
                                                --template "sources/data/interactive_table_template.html" \
                                                --output "communities/$community/resources/tutorials.html"
                                fi;
                                
                                echo ""
                        fi;
                fi;
        done
fi
