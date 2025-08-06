#!/usr/bin/env bash

python sources/bin/extract_gtn_tutorials.py \
  filter \
  --all "communities/all/resources/tutorials.json" \
  --filtered "communities/all/resources/tutorials.tsv"
  
python sources/bin/create_interactive_table.py \
  --input "communities/all/resources/tutorials.tsv" \
  --template "sources/data/interactive_table_template.html" \
  --output "communities/all/resources/tutorials.html"
