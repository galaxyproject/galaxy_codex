#!/usr/bin/env bash

mkdir -p 'results/'

python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all-tools 'results/all_tools.tsv' \
        --all-tools-json 'results/all_tools.json'

python bin/create_interactive_table.py \
        --table "results/all_tools.tsv" \
        --template "data/interactive_table_template.html" \
        --output "results/index.html"