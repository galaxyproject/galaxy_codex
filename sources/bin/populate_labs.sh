#!/usr/bin/env bash

#This scirpt is meant to create or update a community lab. 
#To launch this script, you need to do so manually from the GitHub action
#Potential future upgrade : Weekly update labs for each community with active labs

## Change the community variable to match your community
COMMUNITY="biodiversity"

##Sections
mkdir -p communities/$COMMUNITY/lab/sections/

#Each section must be reviewed the first time before publication!!

# Data import and preparation
#This is general enough to be the same between several communities.
#Some sections are commented at the bottom and are potential addition for your community
data_import_export_section="communities/$COMMUNITY/lab/sections/1_data_import_and_preparation.yml
if [[ ! -e $data_import_export_section ]]; then
   cp communities/all/labs/sections_templates/1_data_import_and_preparation.yml $data_import_export_section
fi

#Tools
#This creates or update the tool file
tools_section="communities/$COMMUNITY/lab/sections/2_tools.yml"
#Copy tools file from the template file if it does not yet exist
if [[ ! -e $tools_section ]]; then
    cp communities/all/labs/sections_templates/2_tools.yml $tools_section
fi
#Update the tool file
python communities/all/labs/extract_galaxy_tools.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --lab $tools_section

#Workflows
workflows_section="communities/$COMMUNITY/lab/sections/3_workflows.yml"
#Copy workflows file from the template file if it does not yet exist
if [[ ! -e $workflows_section ]]; then
    cp communities/all/labs/sections_templates/3_workflows.yml $workflows_section
fi

#Script to include the expected workflows
python communities/all/labs/extract_galaxy_workflows.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_workflows.json \
    --lab $workflows_section


#Tutorials
tutorials_section="communities/$COMMUNITY/lab/sections/4_tutorials.yml"

#Copy tutorials file from the template file if it does not yet exist
if [[ ! -e $tutorials_section ]]; then
    cp communities/all/labs/sections_templates/4_tutorials.yml $tutorials_section
fi

#Update the tutorial file
python sources/bin/populate_labs_tutorials.py \
    --tsv communities/$COMMUNITY/resources/tutorials.tsv \
    --yml $tutorials_section \
    --title-column Title \
    --description-column Title \
    --button-link-column Link \
    --filter-column Topic \
    --filter $COMMUNITY \
    --filter-logic exclude

#Support and Help
#This is general enough to be the same between several communities.
#Some sections are commented at the bottom and are potential addition for your community
support_help_section="communities/$COMMUNITY/lab/sections/5_support_and_help.yml
if [[ ! -e $support_help_section ]]; then
   cp communities/all/labs/sections_templates/5_support_and_help.yml $support_help_section
fi

#Comunity
#This need manual review to add links that are community specific (matrix, etc)
#Some sections are commented at the bottom and are potential addition for your community
community_section="communities/$COMMUNITY/lab/sections/6_community.yml
if [[ ! -e $community_section ]]; then
   cp communities/all/labs/sections_templates/6_community.yml $community_section
fi

##Tools
#This creates a tools folder (in the communauty lab folder) with one yaml files per tool
python sources/bin/extract_galaxy_tools.py \
    getLabTools \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --tools communities/$COMMUNITY/lab/tools


# Below are scripts used by the microgalaxy community to create other sections:
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
