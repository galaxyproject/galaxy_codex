#!/usr/bin/env bash

mkdir -p 'results/'

output="results/${1}_tools.tsv"

python bin/extract_galaxy_tools.py \
        extractools \
        --api "$GITHUB_API_KEY" \
        --all_tools "$output" \
        --planemorepository "$1"
