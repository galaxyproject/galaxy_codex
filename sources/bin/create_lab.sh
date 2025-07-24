#!/usr/bin/env bash

#This scirpt is meant to create the html pages to build a community lab on the public galaxy instances. 
#To launch this script, you need to do so manually from the GitHub action

#Copy the expected files from the template folder to your community folder
#Remember to check the files manually once they are in your community folder!

contributors="communities/$COMMUNITY/lab/CONTRIBUTORS"
if [[ ! -e $contributors ]]; then
   cp communities/all/labs/page_templates/CONTRIBUTORS $contributors
fi

readme="communities/$COMMUNITY/lab/README.md"
if [[ ! -e $readme ]]; then
   cp communities/all/labs/page_templates/README.md $readme
fi

base="communities/$COMMUNITY/lab/base.yml"
if [[ ! -e $base ]]; then
   cp communities/all/labs/page_templates/base.yml $base
fi

conclusion="communities/$COMMUNITY/lab/conclusion.html"
if [[ ! -e $conclusion ]]; then
   cp communities/all/labs/page_templates/conclusion.html $conclusion
fi

intro="communities/$COMMUNITY/lab/intro.html"
if [[ ! -e $intro ]]; then
   cp communities/all/labs/page_templates/intro.html $intro
fi
