#!/usr/bin/env bash

if [ ! -z $1 ] 
then
    if [ $1 == "test" ]
    then 
        python sources/bin/citation_manager.py \
            extract \
            --publications 'communities/all/metadata/major_publications.json' \
            --all-json 'communities/all/resources/citations.json' \
            --all-yaml 'communities/all/resources/citations.yml' \
            --all-tsv 'communities/all/resources/citations.tsv' \
            --test \
            --no-scholarly
    else
        python sources/bin/citation_manager.py \
            extract \
            --publications 'communities/all/metadata/major_publications.json' \
            --all-json 'communities/all/resources/citations.json' \
            --all-yaml 'communities/all/resources/citations.yml' \
            --all-tsv 'communities/all/resources/citations.tsv' \
            --no-scholarly
    fi
else
    python sources/bin/citation_manager.py \
        extract \
        --publications 'communities/all/metadata/major_publications.json' \
        --all-json 'communities/all/resources/citations.json' \
        --all-yaml 'communities/all/resources/citations.yml' \
        --all-tsv 'communities/all/resources/citations.tsv'
fi
