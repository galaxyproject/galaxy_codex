#!/usr/bin/env bash

## Change the community variable to match your community
COMMUNITY="biodiversity"

#Tools - Works (stand alone)
python sources/bin/extract_galaxy_tools.py \
    getLabTools \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --tools communities/$COMMUNITY/lab/tools

#Workflows
python sources/bin/extract_galaxy_workflows.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_workflows.json \
    --lab communities/$COMMUNITY/lab/sections/5_workflows.yml

#Copy files from another community if they do not yet exist
if [[ ! -e communities/$COMMUNITY/lab/sections/4_tools.yml ]]; then
    mkdir communities/$COMMUNITY/lab/sections/
    cp communities/microgalaxy/lab/sections/4_tools.yml communities/$COMMUNITY/lab/sections/4_tools.yml
fi

if [[ ! -e communities/$COMMUNITY/lab/sections/5_workflows.yml ]]; then
    cp communities/microgalaxy/lab/sections/5_workflows.yml communities/$COMMUNITY/lab/sections/5_workflows.yml
fi

if [[ ! -e communities/$COMMUNITY/lab/sections/6_tutorials.yml ]]; then
    cp communities/microgalaxy/lab/sections/6_tutorials.yml communities/$COMMUNITY/lab/sections/6_tutorials.yml
fi


: '
python sources/bin/extract_galaxy_tools.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --lab communities/$COMMUNITY/lab/sections/4_tools.yml



#Tutorials
python sources/bin/populate_labs_tutorials.py \
    --tsv communities/$COMMUNITY/resources/tutorials.tsv \
    --yml communities/$COMMUNITY/lab/sections/6_tutorials.yml \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter $COMMUNITY \
    --filter-logic exclude
'
# Below are scripts used by the microgalaxy community:
#python sources/bin/populate_labs_tutorials.py \
#    --tsv communities/microgalaxy/resources/tutorials.tsv \
#    --yml communities/microgalaxy/lab/sections/2_microbial_isolates.yml \
#    --title-column Title \
#    --description-column Title \
#    --button-link-column Link \
#    --filter-column Topic \
#    --filter Microbiome \
#    --filter-logic exclude

#python sources/bin/populate_labs_tutorials.py \
#    --tsv communities/microgalaxy/resources/tutorials.tsv \
#    --yml communities/microgalaxy/lab/sections/3_microbiome.yml \
#    --title-column Title \
#    --description-column Title \
#    --button-link-column Link \
#    --filter-column Topic \
#    --filter Microbiome \
#    --filter-logic include
