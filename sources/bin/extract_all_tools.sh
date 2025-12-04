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
                        --all-workflows "communities/all/resources/test_workflows.json" \
                        --all-yml 'communities/all/resources/test_tools.yml' \
                        --all-tutorials "communities/all/resources/test_tutorials.json" \
                        --planemo-repository-list "test.list" \
                        --test
        else
                tsv_output="communities/all/resources/${1}_tools.tsv"
                json_output="communities/all/resources/${1}_tools.json"
                yml_output="communities/all/resources/${1}_tools.yml"

                if [[ $1 =~ "01" ]]; then
                python sources/bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv $tsv_output \
                        --all $json_output \
                        --all-yml $yml_output \
                        --all-workflows "communities/all/resources/workflows.json" \
                        --all-tutorials "communities/all/resources/tutorials.json" \
                        --planemo-repository-list $1
                else
                python sources/bin/extract_galaxy_tools.py \
                        extract \
                        --api $GITHUB_API_KEY \
                        --all-tsv $tsv_output \
                        --all $json_output \
                        --all-yml $yml_output \
                        --all-workflows "communities/all/resources/workflows.json" \
                        --all-tutorials "communities/all/resources/tutorials.json" \
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
                --all 'communities/all/resources/tools.json' \
                --all-yml 'communities/all/resources/tools.yml' \
                --all-workflows "communities/all/resources/workflows.json" \
                --all-tutorials "communities/all/resources/tutorials.json" 

        ln -s "./../../communities/all/resources/tools.yml" "./website/_data/tools.yml"

fi

