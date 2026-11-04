#!/usr/bin/env bash

# Extract the date of the last manual curation of each community
# i.e. the last commit touching communities/<community>/metadata/
# Commits from the automatic weekly resource updates are ignored
# Needs the full git history (actions/checkout with fetch-depth: 0)

set -euo pipefail

last_update_file="communities/all/metadata/community_last_update.tsv"

{
    printf "Community\tLast curation\n"
    for community_dir in communities/*/; do
        community=$(basename "$community_dir")
        if [[ "$community" == "all" || ! -d "communities/$community/metadata" ]]; then
            continue
        fi
        last_update=$(git log -1 --format=%cs \
            --invert-grep \
            --grep="community resources update" \
            --grep="^Update resources" \
            -- "communities/$community/metadata/")
        if [[ -n "$last_update" ]]; then
            printf "%s\t%s\n" "$community" "$last_update"
        fi
    done
} > "$last_update_file"
