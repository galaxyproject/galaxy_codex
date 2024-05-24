#!/usr/bin/env bash

mkdir -p 'results/'

tsv_output="results/${1}_tools.tsv"
json_output="results/${1}_tools.json"

python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all_tools $tsv_output \
        --all-tools-json $json_output \
        --planemorepository $1 \
        --test

