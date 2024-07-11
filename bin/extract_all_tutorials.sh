#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python bin/extract_gtn_tutorials.py \
                extract \
                --all "results/test_tutorials.json" \
                --tools "results/all_tools.json" \
                --api $PLAUSIBLE_API_KEY \
                --test
else
        python bin/extract_gtn_tutorials.py \
                extract \
                --all "results/all_tutorials.json" \
                --tools "results/all_tools.json" \
                --api $PLAUSIBLE_API_KEY
fi