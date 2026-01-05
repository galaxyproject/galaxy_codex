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
                        
                        python sources/bin/citation_manager.py \
                                filter \
                                --all-json "communities/all/resources/citations.json" \
                                --filtered-json "communities/$community/resources/citations.json" \
                                --filtered-yaml "communities/$community/resources/citations.yml" \
                                --filtered-tsv "communities/$community/resources/citations.tsv" \
                                --keywords "communities/$community/metadata/citation_keywords"

                        if [[ -f "communities/$community/metadata/citations.yml" ]]; then
                                mkdir -p _data/communities/$community/
                                ln -sf ../../../communities/$community/resources/citations.yml _data/communities/$community/citations.yml
                        fi;
                fi;
        fi;
done
