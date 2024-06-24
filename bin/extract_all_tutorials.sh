#!/usr/bin/env bash

python bin/extract_gtn_tutorials.py \
        extracttutorials \
        --all_tutorials "results/all_tutorials.json" \
        --tools "results/all_tools.json" \
        --api $PLAUSIBLE_API_KEY