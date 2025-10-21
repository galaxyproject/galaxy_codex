#!/usr/bin/env bash

# This script is meant to create or update communities labs and is launched weekly (Every Sunday at 8:00 am)
# To add you community, modify `.github/workflows/fetch_filter_resources.yaml` (instructions available in the yaml document)

# This script will create the structure and files needed for the generation of a community lab
# The files are created from generic templates, so you will need to review them and tailor them to your community.
# TODO : The week following the creation of the files in your community folder, review and edit the files to tailor them to your community needs.

## Structure : Creation of the 'Sections' folder
mkdir -p communities/$COMMUNITY/lab/sections/

# Files updated weekly (tools, workflows and tutorial)
## TOOLS
if [ "$COMMUNITY" != "microgalaxy" ]; then
    tools_section="communities/$COMMUNITY/lab/sections/2_tools.yml"
else
    tools_section="communities/$COMMUNITY/lab/sections/4_tools.yml"
fi

### Copy tools file from the template file if it does not yet exist
if [[ ! -e $tools_section ]]; then
    cp communities/all/labs/sections_templates/2_tools.yml $tools_section
fi

### Update the tool file
python sources/bin/extract_galaxy_tools.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --lab $tools_section

### Creates a tools folder (in the communauty lab folder) with one yaml files per tool
python sources/bin/extract_galaxy_tools.py \
    getLabTools \
    --curated communities/$COMMUNITY/resources/curated_tools.tsv \
    --tools communities/$COMMUNITY/lab/tools


## WORKFLOWS
if [ "$COMMUNITY" != "microgalaxy" ]; then  
    workflows_section="communities/$COMMUNITY/lab/sections/3_workflows.yml"
else
    workflows_section="communities/$COMMUNITY/lab/sections/5_workflows.yml"
fi

### Copy workflows file from the template file if it does not yet exist
if [[ ! -e $workflows_section ]]; then
    cp communities/all/labs/sections_templates/3_workflows.yml $workflows_section
fi

### Script to include the expected workflows
python sources/bin/extract_galaxy_workflows.py \
    popLabSection \
    --curated communities/$COMMUNITY/resources/curated_workflows.json \
    --lab $workflows_section

## TUTORIALS
if [ "$COMMUNITY" != "microgalaxy" ]; then
    tutorials_section="communities/$COMMUNITY/lab/sections/4_tutorials.yml"

    ### Copy tutorials file from the template file if it does not yet exist
    if [[ ! -e $tutorials_section ]]; then
        cp communities/all/labs/sections_templates/4_tutorials.yml $tutorials_section
    fi

    ### Update the tutorial file
    python sources/bin/populate_labs_tutorials.py \
        --tsv communities/$COMMUNITY/resources/tutorials.tsv \
        --yml $tutorials_section \
        --title-column Title \
        --description-column Title \
        --button-link-column Link \
        --filter-column Topic \
        --filter $COMMUNITY \
        --filter-logic exclude
else
    python sources/bin/populate_labs_tutorials.py \
        --tsv communities/$COMMUNITY/resources/tutorials.tsv \
        --yml communities/$COMMUNITY/lab/sections/2_microbial_isolates.yml \
        --title-column Title \
        --description-column Title \
        --button-link-column Link \
        --filter-column Topic \
        --filter Microbiome \
        --filter-logic exclude

    python sources/bin/populate_labs_tutorials.py \
        --tsv communities/$COMMUNITY/resources/tutorials.tsv \
        --yml communities/$COMMUNITY/lab/sections/3_microbiome.yml \
        --title-column Title \
        --description-column Title \
        --button-link-column Link \
        --filter-column Topic \
        --filter Microbiome \
        --filter-logic include
fi

# Static files (intro, footer, etc)
# These files are created once at the creation of the lab and need to be updated manually atfer that
## DATA IMPORT AND PREPARATION
### This is general enough to be the same between several communities.
### Some sections are commented at the bottom and are potential addition for your community
data_import_export_section="communities/$COMMUNITY/lab/sections/1_data_import_and_preparation.yml"
if [[ ! -e $data_import_export_section ]]; then
   cp communities/all/labs/sections_templates/1_data_import_and_preparation.yml $data_import_export_section
fi

## SUPPORT AND HELP
if [ "$COMMUNITY" != "microgalaxy" ]; then
    ### This is general enough to be the same between several communities.
    ### Some sections are commented at the bottom and are potential addition for your community
    support_help_section="communities/$COMMUNITY/lab/sections/5_support_and_help.yml"
else
    support_help_section="communities/$COMMUNITY/lab/sections/6_support_and_help.yml"
fi
if [[ ! -e $support_help_section ]]; then
   cp communities/all/labs/sections_templates/5_support_and_help.yml $support_help_section
fi

## COMMUNITY
if [ "$COMMUNITY" != "microgalaxy" ]; then
    ### This need manual review to add links that are community specific (matrix, etc)
    ### Some sections are commented at the bottom and are potential addition for your community
    community_section="communities/$COMMUNITY/lab/sections/6_community.yml"
else
    community_section="communities/$COMMUNITY/lab/sections/7_community.yml"
fi
if [[ ! -e $community_section ]]; then
   cp communities/all/labs/sections_templates/6_community.yml $community_section
fi

## CONTRIBUTORS
contributors="communities/$COMMUNITY/lab/CONTRIBUTORS"
if [[ ! -e $contributors ]]; then
   cp communities/all/labs/page_templates/CONTRIBUTORS $contributors
fi

## README
readme="communities/$COMMUNITY/lab/README.md"
if [[ ! -e $readme ]]; then
   cp communities/all/labs/page_templates/README.md $readme
fi

## Base
base="communities/$COMMUNITY/lab/base.yml"
if [[ ! -e $base ]]; then
   cp communities/all/labs/page_templates/base.yml $base
fi

## Conclusion
conclusion="communities/$COMMUNITY/lab/conclusion.html"
if [[ ! -e $conclusion ]]; then
   cp communities/all/labs/page_templates/conclusion.html $conclusion
fi

## Intro
intro="communities/$COMMUNITY/lab/intro.html"
if [[ ! -e $intro ]]; then
   cp communities/all/labs/page_templates/intro.html $intro
fi
