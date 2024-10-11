#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python bin/extract_galaxy_workflows.py extract \
                --all results/workflows.json \
                --tools results/all_tools.json \
                --test
else
        python bin/extract_galaxy_workflows.py extract \
                --all results/workflows.json \
                --tools results/all_tools.json
fi