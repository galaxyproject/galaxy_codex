#!/usr/bin/env bash

for com_data_fp in communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`
                if [[ ! -z $1  && $1 == "test"  && "$community" != "microgalaxy" ]]; then
                        continue
                fi;

                if [[ "$community" != "all" && -f "communities/$community/metadata/tutorial_tags" ]]; then
                        echo "$community";
                        mkdir -p "communities/$community/resources"
                        
                        python sources/bin/extract_gtn_tutorials.py \
                                filter \
                                --all "communities/all/resources/tutorials.json" \
                                --yml "communities/$community/resources/tutorials.yml" \
                                --filtered "communities/$community/resources/tutorials.tsv" \
                                --tags "communities/$community/metadata/tutorial_tags"

                        if [[ -f "communities/$community/resources/tutorials.yml" ]]; then
                                mkdir -p _data/communities/$community/
                                ln -sf ../../../communities/$community/resources/tutorials.yml _data/communities/$community/tutorials.yml
                                #For pages - Can't copy from template, need to copy from existing md file
                                cp pages/microgalaxy_tutorials.md pages/${community}_tutorials.md
                                sed -i -e "s/microgalaxy/${community}/g" pages/${community}_tutorials.md
                                #For _includes - To keep same process as above, copying from existing file
                                mkdir -p _includes/communities/$community/
                                cp _includes/communities/microgalaxy/tutorials.html _includes/communities/$community/tutorials.html
                                sed -i -e "s/microgalaxy/${community}/g" _includes/communities/$community/tutorials.html
                        fi;

                        if [[ -e "communities/$community/resources/tutorials.tsv" ]]; then                        
                                python sources/bin/create_interactive_table.py \
                                        --input "communities/$community/resources/tutorials.tsv" \
                                        --template "sources/data/interactive_table_template.html" \
                                        --output "communities/$community/resources/tutorials.html"
                        fi;
                fi;
        fi;
done
