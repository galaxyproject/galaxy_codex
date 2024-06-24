#!/usr/bin/env bash

mkdir -p 'results/'

tsv_output="results/${1}_tools.tsv"
json_output="results/${1}_tools.json"

python bin/extract_gtn_tutorials.py \
        extracttutorials \
        --all_tutorials "results/test_tutorials.json" \
        --tools "results/all_tools.json" \
        --api $PLAUSIBLE_API_KEY \
        --test

if [[ ! -f "results/test_tutorials.json" ]] ; then
    echo 'File "results/test_tutorials.json" is not there, aborting.'
    exit
fi

python bin/extract_gtn_tutorials.py \
        filtertutorials \
        --all_tutorials "results/test_tutorials.json" \
        --filtered_tutorials "results/microgalaxy/test_tutorials.tsv" \
        --tags "data/communities/microgalaxy/tutorial_tags"

if [[ ! -f "results/microgalaxy/test_tutorials.tsv" ]] ; then
    echo 'File "results/microgalaxy/test_tutorials.tsv" is not there, aborting.'
    exit
fi

rm "results/test_tutorials.json"
rm "results/microgalaxy/test_tutorials.tsv"
