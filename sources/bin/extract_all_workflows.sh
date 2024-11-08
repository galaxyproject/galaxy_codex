#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_galaxy_workflows.py extract \
                --all communities/all/resources/test_workflows.json \
                --tools communities/all/resources/test_tools.json \
                --test
else
        python sources/bin/extract_galaxy_workflows.py extract \
                --all communities/all/resources/workflows.json \
                --tools communities/all/resources/tools.json
fi