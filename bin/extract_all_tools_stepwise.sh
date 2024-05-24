#!/usr/bin/env bash

mkdir -p 'results/'

output="results/${1}_tools.tsv"

if [[ $1 =~ "01" ]]; then
   python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all-tools $output \
        --planemo-repository-list $1
else
   python bin/extract_galaxy_tools.py \
        extractools \
        --api $GITHUB_API_KEY \
        --all-tools $output \
        --planemo-repository-list $1 \
        --avoid-extra-repositories
fi



