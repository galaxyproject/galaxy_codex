#!/usr/bin/env bash

mkdir -p 'results/'

if [ ! -z $1 ] 
then 
        if [ $1=="test" ]
        then 
                echo "Test tool extraction"
                python bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv "results/test_tools.tsv" \
                        --all "results/test_tools.json" \
                        --planemo-repository-list "test.list" \
                        --test
        else
                tsv_output="results/${1}_tools.tsv"
                json_output="results/${1}_tools.json"

                if [[ $1 =~ "01" ]]; then
                python bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv $tsv_output \
                        --all $json_output \
                        --planemo-repository-list $1
                else
                python bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv $tsv_output \
                        --all $json_output \
                        --planemo-repository-list $1 \
                        --avoid-extra-repositories
                fi
        fi
else
        echo "Tool extraction"
        python bin/extract_galaxy_tools.py \
                extract \
                --api $GITHUB_API_KEY \
                --all-tsv 'results/all_tools.tsv' \
                --all 'results/all_tools.json'
fi

