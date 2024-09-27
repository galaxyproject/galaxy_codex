#!/usr/bin/env bash

for com_data_fp in communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                echo "$community";

                if [[ -f "communities/$community/metadata/tools_to_exclude" && -f "communities/$community/metadata/tools_to_keep" && -f "communities/$community/resources/tutorials.tsv" ]]; then

                        python sources/bin/compare_tools.py \
                                --filtered_tutorials "communities/$community/resources/tutorials.tsv" \
                                --exclude "communities/$community/metadata/tools_to_exclude" \
                                --keep "communities/$community/metadata/tools_to_keep" \
                                --all_tools "communities/all/resources/tools.tsv"
                fi;
        fi;
done