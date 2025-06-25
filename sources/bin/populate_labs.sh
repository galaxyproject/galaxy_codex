#!/usr/bin/env bash

#This scirpt is meant to create or update a community lab. 
#To launch this script, you need to do so manually from the GitHub action
#Potential future upgrade : Weekly update labs for each community with active labs

## Change the community variable to match your community
COMMUNITY="biodiversity"

#Tools
#This creates a tools folder (in the communauty lab folder) with one yaml files per tool
python sources/bin/extract_galaxy_tools.py \
    getLabTools \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --tools communities/$COMMUNITY/lab/tools

#This creates or update the tool file
tools_file="communities/$COMMUNITY/lab/sections/4_tools.yml"
#Copy tool file from another community if they do not yet exist
if [[ ! -e $tools_file ]]; then
    mkdir communities/$COMMUNITY/lab/sections/
    cp communities/microgalaxy/lab/sections/4_tools.yml $tools_file
fi
#Update the tool file
python sources/bin/extract_galaxy_tools.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --lab $tools_file

#Workflows
workflows_file="communities/$COMMUNITY/lab/sections/5_workflows.yml"
#Copy file from another community if they do not yet exist
if [[ ! -e $workflows_file ]]; then
    cp communities/microgalaxy/lab/sections/5_workflows.yml $workflows_file
fi
#Script to include the expected workflows
python sources/bin/extract_galaxy_workflows.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_workflows.json \
    --lab $workflows_file


#Tutorials
tutorials_file="communities/$COMMUNITY/lab/sections/6_tutorials.yml"

if [[ ! -e "$tutorials_file" ]]; then
    # Optionally copy a template if needed
    # cp "communities/microgalaxy/lab/sections/5_workflows.yml" "$tutorials_file"

    # Create the file with correct indentation (no leading spaces)
    cat <<EOF > "$tutorials_file"
id: Tutorials
title: Community tutorials
tabs:
id: tutorials
EOF
fi

echo "tutorials_file"
echo $tutorials_file

#Update the tutorial file
python sources/bin/populate_labs_tutorials.py \
    --tsv communities/$COMMUNITY/resources/tutorials.tsv \
    --yml $tutorials_file \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter $COMMUNITY \
    --filter-logic exclude

#awk '
#/^- id: best_practices/ {flag=1; next}
#/^- id:/ {flag=0}
#!flag
#' communities/biodiversity/lab/sections/6_tutorials.yml > tmp.yml && mv tmp.yml communities/biodiversity/lab/sections/6_tutorials.yml

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
