#!/usr/bin/env bash

mkdir -p 'results/'

python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all_tools 'results/all_tools.tsv'