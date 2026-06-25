#!/usr/bin/env bash

#for com_data_fp in communities/* ; do
#        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
#                community=`basename "$com_data_fp"`
                if [[ ! -z $1  && $1 == "test"  && "$COMMUNITY" != "microgalaxy" ]]; then
                        continue
                fi;

                if [[ "$COMMUNITY" != "all" && -f "communities/$COMMUNITY/metadata/tutorial_tags" ]]; then
                        echo "$COMMUNITY";
                        mkdir -p "communities/$COMMUNITY/resources"
                        
                        python sources/bin/extract_gtn_tutorials.py \
                                filter \
                                --all "communities/all/resources/tutorials.json" \
                                --yml "communities/$COMMUNITY/resources/tutorials.yml" \
                                --filtered "communities/$COMMUNITY/resources/tutorials.tsv" \
                                --tags "communities/$COMMUNITY/metadata/tutorial_tags"

                        if [[ -f "communities/$COMMUNITY/resources/tutorials.yml" ]]; then
                                mkdir -p _data/communities/$COMMUNITY/
                                ln -sf ../../../communities/$COMMUNITY/resources/tutorials.yml _data/communities/$COMMUNITY/tutorials.yml
                        fi;

                        if [[ -e "communities/$COMMUNITY/resources/tutorials.tsv" ]]; then                        
                                python sources/bin/create_interactive_table.py \
                                        --input "communities/$COMMUNITY/resources/tutorials.tsv" \
                                        --template "sources/data/interactive_table_template.html" \
                                        --output "communities/$COMMUNITY/resources/tutorials.html"
                        fi;
                fi
#        fi;
#done
