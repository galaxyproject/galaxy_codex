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
fi