#!/usr/bin/env bash


for com_data_fp in data/communities/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                echo "$community";

                mkdir -p "results/$community"

                python bin/extract_galaxy_tools.py \
                        filtertools \
                        --tools "results/all_tools.tsv" \
                        --filtered-tools "results/$community/tools.tsv" \
                        --categories "data/communities/$community/categories" \
                        --exclude "data/communities/$community/tools_to_exclude" \
                        --keep "data/communities/$community/tools_to_keep"

                python bin/create_interactive_table.py \
                        --table "results/$community/tools.tsv" \
                        --template "data/interactive_table_template.html" \
                        --output "results/$community/index.html"

                python bin/create_wordcloud.py \
                        --table  "results/$community/tools.tsv" \
                        --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
                        --output "results/$community/tools_wordcloud.png" \
                        --stats_column "No. of tool users (2022-2023) (usegalaxy.eu)"

  fi;
done
