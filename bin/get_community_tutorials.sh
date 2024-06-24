#!/usr/bin/env bash

for com_data_fp in data/communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                echo "$community";

                if [[ -f "data/communities/$community/tutorial_tags" && -f "results/$community/tutorials.tsv" ]]; then

                        python bin/extract_gtn_tutorials.py \
                                filtertutorials \
                                --all_tutorials "results/all_tutorials.json" \
                                --filtered_tutorials "results/$community/tutorials.tsv" \
                                --tags "data/communities/$community/tutorial_tags"
                fi;
        fi;
done
