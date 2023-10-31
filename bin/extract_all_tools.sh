#!/usr/bin/env bash

python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all_tools 'results/all_tools.tsv'