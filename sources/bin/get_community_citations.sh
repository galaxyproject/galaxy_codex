#!/usr/bin/env bash

#for com_data_fp in communities/* ; do
#        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
#                community=`basename "$com_data_fp"`
                if [[ ! -z $1  && $1 == "test"  && "$COMMUNITY" != "microgalaxy" ]]; then
                        continue
                fi;

                if [[ "$COMMUNITY" != "all" && -f "communities/$COMMUNITY/metadata/citation_keywords" ]]; then
                        echo "$COMMUNITY";
                        mkdir -p "communities/$COMMUNITY/resources"
                        
                        python sources/bin/citation_manager.py \
                                filter \
                                --all-json "communities/all/resources/citations.json" \
                                --filtered-json "communities/$COMMUNITY/resources/citations.json" \
                                --filtered-yaml "communities/$COMMUNITY/resources/citations.yml" \
                                --filtered-tsv "communities/$COMMUNITY/resources/citations.tsv" \
                                --keywords "communities/$COMMUNITY/metadata/citation_keywords"

                        if [[ -f "communities/$COMMUNITY/metadata/citations.yml" ]]; then
                                mkdir -p _data/communities/$COMMUNITY/
                                ln -sf ../../../communities/$COMMUNITY/resources/citations.yml _data/communities/$COMMUNITY/citations.yml
                        fi;
                fi
#        fi;
#done
