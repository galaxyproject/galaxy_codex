#!/usr/bin/env bash

if [ ! -z $1 ] 
then 
        if [ $1 == "test" ]
        then 
                echo "Test tool extraction"
                python sources/bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv "communities/all/resources/test_tools.tsv" \
                        --all "communities/all/resources/test_tools.json" \
                        --planemo-repository-list "test.list" \
                        --test
        else
                tsv_output="communities/all/resources/${1}_tools.tsv"
                json_output="communities/all/resources/${1}_tools.json"

                if [[ $1 =~ "01" ]]; then
                python sources/bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv $tsv_output \
                        --all $json_output \
                        --planemo-repository-list $1
                else
                python sources/bin/extract_galaxy_tools.py \
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
        python sources/bin/extract_galaxy_tools.py \
                extract \
                --api $GITHUB_API_KEY \
                --all-tsv 'communities/all/resources/tools.tsv' \
                --all 'communities/all/resources/tools.json'
fi

