#!/usr/bin/env bash

mkdir -p 'results/'

python bin/create_interactive_table.py \
        --table "results/all_tools.tsv" \
        --template "data/interactive_table_template.html" \
        --output "results/index.html"