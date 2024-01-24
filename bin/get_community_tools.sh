#!/usr/bin/env bash


for com_data_fp in data/* ; do
        if [[ -d "$com_data_fp" && ! -L "$com_data_fp" ]]; then
                community=`basename "$com_data_fp"`

                echo "$community";

                if [[ "$community" == *"microgalaxy"* ]]; then
                        curl \
                                -L \
                                "https://docs.google.com/spreadsheets/d/1Nq_g-CPc8t_eC4M1NAS9XFJDflA7yE3b9hfSg3zu9L4/export?format=tsv&gid=1533244711" \
                                -o "data/$community/tools_to_keep"

                        curl \
                                -L \
                                "https://docs.google.com/spreadsheets/d/1Nq_g-CPc8t_eC4M1NAS9XFJDflA7yE3b9hfSg3zu9L4/export?format=tsv&gid=672552331" \
                                -o "data/$community/tools_to_exclude"
                fi;


                mkdir -p "results/$community"

                python bin/extract_galaxy_tools.py \
                        filtertools \
                        --tools "results/all_tools.tsv" \
                        --filtered_tools "results/$community/tools.tsv" \
                        --categories "data/$community/categories" \
                        --exclude "data/$community/tools_to_exclude" \
                        --keep "data/$community/tools_to_keep"

                python bin/create_interactive_table.py \
                        --table "results/$community/tools.tsv" \
                        --template "data/interactive_table_template.html" \
                        --output "results/$community/index.html"

                python bin/create_wordcloud.py \
                        --table  "results/$community/tools.tsv" \
                        --wordcloud_mask "data/usage_stats/wordcloud_mask.png" \
                        --output "results/$community/tools_wordcloud.png" \
                        --stats_column "https://usegalaxy.eu usage"

  fi;
done
