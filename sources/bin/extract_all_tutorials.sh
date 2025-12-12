#!/usr/bin/env bash

if [ ! -z $1 ] 
then
        python sources/bin/extract_gtn_tutorials.py \
                extract \
                --all "communities/all/resources/test_tutorials.json" \
                --tools "communities/all/resources/test_tools.json" \
                --api $PLAUSIBLE_API_KEY \
                --test
else
        python sources/bin/extract_gtn_tutorials.py \
                extract \
                --all "communities/all/resources/tutorials.json" \
                --tools "communities/all/resources/tools.json" \
                --api $PLAUSIBLE_API_KEY

        python sources/bin/extract_gtn_tutorials.py \
                filter \
                --all "communities/all/resources/tutorials.json" \
                --yml "communities/all/resources/tutorials.yml" \
                --filtered "communities/all/resources/tutorials.tsv"

        # ln -s "./../../communities/all/resources/tutorials.yml" "./_data/tutorials.yml"
  
        python sources/bin/create_interactive_table.py \
                --input "communities/all/resources/tutorials.tsv" \
                --template "sources/data/interactive_table_template.html" \
                --output "communities/all/resources/tutorials.html"          
fi


