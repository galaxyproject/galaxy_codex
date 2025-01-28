#!/usr/bin/env bash

## MICROGALAXY LAB

python sources/bin/populate_labs_tools.py \
    --tool_tsv communities/microgalaxy/resources/curated_tools.tsv \
    --tool_yml communities/microgalaxy/lab/sections/4_tools.yml

python sources/bin/populate_labs_tutorials.py \
    --tsv communities/microgalaxy/resources/tutorials.tsv \
    --yml communities/microgalaxy/lab/sections/2_microbial_isolates.yml \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter Microbiome \
    --filter-logic exclude

python sources/bin/populate_labs_tutorials.py \
    --tsv communities/microgalaxy/resources/tutorials.tsv \
    --yml communities/microgalaxy/lab/sections/3_microbiome.yml \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter Microbiome \
    --filter-logic include

python sources/bin/populate_labs_workflows.py \
    --tsv communities/microgalaxy/resources/curated_workflows.tsv \
    --yml communities/microgalaxy/lab/sections/5_workflows.yml