#!/usr/bin/env bash

python bin/extract_galaxy_tools.py \
        --api $GITHUB_API_KEY \
        --output microgalaxy_tools.csv \
        --categories "data/microgalaxy/categories" \
        --excluded "data/microgalaxy/tools_to_exclude" \
        --keep "data/microgalaxy/tools_to_keep"