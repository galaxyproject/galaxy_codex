#!/usr/bin/env bash

## Change the community variable to match your community
COMMUNITY="biodiversity"

#Tools - Works (stand alone)
python sources/bin/extract_galaxy_tools.py \
    getLabTools \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --tools communities/$COMMUNITY/lab/tools
    
#Copy tool file from another community if they do not yet exist
if [[ ! -e communities/$COMMUNITY/lab/sections/4_tools.yml ]]; then
    mkdir communities/$COMMUNITY/lab/sections/
    cp communities/microgalaxy/lab/sections/4_tools.yml communities/$COMMUNITY/lab/sections/4_tools.yml
fi
#Update the tool file
python sources/bin/extract_galaxy_tools.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --lab communities/$COMMUNITY/lab/sections/4_tools.yml

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
id: workflows
title: Community workflows
tabs:
EOF
fi

#Update the tutorial file
python sources/bin/populate_labs_tutorials.py \
    --tsv communities/$COMMUNITY/resources/tutorials.tsv \
    --yml communities/$COMMUNITY/lab/sections/6_tutorials.yml \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter $COMMUNITY \
    --filter-logic exclude

awk '
/^- id: best_practices/ {flag=1; next}
/^- id:/ {flag=0}
!flag
' communities/biodiversity/lab/sections/6_tutorials.yml > tmp.yml && mv tmp.yml communities/biodiversity/lab/sections/6_tutorials.yml

awk '
/^- id: iwc/ {flag=1; next}
/^- id:/ {flag=0}
!flag
' communities/biodiversity/lab/sections/6_tutorials.yml > tmp.yml && mv tmp.yml communities/biodiversity/lab/sections/6_tutorials.yml

awk '
/^- id: other_workflowhub/ {flag=1; next}
/^- id:/ {flag=0}
!flag
' communities/biodiversity/lab/sections/6_tutorials.yml > tmp.yml && mv tmp.yml communities/biodiversity/lab/sections/6_tutorials.yml


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
