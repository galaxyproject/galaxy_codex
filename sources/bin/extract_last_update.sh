#!/usr/bin/env bash

# This script is meant to extract the date of the last update to each community folder
# It will run automatically each time a change is made to a community folder

#COMMUNITY="biodiversity"
last_update_file="communities/all/community_last_update.tsv"

sed -i "/^$COMMUNITY\t/d" "$last_update_file"
echo -e "$COMMUNITY\t$(git log -1 --format=%cd -- communities/$COMMUNITY/)" >> $last_update_file