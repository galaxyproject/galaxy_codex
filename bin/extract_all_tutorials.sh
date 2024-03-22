#!/usr/bin/env bash

python bin/extract_all_gtn_tutorials.py \
        extracttutorials \
        --all_tutorials "results/all_tutorials.json" \
        --tools "results/all_tools.tsv" \
        --api $PLAUSIBLE_API_KEY