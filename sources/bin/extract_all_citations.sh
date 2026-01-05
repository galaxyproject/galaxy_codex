#!/usr/bin/env bash

if [ ! -z $1 ] 
then
    python sources/bin/citation_manager.py \
        extract \
        --all-json 'communities/all/resources/citations.json' \
        --all-yaml 'communities/all/resources/citations.yml' \
        --all-tsv 'communities/all/resources/citations.tsv' \
        --test
else
    python sources/bin/citation_manager.py \
        extract \
        --all-json 'communities/all/resources/citations.json' \
        --all-yaml 'communities/all/resources/citations.yml' \
        --all-tsv 'communities/all/resources/citations.tsv'
fi
