#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python bin/extract_gtn_tutorials.py \
                filter \
                --all "results/test_tutorials.json" \
                --filtered "results/microgalaxy/test_tutorials.tsv" \
                --tags "data/communities/microgalaxy/tutorial_tags"

else
        for com_data_fp in data/communities/* ; do
                if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                        community=`basename "$com_data_fp"`

                        echo "$community";

                        if [[ -f "data/communities/$community/tutorial_tags" && -f "results/$community/tutorials.tsv" ]]; then

                                python bin/extract_gtn_tutorials.py \
                                        filter \
                                        --all "results/all_tutorials.json" \
                                        --filtered "results/$community/tutorials.tsv" \
                                        --tags "data/communities/$community/tutorial_tags"
                        fi;
                fi;
        done
fi
