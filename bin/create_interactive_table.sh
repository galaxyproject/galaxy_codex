#!/usr/bin/env bash

mkdir -p 'results/microgalaxy'

python bin/create_interactive_table.py \
        --table 'results/microgalaxy/tools.tsv' \
        --template 'data/datatable_template.html' \
        --output 'results/microgalaxy/index.html'
