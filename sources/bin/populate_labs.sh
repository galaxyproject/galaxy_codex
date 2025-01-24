#!/usr/bin/env bash

## MICROGALAXY LAB

python sources/bin/populate_labs_tools.py \
    --tool_tsv communities/microgalaxy/resources/curated_tools.tsv \
    --tool_yml communities/microgalaxy/lab/sections/4_tools.yml

python sources/bin/populate_labs_workflows_tutorials.py \
    --tsv communities/microgalaxy/resources/tutorials.tsv \
    --yml communities/microgalaxy/lab/sections/tutorials_isolates_snippet.yml \
    -tc Title \
    -dc Title \
    -blc Link \
    -fc Topic \
    -fi Microbiome \
    -fl exclude

python sources/bin/populate_labs_workflows_tutorials.py \
    --tsv communities/microgalaxy/resources/tutorials.tsv \
    --yml communities/microgalaxy/lab/sections/tutorials_microbiome_snippet.yml \
    -tc Title \
    -dc Title \
    -blc Link \
    -fc Topic \
    -fi Microbiome \
    -fl include

python sources/bin/populate_labs_workflows_tutorials.py \
    --tsv communities/microgalaxy/resources/workflows.tsv \
    --yml communities/microgalaxy/lab/sections/workflows_isolate_snippet.yml \
    -tc Name \
    -dc Name \
    -blc Link \
    -fc Tags \
    -fi "metagenomics, metatranscriptomics" \
    -fl exclude

python sources/bin/populate_labs_workflows_tutorials.py \
    --tsv communities/microgalaxy/resources/workflows.tsv \
    --yml communities/microgalaxy/lab/sections/workflows_microbiome_snippet.yml \
    -tc Name \
    -dc Name \
    -blc Link \
    -fc Tags \
    -fi "metagenomics, metatranscriptomics" \
    -fl include