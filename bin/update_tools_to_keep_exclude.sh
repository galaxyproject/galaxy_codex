#!/usr/bin/env bash

for com_data_fp in data/communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                echo "$community";

                if [[ -f "data/communities/$community/tools_to_exclude" && -f "data/communities/$community/tools_to_keep" && -f "results/$community/tutorials.tsv" ]]; then

                        python bin/compare_tools.py \
                                --filtered_tutorials "results/$community/tutorials.tsv" \
                                --exclude "data/communities/$community/tools_to_exclude" \
                                --keep "data/communities/$community/tools_to_keep" \
                                --all_tools "results/all_tools.tsv"
                fi;
        fi;
done